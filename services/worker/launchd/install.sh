#!/bin/sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
  echo "ButterflyLens launchd installation requires macOS." >&2
  exit 1
fi

script_directory=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repository_directory=$(CDPATH= cd -- "${script_directory}/../../.." && pwd)
account_name=$(id -un)
user_home_directory=$(/usr/bin/dscl . -read "/Users/${account_name}" NFSHomeDirectory | /usr/bin/awk '{print $2}')
launch_agents_directory="${user_home_directory}/Library/LaunchAgents"
support_directory="${user_home_directory}/Library/Application Support/ButterflyLens/worker"
log_directory="${user_home_directory}/Library/Logs/ButterflyLens"
plist_path="${launch_agents_directory}/com.karikris.butterflylens.worker.plist"
environment_path="${support_directory}/worker.env"
state_directory="${support_directory}/state"
python_executable=${BUTTERFLYLENS_PYTHON:-"${repository_directory}/.venv/bin/python"}

if [ ! -x "${python_executable}" ]; then
  echo "Python is not executable: ${python_executable}" >&2
  echo "Set BUTTERFLYLENS_PYTHON to the pinned worker interpreter." >&2
  exit 1
fi

/bin/mkdir -p "${launch_agents_directory}" "${support_directory}" "${state_directory}" "${log_directory}"
/bin/chmod 700 "${launch_agents_directory}" "${support_directory}" "${state_directory}" "${log_directory}"
if [ ! -e "${environment_path}" ]; then
  /usr/bin/install -m 600 /dev/null "${environment_path}"
  /usr/bin/printf '%s\n' \
    'BUTTERFLYLENS_HEARTBEAT_SECONDS=30' \
    'BUTTERFLYLENS_MAX_QUEUE_RECORDS=512' \
    'BUTTERFLYLENS_MAX_QUEUE_BYTES=2147483648' \
    'BUTTERFLYLENS_PREFETCH_BATCHES=2' > "${environment_path}"
fi
/bin/chmod 600 "${environment_path}"

"${python_executable}" "${script_directory}/render_plist.py" \
  --template "${script_directory}/com.karikris.butterflylens.worker.plist.in" \
  --output "${plist_path}" \
  --python "${python_executable}" \
  --environment-file "${environment_path}" \
  --state-dir "${state_directory}" \
  --repository "${repository_directory}" \
  --pythonpath "${repository_directory}/services/worker/python:${repository_directory}/packages/contracts/python" \
  --stdout-log "${log_directory}/worker.stdout.log" \
  --stderr-log "${log_directory}/worker.stderr.log"

/usr/bin/plutil -lint "${plist_path}"
domain="gui/$(id -u)"
/bin/launchctl bootout "${domain}" "${plist_path}" >/dev/null 2>&1 || true
/bin/launchctl bootstrap "${domain}" "${plist_path}"
/bin/launchctl enable "${domain}/com.karikris.butterflylens.worker"
/bin/launchctl kickstart -k "${domain}/com.karikris.butterflylens.worker"
echo "Installed com.karikris.butterflylens.worker"
echo "Logs: ${log_directory}"
echo "Non-secret configuration: ${environment_path}"
