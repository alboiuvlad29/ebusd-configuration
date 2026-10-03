# vaillant: add fixed-ID fault history (LastError, FaultHistory1-9) for HMU HW5103
Branch: `upstream-faulthistory`. **Coordinate with #662** (BCD fix for the shared `errorhistory` model): once #662 is merged the
index-appended `Errorhistory` decodes too; this PR is then only useful as fixed-ID entries (one message per slot, easier for MQTT/HA). Consider rebasing/dropping after #662.

Evidence (`MF=Vaillant;ID=HMU00;SW=0902;HW=5103`): raw `hex 08b5030301010<n>` → `0a 02 41 18 18 09 26 16 00 00 00` =
status 2, 18:41, 18.09.26, error 0x16 (F.22). Empty slot: `0a 01 00 00 00 00 00 ff ff 00 00`. Time and date are BCD (`BTM`, `BDA:3`),
followed by 2 unused bytes. Entry 0 is `LastError` (b503 `010100`), entries 1–9 are `FaultHistory1..9` (`010101`..`010109`).
Never define a `FaultHistory0`: it would share the ID with `LastError`, and ebusd stops loading the file at a duplicate ID.
