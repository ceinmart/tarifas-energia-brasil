<!--
Versao: v1
Criado em: 2026-09-23 10:57 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas_energia_brasil
Finalidade: Documentar apuracao de energia, contratos das fontes e migracao da versao 0.3.0.
-->

# Documentacao tecnica 0.3.0

## Problema corrigido

A distribuicao usava um divisor minimo de um segundo mesmo quando o intervalo
observado era menor. Um delta de 0,20 kWh em 43,490 ms resultava em apenas
0,008698 kWh. Agora a soma das parcelas conserva os 0,20 kWh. A ultima parcela
absorve o residuo de ponto flutuante. As tres distribuicoes usam a mesma rotina.

Um evento de uma fonte tambem avancava os horarios de outras fontes sem variacao.
Agora cada fonte conserva sua referencia e utiliza o `last_updated` da entidade
quando disponivel. Leituras repetidas nao alteram a referencia. A coleta de tarifas
nao reutiliza um horario anterior ao I/O para processar leituras obtidas depois.

## Fontes suportadas e migracao

As entradas continuam sendo contadores **acumulados de energia**. Wh e MWh sao
normalizados para kWh; por compatibilidade, unidade ausente significa kWh.
Valores negativos do contador, NaN, infinito, fontes `measurement`, unidades
incompativeis, `unknown`, `unavailable` e estados marcados `restored` nao alimentam
a apuracao. Uma correcao negativa de um contador positivo e diferente de um valor
absoluto negativo.

| Politica | Queda do contador |
|---|---|
| `continuous` | Preserva a referencia; sinaliza queda ambigua. Recuperacao acima da referencia conta somente o avanco real. |
| `signed` | Aplica a diferenca negativa no periodo de chegada. Recuperacao compensa a queda. O periodo historico correto da correcao e desconhecido. |
| `reset` | Assume reset real para zero por contrato do usuario; conta a leitura pos-reset no periodo de chegada e sinaliza a lacuna anterior. |
| `rollover` | Assume exatamente uma volta no limite exclusivo configurado: `limite - anterior + atual`. Limite e leituras devem ser compativeis. |

O padrao e `continuous`, inclusive para entradas existentes sem a nova opcao.
**Mudanca de comportamento:** versoes anteriores reancoravam qualquer queda.
Usuarios com sensores que zeram precisam selecionar `reset`; correcoes conhecidas
pedem `signed`. Nao existe inferencia universal capaz de distinguir reset, leitura
antiga e correcao apenas por dois valores numericos. A configuracao expressa o
contrato, nao prova que a origem o respeitou.

Energia por intervalo e potencia instantanea nao sao novos modos suportados nesta
versao. Converta para um acumulado adequado antes de configurar. Fontes de energia
por intervalo que se anunciem incorretamente como acumulados nao podem ser
identificadas automaticamente. Multiplos resets/rollovers nao observados nao podem
ser recuperados integralmente.

Trocar a entidade de origem estabelece uma nova referencia, conserva os totais e
sinaliza reconciliacao. Troca fisica que reutiliza o mesmo entity_id e nao produz
uma queda nao e detectavel automaticamente; exige conferência/reconciliacao.

## Tempo, ciclos e assincronia

- Delimitacao por fuso configurado no HA; duracoes usam timestamps reais, incluindo
  transicoes de horario de verao. Dias de leitura 29–31 usam o ultimo dia nos meses
  mais curtos, mantendo a chave do dia configurado.
- Rateio proporcional ao tempo conserva energia, mas a distribuicao por dia/ciclo/
  posto e **estimada**. Um delta entre 23h55 e 00h10 nao revela a distribuicao real.
- Lacunas de ate 366 dias sao processadas com custo limitado. Acima disso, a base
  e o delta potencial ficam pendentes; nao ha descarte seguido de reancoragem.
- Timestamp igual com valor diferente ou evento antigo fica pendente. Uma leitura
  posterior valida pode recuperar o delta completo contra a referencia preservada.
- A virada de meia-noite atualiza a visualizacao do periodo sem avancar referencias
  de fontes inalteradas. Dados do ciclo anterior nao sao apresentados como atuais.
- Autoconsumo pode ser temporariamente negativo enquanto as fontes se atualizam.
  Os valores do mesmo periodo obedecem `geracao - injecao`, sem truncar em zero.
- Fontes atrasadas podem deixar o periodo atual provisoriamente em zero. Os
  diagnosticos mostram o ciclo efetivamente apurado e a idade da ultima variacao.
  Essa idade nao prova indisponibilidade: um contador pode permanecer constante.
- Creditos de ciclos encerrados aguardam consumo e exportacao (ou geracao no modo
  alternativo) e fecham em ordem, uma vez. Uma fonte sem novas variacoes pode adiar
  o fechamento; nenhum credito e inventado para completar a fonte ausente.
- O fechamento e uma estimativa tarifaria: usa o contexto capturado no primeiro
  rollover observado. Nao reconstrói tarifas historicas que nao foram coletadas.

## Persistencia e diagnosticos

Totais, referencias, ciclos pendentes e marcador do ultimo ciclo fechado sao
serializados juntos em copias independentes. As mutacoes de energia sao sincronas
no event loop, sem `await` entre leitura, acumulacao e atualizacao das bases.
Um checkpoint antigo consistente pode recuperar energia de contadores continuos
pela diferenca posterior. Reset nao observado ou dados ausentes continuam sendo
limitacoes. Nao ha garantia de recuperar energia que a propria origem perdeu.

O envelope Store permanece compativel com a versao anterior; o payload inclui
`energy_schema: 2` e campos opcionais. Na carga de payload antigo, os totais sao
preservados e marcados como historico nao reconciliado. A atualizacao nao reescreve
estatisticas nem recompõe automaticamente os creditos anteriores.

Diagnosticos incluem `apuracao_fontes`, `ciclos_pendentes`,
`incremental_intervalos_longos_pendentes`, totais mensais apurados e
`metodo_rateio: proporcional_ao_tempo_estimado`. Os sensores de autoconsumo exibem
as referencias de apuracao mesmo com atributos extras desabilitados. Campos de
idade usam a ultima variacao aceita; eventos invalidos preservam as referencias.

## Reconciliacao mensal

A action `tarifas_energia_brasil.reconciliar_mensal` aceita tres totais mensais
absolutos e as tres leituras acumuladas que lhes servem de referencia. O ciclo
deve ser o atual; as referencias precisam coincidir com as fontes atuais em kWh.
Requer as tres fontes configuradas e validas. Nao e uma soma de offsets repetiveis.

Exemplo **ficticio**, substitua todos os valores pelas referencias verificadas:

```yaml
action: tarifas_energia_brasil.reconciliar_mensal
data:
  config_entry_id: SUBSTITUA_PELO_ID_DA_ENTRADA
  ciclo: "2026-08-D24"
  totais_kwh:
    consumo: 200
    geracao: 300
    injecao: 180
  referencias_kwh:
    consumo: 5000
    geracao: 4000
    injecao: 2000
  aplicar: false
```

1. Solicite a resposta da action para conferir `antes_kwh` e `depois_kwh`.
2. Capture novamente as referencias se as fontes avancarem. Use `aplicar: true`
   somente com os totais coerentes com essas referencias.
3. A action salva um backup Store com chave unica retornada em
   `backup_storage_key` antes da alteracao. Se o estado mudar durante a gravacao,
   aborta a aplicacao para nao sobrescrever um evento concorrente.
4. Repetir os mesmos totais e referencias aplica valores absolutos, sem somar
   novamente a correcao. Novas leituras exigem nova referencia.

A calibracao mensal nao corrige diario/semanal, estatisticas passadas, reparticao
por postos nem creditos de ciclos ja encerrados. O consumo mensal por postos
pode continuar divergente do total calibrado; o diagnostico sinaliza essa
condicao. Ciclos anteriores pendentes exigem analise propria. Nao inferir custos
historicos exatos apenas a partir dos totais corrigidos.

## Atualizacao e rollback

1. Guarde backup da configuracao e do estado da integracao antes do upgrade.
2. Instale 0.3.0 pelo HACS e reinicie o HA quando conveniente. Revise as politicas
   das fontes nas opcoes da integracao.
3. Confira unidades, referencias e diagnosticos; reconcilie apenas bases comprovadas.
4. Para rollback completo, use o pacote anterior e o estado anterior correspondente
   ao mesmo backup, com a integracao parada. Nao copie armazenamento sobre um
   coordinator ativo. Um rollback perde a apuracao posterior ao backup, que precisa
   ser novamente reconciliada. A action nao oferece restauracao automatica.

Esta release publica codigo; nao instala nem reinicia automaticamente o HA.

## Validacao

Os testes cobrem regressao de 43,490 ms, microssegundos a horas, eventos alternados,
quedas/recuperacoes, politicas explicitas, indisponibilidade, lacunas de 60 dias e
mais de 366 dias, ciclos atrasados, persistencia e retomada, troca de fonte,
unidades invalidas, NaN/infinito, horario de verao, meses curtos e reconciliacao
com evento concorrente durante backup. Sequencias geradas verificam conservacao
dos tres contadores e dos postos. A suite existente tambem permanece obrigatoria.

Validacoes de publicacao: pytest, Ruff, compilacao Python, consistencia de versao e
links locais; workflows Python CI, HACS e Hassfest no commit publicado.
