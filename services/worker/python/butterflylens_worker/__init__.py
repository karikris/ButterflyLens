"""ButterflyLens persistent-worker runtime primitives."""

from .heartbeat import (
    HeartbeatError,
    HeartbeatSink,
    LeaseSnapshot,
    WorkerHeartbeatEmitter,
    collect_resources,
)
from .identity import (
    IdentityError,
    WorkerCapabilities,
    WorkerRegistration,
    build_worker_identity,
    load_or_create_registration,
    probe_machine_profile,
)
from .configuration import ConfigurationError, WorkerServiceConfiguration, load_environment_file
from .keychain import KeychainError, KeychainSecretProvider
from .local_sink import LocalJsonlHeartbeatSink, LocalSinkError

__all__ = [
    "HeartbeatError",
    "HeartbeatSink",
    "ConfigurationError",
    "IdentityError",
    "KeychainError",
    "KeychainSecretProvider",
    "LeaseSnapshot",
    "WorkerCapabilities",
    "WorkerHeartbeatEmitter",
    "WorkerRegistration",
    "WorkerServiceConfiguration",
    "build_worker_identity",
    "collect_resources",
    "load_environment_file",
    "LocalJsonlHeartbeatSink",
    "LocalSinkError",
    "load_or_create_registration",
    "probe_machine_profile",
]
