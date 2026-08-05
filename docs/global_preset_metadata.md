# Global preset metadata

## Status

Validated with startup captures from the Matribox II Pro editor.

The global startup response reconstructs to an outer binary container:

- bytes `0..3`: signature `01 00 00 10`;
- bytes `4..7`: compressed LZO1X size as little-endian `uint32`;
- bytes `8..end`: compressed LZO1X stream.

After decompression, the payload is exactly 7,444 bytes:

| Region | Offset | Size |
|---|---:|---:|
| Internal header | 0 | 4 |
| 240 preset IDs | 4 | 960 |
| 240 preset names | 964 | 4,080 |
| 240 filter tags | 5,044 | 2,400 |
| End | 7,444 | — |

A preset name record is 17 bytes. A filter-tag record is 10 bytes.
Both are ASCII strings terminated by `00`.

Preset addressing uses:

```text
index = (bank - 1) * 4 + position
position: A=0, B=1, C=2, D=3
```

Validated examples:

```text
45A -> index 176
45B -> index 177
45C -> index 178
```

The fixture `data/fixtures/global_metadata/preset_metadata_45abc.bin`
contains the validated state:

```text
45A: name=Matribox II PRO, filter=JKLMNOPQR
45B: name=NOME123456789, filter=TAG45A123
45C: name=Matribox II PRO, filter=UVWXYZ789
```

## Stable API

```python
from tools.commands.global_preset_metadata import (
    decode_global_preset_metadata_file,
)

table = decode_global_preset_metadata_file(
    "path/to/capture_global.bin"
)

current = table.by_label("45B")

print(current.name)
print(current.filter_tag)
```

This module only reads a reconstructed binary block. It does not open MIDI
ports and does not send SysEx messages.
