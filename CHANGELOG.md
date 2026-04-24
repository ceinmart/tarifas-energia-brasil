# Changelog

## Unreleased

## 0.1.0-alpha.4 - 2026-04-24

### Corrigido

- Listener de mudanca das entidades de consumo/geracao agora roda no event loop do Home Assistant, evitando o erro frequente de thread safety ao atualizar sensores via `async_update_listeners()`.
- Apuracao temporal da Tarifa Branca passou a respeitar o fuso horario da leitura recebida antes de classificar os intervalos.

### Testes

- Stub de testes do coordinator atualizado para cobrir o decorador `callback` do Home Assistant.

## 0.1.0-alpha.3 - 2026-04-23

### Alterado

- Acumuladores de consumo e geracao passaram a tratar reset/rebase de entidades `total` sem zerar artificialmente o ciclo corrente, reaproveitando a leitura atual como base segura do novo periodo.
- Acumuladores da Tarifa Branca passaram a reclassificar a leitura de reset no posto tarifario atual, marcando baixa confianca quando houver necessidade de estimativa.
- Diagnosticos passaram a refletir melhor o estado corrente dos acumuladores mensais de consumo e geracao, alem do sinalizador efetivo de confianca da Tarifa Branca.
- Estados numericos publicados nos sensores agora sao exibidos com no maximo 4 casas decimais para melhorar leitura no Home Assistant.

### Testes

- Cobertura adicionada para:
  - reset de entidades acumuladas preservando o valor corrente do ciclo;
  - reclassificacao de reset na Tarifa Branca;
  - arredondamento de exibicao dos sensores para 4 casas decimais.

## 0.1.0-alpha.2 - 2026-04-23

### Alterado

- Mantido um unico device principal da integracao, com organizacao por grupos logicos no mesmo device.
- Adicionados toggles no `options_flow` para controlar publicacao dos grupos:
  - `Geracao/SCEE`
  - `Tarifa Branca`
- Novas instalacoes passam a iniciar com `Tarifa Branca` desabilitada por default para reduzir ruido visual.
- Entries antigas preservam o grupo `Tarifa Branca` visivel por compatibilidade ate o usuario optar por ocultar.
- Sensores tecnicos de apoio passaram a usar categoria `diagnostic` quando apropriado.
- A Tarifa Branca passou a usar apuracao temporal real a partir do delta da entidade acumulada de consumo.
- Sabados, domingos, feriados nacionais e feriados extras agora entram na classificacao temporal da Tarifa Branca.
- O `options_flow` passou a permitir override manual das janelas horarias da Tarifa Branca.
- Consumo e geracao acumulados passaram a respeitar rateio temporal em viradas de dia, semana e ciclo mensal.
- Fechamento do ciclo mensal de creditos SCEE foi reforcado para usar os acumuladores correntes do periodo antes da troca de ciclo.
- Campos `Dia de leitura` e `Frequencia de atualizacao` passaram a usar caixa de entrada numerica no fluxo de configuracao.
- A selecao de linhas ANEEL passou a priorizar o recorte residencial correto para `TE`, `TUSD` e `Fio B`, evitando linhas de `SCEE`, `Tarifa Social`, `Baixa Renda` e variantes equivalentes quando existir a linha residencial padrao.
- O bootstrap inicial do ICMS passou a usar fallback seguro sem forcar faixa isenta quando ainda nao houver historico de consumo mensal acumulado.
- Diagnosticos da integracao agora expõem a linha escolhida da ANEEL para tarifas e `Fio B`, alem da origem aplicada do ICMS.

### Testes

- Cobertura adicionada para:
  - defaults e normalizacao dos grupos no `config_flow/options_flow`;
  - criacao condicional de sensores por grupo;
  - estabilidade de `unique_id` e `device_info` no modelo de um unico device.
  - horarios, feriados e rateio temporal da Tarifa Branca;
  - calculo monetario da Tarifa Branca por posto.
  - selecao correta das linhas da ANEEL para `CPFL-PIRATINING`;
  - uso de `NumberSelector` em modo caixa para os campos numericos do `config_flow`.

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
