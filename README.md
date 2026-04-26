# Tarifas Energia Brasil

![Icone Tarifas Energia Brasil](./custom_components/tarifas_energia_brasil/brand/icon.png)

Integracao customizada para Home Assistant que coleta tarifas ANEEL, tributos de concessionarias e calcula estimativas de custo de energia no Brasil (convencional, tarifa branca e cenarios com geracao/SCEE).

## Status

- Versao atual: `0.1.0-alpha.10` (pre-release).
- Escopo inicial: base funcional da integracao + MVP com concessionarias suportadas.
- Concessionaria obrigatoria do MVP: `CPFL-PIRATINING`.
- Documentacao tecnica do pre-release: [DOCUMENTACAO_CODIGO_0.1.0-alpha.10.md](./DOCUMENTACAO_CODIGO_0.1.0-alpha.10.md).

## Instalacao (HACS)

1. Abra o HACS.
2. Va em `Integrations`.
3. Adicione o repositorio custom: `https://github.com/ceinmart/tarifas-energia-brasil`.
4. Instale `Tarifas Energia Brasil`.
5. Reinicie o Home Assistant.
6. Adicione a integracao em `Configuracoes > Dispositivos e Servicos`.

## Configuracao no Home Assistant

Campos da configuracao inicial:

- `Concessionaria` (somente suportadas).
- `Dia de leitura/reset mensal` (default `1`).
- `Frequencia de atualizacao` em horas (default `24`).
- `Meio prioritario de acesso ANEEL`:
  - `datastore_search`
  - `datastore_search_sql`
  - `csv_xml`
- `Entidade de consumo acumulado em kWh` (obrigatoria).
- `Entidade de geracao acumulada em kWh` (opcional).
- `Entidade de energia injetada acumulada em kWh` (opcional, recomendada para SCEE e auto-consumo preciso).
- `Tipo de fornecimento` (obrigatorio quando existe entidade de geracao ou injecao):
  - `monofasico`
  - `bifasico`
  - `trifasico`
- `Quebras de calculo`:
  - `daily`
  - `weekly`
  - `monthly`

Pos-configuracao (options flow):

- Ajuste de concessionaria, frequencia, metodo ANEEL, entidades e quebras.
- Controle de grupos de entidades no mesmo device principal:
  - `Grupo de geracao/SCEE`: aparece quando existe entidade de geracao ou injecao configurada.
  - `Grupo de tarifa branca`: toggle explicito para publicar ou ocultar esse conjunto de sensores.
- Ajuste manual dos horarios da Tarifa Branca:
  - `inicio/fim ponta`
  - `inicio/fim intermediario 1`
  - `inicio/fim intermediario 2`
  - `feriados extras` em `YYYY-MM-DD`

Defaults de grupos:

- Novas instalacoes: `Tarifa Branca` inicia desabilitada para reduzir ruido visual.
- Entries antigas: o grupo `Tarifa Branca` permanece visivel por compatibilidade ate o usuario optar por ocultar.

## Concessionarias

Suportadas no fluxo de configuracao:

- `CPFL-PIRATINING`
- `CPFL-PAULISTA`
- `CELESC`

Mapeadas mas ainda nao suportadas no fluxo:

- `RGE SUL` (pendencia em PIS/COFINS mensal aberto).
- `CEMIG-D` (pendencia de ICMS aberto por faixa).
- `ENEL SP` (pendencia em PIS/COFINS mensal aberto).

Extratores internos parciais implementados (nao habilitados no fluxo):

- `RGE SUL`: parser de HTML para PIS/COFINS/ICMS com pendencia de validacao mensal completa.
- `CEMIG-D`: parser de HTML para PIS/COFINS; ICMS permanece em fallback pendente de validacao oficial.

## Fontes oficiais

APIs ANEEL:

- [Tarifas distribuidoras de energia eletrica](https://dadosabertos.aneel.gov.br/dataset/tarifas-distribuidoras-energia-eletrica)
- [Componentes tarifarias](https://dadosabertos.aneel.gov.br/dataset/componentes-tarifarias)
- [Bandeiras tarifarias](https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias)
- [SAMP](https://dadosabertos.aneel.gov.br/dataset/samp)

Links de concessionarias usados para tributos (MVP atual):

- [CPFL Piratininga - PIS/COFINS](https://www.cpfl.com.br/piratininga/pis-cofins)
- [CPFL Paulista - PIS/COFINS](https://www.cpfl.com.br/paulista/pis-cofins)
- [Celesc - Tarifas e tributos](https://www.celesc.com.br/tarifas-de-energia)

## Endpoints/datasets consultados

- `datastore_search` em:
  - `fcf2906c-7c32-4b9b-a637-054e7a5234f4` (TE/TUSD e tarifa branca)
  - `e8717aa8-2521-453f-bf16-fbb9a16eea39`, `a4060165-3a0c-404f-926c-83901088b67c`, `70ac08d1-53fc-4ceb-9c22-3a3a2c70e9fa` (Fio B multi-ano)
  - `0591b8f6-fe54-437b-b72b-1aa2efd46e42` (acionamento de bandeiras)
  - `5879ca80-b3bd-45b1-a135-d9b77c1d5b36` (adicional de bandeiras)
- Fallbacks:
  - `datastore_search_sql`
  - `csv_xml` (resource_show + download CSV/XML)

## Frequencia de chamadas e fallback

- A frequencia e controlada em horas pelo usuario (`default: 24`).
- Fluxo de tentativa:
  1. Metodo prioritario escolhido pelo usuario.
  2. Metodos restantes em fallback automatico.
  3. Em falha geral, manter ultimo valor valido.
- Nenhuma falha externa deve zerar sensor que ja tinha valor valido.

## Persistencia de creditos SCEE (60 meses)

- O historico de creditos e salvo em storage local do Home Assistant por `entry_id`.
- Regra implementada:
  - creditos expiram em janela de `60 meses`;
  - consumo usa primeiro os creditos mais antigos;
  - creditos gerados no ciclo atual entram no ledger no fechamento do ciclo mensal.
- O estado persistido inclui:
  - acumuladores de consumo/geracao/injecao por periodo;
  - ciclo mensal atual;
  - credito consumido estimado no ciclo;
  - credito gerado estimado no ciclo;
  - ledger de creditos por competencia.

## Como ver a ultima atualizacao

Cada entidade publica atributos de coleta, quando aplicavel:

- `ultima_coleta`
- `fonte`
- `dataset`
- `resource_id`
- `metodo_acesso`
- `usou_fallback`
- `tentativas`
- `mensagem_erro`
- `confianca_fonte`
- `vigencia_inicio`
- `vigencia_fim`

## Device e entidades

Device criado:

- Nome: `Tarifas Energia Brasil - <Concessionaria>`
- Identificador: `tarifas_energia_brasil_<slug_concessionaria>`

Quando entidades sao criadas:

- Grupo `Regular` (sempre criado): tarifa convencional, tributos, bandeira e valores de conta regular.
- Grupo `Geracao/SCEE` (opcional): Fio B, creditos, auto-consumo e valores de conta com geracao.
- Grupo `Tarifa Branca` (opcional): tarifas por posto e valores de conta de tarifa branca.
- Dependentes de quebras: sensores de valor diario/semanal/mensal conforme `daily`, `weekly`, `monthly`.

Tabela completa de entidades (potenciais):

Observacoes:

- O Home Assistant define o `entity_id` final automaticamente. A coluna `ID sugerido` e apenas referencia.
- A coluna `Chave interna` e o `value_key` publicado pelo coordinator.
- Entidades por periodo usam as quebras configuradas em `Quebras de calculo` (`daily`, `weekly`, `monthly`).
- Default de quebras quando nao informado: `daily` e `monthly`.
- Atualmente nao ha sensores com `state_class` `total` ou `total_increasing` nesta integracao.
- Alguns sensores tecnicos ficam na categoria `diagnostic` para reduzir poluicao visual no device.

| Nome amigavel | Chave interna (`value_key`) | ID sugerido | Unidade | Tipo HA (`state_class`) | Condicao de criacao | Observacao |
|---|---|---|---|---|---|---|
| TE convencional | `te_convencional_r_kwh` | `sensor.te_convencional` | R$/kWh | `measurement` | Sempre | Coletado da ANEEL e convertido para R$/kWh. |
| TUSD convencional | `tusd_convencional_r_kwh` | `sensor.tusd_convencional` | R$/kWh | `measurement` | Sempre | Coletado da ANEEL e convertido para R$/kWh. |
| Tarifa convencional bruta | `tarifa_convencional_bruta_r_kwh` | `sensor.tarifa_convencional_bruta` | R$/kWh | `measurement` | Sempre | `TE + TUSD`. |
| Tarifa convencional final | `tarifa_convencional_final_r_kwh` | `sensor.tarifa_convencional_final` | R$/kWh | `measurement` | Sempre | Com tributos por dentro. |
| TE branca fora ponta | `te_branca_fora_ponta_r_kwh` | `sensor.te_branca_fora_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Parcela TE por posto. |
| TUSD branca fora ponta | `tusd_branca_fora_ponta_r_kwh` | `sensor.tusd_branca_fora_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Parcela TUSD por posto. |
| Tarifa branca fora ponta bruta | `tarifa_branca_fora_ponta_bruta_r_kwh` | `sensor.tarifa_branca_fora_ponta_bruta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `TE + TUSD` fora ponta. |
| Tarifa branca fora ponta final | `tarifa_branca_fora_ponta_final_r_kwh` | `sensor.tarifa_branca_fora_ponta_final` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Com tributos por dentro. |
| TE branca intermediario | `te_branca_intermediario_r_kwh` | `sensor.te_branca_intermediario` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Parcela TE por posto. |
| TUSD branca intermediario | `tusd_branca_intermediario_r_kwh` | `sensor.tusd_branca_intermediario` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Parcela TUSD por posto. |
| Tarifa branca intermediario bruta | `tarifa_branca_intermediario_bruta_r_kwh` | `sensor.tarifa_branca_intermediario_bruta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `TE + TUSD` intermediario. |
| Tarifa branca intermediario final | `tarifa_branca_intermediario_final_r_kwh` | `sensor.tarifa_branca_intermediario_final` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Com tributos por dentro. |
| TE branca ponta | `te_branca_ponta_r_kwh` | `sensor.te_branca_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Parcela TE por posto. |
| TUSD branca ponta | `tusd_branca_ponta_r_kwh` | `sensor.tusd_branca_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Parcela TUSD por posto. |
| Tarifa branca ponta bruta | `tarifa_branca_ponta_bruta_r_kwh` | `sensor.tarifa_branca_ponta_bruta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `TE + TUSD` ponta. |
| Tarifa branca ponta final | `tarifa_branca_ponta_final_r_kwh` | `sensor.tarifa_branca_ponta_final` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | Com tributos por dentro. |
| Fio B bruto | `fio_b_bruto_r_kwh` | `sensor.fio_b_bruto` | R$/kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | `TUSD_FioB / 1000`. |
| Fio B final | `fio_b_final_r_kwh` | `sensor.fio_b_final` | R$/kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Custo efetivo da compensacao: TUSD consumo final menos TUSD injetada creditada final. Inclui atributos com a expressao do calculo. |
| PIS | `pis_percent` | `sensor.pis` | % | `measurement` | Sempre | Aliquota da concessionaria/fallback. |
| COFINS | `cofins_percent` | `sensor.cofins` | % | `measurement` | Sempre | Aliquota da concessionaria/fallback. |
| ICMS | `icms_percent` | `sensor.icms` | % | `measurement` | Sempre | Pode aplicar regra por faixa mensal. |
| Bandeira vigente | `bandeira_vigente` | `sensor.bandeira_vigente` | texto | sem `state_class` | Sempre | Cor/status da bandeira ativa. |
| Adicional da bandeira | `adicional_bandeira_r_kwh` | `sensor.adicional_bandeira` | R$/kWh | `measurement` | Sempre | Adicional homologado convertido de R$/MWh. |
| Indicador taxa minima | `indicador_taxa_minima` | `sensor.indicador_taxa_minima` | texto (`sim`/`nao`) | sem `state_class` | Sempre | Indica se disponibilidade minima foi aplicada no mensal. |
| kWh adicionados para disponibilidade | `kwh_adicionados_disponibilidade` | `sensor.kwh_adicionados_para_disponibilidade` | kWh | `measurement` | Sempre | Diferenca para atingir disponibilidade minima. |
| Saldo de creditos do mes anterior | `saldo_creditos_mes_anterior_kwh` | `sensor.saldo_creditos_do_mes_anterior` | kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Sem o grupo de geracao esse sensor nao e criado. |
| Previsao de creditos gerados | `previsao_creditos_gerados_kwh` | `sensor.previsao_de_creditos_gerados` | kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Usa injecao acumulada quando configurada. |
| Auto-consumo | `auto_consumo_kwh` | `sensor.auto_consumo` | kWh | `measurement` | Quando houver entidade de geracao e o grupo `Geracao/SCEE` estiver habilitado | Usa `geracao - injecao` quando a entidade de injecao existe. |
| Auto-consumo em reais | `auto_consumo_reais` | `sensor.auto_consumo_em_reais` | R$ | `measurement` | Quando houver entidade de geracao e o grupo `Geracao/SCEE` estiver habilitado | Auto-consumo vezes tarifa convencional final. |
| Valor conta consumo regular diario | `valor_conta_consumo_regular_daily_r` | `sensor.valor_conta_consumo_regular_diario` | R$ | `measurement` | Quando `daily` estiver habilitado | Sensor dinamico por quebra de periodo. |
| Valor conta consumo regular semanal | `valor_conta_consumo_regular_weekly_r` | `sensor.valor_conta_consumo_regular_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado | Sensor dinamico por quebra de periodo. |
| Valor conta consumo regular mensal | `valor_conta_consumo_regular_monthly_r` | `sensor.valor_conta_consumo_regular_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado | Sensor dinamico por quebra de periodo. |
| Valor conta tarifa branca diario | `valor_conta_tarifa_branca_daily_r` | `sensor.valor_conta_tarifa_branca_diario` | R$ | `measurement` | Quando `daily` estiver habilitado e o grupo `Tarifa Branca` estiver habilitado | Sensor dinamico por quebra de periodo. |
| Valor conta tarifa branca semanal | `valor_conta_tarifa_branca_weekly_r` | `sensor.valor_conta_tarifa_branca_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado e o grupo `Tarifa Branca` estiver habilitado | Sensor dinamico por quebra de periodo. |
| Valor conta tarifa branca mensal | `valor_conta_tarifa_branca_monthly_r` | `sensor.valor_conta_tarifa_branca_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado e o grupo `Tarifa Branca` estiver habilitado | Sensor dinamico por quebra de periodo. |
| Valor conta com geracao diario | `valor_conta_com_geracao_daily_r` | `sensor.valor_conta_com_geracao_diario` | R$ | `measurement` | Quando `daily` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Sem o grupo de geracao esse sensor nao e criado. |
| Valor conta com geracao semanal | `valor_conta_com_geracao_weekly_r` | `sensor.valor_conta_com_geracao_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Sem o grupo de geracao esse sensor nao e criado. |
| Valor conta com geracao mensal | `valor_conta_com_geracao_monthly_r` | `sensor.valor_conta_com_geracao_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Sem o grupo de geracao esse sensor nao e criado. |
| Valor Fio B compensada diario | `valor_fio_b_compensada_daily_r` | `sensor.valor_fio_b_compensada_diario` | R$ | `measurement` | Quando `daily` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Usa energia compensada apurada pelo SCEE. |
| Valor Fio B compensada semanal | `valor_fio_b_compensada_weekly_r` | `sensor.valor_fio_b_compensada_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Usa energia compensada apurada pelo SCEE. |
| Valor Fio B compensada mensal | `valor_fio_b_compensada_monthly_r` | `sensor.valor_fio_b_compensada_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Usa energia compensada apurada pelo SCEE. |

## Calculos detalhados

1. Conversao de unidade:
   - `valor_r_kwh = valor_r_mwh / 1000`
2. Tarifa convencional:
   - `tarifa_convencional_bruta = te + tusd`
   - `tarifa_convencional_final = aplicar_tributos_por_dentro(...)`
3. Tarifa branca por posto:
   - `tarifa_branca_bruta_posto = te_posto + tusd_posto`
   - `tarifa_branca_final_posto = aplicar_tributos_por_dentro(...)`
   - o consumo e rateado por posto com base no delta da entidade acumulada de consumo, respeitando:
     - horarios default da concessionaria
     - override manual do usuario
     - sabados e domingos como `fora ponta`
     - feriados nacionais e feriados extras como `fora ponta`
4. Tributos por dentro:
   - `valor_com_tributos = valor_sem_tributos / (1 - pis - cofins - icms)`
   - o `ICMS` aplicado pode ser ajustado por faixa de consumo mensal para concessionarias com regra mapeada
5. Bandeira:
   - `valor_bandeira = kwh_faturado * adicional_bandeira_r_kwh`
6. Disponibilidade:
   - minimo por fornecimento: `30/50/100 kWh`
   - `valor_faturado = max(valor_disponibilidade, valor_calculado)`
7. Fio B:
   - `fio_b_bruto = tusd_fio_b_r_mwh / 1000`
   - `fio_b_final = aplicar_tributos_por_dentro(fio_b_bruto * percentual_ano, ...)`
8. SCEE (modelo inicial):
   - `valor_consumo_scee = valor_energia_nao_compensada + valor_fio_b_compensada`
   - `valor_consumo_faturado = max(valor_disponibilidade, valor_consumo_scee)`
   - consumo, geracao e injecao acumulados agora sao apurados de forma incremental no tempo, com rateio por virada de dia/semana/ciclo mensal
   - quando a entidade de injecao existe, ela e usada como energia compensavel do SCEE
   - auto-consumo usa `max(geracao_acumulada - injecao_acumulada, 0)` quando as duas entidades estao configuradas
   - creditos continuam persistidos e consumidos do mais antigo para o mais novo

Limitacoes atuais da pre-release:

- A Tarifa Branca depende da qualidade temporal da entidade acumulada de consumo; leituras muito espacadas reduzem a confianca do rateio por posto.
- O motor SCEE esta mais robusto no ciclo incremental, mas ainda precisa de validacao contra faturas reais para fechamento fino de casos regulatórios.
- Sem entidade de injecao configurada, auto-consumo e creditos seguem em modo estimado/fallback a partir dos dados disponiveis.
- Entidades auxiliares de horario efetivo, posto atual e consumo por posto ainda nao foram expostas; hoje o calculo ja usa essa logica internamente.
- Extratores web podem exigir ajuste quando houver mudanca de layout das concessionarias.

Regra adicional implementada:

- Aplicacao de ICMS por faixa de consumo mensal (quando regra da concessionaria esta mapeada), com fallback para aliquota base do extrator.

## Fixtures e testes de extratores

- Parsers de tributos foram desacoplados para funcoes testaveis.
- Fixtures iniciais:
  - [cpfl_pis_cofins_sample.html](./tests/fixtures/cpfl_pis_cofins_sample.html)
  - [celesc_tributos_sample.html](./tests/fixtures/celesc_tributos_sample.html)
- Em alteracao de parser, atualize fixture e execute `pytest` para evitar regressao silenciosa.

## Links de versao

- [CHANGELOG](./CHANGELOG.md)
- [Releases](https://github.com/ceinmart/tarifas-energia-brasil/releases)
