# vaillant: make GreenIQ writable on the VRC 720 controller
Branch: `upstream-greeniq-write`. One line: `GreenIQ` (b524 reg 0x9a, group 00) gets the `w_1` write line (`020100009a00`, UCH 0=off;1=on).

Evidence: reg 00.9A followed three panel toggles (Menu → Control → Green iQ) and nothing else changed; the write line mirrors the
read (same type as the existing read). Open: I have only toggled it on the panel and read it back; the write itself still needs one test on the device before opening the PR.
