<!--
Versão: v7
Criado em: 2026-09-22 17:35 -03:00
Alterado em: 2026-09-22 18:12 -03:00
Alterado em: 2026-09-23 10:34 -03:00
Alterado em: 2026-09-23 11:02 -03:00
Alterado em: 2026-09-23 14:03 -03:00
Alterado em: 2026-09-23 14:15 -03:00
Alterado em: 2026-09-23 14:49 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: C:\tmp\ha.ext\tarifas\tarifas_energia_brasil
Finalidade: Registrar investigação, plano inicial, aplicação autorizada nos templates e aprofundamento da divergência de injeção.
-->

# Autoconsumo: diagnóstico e plano de correção

> Estado vigente: a seção **Reconciliação aplicada em 23/09/2026 (v6)** registra a execução do plano. As seções anteriores permanecem como histórico; recomendações já executadas nelas não são pendências atuais.

> Histórico: as seções iniciais registram a investigação v1 anterior à aplicação. A seção **Execução autorizada e investigação aprofundada (v2)**, ao final, atualiza o estado de execução e resolve a pendência sobre a injeção. Os valores originais foram preservados como evidência do instante inicial.

## Resultado

A referência solicitada está correta: autoconsumo no período = geração no período − injeção no mesmo período, para a instalação descrita, sem armazenamento ou outra fonte no balanço. O consumo importado do disjuntor não entra nessa subtração. O consumo total das cargas seria importação + autoconsumo.

Consulta em 22/09/2026, aproximadamente 17:23–17:33, America/Sao_Paulo. Os quatro valores informados pelo usuário foram confirmados pela API.

| Grandeza | Referência CPFL / cálculo A | Sensor divergente | Diferença para A |
|---|---:|---:|---:|
| Geração mensal | 320,50 kWh | — | — |
| Injeção mensal | 183,43 kWh | — | — |
| Autoconsumo calculado A | 137,07 kWh | — | — |
| Autoconsumo do usuário | 137,07 kWh | 159,19 kWh | +22,12 kWh |
| Autoconsumo da extensão | 137,07 kWh | 122,3603 kWh | −14,7097 kWh |

Há dois mecanismos de erro comprovados, distintos. A recuperação dos valores já acumulados também será necessária; corrigir somente o algoritmo não elimina o desvio guardado.

## Escopo e evidências

- Home Assistant 2026.9.1; extensão instalada e checkout local na versão 0.2.4.
- `coordinator.py` e `calculators.py` locais correspondem aos instalados após normalizar finais de linha (SHA-256 comparado).
- Acesso somente de leitura: SSH pelo alias `rede-dmartins-root`, trechos de YAML, campos selecionados de armazenamento da extensão, API de estados e histórico e código instalado do `utility_meter`.
- Comandos de consulta: `ssh rede-dmartins-root` com `grep`/`sed` direcionados e Python enviado por stdin; `docker exec -i ha python -` somente para ler o código instalado do utility_meter. Consultas API: `GET /api/states/<entity_id>`, `GET /api/config` e `GET /api/history/period/<inicio>?filter_entity_id=...&end_time=...&minimal_response&no_attributes`.
- Token permaneceu em memória no servidor, sem exposição ou cópia. Não houve consultas à API FoxESS nem alterações nas fontes.
- Nenhuma configuração real, estado, estatística ou código de produção foi alterado. Nenhuma recarga, calibração ou reinicialização foi executada.
- A consulta pedida desde 23/08 retornou registros apenas a partir de 07/09. Não há evidência suficiente para reconstruir todo o ciclo desde 24/08 pela API de histórico consultada.

## Fontes e ciclo confirmados

| Caminho | Fonte |
|---|---|
| Geração mensal CPFL | `sensor.energia_gerada_acumulada_micro_inversores` → utility_meter |
| Geração acumulada | Soma dos acumulados FoxESS dos microinversores A e B, em `templates.yaml:56` |
| Injeção mensal CPFL | `sensor.disjuntor_geral_energia_injetada` → utility_meter |
| Consumo mensal CPFL | `sensor.disjuntor_geral_energia_consumida` → utility_meter |
| Autoconsumo mensal do usuário | `sensor.auto_consumo_acumulado_sincronizado` → utility_meter |
| Extensão | As mesmas três fontes acumuladas de consumo, geração e injeção |

Em `/dados/ha/utility_meter.yaml`, os quatro medidores mensais usam `cron: "0 00 24 * *"`. Os atributos confirmam último reset em 24/08/2026 e próximo em 24/09/2026, meia-noite local. A extensão usa `dia_leitura_reset_mensal: 24` e chave mensal `2026-08-D24`.

Não se trata de diferença entre mês civil e ciclo CPFL, nem de a extensão usar o consumo importado na fórmula do autoconsumo.

## 1. Sensor do usuário: soma assimétrica e perda de estado

### Implementação observada

`/dados/ha/templates.yaml:81–129`:

1. Dispara apenas quando a geração acumulada muda; não dispara diretamente por alteração da injeção.
2. Obtém diferenças de geração e injeção contra atributos da execução anterior.
3. Soma `delta_geracao - delta_injecao` ao próprio estado, usando `this.state | float(0)`.
4. Permite resultado menor que o anterior, mas declara `state_class: total_increasing`.
5. O utility_meter mensal em `/dados/ha/utility_meter.yaml:11–15` não configura `net_consumption`.

Geração e injeção chegam em instantes diferentes. Uma janela pode ter delta de injeção maior que o de geração sem representar autoconsumo físico negativo. Na implementação instalada do HA, `utility_meter/sensor.py:522–533`, ajustes negativos são ignorados quando `net_consumption` está desligado, mas o último valor válido é atualizado. A subida seguinte é somada normalmente. Assim, a soma dos incrementos positivos excede a variação líquida.

É importante distinguir esse efeito do tratamento das estatísticas de `total_increasing`: o excesso do utility_meter foi comprovado pela regra de ignorar ajustes negativos, e não pela hipótese de que ele somaria todo o acumulado a cada queda.

### Prova numérica em 21/09, dia local completo

| Medida | Valor |
|---|---:|
| Acumulado sincronizado no início | 33,60 kWh |
| Acumulado sincronizado no fim | 37,24 kWh |
| Variação líquida | 3,64 kWh |
| Soma das subidas | 5,92 kWh |
| Soma das 56 quedas, em módulo | 2,28 kWh |
| Autoconsumo mensal: início → fim | 149,82 → 155,74 kWh |
| Aumento indevido nesse dia | 2,28 kWh |

Exemplo real de queda: 21/09 às 08:14:00 local, de 33,95 para 33,93 kWh.

### Segundo defeito: perda do acumulado e da primeira janela

Em 22/09:

- 14:45:29: acumulado sincronizado = 39,90 kWh; geração = 2166,80; injeção = 1319,45.
- 14:46:00: a entidade passou por indisponibilidade/remoção/estado desconhecido.
- 14:46:29: voltou com acumulado = 0,00 kWh; geração = 2166,90; injeção = 1319,46.
- A janela líquida de 0,10 − 0,01 = 0,09 kWh não entrou no medidor mensal.

O histórico também mostra queda de 806,45 para zero em 15/09. O uso de `this.state | float(0)` e a inicialização das referências com os valores atuais explicam a perda quando o estado não está disponível. A sequência é compatível com recarga/recriação, mas o agente que a provocou não foi identificado; não se atribui a causa operacional sem evidência.

## 2. Extensão: perda de energia em intervalos inferiores a um segundo

### Valores internos confirmados

| Grandeza | Utility meter CPFL | Acumulador mensal da extensão | Extensão − referência |
|---|---:|---:|---:|
| Geração | 320,50 | 314,6157612 | −5,8842388 kWh |
| Injeção | 183,43 | 192,25542723 | +8,82542723 kWh |
| Autoconsumo | 137,07 | 122,36033397 | −14,70966603 kWh |

A subtração da extensão está correta para seus valores internos; esses valores já estão divergentes. A atualização de energia funciona por eventos, independentemente da data da última consulta tarifária ANEEL. Não é necessário aumentar consultas externas para resolver este defeito.

### Defeito comprovado no código

Em `custom_components/tarifas_energia_brasil/coordinator.py:696`, o divisor da distribuição temporal é:

```python
total_seconds = max((end - start).total_seconds(), 1.0)
```

O numerador usa a duração real do segmento. Para intervalo positivo menor que um segundo, a soma dos pesos fica abaixo de 1, descartando parte do delta. A mesma expressão existe no cálculo por posto em `coordinator.py:754` e em `tarifa_branca_time.py:381`.

Reprodução em memória extraindo os métodos da versão instalada, sem inicializar a integração, com intervalo no mesmo dia e fuso fixo -03:00:

| Delta de entrada | Intervalo | Energia contabilizada |
|---|---:|---:|
| 0,10 kWh | 0,02 s | 0,002 kWh |
| 0,10 kWh | 0,20 s | 0,020 kWh |
| 0,10 kWh | 1 s | 0,100 kWh |
| 0,10 kWh | 60 s | 0,100 kWh |

### Prova com evento real

Em 17/09/2026, às 12:20:48 local:

- Geração passou de 2098,00 para 2098,20 kWh em 0,043490 segundo.
- O utility_meter mensal passou de 250,80 para 251,00 kWh: +0,20.
- Injeção permaneceu constante.
- Autoconsumo da extensão passou de 99,9957 para 100,0044 kWh: apenas +0,0087.
- A fórmula defeituosa prevê `0,20 × 0,043490 = 0,008698`, reproduzindo o resultado arredondado.

Além disso, o listener lê as três fontes em cada evento e avança os três timestamps válidos mesmo quando apenas uma fonte mudou (`coordinator.py:448–486` e `1140–1153`). Isso favorece intervalos artificiais muito curtos entre atualizações de fontes diferentes e distorce a janela atribuída a cada uma.

### Limite da atribuição histórica

A perda em intervalos inferiores a um segundo é comprovada e explica a deriva observada. Porém, ela sozinha não explica por que a injeção interna está 8,8254 kWh acima da referência: perda por ponderação não cria energia. Há discrepância anterior de base/estado que precisa ser reconciliada. O histórico consultado não cobre o início do ciclo, e não é correto atribuir integralmente os 14,7097 kWh a um único evento ou mecanismo.

Entre o fim de 07/09 e o fim de 22/09, o desvio da extensão cresceu de −3,9989 para −14,7097 kWh. No mesmo intervalo, o desvio do usuário passou de +12,26 para +22,12 kWh.

## Plano de correção

### A. Autoconsumo do usuário: derivar diretamente do período

1. Criar inicialmente um sensor de conferência baseado diretamente em `energia_gerada_micro_inversores_mensal_cpfl - energia_injetada_casa_mensal_cpfl`, sem acumulação recursiva e sem outro utility_meter sobre a diferença.
2. Recalcular por mudanças de ambas as fontes; arredondar apenas o resultado apresentado. Não usar zero como substituto para `unknown`/`unavailable` e não descartar deltas negativos intermediários.
3. Exigir entradas numéricas, unidade kWh e mesmo ciclo. Na transição mensal, comparar os marcadores de ciclo (por exemplo, `next_reset` não nulo e igual), sem exigir igualdade dos microssegundos de `last_reset`. Enquanto apenas um medidor tiver virado, não publicar a diferença entre ciclos distintos.
4. Usar `device_class: energy` e `state_class: measurement` para esse indicador do período, como a extensão já faz. Ele pode diminuir por chegada assíncrona da injeção; não declará-lo `total_increasing`. Se houver necessidade de estatísticas acumulativas/Painel Energia, tratar como requisito separado com fontes e semântica próprias.
5. Migrar o entity_id utilizado pelos painéis e automações com cuidado: o sensor atual pertence à plataforma utility_meter. Preservar o histórico anterior e documentar o ponto de mudança; não criar duas entidades concorrendo pelo mesmo entity_id nem editar o registry diretamente.
6. Revisar os autoconsumos diário e semanal que usam a mesma fonte defeituosa. Aplicar a diferença dos respectivos medidores de geração e injeção, preservando os ciclos correspondentes.
7. Auditar consumidores do antigo acumulador antes de aposentá-lo. Apenas habilitar `net_consumption` pode impedir o descarte das quedas, mas não resolve perda do estado, janelas iniciais perdidas ou bases já incorretas; não é a solução completa recomendada.

### B. Extensão: conservar integralmente cada delta

1. Corrigir as três ocorrências do divisor: usar a duração real positiva. Tratar intervalos zero/negativos explicitamente sem dividir por zero nem apagar silenciosamente um delta legítimo.
2. Garantir `soma(delta_dos_segmentos) = delta_da_fonte`, inclusive em intervalos de microssegundos, viradas de dia/ciclo e fronteiras da Tarifa Branca. Uma parcela final pode absorver o resíduo de ponto flutuante.
3. Separar o timestamp de observação de cada fonte do timestamp da última mudança de outra fonte. Atualizar a referência temporal de uma fonte somente de acordo com a leitura/evento daquela fonte; tratar o rollover de período separadamente.
4. Na coleta tarifária assíncrona, revisar o `now` capturado antes de `await asyncio.gather` e usado depois com leituras atuais. Usar instante coerente com as leituras processadas e preservar proteção contra eventos antigos.
5. Tratar reset real, correção para baixo e indisponibilidade como situações diferentes. Evitar referências zeradas quando a fonte estiver indisponível. Expor a causa e a qualidade da apuração em diagnósticos.
6. Publicar atributos de geração/injeção do período, início do ciclo, fontes e estado de reconciliação para permitir auditar o autoconsumo sem abrir arquivos internos.

### C. Reconciliar o ciclo já contaminado

1. Antes da aplicação, guardar backup dos arquivos operacionais afetados e do estado da integração em `/dados/ha/bkp.configs`, com timestamp e motivo conforme a skill operacional.
2. Após corrigir o mecanismo, capturar numa mesma janela as referências mensais e os acumulados atuais. Reconciliar geração, injeção e consumo da extensão com os medidores CPFL escolhidos pelo usuário e alinhar as referências de leitura subsequentes.
3. Não aplicar offsets permanentes de +14,7097 ou −22,12: são diferenças de um instante e escondem erros futuros. O novo template deve produzir diretamente o valor atual; a extensão precisa de bases mensais consistentes e persistidas.
4. Fazer reconciliação por mecanismo controlado de migração/calibração, com prévia do antes/depois e rollback. Não editar armazenamento interno enquanto o coordinator puder sobrescrevê-lo.
5. Auditar efeitos sobre os valores de conta e créditos que consomem os mesmos acumuladores. Não reconstruir repartição por postos da Tarifa Branca nem créditos históricos apenas com totais mensais; isso exige dados do intervalo correspondente.
6. Preservar o histórico antigo. Correção de estatísticas passadas é uma etapa separada, limitada aos períodos demonstráveis. Não fabricar os dados ausentes de 24/08 a 06/09.
7. Se for necessário garantir igualdade exata com os helpers CPFL sob qualquer reinício/calibração, prever modo opcional que use diretamente as entidades do período e valide seus ciclos. Não substituir as fontes acumuladas atuais por fontes mensais num campo que ainda interprete tudo como contador vitalício.

### D. Critérios de validação da implementação futura

- Regressão: +0,20 kWh em 43,490 ms deve contar +0,20 kWh, não +0,008698.
- Eventos alternados entre as três fontes não podem perder nem duplicar energia.
- Soma dos segmentos diária/mensal e por postos deve conservar o delta original, inclusive em fronteiras e múltiplas atualizações no mesmo segundo.
- Fonte inválida, retorno da fonte, reinício e recarga não podem zerar a base válida ou inventar energia.
- Resets mensais em ordem diferente não devem publicar valores de ciclos misturados.
- No snapshot de referência, ambos devem indicar 137,07 kWh (a extensão pode mostrar 137,0700), com tolerância somente de arredondamento após propagação dos eventos.
- Alterações futuras em geração e injeção devem manter esse vínculo sem offsets fixos; validar também a virada de 24/09.

## Pendências delimitadas

- TODO: implementar e testar as correções; esta tarefa produziu diagnóstico e plano.
- TODO: apurar, se houver outra fonte histórica autorizada, a origem anterior da injeção interna excedente e do saldo inicial divergente. PENDENTE VALIDAR; não impede corrigir o defeito comprovado nem reconciliar o ciclo usando as referências escolhidas.
- TODO: definir e executar a migração do entity_id e os ajustes históricos em etapa de aplicação.

## Referências

- [Home Assistant — Utility Meter](https://www.home-assistant.io/integrations/utility_meter/): tratamento de ajustes negativos e opções de consumo líquido/reset.
- [Home Assistant — Sensor entity](https://developers.home-assistant.io/docs/core/entity/sensor/): semântica de `measurement`, `total` e `total_increasing`.
- A interpretação operacional acima foi verificada também no código da versão HA 2026.9.1 instalada, evitando depender apenas da documentação corrente.

## Execução autorizada e investigação aprofundada (v2)

### Alterações aplicadas em 22/09/2026

Pedido explícito do usuário: permitir subtrações nos utility_meter de autoconsumo, calcular o mensal a partir dos medidores CPFL, eliminar a perda de estado do acumulador e aprofundar a investigação da injeção da extensão.

1. Em `/dados/ha/utility_meter.yaml`, diário e semanal de autoconsumo receberam `net_consumption: true` e `periodically_resetting: false`. A primeira opção contabiliza deltas negativos; a segunda usa a última leitura válida quando a fonte volta de indisponibilidade, pois essa fonte não tem reset periódico.
2. O mensal foi migrado de utility_meter para template em `/dados/ha/templates.yaml`, mantendo `sensor.energia_autoconsumo_casa_mensal_cpfl` como entidade utilizada. O template calcula diretamente geração mensal menos injeção mensal e verifica números e coincidência de `next_reset` antes de ficar disponível.
3. A antiga entidade utility_meter mensal foi renomeada via API WebSocket para `sensor.energia_autoconsumo_casa_mensal_cpfl_legado` e desabilitada no registry. Sua definição foi removida do YAML. O novo template possui unique_id próprio. O histórico do recorder não foi reescrito nem apagado.
4. `sensor.auto_consumo_acumulado_sincronizado` passou a ser um template de estado, recalculável a partir das duas fontes acumuladas, com `state_class: total`. A fórmula é `geracao_acumulada - injecao_acumulada - 847.44`. Não usa `this.state`, nem converte fonte inválida em zero.

O valor 847,44 é a referência de origem calculada uma única vez na migração: `2167,90 - 1319,57 - 0,89`. Preserva os 0,89 kWh existentes, evitando adicionar 847,44 kWh artificialmente aos medidores diário/semanal. Não é correção do desvio mensal nem depende do mês; qualquer variação posterior de geração ou injeção passa integralmente ao acumulador. O offset está documentado em atributo da entidade. Se algum contador físico for substituído/zerado, essa referência deverá ser revista: a fórmula pressupõe continuidade dos contadores de origem.

Os totais diário/semanal anteriores foram preservados; a mudança corrige o tratamento dos próximos deltas. Não houve calibração retroativa desses totais. O template de janela `sensor.auto_consumo_sincronizado`, que não alimenta os utility_meter encontrados, permaneceu na configuração.

### Backups e validação

Backups anteriores às alterações, no servidor:

- `/dados/ha/bkp.configs/templates.codex-bkp.20260922-175650.autoconsumo.yaml`
- `/dados/ha/bkp.configs/utility_meter.codex-bkp.20260922-175650.autoconsumo.yaml`
- `/dados/ha/bkp.configs/core.entity_registry.codex-bkp.20260922-175650.autoconsumo.json`

`docker exec ha python -m homeassistant --script check_config -c /config --json` terminou com **zero erros e zero avisos**. Testes isolados dos templates reais cobriram resultado atual, redução da injeção líquida, indisponibilidade, retorno da fonte, recuperação sem `this.state`, ciclos diferentes e virada alinhada.

A recarga `template.reload` retornou HTTP 200. Como o HA instalado não oferece `utility_meter.reload`, foi solicitada autorização específica de reinício após as 17h; o usuário respondeu “pode continuar”. Foi executado apenas `docker restart ha`.

Estados confirmados após o reinício:

| Entidade | Valor | Estado / observação |
|---|---:|---|
| Autoconsumo acumulado sincronizado | 0,89 kWh | `total`; recuperado sem zerar |
| Autoconsumo mensal CPFL | 137,17 kWh | `measurement`; 320,60 − 183,43 |
| Autoconsumo diário | 3,55 kWh | `total`; valor preservado |
| Autoconsumo semanal | 9,47 kWh | `total`; valor preservado |

A cópia de log exigida pela regra do projeto falhou porque `\\box\dados\ha\home-assistant.log` não estava acessível. A validação operacional foi feita por check_config e API; não se afirma ter validado o log.

Para rollback, os YAML originais estão nos backups acima. A troca do registry deve ser revertida pela API, devolvendo o entity_id ao utility_meter e reabilitando-o após retirar/renomear a entidade template; não copiar o backup inteiro do registry sobre o arquivo em uso. A aplicação do rollback dos utility_meter também requer reinício. Não foi executado rollback.

### Injeção: causa histórica identificada

Esta conclusão substitui a pendência da v1. A extensão não está acima do avanço real do contador do disjuntor: o helper mensal CPFL deixou de contabilizar mais energia que a extensão.

Foram lidos apenas os membros necessários de backups operacionais já existentes:

- `2026-08-25_020001.Box.tgz`: estado da extensão e restore_state dos sensores envolvidos.
- `2026-08-28_020001.Box.tgz`: mesmos campos.
- `2026-09-08_165826.Box.tgz`: mesmos campos e banco histórico `dados/backups/ha/home-assistant_v2_20260908_170010.db.gz`.

O banco histórico foi descompactado numa pasta temporária local do Windows, aberto por SQLite com `mode=ro` e consultado por entity_id/metadata_id e intervalo de datas. Nenhum backup foi restaurado sobre o ambiente real. O banco temporário foi removido após a análise.

| Momento | Injeção mensal da extensão | Helper mensal CPFL |
|---|---:|---:|
| Backup de 25/08 | 13,45 | 13,45 |
| Backup de 28/08 | 28,55049704 | 30,15 |
| Backup de 08/09 | 113,26231754 | 104,04 |
| Coleta de 22/09 | 192,25542723 | 183,43 |

O banco recuperado permitiu observar a origem da inversão. O contador bruto de injeção não teve nenhuma queda nos registros analisados de 24/08 a 22/09, combinando o backup histórico e o histórico atual sobreposto.

#### Evento principal: retorno do HA em 28/08 à noite

Horários locais, America/Sao_Paulo:

| Momento | Contador bruto / última leitura | Mensal CPFL |
|---|---:|---:|
| 28/08 09:36:34, último registro antes da lacuna | 1157,24 | 32,05 |
| 28/08 23:04:09, helper restaurado | `last_valid_state` = 1156,96 | 31,77 |
| 28/08 23:04:13, primeira leitura do disjuntor após retorno | 1166,63 | 31,77 |
| 29/08 07:42:32, primeira subida posterior | 1166,64 | 31,78 |

Há duas parcelas observáveis: 0,28 kWh foram perdidos no retorno a um estado persistido anterior, e 9,39 kWh avançaram no contador durante a lacuna de registros. A diferença total não incorporada é `1166,63 − 1156,96 = 9,67 kWh`.

O primeiro registro de estado do disjuntor após retorno possui `old_state_id = NULL`. O código do utility_meter com `periodically_resetting` habilitado depende do estado anterior do evento, em vez de recuperar o delta contra `last_valid_state`. Sem aquele estado anterior válido, a leitura não entra como consumo; a próxima mudança registra apenas 0,01 kWh. Os registros de `recorder_runs` mostram vários inícios do HA e encerramentos incorretos nesse intervalo, coerentes com o retorno a um checkpoint anterior.

#### Demais perdas e fechamento da diferença

As mudanças de `last_valid_state - valor_mensal`, com `last_reset` permanecendo em 24/08, quantificam energia não preservada na apuração mensal:

| Evento / dia | Energia não contabilizada no helper de injeção |
|---|---:|
| Retorno em 28/08 à noite / primeira subida em 29/08 | 9,67 kWh |
| Outros retornos em 29/08 | 0,15 + 0,01 + 0,35 = 0,51 kWh |
| Retornos em 03/09 | 0,62 + 0,03 = 0,65 kWh |
| Retorno em 11/09 | 0,11 kWh |
| Retorno em 18/09 | 0,01 kWh |
| **Total** | **10,95 kWh** |

Em 11/09, por exemplo, a API com todos os estados também mostrou o helper voltando de 107,28 para 107,17 kWh no retorno do HA. A consulta anterior com resposta mínima não mostrava toda essa sequência. A investigação v2 usa atributos e todos os estados para verificar a persistência.

O início do ciclo foi confirmado por `1125,20 − 0,01 = 1125,19 kWh` na primeira subida de 24/08. Na coleta atual, o contador marca 1319,57. Logo:

```text
Avanço bruto do disjuntor no ciclo = 1319,57 − 1125,19 = 194,38 kWh
Perda no helper CPFL              = 194,38 − 183,43   = 10,95 kWh
Diferença da extensão para bruto  = 194,38 − 192,25542723 = 2,12457277 kWh
Extensão acima do helper          = 10,95 − 2,12457277 = 8,82542723 kWh
```

Assim, a extensão aparentava incrementar a mais na comparação escolhida porque o helper CPFL perdeu mais. A extensão também apresenta subcontagem, compatível com o defeito de distribuição já reproduzido; não se atribui cada parcela histórica dos 2,12457277 kWh a esse defeito sem reproduzir todos os eventos internos.

### Consequências e próximos ajustes identificados

- O novo autoconsumo mensal cumpre a fórmula solicitada e acompanha os helpers atuais. Isso não recupera automaticamente energia que esses helpers perderam antes.
- O helper mensal de geração também apresentou perda de referência: a base inicial era 1831,00 kWh e a base corrente efetiva é 1847,30, diferença de 16,30 kWh. O histórico mostra restaurações temporárias de valores antigos na fonte de geração; isso precisa ser considerado na reconciliação, não interpretado automaticamente como reset físico.
- Para os medidores alimentados por contadores contínuos do disjuntor, a correção preventiva indicada é avaliar/aplicar `periodically_resetting: false` para aproveitar `last_valid_state` em retornos. `net_consumption` é necessário para a diferença de autoconsumo, mas não é a correção para perda da primeira leitura do contador contínuo.
- A recuperação histórica exige reconciliar os medidores com as bases reais do ciclo e tratar também checkpoints antigos restaurados. Mudar a opção não devolve por si só os 10,95 kWh perdidos.
- O escopo aplicado nesta etapa foi o autoconsumo. Os helpers de geração/injeção CPFL e o código da extensão requerem uma etapa adicional de correção e reconciliação. Seus valores históricos não foram recalibrados nesta execução.

## Plano de ação revisado (v3)

Revisão solicitada em 23/09/2026 para abranger uma extensão pública, utilizada com sensores de fabricantes, ritmos de atualização e comportamentos distintos. O objetivo é conservar os deltas válidos, evitar duplicações e explicitar incertezas. Não se promete reconstrução exata quando a origem não fornece informação suficiente.

### 1. Utility meters e fontes deste ambiente

1. TODO: inventariar somente os medidores derivados dos contadores de consumo, injeção, geração e autoconsumo envolvidos; registrar configuração, origem, ciclo, estado e última leitura válida antes de alterar.
2. TODO: configurar `periodically_resetting: false` no mensal de injeção e, após confirmar continuidade da origem, no mensal de consumo e nos demais medidores desses contadores contínuos. Preservar o cron mensal do dia 24: a opção descreve resets da origem, não desativa o ciclo do utility_meter.
3. TODO: configurar o mensal de geração para origem contínua, junto com proteção contra leituras incompletas ou temporariamente antigas dos microinversores. Não supor que `periodically_resetting: false`, sozinho, resolve restauração de valores antigos; ignorar uma queda e aceitar a recuperação pode duplicar energia. A capacidade de distinguir leitura restaurada de medição atual é PENDENTE VALIDAR na origem.
4. TODO: conferir `net_consumption: true` e `periodically_resetting: false` já aplicados no autoconsumo diário/semanal. Não habilitar consumo líquido indiscriminadamente nos contadores unidirecionais.
5. Manter o mensal de autoconsumo como diferença dos dois medidores mensais, validando disponibilidade e ciclo. Ele acompanha o reset das entradas; não precisa de reset próprio.
6. TODO: reconciliar os totais do ciclo usando bases comprovadas e leituras capturadas em uma janela coerente. Os 10,95 kWh e 16,30 kWh são evidências históricas, não offsets a reaplicar. Exibir prévia dos valores e preservar histórico; calibração atual e correção de estatísticas passadas são etapas distintas.

### 2. Contrato das fontes da extensão pública

TODO: documentar e validar por fonte (consumo, geração e injeção) sua unidade, semântica, política de queda/reset e informações disponíveis de tempo/qualidade. Metadados como `state_class` ajudam na validação, mas não provam sozinhos a causa de uma queda.

| Tipo de fonte | Tratamento previsto |
|---|---|
| Contador acumulado contínuo | Delta entre leituras válidas aceitas; recuperação após indisponibilidade contra a referência persistida. |
| Contador com reset periódico ou rollover | Modo explícito com regra de reset ou limite de rollover conhecido; não inferir todo decréscimo como reset. Se o reset ocultar energia entre observações, sinalizar trecho não reconstruível. |
| Acumulado que admite correção negativa | Política explícita para aceitar correções sem criar energia na recuperação; conservar correções assinadas e indicar incerteza sobre o período histórico ao qual pertencem. |
| Energia por intervalo | Suportar somente com identidade/limites de intervalo suficientes para evitar duplicações e distinguir dois intervalos consecutivos de mesmo valor. Sem esse contrato, rejeitar a configuração com orientação clara. |
| Potência instantânea | Não aceitar como contador de energia. Orientar conversão por integração adequada antes de configurar a fonte. |

Os modos adicionais só serão anunciados como suportados após implementação e testes. Configurações existentes exigem migração compatível e indicação das políticas assumidas; não mudar silenciosamente a interpretação dos sensores de outros usuários.

### 3. Apuração independente e conservação de energia

1. TODO: corrigir as três distribuições temporais identificadas para usar duração real positiva. Garantir soma dos segmentos igual ao delta aceito, inclusive abaixo de um segundo; limitar arredondamento à apresentação e controlar resíduos numéricos.
2. TODO: manter leitura aceita, instante e qualidade independentes por fonte. Eventos de uma fonte não avançam a referência de outra. Observação repetida sem novo dado não pode encurtar artificialmente a janela de energia. Separar horário de observação de horário da medição quando a origem fornecer ambos.
3. TODO: serializar alterações do estado compartilhado entre listeners, atualizações assíncronas, virada de ciclo e persistência. Uma mesma leitura não poderá ser processada duas vezes; leituras obtidas após um `await` não devem usar um instante anterior incompatível.
4. TODO: tratar timestamps iguais, duração zero/negativa, eventos repetidos e fora de ordem explicitamente. Descartar como antigo somente com evidência temporal/identidade suficiente; caso ambíguo, manter a referência confiável, registrar pendência e aplicar uma política documentada, sem descartar silenciosamente energia.
5. TODO: calcular autoconsumo como geração menos injeção do mesmo período, preservando resultados negativos temporários por assincronia. Não aplicar `max(delta, 0)` ao autoconsumo. Expor idade das leituras e defasagem; atualização lenta, isoladamente, não é prova de falha.
6. TODO: aceitar indisponibilidade sem usar zero como substituto e preservar referências. Diferenciar ausência inicial de referência de retorno após indisponibilidade: a primeira leitura estabelece base e não representa automaticamente consumo de todo o contador.

### 4. Intervalos lentos, ciclos e Tarifa Branca

TODO: conservar o total conhecido mesmo quando as atualizações ocorrerem a cada minutos ou horas. Quando um delta atravessar meia-noite, mudança de tarifa ou ciclo mensal, repartir pela duração como estimativa explícita, salvo se a fonte fornecer medições intervalares suficientes para atribuição exata.

Exemplo: leituras às 23h55 e 00h10 permitem conhecer o avanço total, mas não provar quanto ocorreu em cada dia. Informar método, janela e energia estimada nos diagnósticos. Lacunas que atravessem vários ciclos precisam atualizar os períodos correspondentes de forma controlada ou registrar pendência de reconciliação; nunca atribuir silenciosamente tudo ao ciclo atual.

TODO: separar rollover do calendário de chegada de medições; evitar misturar ciclos quando fontes reiniciarem em ordens diferentes. Testar fuso configurado e transições de horário de verão para usuários de outras regiões. Não prometer igualdade instantânea entre fontes assíncronas, nem igualdade exata de totais mensais obtidos por diferentes métodos de repartição nas fronteiras.

### 5. Quedas, restauração e persistência

1. TODO: implementar políticas explícitas para reset real, rollover, correção e leitura antiga. Uma queda numérica isolada é ambígua. Quando não houver evidência suficiente, preservar a última referência confiável e sinalizar reconciliação necessária; não criar uma heurística silenciosa baseada em fabricante.
2. TODO: persistir totais, bases, timestamps, ciclos e pendências em um estado consistente e versionado. Testar migração do armazenamento atual e retomada após interrupção entre processamento e gravação.
3. TODO: após reinício, recuperar deltas de contadores contínuos quando houver referência válida e continuidade demonstrável. Registrar perdas não recuperáveis, como resets não observados ou intervalos sem identidade, em vez de prometer recuperação universal.
4. TODO: tratar troca de sensor, mudança de unidade, substituição de equipamento e alteração da política de fonte como migrações de referência. Não interpretar a diferença entre dois equipamentos como consumo.

### 6. Diagnósticos e reconciliação

TODO: expor geração/injeção utilizadas, fontes, início do ciclo, última leitura aceita, idade das medições, política de reset e condição de apuração: válida, defasada, estimada ou pendente de reconciliação. Documentar o significado dessas condições e evitar excesso de atributos mutáveis no recorder.

TODO: fornecer reconciliação controlada com prévia, backup e rollback, sincronizando totais e referências subsequentes. Não modificar armazenamento ativo por fora do coordinator. Auditar impactos sobre conta e créditos; não reconstruir repartição por postos ou créditos históricos apenas com totais mensais.

A reconciliação deste ambiente deve usar referências CPFL já validadas/corrigidas, e não copiar automaticamente os medidores que subcontaram. O valor de 137,07 kWh foi um snapshot histórico; deixa de ser critério numérico fixo de aceite. Comparações futuras exigem mesmo ciclo, mesmas bases e janelas compatíveis.

### 7. Matriz de testes e critérios de aceite

TODO: implementar testes determinísticos e sequências geradas de eventos, usando contadores e relógio simulados; não reiniciar o HA de produção para testar hipóteses.

| Cenário | Resultado exigido |
|---|---|
| +0,20 kWh em 43,490 ms; intervalos de segundos, minutos e horas | Conservar o delta integral, dentro de tolerância numérica documentada. |
| Fontes rápidas/lentas intercaladas e ordens distintas de chegada | Não perder nem duplicar deltas; cada fonte mantém sua referência. |
| Leituras repetidas, intervalos consecutivos iguais, evento antigo e timestamp igual | Deduplicação conforme contrato; ambiguidade explícita quando não houver identidade suficiente. |
| Injeção atualiza antes da geração | Autoconsumo pode diminuir temporariamente; converge com leituras compatíveis sem viés de truncamento. |
| `unknown`, `unavailable`, valor não finito ou unidade incompatível | Não zerar referência nem inventar delta; rejeitar/sinalizar entrada inválida. |
| Retorno após indisponibilidade e primeira instalação | Recuperar diferença demonstrável no retorno; estabelecer base na primeira leitura. |
| Queda e recuperação; reset real; rollover; troca de sensor | Aplicar política configurada; não contar recuperação de leitura antiga como geração nova. |
| Reinício, checkpoint antigo, gravação interrompida e concorrência | Totais e referências consistentes; sem reaplicação de delta já contabilizado; limitações de recuperação sinalizadas. |
| Virada diária/mensal, vários ciclos, Tarifa Branca e horário de verão | Conservar soma dos segmentos e distinguir atribuição exata de estimada. |
| Atualização de instalação existente e calibração repetida | Migração preserva estado compatível; reconciliação não soma a mesma correção duas vezes. |

Invariantes: soma dos segmentos = delta aceito; total final = total inicial + soma dos deltas aceitos; autoconsumo = geração − injeção para o mesmo período e método de atribuição. Dados ausentes/ambíguos não podem ser apresentados como apuração exata.

### 8. Ordem de execução e aplicação

1. TODO: concluir contrato das fontes e testes que reproduzem os defeitos; implementar conservação de deltas, referências independentes e controle de concorrência.
2. TODO: implementar políticas de recuperação/reset, persistência, migração e diagnósticos; executar a matriz de testes antes de preparar uma versão pública.
3. TODO: aplicar correções locais dos utility_meter e fontes com backup em `/dados/ha/bkp.configs`, validação da configuração e conferência das entidades.
4. TODO: preparar atualização da extensão com notas de compatibilidade, documentação dos modos suportados e rollback; reconciliar somente após as duas apurações estarem corrigidas.
5. TODO: validar em produção por leituras antes/depois e por uma virada de ciclo, incluindo estimativas e pendências eventualmente encontradas.

Preferir recarga granular quando suportada. Por determinação explícita do usuário, qualquer reinício do Home Assistant depende de autorização específica, independentemente do horário. A revisão deste plano não autoriza reinício nem constitui aplicação das correções.


## Implementacao autorizada em 23/09/2026 (v4)

Pedido: ajustar sensores reais e publicar a extensao, sem reiniciar o HA.

- Configuracao real: 15 utility_meter de consumo/injecao do disjuntor, geracao individual A/B e soma receberam `periodically_resetting: false`. Os nove de geracao tambem receberam `net_consumption: true`, para compensar simetricamente uma leitura temporariamente antiga e sua recuperacao. Diario/semanal de autoconsumo ja tinham ambas as opcoes. Cron e IDs foram preservados.
- O template de soma dos microinversores agora rejeita atributos `restored` em qualquer entrada e protege a conversao numerica no proprio estado. Valores antigos numericos sem esse atributo nao podem ser identificados apenas pelo valor; o tratamento assinado nos medidores de geracao impede vies por descartar somente a queda.
- Backups: `/dados/ha/bkp.configs/utility_meter.codex-bkp.20260923-104110.contadores-continuos.yaml` e `/dados/ha/bkp.configs/templates.codex-bkp.20260923-105123.geracao-disponibilidade.yaml`.
- `docker exec ha python -m homeassistant --script check_config -c /config --json`: zero erros e zero avisos depois das alteracoes.
- Nenhuma recarga nem reinicio foi executado. Configuracao em disco aguarda o reinicio manual solicitado pelo usuario, depois de instalar a release.
- Extensao 0.3.0: conservacao compartilhada de deltas, referencias por fonte, quatro politicas de queda, conversao de unidades, rejeicao de dados invalidos, rateio estimado limitado a 366 dias, ciclos SCEE pendentes, persistencia consistente, action de reconciliacao com previa/backup e diagnósticos.
- Validacao local: 167 testes, Ruff, compilacao e links/versoes; importacao em processo isolado usando as bibliotecas reais do HA passou. O pacote instalado nao foi substituido.
- O documento publico da 0.3.0 descreve compatibilidade e limitacoes. Este diagnostico operacional permanece local, fora do commit publico.

### Pendencias apos instalacao e reinicio pelo usuario

- Conferir os parametros ativos e a apuracao em producao.
- Reconciliar o ciclo com leituras atuais e bases comprovadas; os valores historicos nao foram recalibrados nesta manutencao. A action nova ainda depende da instalacao da release.
- Conferir a virada de ciclo. Creditos historicos, diario/semanal, estatisticas e reparticao por postos nao foram reconstruidos.
- Energia por intervalo e potencia nao sao modos de entrada desta release. Contadores de rollover exigem limite conhecido e no maximo uma volta entre leituras; quedas ambiguas ficam pendentes.


### Publicacao concluida

- Commits publicados: `08a7ec7` (implementacao) e `dbcfd1c` (distincao entre reset configurado e queda ambigua).
- Release estavel: https://github.com/ceinmart/tarifas-energia-brasil/releases/tag/v0.3.0
- Tag `v0.3.0` confirmada em `dbcfd1c2578c30abf377554cbf3713f94d8ad10e`; publicada em 23/09/2026 11:03:31 -03:00.
- Python CI, HACS e Hassfest passaram no commit final. Os 167 testes locais passaram.
- Nenhum reinicio, reload ou instalacao da extensao em producao foi executado. O usuario fara a atualizacao e o reinicio.

## Verificação pós-reinício e plano de reconciliação (v5)

Consulta somente de leitura à API do HA em 23/09/2026, aproximadamente 13h35 (America/Sao_Paulo), após o usuário instalar a extensão 0.3.0 e reiniciar o HA. A versão instalada foi confirmada no `manifest.json`. Corrige uma interpretação anterior: **não há evidência de falha atual na atualização dinâmica da energia**. O horário antigo de coleta tarifária foi confundido com o horário de atualização dos acumuladores de energia.

| Grandeza | HA em 22/09 | HA em 23/09 | Delta HA | Extensão em 22/09 | Extensão em 23/09 | Delta extensão |
|---|---:|---:|---:|---:|---:|---:|
| Geração mensal | 320,50 | 325,20 | +4,70 | 314,6157612 | 319,3157612 | +4,70 |
| Injeção mensal | 183,43 | 184,97 | +1,54 | 192,25542723 | 193,79542723 | +1,54 |
| Autoconsumo | 137,07 | 140,23 | +3,16 | 122,36033397 | 125,52033397 | +3,16 |

Os desvios entre as duas apurações permaneceram constantes, dentro do arredondamento: extensão − HA = −5,8842388 kWh em geração, +8,82542723 kWh em injeção e −14,70966603 kWh em autoconsumo. O valor da extensão mudou de 122,3603 para 125,5203 kWh; portanto, os eventos novos estão chegando e sendo contabilizados. A release corrigiu o processamento futuro, mas preservou os acumuladores históricos. Os utility meters também conservaram os totais anteriores; `periodically_resetting: false` evita um mecanismo de perda futura, sem restaurar o que já foi perdido.

No snapshot da extensão, `last_updated = 2026-09-23T16:35:53Z` corresponde a 13h35 local. Os diagnósticos por fonte mostram `ultima_variacao` no dia 23/09. Já `ultima_coleta_bem_sucedida` e `ultima_atualizacao` com horário de 22/09 21h09 referem-se à obtenção dos **dados tarifários ANEEL**. A tentativa posterior falhou por conexão; `usando_dados_anteriores = true` indica uso das tarifas em cache. Isso não impede o listener de energia em `coordinator.py:_handle_tracked_state_change` de atualizar o snapshot. A periodicidade de 72 horas é da coleta externa, não das leituras dos disjuntores e microinversores. Assim, aguardar a próxima coleta ANEEL não corrigirá os 14,7097 kWh.

### Causa do desvio que parece ser falha de atualização

O ciclo em andamento começou em 24/08. A investigação v2 comprovou que o helper mensal de injeção perdeu 10,95 kWh em retornos do HA, enquanto a extensão havia perdido 2,12457277 kWh em relação ao avanço bruto até 22/09. Daí a extensão aparecer 8,82542723 kWh acima desse helper, mesmo estando abaixo do contador bruto. O helper mensal de geração também carregava referência antiga divergente; parte da perda da extensão ocorreu pelo defeito de intervalos inferiores a um segundo da versão anterior. A evidência disponível não permite atribuir toda a diferença histórica de geração a um único mecanismo. Nenhum desses valores antigos foi recalibrado com a atualização para 0.3.0.

### Plano corrigido para este ambiente

1. Capturar fontes acumuladas, helpers mensais e acumuladores internos da extensão numa mesma janela, com a chave de ciclo, unidades, horários e qualidade das leituras. Confirmar novamente que novos deltas de geração e injeção coincidem. Separar a saúde da coleta ANEEL da saúde da apuração energética.
2. Reconstruir, com as bases comprovadas do dia 24/08 e os eventos de restauração disponíveis, os totais corretos do ciclo para **consumo, geração e injeção**. O helper mensal de injeção e o de geração não podem ser copiados como referência autoritativa antes dessa validação: já se comprovou subcontagem histórica. Qualquer trecho sem evidência suficiente fica marcado como pendente, sem inventar energia.
3. Se o ciclo `2026-08-D24` ainda estiver ativo, preparar prévia de calibração dos utility meters afetados e prévia da action `tarifas_energia_brasil.reconciliar_mensal`, fornecendo totais **absolutos** de consumo, geração e injeção, além das três leituras acumuladas atuais (`referencias_kwh`). A action usa `aplicar: false` por padrão. Validar ciclo, fontes, prévia, backup e rollback antes de aplicar a calibração dos utility meters e a reconciliação da extensão pelos mecanismos oficiais; não editar `.storage` diretamente. A calibração atual não reconstitui estatísticas, créditos ou repartição passada por postos.
4. Se o reset de 24/09 já tiver ocorrido, não transportar o desvio de 14,7097 kWh ao ciclo novo nem usar a action do ciclo corrente para corrigir o ciclo encerrado. Conferir os três acumuladores desde zero no ciclo novo; tratar o anterior por procedimento histórico específico e apenas com dados demonstráveis.
5. Depois da reconciliação ou da virada, verificar duas mudanças independentes de geração e injeção, a diferença geração − injeção e a permanência do alinhamento após indisponibilidade/reinício futuro. Por determinação do usuário, **nenhum reinício do HA** será feito sem autorização específica.
6. Melhorar, numa revisão futura da extensão, os nomes ou a apresentação dos diagnósticos para distinguir claramente `ultima_coleta_bem_sucedida` (tarifas ANEEL), `ultima_variacao` (fonte energética) e atualização do sensor. Isso corrige a ambiguidade observacional; os números coletados não justificam alterar novamente o algoritmo de eventos da 0.3.0.

Esta revisão é diagnóstico e plano. Não executou calibração, action de reconciliação, recarga, atualização ou reinício.

## Reconciliação aplicada em 23/09/2026 (v6)

Execução autorizada pelo usuário no ciclo `2026-08-D24`, entre 14h13 e 14h15 (America/Sao_Paulo). Foram utilizadas as actions oficiais `utility_meter.calibrate` e `tarifas_energia_brasil.reconciliar_mensal`, sem editar armazenamento ativo e sem reiniciar/recarregar o HA.

### Bases e prévia

O `core.restore_state` do backup operacional de 25/08 mostrou, no início do ciclo, consumo mensal 11,31 kWh com `last_valid_state = 2213,37`, geração mensal 17,70 com `last_valid_state = 1848,70` e injeção mensal 13,45 com `last_valid_state = 1138,64`. Daí resultam as bases acumuladas **2202,06**, **1831,00** e **1125,19 kWh**, respectivamente. O estado da extensão no mesmo backup corroborou a base de consumo: leitura 2213,54 e mensal 11,479166 kWh. O histórico disponível de 07/09 em diante mostrou zero quedas numéricas nos contadores brutos de consumo e injeção e apenas uma queda temporária de 0,20 kWh na soma de geração. A investigação anterior já havia verificado o avanço da injeção desde 24/08.

Às 14h13, a prévia da extensão, com `aplicar: false`, aceitou os totais calculados `leitura acumulada − base do ciclo`: consumo 564,63; geração 342,20; injeção 196,34 kWh. Nenhuma alteração ocorreu nessa prévia.

### Backups anteriores às actions

Todos estão em `/dados/ha/bkp.configs`:

- `/dados/ha/bkp.configs/core.restore_state.codex-bkp.20260923-141355.reconciliacao-ciclo.json`
- `/dados/ha/bkp.configs/tarifas_energia_brasil_01KQAH2XFT77V9AE3JZ4B05ZZ4_state.codex-bkp.20260923-141355.reconciliacao-ciclo.json`
- `/dados/ha/bkp.configs/autoconsumo-estados.codex-bkp.20260923-141355.reconciliacao-ciclo.json`

A própria action da extensão também salvou o snapshot anterior em `/dados/ha/.storage/tarifas_energia_brasil_01KQAH2XFT77V9AE3JZ4B05ZZ4_reconciliation_20260923T141447117381`; a existência desse arquivo foi confirmada. Esses arquivos são pontos de recuperação, não devem ser copiados sobre o armazenamento com o HA em execução. Para reverter valores correntes, recalcular pelo contador bruto e usar calibração/reconciliação controladas.

### Aplicação e resultado imediato

| Medidor mensal | Antes | Calibração inicial | Verificação imediata |
|---|---:|---:|---|
| Consumo CPFL | 559,80 | 564,63 | `2766,69 − 2202,06 = 564,63` |
| Geração CPFL | 325,90 | 342,20 | `2173,20 − 1831,00 = 342,20` |
| Injeção CPFL | 185,41 | 196,36 | `1321,55 − 1125,19 = 196,36` |

As três chamadas `utility_meter.calibrate` retornaram HTTP 200 e resíduo zero contra o contador bruto imediatamente após cada action. Em seguida, a prévia da extensão informou antes: consumo 564,61224973; geração 320,01576120; injeção 194,24542723 kWh. A action com `aplicar: true` aceitou os totais absolutos 564,63; 342,20; 196,37 kWh e as referências brutas 2766,69; 2173,20; 1321,56 kWh. A injeção avançou 0,01 kWh entre as duas etapas, e o helper acompanhou esse avanço.

O primeiro estado após a aplicação mostrou autoconsumo mensal **145,83 kWh** tanto no template CPFL quanto na extensão (`342,20 − 196,37`). No evento seguinte de injeção, ambos passaram a **145,82 kWh** (`342,20 − 196,38`). Diagnósticos da extensão passaram a marcar `historico_anterior_nao_reconciliado: false` nas três fontes.

### Limites e validação restante

- Validação posterior concluída: a geração acumulada passou de 2173,20 para 2173,30 kWh e ambos os mensais de geração passaram de 342,20 para 342,30. A injeção acumulada passou de 1321,56 para 1321,59 kWh; ambos os mensais de injeção passaram de 196,37 para 196,40. O template e a extensão convergiram para **145,90 kWh** de autoconsumo (`342,30 − 196,40`).
- TODO: confirmar a virada mensal em 24/09 antes de declarar o próximo ciclo estável.
- A calibração foi dos **totais mensais atuais**. Não redistribui retroativamente o consumo por dia/semana/posto da Tarifa Branca, nem recalcula créditos SCEE e estatísticas anteriores. Qualquer correção desses históricos exige série temporal suficiente e procedimento separado.
- A falha de coleta ANEEL continua independente. Ela não impede o acompanhamento energético por eventos; a nomenclatura dos diagnósticos tarifários merece ajuste futuro para evitar confusão.

## Procedimento manual documentado (v7)

O passo a passo para repetir a calibração, com fórmulas, pré-condições, actions YAML, payloads e valores exatos desta execução, está em [recalibracao_manual_autoconsumo_cpfl.md](recalibracao_manual_autoconsumo_cpfl.md). Esta seção documental não executou nova action nem alterou o HA.
