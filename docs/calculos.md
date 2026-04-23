# Calculos

## Conversao de unidade

`R$/kWh = R$/MWh / 1000`

## Tarifa convencional

- Bruta: `TE + TUSD`
- Final: `bruta / (1 - pis - cofins - icms)`
- ICMS aplicado:
  - usa regra por faixa mensal para concessionarias mapeadas;
  - em ausencia de regra, usa aliquota base extraida da fonte da concessionaria.

## Tarifa branca

Para cada posto (`fora ponta`, `intermediario`, `ponta`):

- Bruta: `TE_posto + TUSD_posto`
- Final: `bruta_posto / (1 - pis - cofins - icms)`

## Bandeira tarifaria

`valor_bandeira = kwh_faturado * adicional_bandeira_r_kwh`

## Disponibilidade minima

- Monofasico: `30 kWh`
- Bifasico: `50 kWh`
- Trifasico: `100 kWh`

`valor_faturado = max(valor_disponibilidade, valor_calculado)`

## Fio B

- Bruto: `tusd_fio_b_r_mwh / 1000`
- Final: `aplicar_tributos_por_dentro(fio_b_bruto * percentual_transicao_ano)`

Percentuais de transicao:

- 2023: 15%
- 2024: 30%
- 2025: 45%
- 2026: 60%
- 2027: 75%
- 2028: 90%
- 2029+: 100%

## SCEE (modelo inicial)

- `energia_compensada = min(consumo, geracao + credito_entrada)`
- `energia_nao_compensada = consumo - energia_compensada`
- `valor_consumo_scee = valor_energia_nao_compensada + valor_fio_b_compensada`
- `valor_faturado = max(valor_disponibilidade, valor_consumo_scee)`
