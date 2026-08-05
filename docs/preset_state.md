# Preset state protocol

## Status

Validated with physical Matribox II Pro captures.

The current preset is represented by an absolute index:

```text
index = (bank - 1) * 4 + position
position: A=0, B=1, C=2, D=3
```

Examples:

```text
01A -> 0
44B -> 173
45A -> 176
45B -> 177
45C -> 178
45D -> 179
46A -> 180
46B -> 181
60D -> 239
```

## Query current preset

The official editor sends a 46-byte SysEx command:

```text
command   = 0x10
direction = 0x11
checksum  = 0x1E
```

The response is a standard incoming preset event using command `0x14`.

## Select preset

Selection uses a 54-byte SysEx command:

```text
command   = 0x14
direction = 0x12
address   = bytes 39 and 40
```

The address is the absolute preset index split into two nibbles.

Validated selection checksums:

```text
01A -> 0x26
44B -> 0x3D
45A -> 0x31
45B -> 0x32
45C -> 0x33
45D -> 0x34
46A -> 0x35
46B -> 0x36
```

## Incoming events

Incoming confirmations and spontaneous pedal changes use:

```text
command   = 0x14
direction = 0x00
address   = bytes 39 and 40
```

The parser does not reject an otherwise valid incoming event only because
its received checksum differs. Two physically observed 45B confirmations
had the same structure and address but checksums `0x32` and `0x53`.

## Stable API

```python
from tools.commands.preset_state import (
    build_current_preset_query,
    build_select_preset,
    parse_preset_event,
)

query = build_current_preset_query()
select_45b = build_select_preset("45B")

event = parse_preset_event(received_sysex)

if event is not None:
    print(event.label)
    print(event.index)
```

This module only constructs and parses bytes. It does not open MIDI ports
or send commands by itself.
