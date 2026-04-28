# Changelog

## Unreleased

## 0.1.6 - 2026-04-28

### Alterado

- Padronizada a nomenclatura interna controlada pela integracao para portugues, incluindo constantes, modelos, chaves dinamicas de sensores e valores de quebra.
- Quebras de calculo passam a usar `diario`, `semanal` e `mensal` no lugar de `daily`, `weekly` e `monthly`.
- Entidades atuais de auto-consumo foram renomeadas para explicitar que representam valor acumulado.

### Adicionado

- Auto-consumo passa a ter entidades por quebra habilitada:
  - `auto_consumo_diario_kwh` e `auto_consumo_diario_reais`;
  - `auto_consumo_semanal_kwh` e `auto_consumo_semanal_reais`;
  - `auto_consumo_mensal_kwh` e `auto_consumo_mensal_reais`.

### Documentacao

- README, docs e documentacao tecnica atualizados para refletir os nomes em portugues e a nova release.

### Atencao

- Esta versao altera chaves tecnicas de entidades dinamicas que antes usavam `daily`, `weekly` e `monthly`; o Home Assistant pode criar novos `entity_id`s para essas entidades.

## 0.1.5 - 2026-04-27

### Corrigido

- A coleta de Fio B via CSV passa a processar recursos ano a ano e parar assim que encontrar Fio B convencional vigente com prioridade maxima, evitando baixar todos os CSVs grandes antes de validar o resultado.
- Falhas em um recurso especifico de Fio B deixam de interromper imediatamente os demais recursos do mesmo metodo, permitindo seguir para o proximo ano quando um CSV falhar ou expirar.

### Alterado

- Logs do fallback CSV passam a indicar inicio do download, tamanho informado pelo servidor, progresso em bytes, fim do stream, linhas lidas e quantidade de registros filtrados.

### Testes

- Cobertura adicionada para garantir que a coleta CSV de Fio B para no primeiro recurso valido e nao baixa recursos antigos desnecessarios.

## 0.1.4 - 2026-04-27

### Alterado

- Logs da coleta ANEEL passam a informar quando um fallback foi acionado, qual metodo falhou, qual sera o proximo metodo, quais filtros foram usados e o tipo/mensagem da excecao.
- Falhas de coleta no coordinator passam a registrar se existe snapshot valido sendo mantido, ou se nao ha cache disponivel, junto com a previsao da proxima tentativa automatica.

### Testes

- Cobertura adicionada para garantir que logs de falha ANEEL incluem filtros e tipo de excecao mesmo quando o erro vem sem mensagem textual.

## 0.1.3 - 2026-04-27

### Corrigido

- A integracao passa a restaurar o ultimo snapshot valido salvo no Home Assistant durante o setup, mantendo sensores com os dados anteriores quando a coleta externa inicial falhar.
- O fallback CSV da ANEEL passa a detectar delimitador `;`/`,` e decodificar o arquivo em streaming com encoding compativel com os CSVs publicados, corrigindo a coleta de Fio B da CPFL-PIRATINING quando o datastore CKAN nao retorna registros.

### Testes

- Cobertura adicionada para restauracao de snapshot apos reinicio, CSV ANEEL com delimitador `;` e encoding latin-1, e linhas vigentes de Fio B da CPFL-PIRATINING.

## 0.1.2 - 2026-04-27

### Corrigido

- O setup da integracao deixa de bloquear aguardando a primeira coleta externa completa, evitando cancelamento pelo timeout global de bootstrap do Home Assistant quando a ANEEL ou o fallback CSV estiverem lentos.
- A primeira atualizacao passa a ser agendada em background; se falhar ou for cancelada, a integracao permanece carregada e novas tentativas ocorrem pelos ciclos normais do coordinator.

### Testes

- Cobertura adicionada para garantir que o setup agenda a primeira atualizacao sem chamar `async_config_entry_first_refresh()` de forma bloqueante.

## 0.1.1 - 2026-04-26

### Alterado

- Atualizada a documentacao do README para manter a referencia ao CHANGELOG visivel e detalhar, na tabela de entidades, a origem ou formula resumida usada por cada sensor.
- A selecao de faixa de ICMS passa a considerar a base faturavel minima por tipo de fornecimento (`30/50/100 kWh`) quando ela for maior que o consumo mensal apurado.

### Corrigido

- A previsao de creditos SCEE agora considera a disponibilidade minima depois da compensacao: `credito_disponibilidade = max(disponibilidade_minima_kwh - energia_nao_compensada, 0)`.
- O credito de disponibilidade foi separado do credito de energia para nao contaminar o calculo de auto-consumo quando a integracao opera sem entidade de injecao.

### Testes

- Cobertura adicionada para creditos de disponibilidade apos compensacao, consumo nao compensado no SCEE e ICMS com minimo trifasico.

## 0.1.0 - 2026-04-26

### Alterado

- Promovida a integracao para a primeira release oficial `0.1.0`.

### Corrigido

- Leituras temporariamente indisponiveis (`unknown`, `unavailable` ou ausentes) das entidades acumuladas deixam de ser convertidas para `0.0`, evitando falso reset no boot do Home Assistant.
- O consumo, geracao e injecao mantem a ultima referencia valida quando uma entidade ainda nao carregou, impedindo que a proxima leitura real entre como delta integral e contamine os calculos diario/mensal.

### Testes

- Cobertura adicionada para garantir que uma leitura indisponivel no startup nao altera a referencia incremental nem os acumuladores atuais.

## 0.1.0-alpha.10 - 2026-04-25

### Corrigido

- `Fio B final` deixa de usar a maior faixa de ICMS como referencia fixa e passa a usar o `ICMS` atualmente aplicado pela regra de faixa mensal.
- No inicio do ciclo, quando a faixa atual de ICMS ainda for `0%`, a expressao do sensor `Fio B final` passa a refletir `0%` no consumo e na compensacao.
- O sensor `ICMS` passa a expor atributos com a expressao textual da regra aplicada, consumo mensal apurado e faixas da concessionaria.

### Testes

- Cobertura adicionada para manter o custo efetivo do Fio B dentro da faixa atual de ICMS e para explicar a regra de ICMS por concessionaria.

## 0.1.0-alpha.9 - 2026-04-25

### Alterado

- `Fio B final` passa a representar o custo efetivo da compensacao de energia, calculado como TUSD de consumo final menos TUSD injetada creditada final.
- O calculo do custo efetivo do Fio B passa a usar ICMS de referencia da faixa residencial cheia para consumo e ICMS zero para compensacao, evitando que o inicio do ciclo mensal subestime o custo.
- O sensor `Fio B final` passa a expor atributos com a expressao textual do calculo e os valores usados.

### Testes

- Cobertura adicionada para o custo efetivo de compensacao e para a selecao do ICMS de referencia por concessionaria.

## 0.1.0-alpha.8 - 2026-04-25

### Adicionado

- Novas entidades mensais sem custo de disponibilidade para consumo regular, Tarifa Branca e conta com geracao/SCEE.

### Alterado

- Sensores mensais de valor de conta passam a representar a conta faturavel, aplicando custo de disponibilidade quando ele for maior que o consumo calculado.
- Quebras diaria e semanal deixam de aplicar custo de disponibilidade, mantendo apenas o valor real apurado no periodo.
- Coleta ANEEL via CSV passa a filtrar registros em streaming e usar timeouts maiores para fontes lentas.
- Coleta de tributos passa a usar timeout HTTP maior.

### Testes

- Cobertura adicionada para disponibilidade mensal versus quebras diaria/semanal.
- Cobertura adicionada para as novas entidades mensais sem disponibilidade.
- Cobertura adicionada para timeouts e parsing em streaming da coleta ANEEL/tributos.

## 0.1.0-alpha.7 - 2026-04-25

### Corrigido

- Quebras diaria, semanal e mensal agora publicam o novo periodo zerado quando uma leitura termina exatamente na virada do dia, semana ou ciclo mensal.
- Ciclo mensal com dia de leitura configurado, como dia `24`, passa a fechar corretamente na virada do dia anterior para o dia configurado.
- Updates dinamicos das entidades agora recalculam ICMS por faixa usando o consumo mensal apurado como base.
- Tarifas finais e Fio B passam a ser recalculados quando a faixa de ICMS muda durante o ciclo, corrigindo os valores de conta regular e conta com geracao.

### Testes

- Cobertura adicionada para virada diaria/mensal no dia de leitura, virada semanal e recalculo de ICMS por consumo mensal.

## 0.1.0-alpha.6 - 2026-04-24

### Adicionado

- Nova entidade opcional de energia injetada acumulada (`entidade_injecao_kwh`) no fluxo de configuracao e nas opcoes da integracao.
- Persistencia e acumuladores independentes para injecao, com diagnosticos de reset e apuracao mensal.

### Corrigido

- Auto-consumo agora usa `geracao acumulada - energia injetada acumulada` quando a entidade de injecao esta configurada, evitando confundir consumo, geracao e credito estimado.
- Calculos SCEE passam a usar a energia injetada apurada como energia compensavel quando esse sensor existe.
- Grupo de geracao/SCEE tambem pode ser habilitado quando ha entidade de injecao configurada.

### Documentacao

- README e documentacao tecnica atualizados para o pre-release `0.1.0-alpha.6`.

## 0.1.0-alpha.5 - 2026-04-24

### Corrigido

- Reset/rebase de entidades acumuladas agora reinicializa a referencia incremental sem copiar a leitura total atual para todos os acumuladores de dia, semana, mes e Tarifa Branca.
- Auto-consumo com geracao/SCEE agora usa a diferenca entre energia gerada e energia injetada, evitando limitar o valor pelo consumo do periodo.

### Documentacao

- Adicionada documentacao tecnica gerada a partir do codigo para o pre-release `0.1.0-alpha.5`, com fluxo de funcionamento, objetos principais, funcoes de calculo e criterios de teste.

### Testes

- Cobertura adicionada para reset sem contaminacao dos acumuladores, Tarifa Branca apos rebase e calculo de auto-consumo por energia gerada menos energia injetada.

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
