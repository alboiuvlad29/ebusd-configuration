# Handoff prompt: my fork of john30/ebusd-configuration (written 2026-10-03)

You're setting up and maintaining **my fork of https://github.com/john30/ebusd-configuration** (create it as `alboiuvlad29/ebusd-configuration` if it doesn't exist). Goal: replace the hand-edited CSV files my ebusd uses today with a reproducible build from TypeSpec, and send our findings upstream as small pull requests.

A separate agent works on my Home Assistant integration (`alboiuvlad29/ebusd-vaillant-component`); a Claude session inside my Home Assistant installs and tests whatever you produce. Don't change the integration repo.

## My devices (eBUS scan)
| Address | ebusd circuit / file | Device | SW / HW |
|---|---|---|---|
| 08 | `08.hmu.HW5103` | aroTHERM plus 5 kW (VWL 55/6 A 230V S2), HMU | 0902 / 5103 |
| 15 | `15.ctlv3` (built from `15.ctlv2.tsp`) | sensoCOMFORT VRC 720/3 | 0808 / 8004 |
| 26 | `26.vr_71` | VR 71 (FM5, config 3) | 0201 / 0503 |
| 35 | (none) | VR 92 remote | 0709 / 3904 |
| 76 | `76.vwzio` | VWZ AI appliance interface (**not** the HW5103 hydraulic station) | 0202 / 0103 |

## What ebusd loads today (files in `local/`)
- Base: ebus.github.io CDN snapshot 8f6e45a (2026-04-19), with `08.hmu.HW5103.csv` and `15.ctlv3.csv` replaced by a TypeSpec build of **PR #660** (ClausLDK, head b3fd23e — unchanged since; built from `15.ctlv2.tsp`, the file is named `15.ctlv3.csv`).
- Plus hand edits — see `local_vs_pr660_diff.txt` (ADDED / CHANGED / REMOVED per message):
  1. **Poll priorities** (`r1` ≈ 1 min essentials, `r5` ≈ 6 min, `r9` ≈ 14 min) on ~150 messages. These are my local tuning, **not upstream material**.
  2. **New messages (all verified on my devices — see evidence below):**
     - ctlv3 `HwcPreset` b524 `02 00 01 00 14 00` UCH 0=comfort;1=eco (read+write)
     - ctlv3 `HwcEcoTempDesired` reg 0x15 EXP °C; `HwcEcoChargeHyst` 0x16 EXP K; `HwcEcoMinTemp13h` 0x17 EXP °C; `HwcEcoMinTemp24h` 0x18 EXP °C (group 01, read+write; the controller flags them inactive while the preset is Comfort)
     - ctlv3 `GreenIQ` write line (b524 `02 01 00 00 9a 00`, read already upstream)
     - hmu `LastError` b503 `010100` and `FaultHistory1`–`9` b503 `0101 01..09`: `status UCH, time BTM, date BDA:3, error UIN, IGN:2` (upstream `Errorhistory` with an index field fails to decode; see also PR #662). **Never define `FaultHistory0`** — same ID as `LastError`; ebusd stops loading the rest of the file at a duplicate ID.
  3. **Fixes:** ctlv3 `MultiInputSetting` is **UIN without trailing IGN:3** (upstream UCH+IGN:3 fails: "invalid position in decode"). Values 0=not_connected;1=circulation;2=photovoltaic;3=external_cooling. `MultiRelaySetting` enum verified (4 = not_connected).
  4. **Read-only copies of installer-level hmu values:** `NoiseReductionLevel`, `HwcMode`, `CompHysteresisHeating`, `CompStartHeatingFrom`, `MaxRemainingDeltaP`, `BuildingCircuitPumpOutputHeating/Hwc`, `BlockTimeAfterRestart`, `ImmersionHeaterEnabled`, `EmergencyModeImmersionHeaterEnabled`, `EEVSteps`, `HMUSystemStarts`: the read line drops the `install` level so ebusd can poll them; the write line keeps `install`. Local only (upstream intentionally guards installer values).
  5. Three hmu messages removed because they always fail on my unit: `Status` (b511 03), `Status02` (b511 02), `Status16` (b504 16).
- ebusd add-on options (`ebusd_addon_options.json`): `--configpath=/config/ebusd-config/en`, `--pollinterval=2`, `--enablehex --enabledefine`, `--mqttvar=filter-name=…,filter-seen=1,filter-non-name=…` (the MQTT discovery filter — new message names must match `filter-name` to reach Home Assistant).
- Install today: the files live in `/share/ebusd-config/en/vaillant/`; `ebusd_install.sh` (run by me in the HA terminal) copies them into the add-on config folder; then ebusd is restarted.

## Evidence for the new registers (for upstream PR descriptions)
- **DHW preset:** toggled Comfort↔Eco on the panel while polling b524 group 01: reg 0x14 0→1 and back; regs 0x15–0x18 change flag byte 02 (inactive) → 03 (active) while Eco; reg 0x19 goes 4→0. Changing "Reduced DHW temperature" on the panel moved 0x15 40.0→41.0→40.0. The VRC 720/3 manual (0020334316_03) names the Eco-only settings: Reduced DHW temperature (factory 49 °C), Red. cyl. charging hysteresis (5 K), Min. temp. after 13 hrs (43 °C), Min. temp. after 24 hrs (40 °C) — values on my unit 40 / 10 / 43 / 40.
- **Green iQ:** reg 00.9A followed three panel toggles (Menu → Control → Green iQ), nothing else changed.
- **Fault history:** raw `hex 08b5030301010<n>` → `0a 02 41 18 18 09 26 16 00 00 00` = status 2, 18:41, 18.09.26, error 0x16 (F.22). Empty slots: `0a 01 00 00 00 00 00 ff ff 00 00`.
- **MultiInputSetting:** raw reply `06 03 00 6a 00 00 00` (2-byte value).
- Raw b524 reply format: `LL FF GG RR 00 <value>`, FF = 00 unused, 01 read-only, 02 inactive setting, 03 active/editable setting.

## Upstream PR survey (done 2026-10-03; all branches compiled with @typespec/compiler 1.16 + @ebusd/ebus-typespec 0.29 and compared by bus ID)
- Already covered by my set: #660, #678, #670, #671, #680, #607, #599, #606.
- **Adopt:** #659 `SystemDemand` (ctlv2, b524 020000004800 — reads `off`), driesenj fork `BuildingCircuitPressure` (hmu b514 052a03ffff — reads 2.3 bar), #604 `Hours`/`HoursHc`/`HoursHwc` (hmu b51a 05ff3240/41/44 — read 11837/5668/739 h).
- **Don't adopt:** #598 (written for the VWZ HW5103 hydraulic station; my VWZIO HW0103 times out), **#564** (renames ~73 messages my integration uses, e.g. Z1OpMode→Z1HeatingOpMode, Z1ManualTemp→Z1HeatingManualTemp, CurrentError→CurrentErrors, CylinderChargeHyst→HwcStorageChargeHyst, timers; lacks the preset registers). Track it: if it merges upstream, tell me early.
- Build note: `@ebusd/ebus-typespec` 0.29 needs `@typespec/compiler` ≥ ~1.13 (the pinned 1.12 fails with "does not provide an export named 'sanitizePathSegment'"); 1.16 works. Compile: `npx tsp compile --emit @ebusd/ebus-typespec src/main.tsp --output-dir out`.

## Tasks
1. **Fork + branch:** fork john30/ebusd-configuration; create branch `local` from upstream `master`. Merge/cherry-pick PR #660's HW5103 changes (b3fd23e) and the "Adopt" items above.
2. **Port our additions to TypeSpec** (items 2 and 3 above) in the right `.tsp` files (`15.ctlv2.tsp`, `08.hmu.HW5103.tsp`). Keep upstream naming conventions; add comments with the manual names.
3. **Local overlay for items 1, 4, 5** (poll priorities, read-only installer copies, removed messages): these aren't upstream material. Implement as a small, documented post-build step (e.g. a script + a YAML/CSV table of `message → priority`, `message → drop install level`, `message → remove`) that patches the compiled CSVs. Fail the build if two messages share a bus ID in a file.
4. **CI:** GitHub Actions on push to `local`: compile, apply the overlay, check, and publish the result as a release asset (zip of `en/vaillant/...`), plus `local_vs_upstream.txt`. Give the workflow `permissions: contents: write` (the integration repo's release job failed without it).
5. **Equivalence check:** the first build must reproduce my current `local/` files (same messages, IDs, types, priorities) — explain any difference. Only after that do I switch.
6. **Install path:** update `ebusd_install.sh` (copy in this folder) so it downloads the latest release asset into the ebusd add-on config folder (`/addon_configs/b4d7ad18_ebusd/ebusd-config/en`, run from the HA terminal), with a backup of the previous files and a clear OK/FAIL message. Keep the old "copy from /share" mode as a fallback.
7. **Upstream PRs to john30** (separate, small, TypeSpec, with the evidence above): (a) DHW preset + Eco settings for ctlv2/ctlv3, (b) GreenIQ write, (c) fault history BCD fix (coordinate with #662), (d) MultiInputSetting UIN fix. Draft them in my fork first and tell me before opening them.
8. **Maintenance doc** (`LOCAL.md` in the branch): how to rebase on upstream, add a PR, add a local overlay entry, release, and install.

## Return
- Fork URL, branch, first release with the zip, the equivalence report, the updated install script, and the drafted upstream PRs (links or patches).
- Anything that needs a decision from me.
