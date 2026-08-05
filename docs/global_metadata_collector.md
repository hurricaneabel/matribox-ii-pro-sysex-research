# Global metadata fragment collector

## Status

The fragment layout was extracted from startup captures made with USBPcap.
The stable collector operates on complete SysEx messages already received
from the Matribox II Pro.

It does not open MIDI ports and does not send any command.

## Fragment layout

```text
bytes 0..4    F0 21 25 4D 50
byte 8        incoming direction 00
bytes 9..10   total decoded size, base 128
bytes 11..12  decoded offset, base 128
bytes 13..-2  payload encoded as nibble pairs
last byte     F7
```

A decoded payload byte is reconstructed as:

```text
byte = (high_nibble << 4) | low_nibble
```

The validated global fixture has 3,172 bytes. With the observed payload
capacity of 185 decoded bytes per message, it is reconstructed from exactly
18 fragments.

## Safety and consistency

The collector:

- rejects malformed SysEx and invalid nibbles;
- ignores small blocks that are not global metadata candidates;
- accepts repeated identical fragments;
- detects conflicting overlaps;
- tracks coverage and missing ranges;
- accepts out-of-order fragments;
- validates the external container signature and declared compressed size;
- returns the raw LZO1X container only after complete reconstruction.

## Stable API

```python
from tools.commands.global_metadata_collector import (
    GlobalMetadataCollector,
)
from tools.commands.global_preset_metadata import (
    decode_global_preset_metadata,
)

collector = GlobalMetadataCollector()

for sysex_bytes in received_messages:
    update = collector.feed(sysex_bytes)

    if update.global_block is not None:
        metadata = decode_global_preset_metadata(
            update.global_block
        )
        break
```

The next live layer will pass `message.bin()` from the MIDI input into this
collector and combine the decoded table with the preset events from
`preset_state.py`.
