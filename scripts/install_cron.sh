#!/usr/bin/env bash
# Installs the Sovian crontab (adds the Saturday run that captures Friday's US
# close over the weekend — AEST machine, US close ~6am AEST Sat). Run this once;
# macOS may prompt for Terminal "Full Disk Access" the first time.
set -euo pipefail
cd "$(dirname "$0")/.."
crontab scripts/crontab.desired
echo "Installed. Active crontab:"
crontab -l | grep -v '^\s*#'
