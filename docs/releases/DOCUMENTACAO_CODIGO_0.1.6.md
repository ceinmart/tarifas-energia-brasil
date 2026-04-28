<!--
Versao: 0.1.6
Criado em: 2026-04-28 00:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil
-->

# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.6  
Gerado em: 2026-04-28 00:00:00 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra o estado tecnico da release `0.1.6`. Alteracoes historicas completas ficam no `CHANGELOG.md`.

## Atualizacao 0.1.6

A versao `0.1.6` padroniza a nomenclatura da integracao para portugues nos elementos controlados pelo projeto e adiciona a apuracao de auto-consumo por quebra configurada.

## Nomenclatura

As quebras de calculo agora usam os valores:

- `diario`
- `semanal`
- `mensal`

As constantes, modelos e auxiliares internos foram renomeados para acompanhar esse padrao, reduzindo a mistura entre portugues e ingles no codigo proprio da integracao.

Termos exigidos por APIs externas permanecem no formato esperado pelo Home Assistant, Python, ANEEL ou bibliotecas usadas.

## Auto-consumo

As entidades acumuladas foram mantidas e renomeadas no nome amigavel:

- `auto_consumo_kwh`: Auto-consumo acumulado
- `auto_consumo_reais`: Auto-consumo acumulado em reais

Foram adicionadas entidades conforme as quebras habilitadas:

| Quebra | kWh | R$ |
|---|---|---|
| diario | `auto_consumo_diario_kwh` | `auto_consumo_diario_reais` |
| semanal | `auto_consumo_semanal_kwh` | `auto_consumo_semanal_reais` |
| mensal | `auto_consumo_mensal_kwh` | `auto_consumo_mensal_reais` |

Quando existe entidade de injecao configurada, o calculo por quebra usa:

```text
auto_consumo_periodo = max(geracao_periodo - injecao_periodo, 0)
```

Sem entidade de injecao, o valor segue como estimativa baseada na geracao do periodo e na energia creditada pelo SCEE.

## Impacto para usuarios

Esta release altera chaves tecnicas de entidades dinamicas que antes continham `daily`, `weekly` ou `monthly`. O Home Assistant pode criar novos `entity_id`s para essas entidades; dashboards e automacoes que dependam dos nomes antigos precisam ser revisados.

## Modulos afetados

| Modulo | Mudanca |
|---|---|
| `const.py` | Constantes de configuracao, grupos e quebras renomeadas para portugues. |
| `coordinator.py` | Chaves dinamicas de valores por periodo passam a usar `diario`, `semanal` e `mensal`; auto-consumo por quebra e calculado no resultado dinamico. |
| `sensor.py` | Descricoes de sensores usam `chave_valor` e publicam novas entidades de auto-consumo por quebra. |
| `config_flow.py` | Opcoes de quebra expostas como `diario`, `semanal` e `mensal`. |
| `models.py` | Modelos internos renomeados para portugues. |
| `README.md`, `docs/`, `DOCUMENTACAO_CODIGO_*` | Documentacao revisada para refletir a nova nomenclatura. |
| `tests/` | Cobertura atualizada para as chaves em portugues e novas entidades. |

## Testes

Validacao local usada na release:

```powershell
python -m pytest
python -m ruff check custom_components tests
python -m ruff format --check custom_components tests
git diff --check
```

Resultado esperado desta versao:

- suite completa com `78 passed`;
- lint sem erros;
- arquivos Python formatados;
- diff sem problemas de espacos.
