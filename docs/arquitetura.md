# Arquitetura

## Visao geral

A integracao usa `DataUpdateCoordinator` para centralizar:

- coleta ANEEL
- extracao de tributos
- calculos regulatorios
- fallback e preservacao de ultimo valor valido

## Modulos principais

- `custom_components/tarifas_energia_brasil/const.py`: constantes e catalogos.
- `config_flow.py`: configuracao inicial e opcoes.
- `aneel_client.py`: consultas CKAN (`datastore_search`, `datastore_search_sql`, `csv_xml`).
- `tributos/__init__.py`: extratores de tributos.
- `calculators.py`: formulas de tarifa, tributos, Fio B e SCEE.
- `coordinator.py`: ciclo de atualizacao e geracao de snapshot.
- `sensor.py`: entidades de sensor por chave de snapshot.
- `diagnostics.py`: dados de suporte.

## Fluxo de dados

1. Usuario configura integracao.
2. Coordinator inicia ciclo de coleta.
3. ANEEL client coleta tarifas, bandeiras e Fio B.
4. Extrator de tributos coleta PIS/COFINS/ICMS.
5. Modulo de calculos deriva tarifas finais e contas.
6. Ledger de creditos SCEE e atualizado por competencia mensal com expiracao de 60 meses.
7. Snapshot final alimenta sensores.
8. Em falha externa, ultimo snapshot valido e mantido.
