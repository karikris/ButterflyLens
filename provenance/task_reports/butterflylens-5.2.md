# ButterflyLens 5.2 — persistent macOS development runner

Status: implementation and task gates complete; task commit and non-force main
push follow this report.

Starting SHA and remote SHA: `6258bc2c18faf7d7cecf3d0e39601cd928390b34`.
The ending commit and verified push SHA are recorded in the next append-only
commit receipt because a commit cannot contain its own SHA.

The worker now has a per-user development LaunchAgent template and renderer,
modern install/uninstall scripts, a foreground signal-aware service loop, a
private append-only local heartbeat sink, strict non-secret configuration, and
an on-demand macOS Keychain adapter. Crash exits restart after launchd
throttling; a clean graceful exit stays stopped. Uninstall removes only the
exact rendered plist and retains configuration, state, and logs.

The service was not installed or executed through launchd because this build
environment is Linux/WSL. The plist was parsed and behaviorally inspected with
Python `plistlib`; the scripts passed POSIX shell syntax tests. Current Apple
documentation and Xcode launchd/launchctl manual content informed the design.

YOLOE and BioCLIP remain explicitly unfinished and are not configured, loaded,
or executed. The development service emits operational heartbeats only. It has
no Flickr/provider transport and makes no API call. Keychain access is
implemented as an unused future boundary; the current service requests no
secret.

The checked-in LaunchAgent is intentionally an unsigned development tool. A
distributed production helper still requires a signed/notarized app-bundle
Service Management path.

Focused verification covers environment allowlisting and permission checks,
fixed-argument shell-free Keychain reads, rendered plist fields and permissions,
append-only local persistence, start/idle/draining smoke lifecycle, modern
bounded install/uninstall behavior, and absence of provider/model execution.

Scientific claims allowed: none beyond directly observed operational heartbeat
facts. Worker health does not establish model readiness, evidence maturity,
provider acquisition, quality, or release readiness.

Next safe task: 5.3, bounded media flow without Flickr calls. Task 5.4 must be
marked unfinished and skipped under the user's explicit YOLOE/BioCLIP direction.
