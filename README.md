# Tarifas Energia Brasil

Integracao customizada para Home Assistant que coleta tarifas ANEEL, tributos de concessionarias e calcula estimativas de custo de energia no Brasil (convencional, tarifa branca e cenarios com geracao/SCEE).

## Status

- Versao atual: `0.1.0-alpha.1` (pre-release).
- Escopo inicial: base funcional da integracao + MVP com concessionarias suportadas.
- Concessionaria obrigatoria do MVP: `CPFL-PIRATINING`.

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
- `Tipo de fornecimento` (obrigatorio quando existe entidade de geracao):
  - `monofasico`
  - `bifasico`
  - `trifasico`
- `Quebras de calculo`:
  - `daily`
  - `weekly`
  - `monthly`

Pos-configuracao (options flow):

- Ajuste de concessionaria, frequencia, metodo ANEEL, entidades e quebras.

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
  - acumuladores de consumo/geracao por periodo;
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

- Sempre: componentes tarifarios, tributos, bandeira, Fio B e indicadores base.
- Dependentes de geracao configurada: sensores de conta com geracao, Fio B compensada, auto-consumo e creditos.
- Dependentes de quebras: sensores de valor diario/semanal/mensal.

Tabela resumida de entidades:

| Nome amigavel | ID sugerido | Unidade | Origem | Formula |
|---|---|---|---|---|
| TE convencional | `sensor.te_convencional` | R$/kWh | ANEEL | valor dataset convertido de R$/MWh |
| TUSD convencional | `sensor.tusd_convencional` | R$/kWh | ANEEL | valor dataset convertido de R$/MWh |
| Tarifa convencional bruta | `sensor.tarifa_convencional_bruta` | R$/kWh | Calculo | `TE + TUSD` |
| Tarifa convencional final | `sensor.tarifa_convencional_final` | R$/kWh | Calculo | `bruta / (1 - pis - cofins - icms)` |
| Tarifa branca fora ponta final | `sensor.tarifa_branca_fora_ponta_final` | R$/kWh | Calculo | `(TE + TUSD) por posto com tributos por dentro` |
| Bandeira vigente | `sensor.bandeira_vigente` | texto | ANEEL | ultimo acionamento valido |
| Adicional da bandeira | `sensor.adicional_bandeira` | R$/kWh | ANEEL | adicional homologado convertido de R$/MWh |
| Fio B bruto | `sensor.fio_b_bruto` | R$/kWh | ANEEL | `TUSD_FioB / 1000` |
| Fio B final | `sensor.fio_b_final` | R$/kWh | Calculo | `fio_b_bruto * transicao_ano` + tributos por dentro |
| Valor conta consumo regular mensal | `sensor.valor_conta_consumo_regular_mensal` | R$ | Calculo | `kWh_periodo * (tarifa_final + bandeira)` |

## Calculos detalhados

1. Conversao de unidade:
   - `valor_r_kwh = valor_r_mwh / 1000`
2. Tarifa convencional:
   - `tarifa_convencional_bruta = te + tusd`
   - `tarifa_convencional_final = aplicar_tributos_por_dentro(...)`
3. Tarifa branca por posto:
   - `tarifa_branca_bruta_posto = te_posto + tusd_posto`
   - `tarifa_branca_final_posto = aplicar_tributos_por_dentro(...)`
4. Tributos por dentro:
   - `valor_com_tributos = valor_sem_tributos / (1 - pis - cofins - icms)`
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

Limitacoes atuais da pre-release:

- Sem consumo por posto horario real, a conta de tarifa branca por periodo e estimativa.
- Motor de creditos SCEE esta em modo operacional inicial (incremental) e deve evoluir com validacao em faturas reais.
- Extratores web podem exigir ajuste quando houver mudanca de layout das concessionarias.

## Fixtures e testes de extratores

- Parsers de tributos foram desacoplados para funcoes testaveis.
- Fixtures iniciais:
  - [cpfl_pis_cofins_sample.html](./tests/fixtures/cpfl_pis_cofins_sample.html)
  - [celesc_tributos_sample.html](./tests/fixtures/celesc_tributos_sample.html)
- Em alteracao de parser, atualize fixture e execute `pytest` para evitar regressao silenciosa.

## Links de versao

- [CHANGELOG](./CHANGELOG.md)
- [Releases](https://github.com/ceinmart/tarifas-energia-brasil/releases)
