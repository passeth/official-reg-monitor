#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/passeth/Documents/Codex/2026-07-04/new-chat/outputs/official-reg-monitoring-pipeline"
PLIST_NAME="com.codex.official-reg-monitor.plist"
SOURCE_PLIST="$ROOT/launchd/$PLIST_NAME"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"

mkdir -p "$ROOT/logs" "$HOME/Library/LaunchAgents"
cp "$SOURCE_PLIST" "$TARGET_PLIST"
cd "$ROOT"
launchctl unload "$TARGET_PLIST" >/dev/null 2>&1 || true
launchctl load "$TARGET_PLIST"
launchctl list | grep "com.codex.official-reg-monitor" || true
