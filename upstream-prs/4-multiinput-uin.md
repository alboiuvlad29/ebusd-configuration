# vaillant: fix MultiInputSetting to a 2-byte value
Branch: `upstream-multiinput-uin`. `MultiInputSetting` (b524 reg 0x6a, group 00) is `UIN` (2 bytes) without the trailing `IGN:3`.
Current definition (`UCH` + `IGN:3`) fails to decode: "invalid position in decode". Raw reply from a VRC 720/3: `06 03 00 6a 00 00 00`
→ after the 4-byte header the value is 2 bytes. Values 0=not_connected;1=circulation;2=photovoltaic;3=external_cooling unchanged.
