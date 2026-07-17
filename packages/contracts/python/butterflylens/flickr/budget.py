"""One-key, all-method Flickr hourly reservation and settlement ledger."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Literal


FLICKR_BUDGET_SCHEMA_VERSION = "butterflylens-flickr-hourly-budget:v1.0.0"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUEST_ID = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,159}$")
Lane = Literal["normal", "reserve"]
Outcome = Literal["consumed", "not_sent", "uncertain"]


class BudgetDecisionError(ValueError):
    """Raised when a request would weaken the global budget boundary."""


@dataclass(frozen=True)
class HourlyBudgetPolicy:
    provider_ceiling: int = 3600
    envelope: int = 3500
    normal_maximum: int = 3000
    reserve_maximum: int = 500
    hard_safety_remainder: int = 100
    reserve_purposes: frozenset[str] = frozenset(
        {"retry", "comment", "manual", "judge", "accounting_reconciliation"}
    )

    def validate(self) -> None:
        if self.provider_ceiling - self.envelope != self.hard_safety_remainder:
            raise BudgetDecisionError("provider ceiling does not preserve safety remainder")
        if self.normal_maximum + self.reserve_maximum != self.envelope:
            raise BudgetDecisionError("lane maxima do not equal the hourly envelope")
        if min(
            self.provider_ceiling,
            self.envelope,
            self.normal_maximum,
            self.reserve_maximum,
            self.hard_safety_remainder,
        ) <= 0:
            raise BudgetDecisionError("budget values must be positive")


@dataclass(frozen=True)
class Reservation:
    request_id: str
    method: str
    purpose: str
    lane: Lane
    reserved_at: datetime
    outcome: Outcome | None = None


class FlickrHourlyBudget:
    """In-memory domain model for a durably serialized, fenced UTC ledger."""

    def __init__(
        self,
        *,
        project_id: str,
        credential_fingerprint: str,
        window_start: datetime,
        policy: HourlyBudgetPolicy | None = None,
    ) -> None:
        self.policy = policy or HourlyBudgetPolicy()
        self.policy.validate()
        if _REQUEST_ID.fullmatch(project_id) is None:
            raise BudgetDecisionError("invalid project_id")
        if _SHA256.fullmatch(credential_fingerprint) is None:
            raise BudgetDecisionError("credential fingerprint must be lowercase SHA-256")
        if window_start.tzinfo != timezone.utc or any(
            (window_start.minute, window_start.second, window_start.microsecond)
        ):
            raise BudgetDecisionError("window_start must be an exact UTC clock hour")
        self.project_id = project_id
        self.credential_fingerprint = credential_fingerprint
        self.window_start = window_start
        self.window_end = window_start + timedelta(hours=1)
        self._reservations: dict[str, Reservation] = {}
        self._frozen_reason: str | None = None

    @property
    def frozen(self) -> bool:
        return self._frozen_reason is not None

    @property
    def frozen_reason(self) -> str | None:
        return self._frozen_reason

    @property
    def normal_committed(self) -> int:
        return self._committed("normal")

    @property
    def reserve_committed(self) -> int:
        return self._committed("reserve")

    @property
    def total_committed(self) -> int:
        return self.normal_committed + self.reserve_committed

    @property
    def normal_remaining(self) -> int:
        return self.policy.normal_maximum - self.normal_committed

    @property
    def reserve_remaining(self) -> int:
        return self.policy.reserve_maximum - self.reserve_committed

    @property
    def envelope_remaining(self) -> int:
        return self.policy.envelope - self.total_committed

    def reserve(
        self,
        *,
        request_id: str,
        method: str,
        purpose: str,
        lane: Lane,
        credential_fingerprint: str,
        reserved_at: datetime,
    ) -> Reservation:
        if self.frozen:
            raise BudgetDecisionError("UTC budget window is frozen")
        if credential_fingerprint != self.credential_fingerprint:
            raise BudgetDecisionError("credential rotation or multi-key accounting is forbidden")
        if _REQUEST_ID.fullmatch(request_id) is None or request_id in self._reservations:
            raise BudgetDecisionError("request_id is invalid or duplicated")
        if not method.startswith("flickr.") or len(method) > 160:
            raise BudgetDecisionError("method must be an explicit Flickr method")
        if lane not in {"normal", "reserve"}:
            raise BudgetDecisionError("unknown budget lane")
        if lane == "reserve" and purpose not in self.policy.reserve_purposes:
            raise BudgetDecisionError("purpose is not eligible for reserve")
        if reserved_at.tzinfo != timezone.utc or not (
            self.window_start <= reserved_at < self.window_end
        ):
            raise BudgetDecisionError("reservation is outside its UTC clock hour")
        if self.envelope_remaining <= 0:
            raise BudgetDecisionError("hourly envelope exhausted")
        if lane == "normal" and self.normal_remaining <= 0:
            raise BudgetDecisionError("normal lane exhausted")
        if lane == "reserve" and self.reserve_remaining <= 0:
            raise BudgetDecisionError("reserve lane exhausted")
        reservation = Reservation(
            request_id=request_id,
            method=method,
            purpose=purpose,
            lane=lane,
            reserved_at=reserved_at,
        )
        self._reservations[request_id] = reservation
        return reservation

    def settle(self, request_id: str, outcome: Outcome) -> Reservation:
        try:
            reservation = self._reservations[request_id]
        except KeyError as error:
            raise BudgetDecisionError("unknown request reservation") from error
        if reservation.outcome is not None:
            raise BudgetDecisionError("request reservation is already settled")
        if outcome not in {"consumed", "not_sent", "uncertain"}:
            raise BudgetDecisionError("unknown settlement outcome")
        settled = Reservation(**{**reservation.__dict__, "outcome": outcome})
        self._reservations[request_id] = settled
        if outcome == "uncertain":
            self._frozen_reason = f"uncertain accounting for {request_id}"
        return settled

    def reservations(self) -> tuple[Reservation, ...]:
        return tuple(
            sorted(self._reservations.values(), key=lambda item: item.request_id)
        )

    def _committed(self, lane: Lane) -> int:
        return sum(
            reservation.lane == lane and reservation.outcome != "not_sent"
            for reservation in self._reservations.values()
        )
