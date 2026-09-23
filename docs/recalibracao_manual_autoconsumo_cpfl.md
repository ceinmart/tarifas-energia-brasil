<!--
Versão: v1
Criado em: 2026-09-23 14:47 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: C:\tmp\ha.ext\tarifas\tarifas_energia_brasil
Finalidade: Reproduzir manualmente a calibração mensal CPFL e a reconciliação da extensão, com os dados da execução de 23/09/2026.
-->

# Recalibração manual do autoconsumo mensal CPFL

Este procedimento descreve **a execução de 23/09/2026** no HA 2026.9.1 com a extensão Tarifas Energia Brasil 0.3.0. Foram corrigidos os totais **mensais atuais** de consumo, geração e injeção; o autoconsumo mensal resultou de geração menos injeção. Não houve reinício. A execução real usou Python/`urllib.request` por SSH, lendo o token já provisionado apenas em memória no `srv` e chamando as actions REST do HA. Os exemplos YAML abaixo fazem as mesmas chamadas pela interface. Os números abaixo são evidência daquele ciclo, **não valores para reaplicar em outro dia ou ciclo**.

Para uma nova execução, primeiro confirme a causa da divergência e reconstrua as bases do ciclo. Se o contador de origem tiver sido zerado, substituído, corrigido para baixo ou ficado indisponível durante trecho não reconstruível, a subtração simples do contador atual pela base antiga não basta. Não use `utility_meter.calibrate` para esconder uma falha ainda ativa: verifique antes se os **novos deltas** dos medidores e da extensão acompanham os contadores brutos.

## 1. Entidades, ciclo e bases desta execução

| Grandeza | Contador acumulado usado como fonte | Utility meter mensal a calibrar | Base no começo do ciclo |
|---|---|---|---:|
| Consumo importado | `sensor.disjuntor_geral_energia_consumida` | `sensor.energia_consumo_casa_mensal_cpfl` | 2202,06 kWh |
| Geração | `sensor.energia_gerada_acumulada_micro_inversores` | `sensor.energia_gerada_micro_inversores_mensal_cpfl` | 1831,00 kWh |
| Injeção | `sensor.disjuntor_geral_energia_injetada` | `sensor.energia_injetada_casa_mensal_cpfl` | 1125,19 kWh |

O ciclo era `2026-08-D24`, com `next_reset` dos três utility meters em `2026-09-24T00:00:00-03:00`. A entrada da extensão tinha `config_entry_id: 01KQAH2XFT77V9AE3JZ4B05ZZ4`. O sensor de conferência era `sensor.energia_autoconsumo_casa_mensal_cpfl`; o da extensão, `sensor.tarifas_energia_brasil_cpfl_piratining_auto_consumo_mensal`.

As bases vieram do estado restaurado em backup de 25/08, ainda perto do começo do ciclo:

| Grandeza | `last_valid_state` do contador | Mensal no mesmo estado | Cálculo da base |
|---|---:|---:|---:|
| Consumo | 2213,37 | 11,31 | 2213,37 − 11,31 = **2202,06** |
| Geração | 1848,70 | 17,70 | 1848,70 − 17,70 = **1831,00** |
| Injeção | 1138,64 | 13,45 | 1138,64 − 13,45 = **1125,19** |

O backup foi `/mnt/sd/backups.diarios/2026-08-25_020001.Box.tgz`, membro `dados/ha/.storage/core.restore_state`. O estado da extensão no mesmo backup corroborou a base de consumo. O histórico posterior não mostrou queda física dos contadores do disjuntor; houve uma queda temporária de 0,20 kWh na soma de geração. A investigação completa está em [diagnostico_autoconsumo_2026-09-22.md](diagnostico_autoconsumo_2026-09-22.md).

**Em outro ciclo, determine bases novas.** Não reutilize 2202,06, 1831,00, 1125,19 nem a chave `2026-08-D24`. Confirme que as três fontes e os três medidores pertencem ao mesmo ciclo e que as leituras são numéricas em kWh. O `config_entry_id` pode mudar se a integração for recriada.

## 2. Conferência e cálculo antes de qualquer alteração

No HA, abra **Ferramentas de desenvolvedor → Estados** e anote, numa mesma janela curta, os três contadores acumulados, os três utility meters mensais, os dois autoconsumos, `last_updated`, `last_valid_state`, `next_reset` e a presença de `restored`/indisponibilidade nas fontes. Na extensão, confirme `apuracao_fontes.*.ciclo_apurado` e os atributos `geracao_mensal_kwh_apurado` e `injecao_mensal_kwh_apurado`.

Para cada fonte contínua, calcule:

```text
total mensal correto = leitura acumulada atual − base comprovada do ciclo
autoconsumo mensal  = geração mensal correta − injeção mensal correta
```

A leitura pode mudar a qualquer momento. **Recalcule o alvo a partir da leitura mais recente imediatamente antes de cada action.** As actions recebem totais *absolutos*, não parcelas a somar. Repetir um total antigo depois que a fonte avançou pode produzir nova divergência.

Na prévia inicial de 23/09, as leituras foram consumo 2766,69, geração 2173,20 e injeção 1321,53 kWh. Assim, os alvos naquele instante eram 564,63, 342,20 e 196,34 kWh. A prévia da extensão foi aceita com `aplicar: false`; isso não alterou os sensores.

## 3. Backup antes de aplicar

O Codex criou três arquivos em `/dados/ha/bkp.configs` antes das actions. Para repetir manualmente, acesse o `srv` pelo alias configurado (`ssh rede-dmartins-root`) e use um timestamp novo no shell remoto. Verifique que os destinos **não existem** antes de copiar:

```bash
stamp=$(TZ=America/Sao_Paulo date +%Y%m%d-%H%M%S)
backup_dir=/dados/ha/bkp.configs
state_dir=/dados/ha/.storage
integration_state=tarifas_energia_brasil_01KQAH2XFT77V9AE3JZ4B05ZZ4_state

restore_backup="$backup_dir/core.restore_state.codex-bkp.$stamp.reconciliacao-ciclo.json"
extension_backup="$backup_dir/$integration_state.codex-bkp.$stamp.reconciliacao-ciclo.json"
if test -e "$restore_backup" || test -e "$extension_backup"; then
  echo 'Backup ja existe; escolha outro timestamp antes de prosseguir'
else
  cp -- "$state_dir/core.restore_state" "$restore_backup"
  cp -- "$state_dir/$integration_state" "$extension_backup"
fi
```

Execute esse bloco em uma sessão Bash interativa do `srv` e só continue após conferir que **ambos** os arquivos foram criados. Na execução real, um script Python abriu os destinos em modo exclusivo (`xb`) e copiou o conteúdo. Gerou também um JSON de conferência com estados, horários e bases capturados pela API. Seus arquivos exatos foram:

```text
/dados/ha/bkp.configs/core.restore_state.codex-bkp.20260923-141355.reconciliacao-ciclo.json
/dados/ha/bkp.configs/tarifas_energia_brasil_01KQAH2XFT77V9AE3JZ4B05ZZ4_state.codex-bkp.20260923-141355.reconciliacao-ciclo.json
/dados/ha/bkp.configs/autoconsumo-estados.codex-bkp.20260923-141355.reconciliacao-ciclo.json
```

O JSON de conferência é uma cópia das leituras obtidas por `GET /api/states/<entity_id>` para as oito entidades listadas nas seções anteriores, com os campos `state`, `last_updated`, `last_valid_state`, `last_reset` e `next_reset`, além das três bases. O token da API permaneceu apenas em memória no `srv`; não foi salvo nesse JSON. Para uso manual, guarde uma tabela com esses mesmos campos e o horário da coleta.

Os backups são evidência e pontos de recuperação. **Não copie arquivos antigos sobre `.storage` com o HA em execução.** A forma normal de corrigir uma calibração equivocada é recalcular os alvos e chamar novamente as actions oficiais com referências atuais.

## 4. Calibrar os três utility meters mensais

Em **Ferramentas de desenvolvedor → Ações**, selecione `utility_meter.calibrate`. Para cada medidor, informe `target.entity_id` e `data.value`. O Codex chamou `POST /api/services/utility_meter/calibrate` com os mesmos `entity_id` e `value`. Foram três chamadas separadas, cada uma seguida de leitura do contador e do medidor:

| Ordem | `entity_id` | Estado anterior | `value` aplicado | Leitura acumulada usada |
|---:|---|---:|---:|---:|
| 1 | `sensor.energia_consumo_casa_mensal_cpfl` | 559,80 | **564,63** | 2766,69 |
| 2 | `sensor.energia_gerada_micro_inversores_mensal_cpfl` | 325,90 | **342,20** | 2173,20 |
| 3 | `sensor.energia_injetada_casa_mensal_cpfl` | 185,41 | **196,36** | 1321,55 |

Exemplo do YAML da primeira action na interface:

```yaml
action: utility_meter.calibrate
target:
  entity_id: sensor.energia_consumo_casa_mensal_cpfl
data:
  value: 564.63
```

Para as outras duas, troque `entity_id` e `value` pelos da tabela, **após atualizar a leitura e o cálculo**. Cada chamada de 23/09 retornou HTTP 200. A verificação imediata deu `medidor mensal = leitura acumulada atual − base` com resíduo zero. A injeção subiu de 1321,53 para 1321,55 kWh antes da terceira chamada; por isso a calibração usada foi **196,36**, não o valor **196,34** da prévia inicial.

Se a leitura mudar durante a action, aceite o avanço natural do medidor e compare com o novo cálculo. Se não coincidir dentro do arredondamento da fonte, interrompa antes de reconciliar a extensão e investigue o evento.

## 5. Fazer a prévia e reconciliar a extensão

Releia **as três fontes acumuladas** depois das calibrações. Confira que os utility meters já coincidem com `fonte atual − base`. Em **Ferramentas de desenvolvedor → Ações**, selecione `tarifas_energia_brasil.reconciliar_mensal` e use primeiro `aplicar: false`:

```yaml
action: tarifas_energia_brasil.reconciliar_mensal
data:
  config_entry_id: 01KQAH2XFT77V9AE3JZ4B05ZZ4
  ciclo: 2026-08-D24
  totais_kwh:
    consumo: 564.63
    geracao: 342.20
    injecao: 196.37
  referencias_kwh:
    consumo: 2766.69
    geracao: 2173.20
    injecao: 1321.56
  aplicar: false
```

Esse é o payload **exato da segunda prévia em 23/09**, imediatamente antes da aplicação. A injeção avançara mais 0,01 kWh desde a calibração; o utility meter a acompanhou. A resposta `antes_kwh` foi consumo 564,61224973, geração 320,01576120 e injeção 194,24542723; `depois_kwh` foi 564,63, 342,20 e 196,37. A API usada foi `POST /api/services/tarifas_energia_brasil/reconciliar_mensal?return_response`.

Confira na resposta que `ciclo`, `depois_kwh` e `referencias_kwh` são os esperados e `aplicado` é `false`. Então repita o mesmo YAML com **`aplicar: true`**, desde que as três fontes ainda mostrem exatamente os valores de `referencias_kwh`. A action rejeita referências diferentes da leitura atual; nesse caso, recapture as três leituras, recalcule os totais e faça **nova prévia**. Não force os valores antigos.

Em 23/09 a aplicação retornou `aplicado: true` e criou automaticamente o backup interno:

```text
/dados/ha/.storage/tarifas_energia_brasil_01KQAH2XFT77V9AE3JZ4B05ZZ4_reconciliation_20260923T141447117381
```

Essa action alinha os totais mensais **e** as referências acumuladas da extensão para que os próximos eventos somem apenas os novos deltas. Não execute somente as calibrações dos utility meters se a extensão também estiver historicamente divergente.

## 6. Validar depois da aplicação

1. Compare os três utility meters com `fonte acumulada atual − base do ciclo`.
2. Compare `sensor.energia_autoconsumo_casa_mensal_cpfl` com `geração mensal − injeção mensal`.
3. No sensor da extensão, compare `geracao_mensal_kwh_apurado`, `injecao_mensal_kwh_apurado` e o autoconsumo com os três valores acima. Confira que `apuracao_fontes.*.historico_anterior_nao_reconciliado` passou a `false`.
4. Aguarde uma mudança de **geração** e outra de **injeção** e repita as comparações. O valor do autoconsumo pode cair temporariamente se a injeção atualizar antes da geração; compare os mesmos instantes/fontes.
5. Na próxima virada do dia 24, confirme que todos passaram ao novo ciclo sem carregar o ajuste do ciclo anterior.

Na execução real, o primeiro autoconsumo após aplicar foi **145,83 kWh** nos dois sensores (`342,20 − 196,37`). Depois de novas leituras independentes, geração **342,30** e injeção **196,40**, ambos mostraram **145,90 kWh**. O reset de 24/09 ainda não havia ocorrido no momento deste registro.

Uma coleta ANEEL antiga ou falha não bloqueia esses eventos de energia. Os horários `ultima_coleta_bem_sucedida`/`ultima_atualizacao` da tarifa não servem para decidir se o autoconsumo atualizou; observe `last_updated` do sensor e `apuracao_fontes.*.ultima_variacao`.

## Alcance e recuperação

A calibração alterou apenas os **totais mensais correntes**. Não refez valores diários ou semanais, repartição passada da Tarifa Branca, créditos SCEE de ciclos encerrados ou estatísticas históricas. O contador bruto e a base comprovada determinam o alvo; uma diferença fixa antiga, como 14,7097 kWh, **não** deve ser adicionada como offset permanente.

Se a prévia falhar, não aplique. Se uma action tiver sido aplicada com base incorreta, preserve o backup, obtenha as novas leituras e refaça os cálculos antes de nova calibração. Restaurar diretamente `core.restore_state` ou o arquivo de estado da extensão enquanto o HA está em execução pode sobrescrever eventos posteriores. Nenhuma etapa deste procedimento requer reinício; qualquer reinício do HA depende de autorização específica do usuário.
