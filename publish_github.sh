#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: $0 <owner/repo> [public|private]" >&2
  exit 2
fi

REPO="$1"
VISIBILITY="${2:-private}"

if [[ "$VISIBILITY" != "public" && "$VISIBILITY" != "private" ]]; then
  echo "Visibility must be public or private." >&2
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI is not installed. Install gh first: https://cli.github.com/" >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated." >&2
  echo "Run: gh auth login -h github.com" >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Run this script from the repository root." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Working tree is not clean. Commit or stash changes before publishing." >&2
  exit 1
fi

if gh repo view "$REPO" >/dev/null 2>&1; then
  echo "Repository exists: $REPO"
else
  gh repo create "$REPO" "--$VISIBILITY" --source=. --remote=origin --push
  echo "Published: https://github.com/$REPO"
  exit 0
fi

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "git@github.com:$REPO.git"
else
  git remote add origin "git@github.com:$REPO.git"
fi

git push -u origin main
echo "Published: https://github.com/$REPO"
