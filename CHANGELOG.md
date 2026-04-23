# Changelog

## 0.1.0-alpha.1-base-integracao - 2026-04-22

### Adicionado

- Estrutura inicial de repositorio HACS em `tarifas_energia_brasil/`.
- Integracao Home Assistant em `custom_components/tarifas_energia_brasil`.
- `config_flow` e `options_flow` para configuracao e pos-configuracao.
- `DataUpdateCoordinator` com estrategia de fallback entre metodos ANEEL.
- Coleta de:
  - TE/TUSD convencional e tarifa branca por posto.
  - Bandeira vigente e adicional.
  - Fio B com busca multi-ano em `componentes-tarifarias`.
- Extrator de tributos com fallback para:
  - `CPFL-PIRATINING`
  - `CPFL-PAULISTA`
  - `CELESC`
- Sensores principais de componentes, tributos, Fio B, bandeira e contas por quebra.
- Testes iniciais de calculos (`tests/test_calculators.py`).
- Ledger persistente de creditos SCEE:
  - expiracao em 60 meses;
  - consumo de credito mais antigo primeiro;
  - persistencia em storage local por `entry_id`.
- Parser de tributos desacoplado para testes por fixture:
  - `custom_components/tarifas_energia_brasil/tributos/parsers.py`
  - `tests/test_tributos_parsers.py`
  - `tests/test_credito_ledger.py`
- Testes de fluxo:
  - validacao de `config_flow` e `options_flow` em `tests/test_config_flow.py`
- Extratores internos adicionais (mantidos fora do fluxo de suporte):
  - `RGE SUL` (parcial)
  - `CEMIG-D` (parcial)
- Regra de ICMS por faixa de consumo mensal:
  - novo modulo `icms_rules.py`;
  - aplicacao automatica no `coordinator` com fallback para aliquota base;
  - cobertura de testes em `tests/test_icms_rules.py`.
- Workflows CI:
  - `hacs.yaml`
  - `hassfest.yaml`
  - `ci.yaml`

### Concessionarias

- Suportadas nesta versao:
  - `CPFL-PIRATINING`
  - `CPFL-PAULISTA`
  - `CELESC`
- Mapeadas mas nao suportadas no fluxo:
  - `RGE SUL`
  - `CEMIG-D`
  - `ENEL SP`

### Limitacoes conhecidas

- Estimativa de tarifa branca por periodo sem consumo horario por posto.
- Modelo SCEE inicial (sem persistencia completa historica de creditos).
- Dependencia de layout web para extracao de tributos.

### Breaking changes

- Nao aplicavel (primeira pre-release).
