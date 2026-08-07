# Live preset monitor validation

## Status

The first physical validation confirmed the complete live path:

```text
240 presets loaded
18 global fragments reconstructed
current preset identified
name and filter tag resolved
spontaneous pedal changes received
```

A cold-start race was also reproduced. Immediately after powering the pedal,
one complete 185-byte fragment could be absent while the final 27-byte tail
still arrived:

```text
17 fragments
2,987 / 3,172 bytes
185 bytes missing
```

Running the monitor again with the pedal already warm completed normally.

## Recovery strategy

The live adapter now preserves the partial assembly and automatically resends
only the global metadata query when coverage stops advancing.

Repeated fragments are ignored by the collector. The missing fragment can
therefore complete the same assembly without discarding the bytes already
received.

Defaults:

```text
retry after 1.5 seconds without progress
maximum 3 global-query retries
startup timeout 12 seconds
```

## Physical validator

```powershell
python -m tools.experiments.validate_live_preset_monitor `
  --startup-timeout 30
```

Optional controls:

```powershell
--global-retry-interval 1.5
--global-query-retries 3
```

On a cold start, the terminal may show:

```text
Resposta global parou de avançar.
Reenviando consulta global: 1/3
```

The expected successful result remains:

```text
Metadados carregados: 240 presets
Fragmentos recebidos: 18
Preset atual: 39C
Nome: PaulGilbert
Etiqueta: -
```

After startup, preset changes made on the physical pedal must update the
terminal without another current-preset query.

## Main monitor output modes after Phase 35

The consolidated command keeps the historical append-only behavior by default:

```powershell
python -m tools.commands.matribox_monitor
```

A physically validated dashboard mode is also available:

```powershell
python -m tools.commands.matribox_monitor --live
```

`--live` uses the terminal alternate screen, redraws the complete frame, hides
progress messages that would corrupt the dashboard, and restores the normal
terminal when interrupted. It does not change any MIDI/SysEx behavior.

A compact event log can be written independently of the screen mode:

```powershell
python -m tools.commands.matribox_monitor --live --log data/dumps/monitor_live.txt
```

The final implementation was physically approved on Windows Terminal/PowerShell
after correcting stale characters from shorter frames. The complete suite has
428 passing tests at this milestone.
