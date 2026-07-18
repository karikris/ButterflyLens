"""Foreground development service suitable for a per-user launchd agent."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import signal
from threading import Event

from .configuration import load_environment_file
from .heartbeat import WorkerHeartbeatEmitter
from .identity import (
    WorkerCapabilities,
    build_worker_identity,
    load_or_create_registration,
    probe_machine_profile,
)
from .local_sink import LocalJsonlHeartbeatSink


def run_service(*, environment_file: Path, state_dir: Path, once: bool = False) -> int:
    """Run operational heartbeats only; no provider or model stage is executed."""

    configuration = load_environment_file(environment_file)
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    registration = load_or_create_registration(
        state_dir / "registration.json",
        now=datetime.now(timezone.utc),
    )
    identity = build_worker_identity(
        registration,
        machine_profile=probe_machine_profile(),
        capabilities=WorkerCapabilities(
            supported_stage_ids=("metadata",),
            max_queue_records=configuration.max_queue_records,
            max_queue_bytes=configuration.max_queue_bytes,
            rolling_prefetch_batches=configuration.prefetch_batches,
        ),
        configured_models=(),
    )
    sink = LocalJsonlHeartbeatSink(state_dir / "heartbeats.jsonl")
    emitter = WorkerHeartbeatEmitter(
        identity,
        free_disk_path=state_dir,
        sink=sink,
    )
    stop = Event()

    def request_shutdown(_signum: int, _frame: object) -> None:
        emitter.request_graceful_shutdown()
        stop.set()

    previous_term = signal.signal(signal.SIGTERM, request_shutdown)
    previous_int = signal.signal(signal.SIGINT, request_shutdown)
    try:
        emitter.emit(observed_at=datetime.now(timezone.utc))
        emitter.mark_idle()
        if once:
            emitter.emit(observed_at=datetime.now(timezone.utc))
            emitter.request_graceful_shutdown()
        else:
            while not stop.wait(configuration.heartbeat_seconds):
                emitter.emit(observed_at=datetime.now(timezone.utc))
        emitter.complete_graceful_shutdown(observed_at=datetime.now(timezone.utc))
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment-file", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--once", action="store_true", help="emit a finite local smoke lifecycle")
    arguments = parser.parse_args()
    return run_service(
        environment_file=arguments.environment_file,
        state_dir=arguments.state_dir,
        once=arguments.once,
    )


if __name__ == "__main__":
    raise SystemExit(main())
