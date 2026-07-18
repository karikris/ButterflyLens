from __future__ import annotations

import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/contracts/python"))
sys.path.insert(0, str(ROOT / "services/worker/python"))
sys.path.insert(0, str(ROOT / "services/worker/launchd"))

from butterflylens_worker import (  # noqa: E402
    ConfigurationError,
    KeychainError,
    KeychainSecretProvider,
    LocalJsonlHeartbeatSink,
    load_environment_file,
)
from butterflylens_worker.service import run_service  # noqa: E402
from render_plist import PLACEHOLDERS, render  # noqa: E402


TEMPLATE = (
    ROOT
    / "services/worker/launchd/com.karikris.butterflylens.worker.plist.in"
)
INSTALL = ROOT / "services/worker/launchd/install.sh"
UNINSTALL = ROOT / "services/worker/launchd/uninstall.sh"


def write_environment(path: Path, extra: str = "") -> None:
    path.write_text(
        "\n".join(
            (
                "BUTTERFLYLENS_HEARTBEAT_SECONDS=30",
                "BUTTERFLYLENS_MAX_QUEUE_RECORDS=128",
                "BUTTERFLYLENS_MAX_QUEUE_BYTES=1048576",
                "BUTTERFLYLENS_PREFETCH_BATCHES=1",
                extra,
            )
        ),
        encoding="utf-8",
    )


class WorkerLaunchdServiceTests(unittest.TestCase):
    def test_environment_file_is_allowlisted_non_executable_and_non_secret(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "worker.env"
            write_environment(path)
            path.chmod(0o600)
            configuration = load_environment_file(path)
            self.assertEqual(configuration.heartbeat_seconds, 30)
            self.assertEqual(configuration.max_queue_records, 128)
            self.assertEqual(configuration.max_queue_bytes, 1048576)
            self.assertEqual(configuration.prefetch_batches, 1)
            for bad_line, message in (
                ("BUTTERFLYLENS_SECRET=value", "secrets are forbidden"),
                ("UNRECOGNIZED=value", "not allowlisted"),
                ("BUTTERFLYLENS_HEARTBEAT_SECONDS=$(touch nope)", "unsafe"),
                ("BUTTERFLYLENS_PREFETCH_BATCHES=9", "permitted range"),
            ):
                with self.subTest(line=bad_line):
                    path.write_text(bad_line + "\n", encoding="utf-8")
                    path.chmod(0o600)
                    with self.assertRaisesRegex(ConfigurationError, message):
                        load_environment_file(path)
            write_environment(path)
            path.chmod(0o644)
            with self.assertRaisesRegex(ConfigurationError, "permissions are too broad"):
                load_environment_file(path)

    def test_keychain_read_has_fixed_arguments_no_shell_or_secret_error(self) -> None:
        calls: list[tuple[object, dict[str, object]]] = []

        def runner(arguments: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append((arguments, kwargs))
            return subprocess.CompletedProcess(arguments, 0, "private-value\n", "")

        provider = KeychainSecretProvider(command_runner=runner)
        self.assertEqual(
            provider.read(service="com.karikris.butterflylens.flickr", account="worker"),
            "private-value",
        )
        self.assertEqual(
            calls[0][0],
            (
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                "com.karikris.butterflylens.flickr",
                "-a",
                "worker",
                "-w",
            ),
        )
        self.assertNotIn("shell", calls[0][1])

        def failed(*_: object, **__: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.CalledProcessError(44, "security", stderr="private-value")

        with self.assertRaises(KeychainError) as raised:
            KeychainSecretProvider(command_runner=failed).read(
                service="com.karikris.butterflylens.flickr", account="worker"
            )
        self.assertNotIn("private-value", str(raised.exception))

    def test_rendered_plist_has_absolute_paths_restart_policy_and_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            output = root / "LaunchAgents/com.karikris.butterflylens.worker.plist"
            values = {
                "PYTHON": root / "venv/bin/python",
                "ENVIRONMENT_FILE": root / "support/worker.env",
                "STATE_DIR": root / "support/state",
                "REPOSITORY": root / "repo",
                "PYTHONPATH": root / "repo/services/worker/python",
                "STDOUT_LOG": root / "logs/worker.stdout.log",
                "STDERR_LOG": root / "logs/worker.stderr.log",
            }
            self.assertEqual(set(values), set(PLACEHOLDERS))
            render(TEMPLATE, output, values)
            document = plistlib.loads(output.read_bytes())
            self.assertEqual(document["Label"], "com.karikris.butterflylens.worker")
            self.assertTrue(Path(document["Program"]).is_absolute())
            self.assertEqual(document["Program"], document["ProgramArguments"][0])
            self.assertEqual(document["KeepAlive"], {"SuccessfulExit": False})
            self.assertTrue(document["RunAtLoad"])
            self.assertEqual(document["ProcessType"], "Background")
            self.assertEqual(document["ThrottleInterval"], 30)
            self.assertEqual(document["ExitTimeOut"], 60)
            self.assertEqual(document["Umask"], "0077")
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
            self.assertNotIn("secret", repr(document).casefold())
            self.assertNotIn("api_key", repr(document).casefold())

    def test_local_sink_is_private_append_only_and_exactly_acknowledged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state/heartbeats.jsonl"
            sink = LocalJsonlHeartbeatSink(path)
            heartbeat = {
                "heartbeat_id": "blwh:v1:test",
                "heartbeat_fingerprint": "a" * 64,
                "sequence": 1,
            }
            acknowledgement = sink.append_heartbeat(heartbeat)
            sink.append_heartbeat({**heartbeat, "sequence": 2})
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual([row["sequence"] for row in rows], [1, 2])
            self.assertEqual(acknowledgement["storage_state"], "persisted")
            self.assertEqual(acknowledgement["heartbeat_fingerprint"], "a" * 64)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_once_service_emits_start_idle_and_clean_shutdown_without_models(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            environment = root / "worker.env"
            write_environment(environment)
            environment.chmod(0o600)
            self.assertEqual(
                run_service(
                    environment_file=environment,
                    state_dir=root / "state",
                    once=True,
                ),
                0,
            )
            records = [
                json.loads(line)
                for line in (root / "state/heartbeats.jsonl").read_text().splitlines()
            ]
        self.assertEqual([record["sequence"] for record in records], [1, 2, 3])
        self.assertEqual([record["state"] for record in records], ["starting", "idle", "draining"])
        self.assertTrue(all(record["models"] == [] for record in records))
        self.assertTrue(all(record["scientific_claim_allowed"] is False for record in records))

    def test_install_and_uninstall_are_modern_bounded_and_retain_state(self) -> None:
        subprocess.run(["sh", "-n", INSTALL, UNINSTALL], check=True)
        install_source = INSTALL.read_text(encoding="utf-8")
        uninstall_source = UNINSTALL.read_text(encoding="utf-8")
        for phrase in (
            "launchctl bootstrap",
            "launchctl bootout",
            "launchctl enable",
            "launchctl kickstart -k",
            "plutil -lint",
            "BUTTERFLYLENS_PYTHON",
        ):
            self.assertIn(phrase, install_source)
        self.assertNotIn("source ", install_source)
        self.assertNotIn("launchctl load", install_source)
        self.assertNotIn("launchctl unload", uninstall_source)
        self.assertIn("were retained", uninstall_source)
        for source in (install_source, uninstall_source):
            self.assertNotIn("rm -rf", source)
            self.assertNotIn("api_key", source.casefold())
            self.assertNotIn("password" + "=", source.casefold())
        self.assertTrue(os.access(INSTALL, os.X_OK))
        self.assertTrue(os.access(UNINSTALL, os.X_OK))

    def test_launchd_runtime_has_no_provider_or_model_execution(self) -> None:
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(
                (ROOT / "services/worker/python/butterflylens_worker").glob("*.py")
            )
        )
        for forbidden in (
            "flickr.photos",
            "from_pretrained",
            ".load_state_dict(",
            "import requests",
            "import httpx",
            "import aiohttp",
        ):
            self.assertNotIn(forbidden, sources)


if __name__ == "__main__":
    unittest.main()
