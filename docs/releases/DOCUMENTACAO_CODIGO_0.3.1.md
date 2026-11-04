<!--
Versao: v1
Criado em: 2026-11-04 10:00 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas_energia_brasil
Finalidade: Documentar o limite de compensacao SCEE, a validacao e os limites da release 0.3.1.
-->

# Documentacao tecnica 0.3.1

## Mudanca

O calculo anterior compensava ate todo o consumo com creditos e injecao. Quando
o resultado ficava abaixo da disponibilidade minima, acrescentava a diferenca
ao saldo de creditos. Isso podia manter um saldo de kWh plausivel, mas cobrava
kWh demais pela parcela de compensacao e de menos pela tarifa cheia.

Agora `calcular_scee_creditos_prioritarios` limita a compensacao a
`max(consumo_importado - disponibilidade_minima, 0)`. Dentro desse limite,
consome primeiro os creditos anteriores e depois a injecao do ciclo. A injecao
nao usada permanece como credito real. A disponibilidade minima nao cria
credito sintetico. O valor SCEE cobra os kWh nao compensados pela tarifa
convencional final e aplica o Fio B final apenas aos kWh compensados.

Para um fornecimento trifasico com 382 kWh importados e 306 kWh injetados,
o limite e 282 kWh. A simulacao usa 282 kWh compensados, 100 kWh nao
compensados e deixa 24 kWh para o proximo ciclo. Os testes cobrem tambem
credito anterior, consumo abaixo do minimo e as combinacoes 391/293 e
564/193 kWh. Os valores sao cenarios de validacao, nao dados de uma unidade
consumidora publicada.

## Compatibilidade e limites

- O formato do armazenamento persiste sem mudanca. Creditos de ciclos ja
  encerrados nao sao recalculados pela atualizacao.
- A data de fechamento mensal configurada continua fixa. Divergencias com a
  leitura efetiva da distribuidora exigem reconciliacao separada.
- Adicional de bandeira, tributos do mes, CIP e ajustes da fatura continuam
  sujeitos a verificacao propria; esta release altera apenas a alocacao SCEE.
- Sem entidade de injecao, a geracao continua sendo usada como estimativa
  alternativa da energia disponivel para compensacao.

## Atualizacao

Instale a versao 0.3.1 pelo HACS quando o Home Assistant estiver disponivel.
O carregamento de codigo Python da integracao exige reinicio do HA em momento
escolhido pelo operador. Esta publicacao nao executa instalacao, reinicio ou
reconciliacao no servidor.

## Validacao

- `python -m pytest -q`: suite completa aprovada.
- `python -m ruff check custom_components/tarifas_energia_brasil/calculators.py tests/test_calculators.py tests/test_coordinator_reset.py`: aprovado.
- `git diff --check`: aprovado.
- Conferir no commit publicado os workflows Python CI, HACS e Hassfest.
