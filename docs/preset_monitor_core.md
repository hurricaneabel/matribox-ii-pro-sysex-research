# Preset monitor core

## Status

Offline orchestration layer validated against the existing global metadata
fixture and the stable protocol modules.

This layer does not open MIDI ports. It coordinates bytes already received
from the device.

## Responsibilities

The core combines:

```text
preset_state.py
    -> identifies the current absolute preset index

global_metadata_collector.py
    -> reconstructs the complete global LZO1X container

global_preset_metadata.py
    -> resolves the preset name and editable filter tag
```

It supports either arrival order:

```text
preset event first -> stored until metadata becomes available
metadata first     -> stored until a preset event becomes available
```

When both exist, it creates an enriched snapshot.

## Startup plan

The future MIDI adapter must perform:

```text
1. Send handshake four times.
2. Wait 0.2 second between handshakes.
3. Wait 0.5 second for session stabilization.
4. Send the global metadata query.
5. Send the current preset query.
6. Feed every incoming SysEx message into PresetMonitorCore.feed().
```

The global metadata query and current preset query are different 46-byte
command `0x10` packets:

```text
global metadata query: bytes 31..32 = 00 00, checksum 1D
current preset query:  bytes 31..32 = 00 01, checksum 1E
```

## Stable API

```python
from tools.commands.preset_monitor_core import (
    PresetMonitorCore,
    build_monitor_startup_plan,
    format_monitor_snapshot,
)

plan = build_monitor_startup_plan()
core = PresetMonitorCore()

for received_sysex in incoming_messages:
    update = core.feed(received_sysex)

    if update.snapshot_changed:
        print(
            format_monitor_snapshot(
                update.snapshot
            )
        )
```

Expected display after the physical adapter supplies the live messages:

```text
Preset atual: 45A
Nome: Matribox II PRO
Etiqueta: JKLMNOPQR
```

## Boundary

This commit deliberately stops before opening the Matribox MIDI ports.
The following integration will add the thin live adapter with timeouts,
handshake scheduling and terminal monitoring.
