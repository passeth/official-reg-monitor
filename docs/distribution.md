# Distribution

## Local Git Release

```bash
git init
git add .
git commit -m "Initial official regulation monitor"
```

## Build Wheel

```bash
python3 -m pip wheel . --no-deps --no-build-isolation -w dist
```

The generated wheel can be installed with:

```bash
python3 -m pip install dist/official_reg_monitor-0.1.0-py3-none-any.whl
```

## macOS Schedule

From a cloned checkout:

```bash
./install_launchd.sh
```

The installer renders `launchd/com.codex.official-reg-monitor.plist` with the current checkout path, then installs it into `~/Library/LaunchAgents`.

## Publish To GitHub

Option A, use the helper:

```bash
gh auth login -h github.com
./publish_github.sh <owner/repo> private
```

Option B, manual remote:

```bash
git remote add origin git@github.com:<owner>/official-reg-monitor.git
git branch -M main
git push -u origin main
```

## Versioning

Use semantic versioning:

- Patch: parser bug fixes, registry URL correction.
- Minor: new source parser or normalized table support.
- Major: schema contract changes.
