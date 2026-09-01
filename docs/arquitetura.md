# Arquitetura

## Visao geral

A integracao usa `DataUpdateCoordinator` para centralizar:

- coleta ANEEL
- extracao de tributos
- calculos regulatorios
- alternativo e preservacao de ultimo valor valido

## Modulos principais

- `custom_components/tarifas_energia_brasil/const.py`: constantes e catalogos.
- `config_flow.py`: configuracao inicial e opcoes.
- `aneel_client.py`: DataStore, orquestracao dos leitores Parquet isolados e CSV manual.
- `duckdb_provisioner.py`: selecao, download validado e instalacao persistente do DuckDB CLI.
- `parquet_worker.py`: DuckDB modulo/CLI e PyArrow exclusivamente em processos filhos.
- `tributos/__init__.py`: extratores de tributos.
- `calculators.py`: formulas de tarifa, tributos, Fio B e SCEE.
- `coordinator.py`: ciclo de atualizacao e geracao de resultado.
- `sensor.py`: entidades de sensor por chave de resultado.
- `diagnosticos.py`: dados de suporte.

## Fluxo de dados

1. Usuario configura integracao.
2. Coordinator inicia ciclo de coleta.
3. ANEEL client coleta tarifas, bandeiras e Fio B.
4. Extrator de tributos coleta PIS/COFINS/ICMS.
5. Modulo de calculos deriva tarifas finais e contas.
6. Registro de creditos SCEE e atualizado por competencia mensal com expiracao de 60 meses.
7. Resultado final alimenta sensores.
8. Em falha externa, ultimo resultado valido e mantido.

O fallback automatico Parquet existe apenas para Fio B. A coleta CSV e iniciada por
action, roda em background, admite uma tarefa por entrada e so publica o snapshot
depois que todas as coletas do ciclo terminam.

Isolamento dos leitores e notificacoes da versao 0.2.3: [documentacao](./compatibilidade_parquet_e_alertas.md).
