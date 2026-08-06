# Fase 18 — validação física final do parser estrutural

Esta etapa valida ao vivo a integração das Fases 16 e 17 sem salvar o preset.

O script:

1. inicializa a sessão MIDI;
2. recarrega `56A -> 55D -> 56A`;
3. exige confirmação visual do estado salvo;
4. move a posição visual 5 para 4;
5. valida ordem, classe, modelo, seletor e bypass pelo parser estável;
6. retorna a posição visual 4 para 5;
7. valida novamente o estado original completo;
8. recarrega o preset 56A ao final;
9. gera um ZIP com as duas capturas e o relatório.

Comando:

```powershell
python -m tools.experiments.validate_structural_chain_live
```

O editor oficial deve permanecer fechado. Não salve o preset durante o teste.

Resultado esperado:

```text
Capturas: 2 / 2
Status: APROVADO
```

Antes do teste físico, a suíte pode ser confirmada com:

```powershell
python -m unittest discover -s tests -p "test_validate_structural_chain_live.py" -v
python -m unittest discover -s tests -p "test_*.py"
```

Nenhum commit deve ser feito antes da aprovação física.
