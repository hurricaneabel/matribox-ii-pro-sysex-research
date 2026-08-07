# Histórico das fases

Esta pasta reúne os relatórios detalhados das etapas consolidadas. O estado
atual e o próximo passo oficial permanecem em `docs/PROJECT_CONTINUITY.md`.

| Fase | Documento | Resultado principal |
|---:|---|---|
| 14 | `STRUCTURAL_CLASS_MODEL_PHASE14.md` | classe e modelo por slot |
| 15 | `STRUCTURAL_MODEL_SELECTOR_PHASE15.md` | modelo e seletor secundário |
| 16 | `STRUCTURAL_EFFECT_STATE_PHASE16.md` | contêiner LZO1X estrutural |
| 17 | `STRUCTURAL_CHAIN_INTEGRATION_PHASE17.md` | integração ao parser estável |
| 18 | `STRUCTURAL_CHAIN_LIVE_VALIDATION_PHASE18.md` | validação física estrutural |
| 19 | `MATRIBOX_MONITOR_PHASE19.md` | monitor consolidado e cold boot |
| 20 | `MATRIBOX_MONITOR_PHASE20.md` | leitura não destrutiva do dump |
| 21 | `MATRIBOX_MONITOR_PHASE21.md` | bypass em tempo real |
| 22 | `MBOOST_GAIN_VALIDATION_PHASE22.md` | M-BOOST/GAIN isolado e validado |
| 23A | `EFFECT_CATALOG_JSON_PHASE23A.md` | catálogo multiplataforma em JSON |
| 23B | `EFFECT_PARAMETER_ENGINE_PHASE23B.md` | motor genérico de parâmetros |
| 24 | `DYN_COMP1_PARAMETERS_PHASE24.md` | COMP1 com SUSTAIN/VOLUME e resolução pelo contexto da cadeia |
| 25 | `DYN_EBOOST_PARAMETERS_PHASE25.md` | E-BOOST com GAIN e booleanos +3dB/BRIGHT |
| 26 | `DYN_AC_WOODY_GATE1_PARAMETERS_PHASE26.md` | AC WOODY/SHAPE e GATE 1/THRESHOLD |
| 27 | `DYN_COMP2_PARAMETERS_PHASE27.md` | COMP2 com SUSTAIN/ATTACK/VOLUME/CLIPPING |
| 28 | `DYN_COMP3_PARAMETERS_PHASE28.md` | COMP3 com THRESHOLD/RATIO/VOLUME/ATTACK/RELEASE/TONE/BLEND |
| 29 | `DYN_AC_BB_BOOST_PARAMETERS_PHASE29.md` | AC-BOOST e BB-BOOST com GAIN/VOLUME/BASS/TREBLE |
| 30 | `DYN_RC_FAT_BOOST_GATE2_PARAMETERS_PHASE30.md` | RC-BOOST, FAT BOOST e GATE 2 |
| 31 | `DYN_AC_SIM_ENUM_PARAMETERS_PHASE31.md` | AC SIM com BODY/TOP/VOLUME e MODE enum nomeado |
| 32 | `DYN_GATE3_TIME_PARAMETERS_PHASE32.md` | GATE 3 com float32 completo e tempos adaptativos em ms/s |
| 33 | `FREQ_FILTER_PARAMETERS_PHASE33.md` | FILTER com RATE condicionado por SYNC e defaults implícitos derivados |
| 34 | `FREQ_OCTAVER_PARAMETERS_PHASE34.md` | OCTAVER com LOW OCT/HIGH OCT/DRY e validação dos slots 1 e 2 |
| 35 | `FREQ_DUAL_MELODY_SIGNED_PARAMETERS_PHASE35.md` | DUAL MELODY com primeiro intervalo assinado nativo em float32 |
| 35A | `MONITOR_LIVE_MODE_PHASE35A.md` | painel `--live` em buffer alternativo e `--log` compacto, sem alterar o protocolo |
| 36 | `PRESET_PARAMETER_HYDRATION_PHASE36.md` | hidratação inicial pelo dump `0x10` |
| 37 | `FREQ_PITCH_SAVED_PARAMETERS_PHASE37.md` | PITCH com cinco seletores consecutivos, LOW PITCH assinado e defaults salvos |
| 38 | `FREQ_HARMONY_D_ENUM_PARAMETERS_PHASE38.md` | HARMONY D com KEY, MODE, dois INTERVALS e lacuna física antes de SMOOTH |
