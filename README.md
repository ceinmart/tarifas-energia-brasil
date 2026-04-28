# Tarifas Energia Brasil

![Icone Tarifas Energia Brasil](./custom_components/tarifas_energia_brasil/brand/icon.png)

Integracao customizada para Home Assistant que coleta tarifas ANEEL, tributos de concessionarias e calcula estimativas de custo de energia no Brasil (convencional, tarifa branca e cenarios com geracao/SCEE).

## Indice

- [Status](#status)
- [Instalacao (HACS)](#instalacao-hacs)
- [Configuracao no Home Assistant](#configuracao-no-home-assistant)
- [Concessionarias](#concessionarias)
- [Fontes oficiais](#fontes-oficiais)
- [REGRAS SCEE](#regras-scee)
- [Endpoints/datasets consultados](#endpointsdatasets-consultados)
- [Frequencia de chamadas e fallback](#frequencia-de-chamadas-e-fallback)
- [Persistencia de creditos SCEE (60 meses)](#persistencia-de-creditos-scee-60-meses)
- [Como ver a ultima atualizacao](#como-ver-a-ultima-atualizacao)
- [Device e entidades](#device-e-entidades)
- [Calculos detalhados](#calculos-detalhados)
- [Fixtures e testes de extratores](#fixtures-e-testes-de-extratores)
- [Links de versao](#links-de-versao)

## Status

- Versao atual: `0.1.5` (release oficial).
- Escopo inicial: base funcional da integracao + MVP com concessionarias suportadas.
- Concessionaria obrigatoria do MVP: `CPFL-PIRATINING`.
- Documentacao tecnica de referencia: [DOCUMENTACAO_CODIGO_0.1.0-alpha.10.md](./DOCUMENTACAO_CODIGO_0.1.0-alpha.10.md).
- Historico completo de mudancas: [CHANGELOG](./CHANGELOG.md).

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

## REGRAS SCEE

**SCEE** significa **Sistema de Compensacao de Energia Eletrica**.

Regras gerais aplicadas em toda a extensao:

- A extensao calcula estimativas; o valor oficial continua sendo o fechamento da concessionaria.
- A energia injetada na rede pode virar credito em kWh para compensar consumo.
- Os creditos SCEE podem ser usados por ate 60 meses, conforme regra geral da ANEEL.
- A compensacao considera consumo, energia injetada, creditos existentes e saldo previsto de creditos.
- A geracao so entra no calculo de auto-consumo quando tambem existe a informacao de injecao.
- O tipo de instalacao define o consumo minimo faturavel:
  - monofasico: 30 kWh
  - bifasico: 50 kWh
  - trifasico: 100 kWh
- As regras de ICMS/PIS/COFINS variam por estado, concessionaria e fonte de dados disponivel.
- Dependendo do consumo minimo, a instalacao pode ja entrar em uma faixa minima de ICMS.
- Essa faixa minima pode alterar tarifas finais, custo de disponibilidade, creditos previstos e valor estimado da conta.
- E comum a concessionaria calcular o valor do credito recalculando a tarifa sem os componentes que geram desconto, como Fio B e ICMS.
- Normalmente, a diferenca observada na fatura da concessionaria deve ficar proxima da entidade `Fio B final`.
- Na extensao, `Fio B final` representa o custo efetivo da compensacao: TUSD de consumo final menos TUSD injetada creditada final.
- A bandeira tarifaria vigente entra na estimativa quando houver dado disponivel.
- A bandeira tarifaria representa um adicional aplicado ao consumo conforme a condicao de geracao do sistema eletrico.
- O adicional de bandeira e convertido para R$/kWh e aplicado nos valores estimados de conta.
- A bandeira pode alterar o valor previsto mesmo sem mudanca na tarifa base da concessionaria.
- Em cenarios SCEE, o adicional de bandeira deve incidir apenas sobre energia faturavel/nao compensada, conforme a regra aplicavel.
- Como a bandeira pode mudar por periodo, a previsao mensal pode oscilar ate o fechamento da fatura.
- Auto-consumo e a energia gerada e consumida localmente antes de ser injetada na rede.
- O auto-consumo so pode ser calculado quando existem as informacoes de geracao e injecao.
- A entidade de consumo nao afeta o calculo de auto-consumo e nunca deve ser usada para isso.
- A formula aplicada e: `auto-consumo = geracao - injecao`.
- O auto-consumo nao vira credito SCEE, porque nao foi energia injetada na rede da distribuidora.
- A extensao exibe o auto-consumo para separar a energia usada diretamente da energia que pode gerar credito.
- Essa separacao melhora a leitura de energia injetada, creditos previstos, Fio B e valor final estimado.
- As estimativas podem oscilar durante o mes conforme consumo, injecao, bandeira vigente e mudancas de faixa ate o fechamento.
- A previsao mensal deve ser tratada como tendencia, nao como fatura definitiva.

Exemplos basicos:

- Em uma instalacao monofasica, mesmo com muitos creditos, pode existir cobranca minima equivalente a 30 kWh.
- Se o consumo minimo enquadrar a instalacao em uma faixa de ICMS, a estimativa pode iniciar o mes com tarifa final diferente de zero.
- Se o consumo aumenta durante o mes, a instalacao pode mudar de faixa e alterar ICMS, Fio B, creditos previstos e total estimado.
- Se houver consumo faturavel apos compensacao de creditos, a bandeira pode adicionar custo sobre esse consumo.
- Se os creditos compensarem toda a energia aplicavel, ainda pode existir cobranca minima, tributos ou componentes nao compensaveis conforme a regra da concessionaria.
- Uma mudanca de bandeira no meio do ciclo pode alterar a previsao do mes, mesmo que consumo e geracao sigam parecidos.
- Se a instalacao gerou 20 kWh e injetou 12 kWh, o auto-consumo estimado e 8 kWh.
- Se nao existir informacao de geracao ou nao existir informacao de injecao, a extensao nao calcula auto-consumo.
- A entidade de consumo da casa nao entra nesse calculo.
- Se a energia injetada supera o consumo compensavel, o excedente entra como credito para proximos ciclos, respeitando a validade aplicavel.

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

| Nome amigavel | Chave interna (`value_key`) | ID sugerido | Unidade | Tipo HA (`state_class`) | Condicao de criacao | Calculo, origem ou regra resumida |
|---|---|---|---|---|---|---|
| TE convencional | `te_convencional_r_kwh` | `sensor.te_convencional` | R$/kWh | `measurement` | Sempre | `VlrTUSD_TE` da ANEEL para modalidade convencional, convertido para R$/kWh quando a origem vier em R$/MWh. |
| TUSD convencional | `tusd_convencional_r_kwh` | `sensor.tusd_convencional` | R$/kWh | `measurement` | Sempre | `VlrTUSD` da ANEEL para modalidade convencional, convertido para R$/kWh quando necessario. |
| Tarifa convencional bruta | `tarifa_convencional_bruta_r_kwh` | `sensor.tarifa_convencional_bruta` | R$/kWh | `measurement` | Sempre | `te_convencional_r_kwh + tusd_convencional_r_kwh`. |
| Tarifa convencional final | `tarifa_convencional_final_r_kwh` | `sensor.tarifa_convencional_final` | R$/kWh | `measurement` | Sempre | `tarifa_convencional_bruta / (1 - PIS - COFINS - ICMS)`, com aliquotas em decimal. |
| TE branca fora ponta | `te_branca_fora_ponta_r_kwh` | `sensor.te_branca_fora_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | TE ANEEL da modalidade branca no posto `fora_ponta`, em R$/kWh. |
| TUSD branca fora ponta | `tusd_branca_fora_ponta_r_kwh` | `sensor.tusd_branca_fora_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | TUSD ANEEL da modalidade branca no posto `fora_ponta`, em R$/kWh. |
| Tarifa branca fora ponta bruta | `tarifa_branca_fora_ponta_bruta_r_kwh` | `sensor.tarifa_branca_fora_ponta_bruta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `te_branca_fora_ponta_r_kwh + tusd_branca_fora_ponta_r_kwh`. |
| Tarifa branca fora ponta final | `tarifa_branca_fora_ponta_final_r_kwh` | `sensor.tarifa_branca_fora_ponta_final` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `tarifa_branca_fora_ponta_bruta / (1 - PIS - COFINS - ICMS)`. |
| TE branca intermediario | `te_branca_intermediario_r_kwh` | `sensor.te_branca_intermediario` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | TE ANEEL da modalidade branca no posto `intermediario`, em R$/kWh. |
| TUSD branca intermediario | `tusd_branca_intermediario_r_kwh` | `sensor.tusd_branca_intermediario` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | TUSD ANEEL da modalidade branca no posto `intermediario`, em R$/kWh. |
| Tarifa branca intermediario bruta | `tarifa_branca_intermediario_bruta_r_kwh` | `sensor.tarifa_branca_intermediario_bruta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `te_branca_intermediario_r_kwh + tusd_branca_intermediario_r_kwh`. |
| Tarifa branca intermediario final | `tarifa_branca_intermediario_final_r_kwh` | `sensor.tarifa_branca_intermediario_final` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `tarifa_branca_intermediario_bruta / (1 - PIS - COFINS - ICMS)`. |
| TE branca ponta | `te_branca_ponta_r_kwh` | `sensor.te_branca_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | TE ANEEL da modalidade branca no posto `ponta`, em R$/kWh. |
| TUSD branca ponta | `tusd_branca_ponta_r_kwh` | `sensor.tusd_branca_ponta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | TUSD ANEEL da modalidade branca no posto `ponta`, em R$/kWh. |
| Tarifa branca ponta bruta | `tarifa_branca_ponta_bruta_r_kwh` | `sensor.tarifa_branca_ponta_bruta` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `te_branca_ponta_r_kwh + tusd_branca_ponta_r_kwh`. |
| Tarifa branca ponta final | `tarifa_branca_ponta_final_r_kwh` | `sensor.tarifa_branca_ponta_final` | R$/kWh | `measurement` | Quando o grupo `Tarifa Branca` estiver habilitado | `tarifa_branca_ponta_bruta / (1 - PIS - COFINS - ICMS)`. |
| Fio B bruto | `fio_b_bruto_r_kwh` | `sensor.fio_b_bruto` | R$/kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | `TUSD_FioB_r_mwh / 1000`. |
| Fio B final | `fio_b_final_r_kwh` | `sensor.fio_b_final` | R$/kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Custo efetivo da compensacao: `TUSD_consumo_final - TUSD_credito_final`; atributos mostram a expressao completa. |
| PIS | `pis_percent` | `sensor.pis` | % | `measurement` | Sempre | Aliquota mensal coletada da concessionaria; fallback local quando a coleta falha. |
| COFINS | `cofins_percent` | `sensor.cofins` | % | `measurement` | Sempre | Aliquota mensal coletada da concessionaria; fallback local quando a coleta falha. |
| ICMS | `icms_percent` | `sensor.icms` | % | `measurement` | Sempre | Aliquota por faixa: usa `max(consumo_mensal_kwh, disponibilidade_minima_kwh)` quando ha regra da concessionaria; caso contrario usa fallback. |
| Bandeira vigente | `bandeira_vigente` | `sensor.bandeira_vigente` | texto | sem `state_class` | Sempre | Nome/cor da bandeira ativa na competencia retornada pela ANEEL. |
| Adicional da bandeira | `adicional_bandeira_r_kwh` | `sensor.adicional_bandeira` | R$/kWh | `measurement` | Sempre | `adicional_bandeira_r_mwh / 1000`; aplicado sobre kWh faturado nos valores de conta. |
| Indicador taxa minima | `indicador_taxa_minima` | `sensor.indicador_taxa_minima` | texto (`sim`/`nao`) | sem `state_class` | Sempre | `sim` quando `consumo_mensal_kwh < disponibilidade_minima_kwh` (`30`, `50` ou `100`). |
| kWh adicionados para disponibilidade | `kwh_adicionados_disponibilidade` | `sensor.kwh_adicionados_para_disponibilidade` | kWh | `measurement` | Sempre | Para indicador geral: `max(disponibilidade_minima_kwh - consumo_mensal_kwh, 0)`. No SCEE, o credito usa a sobra apos compensacao. |
| Saldo de creditos do mes anterior | `saldo_creditos_mes_anterior_kwh` | `sensor.saldo_creditos_do_mes_anterior` | kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Soma do ledger persistido de creditos em kWh, consumindo primeiro os creditos mais antigos e expirando em 60 meses. |
| Previsao de creditos gerados | `previsao_creditos_gerados_kwh` | `sensor.previsao_de_creditos_gerados` | kWh | `measurement` | Quando houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | `max(saldo_anterior - credito_consumido + credito_energia + credito_disponibilidade, 0)`, onde `credito_disponibilidade = max(minimo_kwh - energia_nao_compensada, 0)`. |
| Auto-consumo | `auto_consumo_kwh` | `sensor.auto_consumo` | kWh | `measurement` | Quando houver entidade de geracao e o grupo `Geracao/SCEE` estiver habilitado | Com injecao configurada: `max(geracao_total - injecao_total, 0)`; sem injecao, usa estimativa por geracao e credito de energia. |
| Auto-consumo em reais | `auto_consumo_reais` | `sensor.auto_consumo_em_reais` | R$ | `measurement` | Quando houver entidade de geracao e o grupo `Geracao/SCEE` estiver habilitado | `auto_consumo_kwh * tarifa_convencional_final_r_kwh`. |
| Valor conta consumo regular diario | `valor_conta_consumo_regular_daily_r` | `sensor.valor_conta_consumo_regular_diario` | R$ | `measurement` | Quando `daily` estiver habilitado | `consumo_diario_kwh * (tarifa_convencional_final + adicional_bandeira)`. |
| Valor conta consumo regular semanal | `valor_conta_consumo_regular_weekly_r` | `sensor.valor_conta_consumo_regular_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado | `consumo_semanal_kwh * (tarifa_convencional_final + adicional_bandeira)`. |
| Valor conta consumo regular mensal | `valor_conta_consumo_regular_monthly_r` | `sensor.valor_conta_consumo_regular_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado | `max(valor_disponibilidade, consumo_mensal_kwh * (tarifa_convencional_final + adicional_bandeira))`. |
| Valor consumo regular mensal sem disponibilidade | `valor_conta_consumo_regular_sem_disponibilidade_monthly_r` | `sensor.valor_consumo_regular_mensal_sem_disponibilidade` | R$ | `measurement` | Quando `monthly` estiver habilitado | Valor regular puro: `consumo_mensal_kwh * (tarifa_convencional_final + adicional_bandeira)`, sem aplicar minimo. |
| Valor conta tarifa branca diario | `valor_conta_tarifa_branca_daily_r` | `sensor.valor_conta_tarifa_branca_diario` | R$ | `measurement` | Quando `daily` estiver habilitado e o grupo `Tarifa Branca` estiver habilitado | Soma por posto: `fora_ponta*tarifa_fp + intermediario*tarifa_int + ponta*tarifa_ponta + consumo_total*adicional_bandeira`. |
| Valor conta tarifa branca semanal | `valor_conta_tarifa_branca_weekly_r` | `sensor.valor_conta_tarifa_branca_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado e o grupo `Tarifa Branca` estiver habilitado | Mesma formula por posto, usando acumuladores semanais rateados por horario/posto. |
| Valor conta tarifa branca mensal | `valor_conta_tarifa_branca_monthly_r` | `sensor.valor_conta_tarifa_branca_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado e o grupo `Tarifa Branca` estiver habilitado | `max(valor_disponibilidade, valor_tarifa_branca_mensal_por_posto)`. |
| Valor tarifa branca mensal sem disponibilidade | `valor_conta_tarifa_branca_sem_disponibilidade_monthly_r` | `sensor.valor_tarifa_branca_mensal_sem_disponibilidade` | R$ | `measurement` | Quando `monthly` e `Tarifa Branca` estiverem habilitados | Valor mensal por posto sem aplicar `max(valor_disponibilidade, ...)`. |
| Valor conta com geracao diario | `valor_conta_com_geracao_daily_r` | `sensor.valor_conta_com_geracao_diario` | R$ | `measurement` | Quando `daily` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | SCEE diario sem disponibilidade: `energia_nao_compensada*tarifa_final + energia_compensada*fio_b_final`. |
| Valor conta com geracao semanal | `valor_conta_com_geracao_weekly_r` | `sensor.valor_conta_com_geracao_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | Mesma formula SCEE usando acumuladores semanais. |
| Valor conta com geracao mensal | `valor_conta_com_geracao_monthly_r` | `sensor.valor_conta_com_geracao_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | `max(valor_disponibilidade, energia_nao_compensada*tarifa_final + energia_compensada*fio_b_final)`. |
| Valor conta com geracao mensal sem disponibilidade | `valor_conta_com_geracao_sem_disponibilidade_monthly_r` | `sensor.valor_conta_com_geracao_mensal_sem_disponibilidade` | R$ | `measurement` | Quando `monthly` e `Geracao/SCEE` estiverem habilitados | Valor SCEE puro: `energia_nao_compensada*tarifa_final + energia_compensada*fio_b_final`, sem minimo. |
| Valor Fio B compensada diario | `valor_fio_b_compensada_daily_r` | `sensor.valor_fio_b_compensada_diario` | R$ | `measurement` | Quando `daily` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | `energia_compensada_diaria_kwh * fio_b_final_r_kwh`. |
| Valor Fio B compensada semanal | `valor_fio_b_compensada_weekly_r` | `sensor.valor_fio_b_compensada_semanal` | R$ | `measurement` | Quando `weekly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | `energia_compensada_semanal_kwh * fio_b_final_r_kwh`. |
| Valor Fio B compensada mensal | `valor_fio_b_compensada_monthly_r` | `sensor.valor_fio_b_compensada_mensal` | R$ | `measurement` | Quando `monthly` estiver habilitado, houver entidade de geracao ou injecao e o grupo `Geracao/SCEE` estiver habilitado | `energia_compensada_mensal_kwh * fio_b_final_r_kwh`. |

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
   - o `ICMS` aplicado pode ser ajustado por faixa para concessionarias com regra mapeada
   - a base de faixa do ICMS usa `max(consumo_mensal_kwh, disponibilidade_minima_kwh)`
5. Bandeira:
   - `valor_bandeira = kwh_faturado * adicional_bandeira_r_kwh`
6. Disponibilidade:
   - minimo por fornecimento: `30/50/100 kWh`
   - `valor_faturado = max(valor_disponibilidade, valor_calculado)`
   - `valor_disponibilidade = disponibilidade_minima_kwh * tarifa_convencional_final`
7. Fio B:
   - `fio_b_bruto = tusd_fio_b_r_mwh / 1000`
   - `fio_b_final = aplicar_tributos_por_dentro(fio_b_bruto * percentual_ano, ...)`
8. SCEE:
   - `energia_compensada = min(consumo, saldo_creditos + energia_nova)`
   - `energia_nao_compensada = max(consumo - energia_compensada, 0)`
   - `credito_consumido = min(saldo_creditos, energia_compensada)`
   - `credito_energia = max(energia_nova - energia_nova_consumida, 0)`
   - `credito_disponibilidade = max(disponibilidade_minima_kwh - energia_nao_compensada, 0)`
   - `previsao_creditos = max(saldo_creditos - credito_consumido + credito_energia + credito_disponibilidade, 0)`
   - `valor_consumo_scee = valor_energia_nao_compensada + valor_fio_b_compensada`
   - `valor_consumo_faturado = max(valor_disponibilidade, valor_consumo_scee)`
   - consumo, geracao e injecao acumulados agora sao apurados de forma incremental no tempo, com rateio por virada de dia/semana/ciclo mensal
   - quando a entidade de injecao existe, ela e usada como energia compensavel do SCEE
   - auto-consumo usa `max(geracao_acumulada - injecao_acumulada, 0)` quando as duas entidades estao configuradas
   - creditos continuam persistidos e consumidos do mais antigo para o mais novo

Limitacoes atuais da release:

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
