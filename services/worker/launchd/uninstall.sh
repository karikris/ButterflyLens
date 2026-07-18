#!/bin/sh
set -eu

if [ "$(uname -s)" != "Darwin" ]; then
  echo "ButterflyLens launchd uninstallation requires macOS." >&2
  exit 1
fi

account_name=$(id -un)
user_home_directory=$(/usr/bin/dscl . -read "/Users/${account_name}" NFSHomeDirectory | /usr/bin/awk '{print $2}')
plist_path="${user_home_directory}/Library/LaunchAgents/com.karikris.butterflylens.worker.plist"
domain="gui/$(id -u)"

if [ -e "${plist_path}" ]; then
  /bin/launchctl bootout "${domain}" "${plist_path}" >/dev/null 2>&1 || true
  /bin/rm -f -- "${plist_path}"
fi
echo "Uninstalled com.karikris.butterflylens.worker"
echo "Worker state, non-secret configuration, and logs were retained."
