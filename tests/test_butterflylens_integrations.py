from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "packages/openai/python"))
sys.path.insert(0, str(ROOT / "packages/verification/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))

from butterflylens.community import (  # noqa: E402
    ContributorIdentity,
    ContributionEvent,
    compile_contributor_impact,
)
from butterflylens.contracts.ala_contribution import (  # noqa: E402
    ALA_PROVIDER_CHECKS,
    AlaContributionRequest,
    AlaDatasetLicence,
    AlaDatasetMetadata,
    AlaProviderAgreementChecklist,
    AlaProviderCheck,
    AlaQualityDeclaration,
    build_ala_contribution_package,
)
from butterflylens.contracts.darwin_core_export import (  # noqa: E402
    DarwinCoreExportRequest,
    DarwinCoreMediaEvidence,
    DarwinCoreReleaseRecord,
    DarwinCoreTaxonEvidence,
    build_darwin_core_evidence_package,
)
from butterflylens.contracts.occurrence_release import (  # noqa: E402
    RELEASE_GATE_NAMES,
    ReleaseGateEvidence,
    plan_occurrence_release,
)
from butterflylens.flickr import (  # noqa: E402
    AustraliaLaneGate,
    FlickrHourlyBudget,
    SchedulingCandidate,
    SearchTransportResponse,
    allocate_schedule,
    build_logical_query_association,
    checkpoint_partition_count,
    compile_name_assertion,
    execute_search_page,
    plan_partition_pages,
    plan_physical_query_requests,
    score_candidate,
    seed_australia_state_partitions,
)
from butterflylens_openai import EvidenceToolbox, SubmittedEvidenceRepository  # noqa: E402
from butterflylens_verification import (  # noqa: E402
    AuditPlan,
    AuditRecord,
    ConsensusReview,
    ReleaseGates,
    ReliabilityDomain,
    SamplingStratum,
    calculate_layered_consensus,
    estimate_dataset_quality,
)
from butterflylens_verification.dataset_quality import (  # noqa: E402
    INCLUSION_PROBABILITY_METHOD,
)
from butterflylens_worker import (  # noqa: E402
    CommittedWorkJournal,
    MediaInput,
    MediaPipelinePolicy,
    UNFINISHED_MODEL_STAGES,
    WorkItem,
    available_state,
    build_classification_maturity,
    build_public_offline_projection,
    build_resume_plan,
    run_bounded_media_pipeline,
    unavailable_state,
    validate_classification_maturity,
)


NOW = datetime(2026, 7, 18, 12, 0, tzinfo=timezone.utc)
JPEG = b"\xff\xd8\xff\xe0" + b"butterflylens-integration-fixture" * 2


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


class MemoryStore:
    def __init__(self) -> None:
        self.receipts: list[dict[str, object]] = []

    def commit_file(
        self, *, artifact_kind: str, path: Path, content_sha256: str
    ) -> dict[str, object]:
        if file_sha256(path) != content_sha256:
            raise AssertionError("fixture store received bytes with the wrong checksum")
        receipt = {
            "storage_state": "persisted",
            "artifact_kind": artifact_kind,
            "content_sha256": content_sha256,
            "storage_version": f"memory:{len(self.receipts) + 1}",
        }
        self.receipts.append(deepcopy(receipt))
        return receipt


class ButterflyLensIntegrationTests(unittest.TestCase):
    def test_ala_pack_integrates_catalogue_map_and_pinned_artifacts(self) -> None:
        pack_root = ROOT / "data/packs/australian_butterflies/v1"
        pack_path = pack_root / "manifest.json"
        pack = json.loads(pack_path.read_text(encoding="utf-8"))
        catalogue = json.loads(
            (ROOT / "apps/web/src/species/submittedSpeciesCatalogue.json").read_text(
                encoding="utf-8"
            )
        )
        operations = json.loads(
            (ROOT / "apps/web/src/operations/submittedOperationsSnapshot.json").read_text(
                encoding="utf-8"
            )
        )
        ala_snapshot = json.loads(
            (pack_root / "ala/ala_snapshot_manifest.json").read_text(encoding="utf-8")
        )

        for relative_path, evidence in pack["artifacts"].items():
            self.assertEqual(
                file_sha256(pack_root / relative_path),
                evidence["physical_sha256"],
                relative_path,
            )
        self.assertEqual(catalogue["speciesCount"], 463)
        repository = SubmittedEvidenceRepository(ROOT)
        canonical_pack_fingerprint = file_sha256(pack_path)
        self.assertEqual(
            repository.citation("taxonomy_pack")["fingerprint"],
            f"sha256:{canonical_pack_fingerprint}",
        )
        self.assertRegex(
            catalogue["sourceFingerprints"]["packManifest"], r"^[0-9a-f]{64}$"
        )
        self.assertEqual(
            catalogue["sourceFingerprints"]["alaSnapshotManifest"],
            pack["artifacts"]["ala/ala_snapshot_manifest.json"]["physical_sha256"],
        )
        self.assertEqual(
            operations["map"]["releaseState"],
            ala_snapshot["rights"]["downstream_public_product_release_state"],
        )
        self.assertFalse(operations["map"]["occurrenceLayerVisible"])
        self.assertEqual(
            catalogue["states"]["alaOccurrenceEvidence"],
            "withheld_pending_dataset_rights_resolution",
        )
        self.assertFalse(catalogue["states"]["scientificClaimAllowed"])

        self.assertEqual(
            repository.citation("ala_snapshot")["fingerprint"],
            f"sha256:{file_sha256(pack_root / 'ala/ala_snapshot_manifest.json')}",
        )

    def test_flickr_scheduler_integrates_query_plan_budget_and_local_transport(self) -> None:
        assertions = [
            json.loads(line)
            for line in (
                ROOT / "data/packs/australian_butterflies/v1/name_assertions.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        ]
        source = next(
            row
            for row in assertions
            if row["taxon_rank"] == "species"
            and row["query_eligibility"]["eligible"]
        )
        definition = compile_name_assertion(source)
        association = build_logical_query_association(
            definition,
            associated_taxon_key=str(definition["source_taxon_key"]),
            relationship="accepted_name",
            query_lane="australia-known",
            association_reason="authoritative accepted species integration fixture",
        )
        query_plan = plan_physical_query_requests(
            [definition], [association], fixed_parameters={"safe_search": 1}
        )
        request = query_plan["physical_requests"][0]
        candidate = SchedulingCandidate(
            candidate_id=str(request["physical_query_request_id"]),
            partition_fingerprint=str(request["request_fingerprint"]),
            lane="australia_known",
            tier=1,
            unique_media_per_call=25.0,
            geotagged_media_per_call=20.0,
            butterfly_positive_yield=None,
            baseline_coverage_gap=0.8,
            species_coverage_need=0.7,
            review_capacity=0.5,
            reference_readiness=None,
            last_queried_at=None,
            unexplored_date_partition=True,
            calls_observed=0,
            consecutive_low_yield_windows=0,
        )
        scored = score_candidate(candidate, as_of=NOW)
        schedule = allocate_schedule(
            [candidate],
            as_of=NOW,
            normal_budget=1,
            australia_gate=AustraliaLaneGate(0.0, 0.0, 1),
        )
        self.assertEqual(schedule["execution_state"], "planned_not_sent")
        self.assertEqual(schedule["counts"]["scheduled_australia"], 1)
        self.assertEqual(
            scored["missing_components"],
            ["butterfly_positive_yield", "reference_readiness"],
        )

        scope = json.loads(
            (ROOT / "packages/flickr/australia_partition_scopes.json").read_text(
                encoding="utf-8"
            )
        )
        partition = seed_australia_state_partitions(
            request,
            scope,
            min_upload_date=1_700_000_000,
            max_upload_date=1_700_086_399,
        )[0]
        count = checkpoint_partition_count(
            partition, total=1, source_response_fingerprint=digest("local-count")
        )
        page = plan_partition_pages(partition, count)[0]
        credential = "synthetic-integration-credential-never-sent"
        credential_fingerprint = digest(credential)
        calls: list[dict[str, object]] = []

        def local_transport(**kwargs: object) -> SearchTransportResponse:
            calls.append(kwargs)
            parameters = kwargs["normalized_parameters"]
            assert isinstance(parameters, dict)
            self.assertNotIn("api_key", parameters)
            body = json.dumps(
                {
                    "stat": "ok",
                    "photos": {
                        "page": 1,
                        "pages": 1,
                        "perpage": 250,
                        "total": "1",
                        "photo": [{"id": "1001"}],
                    },
                },
                separators=(",", ":"),
            ).encode("utf-8")
            return SearchTransportResponse(200, body, NOW + timedelta(seconds=1))

        ledger = FlickrHourlyBudget(
            project_id="butterflylens-integration",
            credential_fingerprint=credential_fingerprint,
            window_start=NOW,
        )
        execution = execute_search_page(
            page,
            budget=ledger,
            credential=credential,
            credential_fingerprint=credential_fingerprint,
            reserved_at=NOW,
            transport=local_transport,
        )
        self.assertEqual(len(calls), 1)
        self.assertEqual(execution["execution_state"], "checkpointed")
        self.assertEqual(execution["completed_checkpoint"]["returned_count"], 1)
        self.assertEqual(ledger.normal_committed, 1)
        self.assertFalse(execution["credential_persisted"])
        self.assertNotIn(credential, repr({k: v for k, v in execution.items() if k != "response_body"}))

    def test_m5_worker_integrates_local_media_commit_restart_and_offline_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            media_path = root / "source.jpg"
            media_path.write_bytes(JPEG)
            store = MemoryStore()
            result = run_bounded_media_pipeline(
                [
                    MediaInput(
                        media_record_id="media:integration",
                        source_record_fingerprint=digest("source-record"),
                        local_path=media_path,
                        content_sha256=hashlib.sha256(JPEG).hexdigest(),
                        media_type="image/jpeg",
                        metadata={"provider": "local-fixture"},
                    )
                ],
                work_dir=root / "work",
                store=store,
                policy=MediaPipelinePolicy(
                    max_queue_records=2,
                    max_queue_bytes=4096,
                    parquet_batch_records=1,
                ),
            )
            work = WorkItem("artifact_commit", result["checkpoint_fingerprint"])
            journal = CommittedWorkJournal(root / "committed-work.jsonl")
            journal.record_commit(
                work,
                output_fingerprint=result["checkpoint_sha256"],
                committed_at=NOW,
                acknowledgement={
                    "storage_state": "persisted",
                    "output_fingerprint": result["checkpoint_sha256"],
                },
            )
            resume = build_resume_plan(
                [work],
                lease_fingerprint=digest("lease"),
                checkpoint_fingerprint=result["checkpoint_fingerprint"],
                journal=CommittedWorkJournal(journal.path),
            )

        submitted = {
            "snapshot_id": "submitted:integration",
            "mode": "submitted",
            "artifact_fingerprint": digest("submitted"),
            "query_uri": "/api/snapshots/submitted",
        }
        live = {
            "snapshot_id": "live:integration",
            "mode": "live",
            "artifact_fingerprint": result["checkpoint_fingerprint"],
            "query_uri": "/api/snapshots/live/integration",
        }
        projection = build_public_offline_projection(
            submitted_snapshot=submitted,
            committed_live_snapshot=live,
            heartbeat_observed_at=NOW - timedelta(minutes=30),
            as_of=NOW,
            stale_after=timedelta(minutes=5),
        )
        self.assertEqual(result["input_acquisition"], "caller_supplied_local_no_network")
        self.assertEqual(result["model_stage_status"], UNFINISHED_MODEL_STAGES)
        self.assertEqual(resume["reuse_count"], 1)
        self.assertEqual(resume["execute_count"], 0)
        self.assertEqual(projection["worker_status"], "offline")
        self.assertTrue(projection["site_available"])
        self.assertTrue(projection["committed_data_queryable"])
        self.assertEqual(projection["current_snapshot"], live)

    def test_model_flow_remains_unfinished_without_yoloe_or_bioclip_evidence(self) -> None:
        maturity = {
            "butterfly_detected": unavailable_state(
                "YOLOE is unfinished and was not run"
            ),
            "species_candidate_available": unavailable_state(
                "BioCLIP is unfinished and was not run"
            ),
            "community_reviewed": unavailable_state("human review is absent"),
            "quality_estimate_available": unavailable_state(
                "representative quality evidence is absent"
            ),
            "expert_reviewed": unavailable_state("expert review is absent"),
            "release_ready": available_state(
                False, evidence_fingerprints=[digest("blocked-release")]
            ),
        }
        projection = build_classification_maturity(
            image_id="media:model-integration",
            source_record_fingerprint=digest("model-source"),
            observed_at=NOW,
            maturity=maturity,
        )
        validate_classification_maturity(projection)
        self.assertEqual(UNFINISHED_MODEL_STAGES["yoloe"], "unfinished_not_run")
        self.assertEqual(UNFINISHED_MODEL_STAGES["bioclip"], "unfinished_not_run")
        self.assertIsNone(projection["maturity"]["butterfly_detected"]["value"])
        self.assertIsNone(
            projection["maturity"]["species_candidate_available"]["value"]
        )
        self.assertFalse(projection["maturity"]["release_ready"]["value"])
        self.assertFalse(projection["scientific_claim_allowed"])

    def test_review_flow_integrates_consensus_quality_and_contributor_impact(self) -> None:
        domain = ReliabilityDomain(
            family_taxon_key="family:papilionidae",
            source_provider="flickr",
            life_stage="adult",
            visual_domain="live_field",
        )
        reviews = [
            ConsensusReview(
                project_id="project:butterflylens",
                campaign_id="campaign:integration",
                item_id="item:integration",
                reviewer_id=f"reviewer:{index}",
                event_fingerprint=digest(f"review:{index}"),
                outcome="yes",
                qualified=True,
                reviewed_at=f"2026-07-18T12:0{index}:00Z",
            )
            for index in (1, 2)
        ]
        consensus = calculate_layered_consensus(
            consensus_id="consensus:integration",
            project_id="project:butterflylens",
            campaign_id="campaign:integration",
            item_id="item:integration",
            revision=1,
            required_review_count=2,
            events=reviews,
            domain=domain,
            reliability_snapshots={},
            adjudication=None,
            release_gates=ReleaseGates(),
        )
        audit_plan = AuditPlan(
            plan_id="plan:integration",
            audit_kind="representative_audit",
            design="stratified_random",
            representative=True,
            blind=True,
            inclusion_probability_method=INCLUSION_PROBABILITY_METHOD,
            sampling_frame_fingerprint=digest("sampling-frame"),
            grouping_keys=("owner_id", "observation_id"),
            strata=(
                SamplingStratum("stratum:north", "North", 50, 0.5),
                SamplingStratum("stratum:south", "South", 50, 0.5),
            ),
        )
        outcomes = (
            ("stratum:north", "supported"),
            ("stratum:north", "not_supported"),
            ("stratum:south", "supported"),
            ("stratum:south", "not_supported"),
        )
        audit_records = [
            AuditRecord(
                record_id=f"record:{index}",
                stratum_id=stratum,
                inclusion_probability=0.1,
                owner_group_id=f"owner:{index}",
                observation_group_id=f"observation:{index}",
                outcome=outcome,
                consensus_status="complete_agreement",
                review_fingerprint=reviews[(index - 1) % 2].event_fingerprint,
                consensus_fingerprint=str(consensus["consensus_fingerprint"]),
            )
            for index, (stratum, outcome) in enumerate(outcomes, start=1)
        ]
        quality = estimate_dataset_quality(
            quality_snapshot_id="quality:integration",
            project_id="project:butterflylens",
            run_id="run:integration",
            plan=audit_plan,
            records=audit_records,
            generated_at="2026-07-18T12:30:00Z",
            bootstrap_seed="integration-seed-without-credentials",
            bootstrap_replicates=200,
        )
        impact = compile_contributor_impact(
            [
                ContributionEvent(
                    event_fingerprint=reviews[0].event_fingerprint,
                    kind="review",
                    media_object_id="media:integration",
                    species_ids=("species:papilio-aegeus",),
                    region_ids=("region:nsw",),
                    control_fingerprint=digest("control"),
                    expert_eligible=False,
                )
            ],
            identity=ContributorIdentity(
                reviewer_profile_id="reviewer:1",
                project_id="project:butterflylens",
                role="reviewer",
                qualification_state="unverified",
            ),
            calculated_at=NOW,
        )
        self.assertEqual(consensus["status"], "complete_agreement")
        self.assertEqual(consensus["release_consensus"]["outcome"], "not_release_ready")
        self.assertEqual(quality["availability"], "estimated")
        self.assertEqual(quality["precision_estimate"], 0.5)
        self.assertFalse(quality["model_vote_included"])
        self.assertEqual(impact["reviewed_image_count"], 1)
        self.assertEqual(impact["species_helped_count"], 1)
        self.assertFalse(impact["ranking_permitted"])
        self.assertFalse(impact["scientific_claim_allowed"])

    def test_map_updates_require_release_and_location_evidence(self) -> None:
        gates = []
        for gate_name in RELEASE_GATE_NAMES:
            if gate_name == "rights_provenance":
                gates.append(
                    ReleaseGateEvidence(
                        gate_name=gate_name,
                        passed=False,
                        evidence_fingerprints=(),
                        blocker_code="dataset_rights_resolution_pending",
                    )
                )
            else:
                gates.append(
                    ReleaseGateEvidence(
                        gate_name=gate_name,
                        passed=True,
                        evidence_fingerprints=(digest(f"gate:{gate_name}"),),
                        blocker_code=None,
                    )
                )
        decision = plan_occurrence_release(gates)
        operations = json.loads(
            (ROOT / "apps/web/src/operations/submittedOperationsSnapshot.json").read_text(
                encoding="utf-8"
            )
        )
        release_sql = (
            ROOT / "supabase/migrations/20260718110000_occurrence_release_policy.sql"
        ).read_text(encoding="utf-8")
        self.assertEqual(decision.release_state, "blocked")
        self.assertFalse(decision.published_occurrence)
        self.assertFalse(decision.scientific_claim_allowed)
        self.assertFalse(operations["map"]["occurrenceLayerVisible"])
        self.assertIn(
            "private.has_publishable_location_receipt('release_candidate', id)",
            release_sql,
        )
        self.assertIn("private.has_occurrence_release_receipt(id)", release_sql)

    def test_gpt_tools_integrate_only_pinned_submitted_evidence(self) -> None:
        repository = SubmittedEvidenceRepository(ROOT)
        toolbox = EvidenceToolbox(ROOT)
        catalogue = repository.read_json("species_catalogue")
        species_key = catalogue["species"][0]["key"]
        species = toolbox.invoke(
            "inspect_species", {"species_key": species_key, "scientific_name": None}
        )
        map_scope = toolbox.invoke(
            "inspect_map_scope", {"scope_type": "national", "scope_id": None}
        )
        classification = toolbox.invoke(
            "explain_classification", {"classification_id": "classification:integration"}
        )
        pipeline = toolbox.invoke("inspect_pipeline_status", {"pipeline_id": None})

        def fact(result: dict[str, object], name: str) -> dict[str, object]:
            return next(row for row in result["facts"] if row["name"] == name)

        self.assertEqual(species["records"][0]["record_id"], species_key)
        self.assertEqual(fact(map_scope, "accepted_species")["value"], 463)
        self.assertEqual(fact(map_scope, "ala_occurrence_count")["state"], "observed")
        self.assertEqual(fact(map_scope, "ala_occurrence_count")["value"], 213_310)
        self.assertEqual(fact(classification, "yoloe_state")["state"], "unfinished")
        self.assertEqual(fact(classification, "bioclip_state")["state"], "unfinished")
        self.assertFalse(fact(classification, "probability_available")["value"])
        self.assertEqual(fact(pipeline, "snapshot_mode")["value"], "submitted")
        self.assertFalse(fact(pipeline, "live_state_claimed")["value"])

    def test_exports_integrate_release_receipts_dwc_and_ala_preparation(self) -> None:
        record = DarwinCoreReleaseRecord(
            occurrence_id="occurrence:integration",
            event_id="event:integration",
            location_id="location:integration",
            identification_id="identification:integration",
            release_candidate_id="candidate:integration",
            event_date="2026-02-03",
            public_cell_id="83be63fffffffff",
            information_withheld="Raw coordinates and reviewer identities withheld.",
            data_generalizations="Location generalized to the governed public H3 cell.",
            taxon=DarwinCoreTaxonEvidence(
                taxon_id="bltx:v1:papilio-aegeus",
                scientific_name="Papilio aegeus",
                taxon_rank="species",
                family="Papilionidae",
                genus="Papilio",
                taxon_concept_fingerprint=digest("taxon"),
            ),
            media=DarwinCoreMediaEvidence(
                media_id="media:export-integration",
                source_page_url="https://www.flickr.com/photos/example/123/",
                licence_url="https://creativecommons.org/licenses/by/4.0/",
                rights_holder="Fixture photographer",
                creator="Fixture photographer",
                attribution="Fixture photographer / Flickr / CC BY 4.0",
                media_fingerprint=digest("media"),
                rights_fingerprint=digest("rights"),
                title="Human-reviewed source image",
            ),
            candidate_fingerprint=digest("candidate"),
            release_receipt_fingerprint=digest("release-receipt"),
            location_receipt_fingerprint=digest("location-receipt"),
            coordinate_evidence_fingerprint=digest("coordinates"),
            date_evidence_fingerprint=digest("date"),
            duplicate_independence_fingerprint=digest("duplicate"),
            human_consensus_fingerprint=digest("human-consensus"),
            qualified_consensus_fingerprint=digest("qualified-consensus"),
            expert_gate_evidence_fingerprint=digest("expert-gate"),
            conflict_audit_fingerprint=digest("conflict-audit"),
            quality_snapshot_fingerprint=digest("quality"),
            quality_threshold_fingerprint=digest("quality-threshold"),
            evidence_packet_fingerprint=digest("evidence-packet"),
            rights_fingerprint=digest("rights"),
        )
        dwc = build_darwin_core_evidence_package(
            DarwinCoreExportRequest(
                package_id="butterflylens-dwc:integration-v1",
                dataset_id="butterflylens:integration",
                dataset_title="ButterflyLens integration evidence",
                created_at="2026-07-18T12:00:00Z",
                code_sha=digest("code"),
                records=(record,),
            )
        )
        checks = tuple(
            AlaProviderCheck(
                check_id=check_id,
                status="pending" if index == 0 else "passed",
                evidence_reference=None if index == 0 else f"urn:sha256:{digest(check_id)}",
                note="Provider agreement requires human execution." if index == 0 else None,
            )
            for index, check_id in enumerate(ALA_PROVIDER_CHECKS)
        )
        citation = "ButterflyLens contributors (2026). Integration evidence fixture."
        request = AlaContributionRequest(
            package_id="butterflylens-ala:integration-v1",
            prepared_at="2026-07-18T12:30:00Z",
            code_sha=digest("ala-code"),
            source_archive_sha256=dwc.archive_sha256,
            source_package_fingerprint=dwc.package_fingerprint,
            dataset=AlaDatasetMetadata(
                dataset_id="butterflylens:integration",
                title="ButterflyLens integration evidence",
                description="Release-gated Australian butterfly occurrence evidence.",
                purpose="Exercise deterministic offline contribution preparation.",
                geographic_scope="Australia; governed generalized cells only.",
                taxonomic_scope="Australian Papilionoidea in the authoritative baseline.",
                temporal_scope="2026",
                methods="Rights checks, human review, release receipts, and deterministic export.",
                creator_name="ButterflyLens contributors",
                creator_organisation="ButterflyLens",
                administrative_contact_name="Fixture Data Team",
                administrative_contact_email="data@example.invalid",
                provider_url="https://karikris.github.io/ButterflyLens/",
                citation=citation,
                keywords=("Australia", "ButterflyLens", "Papilionoidea"),
            ),
            licence=AlaDatasetLicence(
                identifier="CC-BY-4.0",
                url="https://creativecommons.org/licenses/by/4.0/",
                rights_holder="ButterflyLens contributors",
                rights_authority_fingerprint=digest("rights-authority"),
            ),
            provider_checklist=AlaProviderAgreementChecklist(checks=checks),
            quality=AlaQualityDeclaration(
                unresolved_blockers=(),
                limitations=(
                    "No provider acceptance or publication is implied.",
                    "This deterministic fixture is not a live biodiversity contribution.",
                ),
                representative_audit_reviewed=True,
            ),
            attribution_statement=(
                f"{citation} Dataset licence: https://creativecommons.org/licenses/by/4.0/. "
                "Record-specific media rights and attribution remain authoritative."
            ),
        )
        ala = build_ala_contribution_package(request, dwc.archive_bytes)
        with zipfile.ZipFile(io.BytesIO(ala.archive_bytes)) as archive:
            members = set(archive.namelist())
            manifest = json.loads(archive.read("ala-evidence-manifest.json"))
        self.assertTrue({"occurrence.txt", "eml.xml", "quality-report.json"} <= members)
        self.assertEqual(ala.preparation_state, "blocked_pending_provider_requirements")
        self.assertEqual(manifest["provider_submission_state"], "not_submitted")
        self.assertTrue(manifest["human_submission_required"])
        self.assertFalse(manifest["automatic_submission_available"])
        self.assertEqual(manifest["publication_state"], "prepared_not_published")


if __name__ == "__main__":
    unittest.main()
