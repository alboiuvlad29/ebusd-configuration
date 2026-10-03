# LOCAL.md: the `local` branch of this fork

`local` = upstream `master` + adopted upstream PRs (#660, #659, #604 partly, driesenj's `BuildingCircuitPressure`)
+ our TypeSpec additions + a post-build **overlay** (`overlay/`) that is not upstream material.
Every push to `local` builds and publishes a release (`.github/workflows/local-release.yml`).
Background and device list: `overlay/HANDOFF.md`. First-build comparison: `overlay/EQUIVALENCE.md`.

## Build locally
Needs node >= 20 (`nvm use 22`) and python3.
```bash
./overlay/build.sh      # -> dist/ebusd-config-local.{zip,tar.gz}, dist/local_vs_upstream.txt, dist/local/en/...
```
Steps: `tsp compile` → resolve src symlinks (e.g. `15.ctlv3` = `15.ctlv2`) → overlay → duplicate-ID check
(build fails if two messages in one file share a bus ID) → comparison with `upstream/master` → archives.

## Rebase on upstream
```bash
git fetch upstream
git merge upstream/master            # or: git rebase upstream/master
./overlay/build.sh                   # overlay entries whose message vanished/was renamed fail the build: fix the table
```
If upstream merged one of our PRs, drop the local copy of the models during the merge (keep upstream's).
Watch upstream PR #564 (renames ~73 messages the integration uses): tell the maintainer of the integration if it merges.

## Add an upstream PR
```bash
git fetch upstream pull/<N>/head:pr<N>
git merge --no-ff pr<N> -m "Merge upstream PR #<N>"
./overlay/build.sh && python3 overlay/localbuild.py compare dist/base dist/upstream | less   # review what came in
```
Remove messages you do not want (and note it in a comment) instead of taking a whole PR blindly.

## Overlay entries (`overlay/*.csv`, `#` lines are comments)
- `priorities.csv`: `file,message,priority` (1-9) → read line becomes `r<priority>`; applies to the read line only.
- `readonly_copies.csv`: `file,message` → read line loses level `install` (write line keeps it).
- `remove.csv`: `file,message` → all lines of the message are dropped (warning only if already absent).
`file` is the output name, e.g. `15.ctlv3.csv`. Unknown message in priorities/readonly = build error.
Do not define two messages with the same ID (e.g. never a `FaultHistory0` next to `LastError`).

## Release and install
Push to `local` → workflow creates release `local-<date>-<sha>` with `ebusd-config-local.zip`, `.tar.gz` and `local_vs_upstream.txt`.
In the Home Assistant terminal:
```bash
curl -fsSL https://raw.githubusercontent.com/alboiuvlad29/ebusd-configuration/local/ebusd_install.sh | sh        # latest release
sh ebusd_install.sh share          # fallback: copy from /share/ebusd-config/en
```
(or copy `ebusd_install.sh` to `/homeassistant/` and run `sh /homeassistant/ebusd_install.sh`). It backs up the old files to
`ebusd-config-backup/en.<time>` and prints `OK:` / `FAILED:`. Restart the eBUSd add-on afterwards.
Add-on options (unchanged): `--configpath=/config/ebusd-config/en`, `--pollinterval=2`, `--enablehex --enabledefine`, `--mqttvar=filter-name=…`
(new message names must match `filter-name` to reach Home Assistant; see `overlay/ebusd_addon_options.json`).

## Upstream PR drafts
`upstream-prs/*.md` + branches `upstream-hwc-preset`, `-greeniq-write`, `-faulthistory`, `-multiinput-uin` (each on upstream master). Not opened yet.
