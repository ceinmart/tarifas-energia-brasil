# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.1  
Gerado em: 2026-04-27 14:45:00 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra o estado tecnico da release `0.1.1`. Alteracoes historicas completas ficam no `CHANGELOG.md`.

## Atualizacao 0.1.1

A versao `0.1.1` ajusta regras de ICMS e SCEE:

- a selecao da faixa de ICMS passa a considerar a disponibilidade minima faturavel (`30/50/100 kWh`) quando ela for maior que o consumo mensal apurado;
- a previsao de creditos SCEE passa a separar credito de disponibilidade e credito de energia;
- o README passa a documentar melhor origem e formula resumida das entidades.

## ICMS

O ICMS efetivamente aplicado e resolvido com base no consumo mensal faturavel. Quando o consumo mensal apurado ainda esta abaixo da disponibilidade minima, a base para faixa de ICMS passa a ser:

```text
max(consumo_mensal_kwh, disponibilidade_minima_kwh)
```

Isso evita subestimar a aliquota em ciclos com consumo baixo, mas ainda sujeitos ao minimo faturavel.

## SCEE e disponibilidade

O calculo de creditos prioriza a separacao entre:

- credito de energia compensavel;
- credito relacionado a disponibilidade minima.

A regra evita que disponibilidade minima contamine auto-consumo quando a integracao opera sem entidade de injecao.

## Modulos afetados

| Modulo | Mudanca |
|---|---|
| `coordinator.py` | Usa base faturavel minima para resolver faixa de ICMS. |
| `calculators.py` | Ajusta calculo SCEE e disponibilidade. |
| `README.md` | Documenta entidades, origens e formulas resumidas. |

## Testes

A release adicionou cobertura para:

- creditos de disponibilidade apos compensacao;
- consumo nao compensado no SCEE;
- ICMS com minimo trifasico.
