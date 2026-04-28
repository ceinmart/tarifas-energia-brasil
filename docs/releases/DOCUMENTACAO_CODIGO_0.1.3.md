# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.3  
Gerado em: 2026-04-27 14:45:00 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra o estado tecnico da release `0.1.3`. Alteracoes historicas completas ficam no `CHANGELOG.md`.

## Atualizacao 0.1.3

A versao `0.1.3` corrige dois pontos operacionais importantes:

- restauracao do ultimo resultado valido salvo no Home Assistant durante o setup;
- leitura correta do alternativo CSV da ANEEL para Fio B da `CPFL-PIRATINING`.

## Resultado em memoria local

O coordinator passa a persistir `last_resultado` no `Store` local do Home Assistant. Esse resultado contem:

- `atualizado_em`;
- `concessionaria`;
- `valores`;
- `coletas_por_chave`;
- `diagnosticos`.

Durante o setup, `async_ensure_state_loaded()` e executado antes da criacao das entidades, permitindo que sensores nascam com os ultimos valores validos quando a coleta externa inicial falhar.

Se a coleta falhar e houver `self.data`, o coordinator retorna um novo `ResultadoCalculo` reaproveitando os valores anteriores e adicionando diagnosticos de falha.

## Alternativo CSV da ANEEL

O alternativo CSV passa a:

- processar a resposta em chunks;
- decodificar com `latin-1`;
- detectar delimitador `,` ou `;`;
- remontar linhas quebradas entre chunks;
- aplicar filtros linha a linha;
- manter em memoria apenas registros filtrados.

Essa mudanca corrige o caso em que o datastore CKAN nao retorna `CPFL-PIRATINING`, mas o CSV publicado contem linhas vigentes de Fio B.

## Fio B CPFL-PIRATINING

O filtro usado para componentes tarifarios e:

```json
{
  "SigNomeAgente": "CPFL-PIRATINING",
  "DscComponenteTarifario": "TUSD_FioB"
}
```

O analisador prioriza linha residencial B1, modalidade adequada, `Tarifa de Aplicacao` e vigencia valida.

## Modulos afetados

| Modulo | Mudanca |
|---|---|
| `__init__.py` | Carrega estado persistido antes de criar entidades. |
| `coordinator.py` | Serializa/restaura `last_resultado`. |
| `aneel_client.py` | CSV streaming com delimitador detectado e encoding compativel. |
| `tests/test_coordinator_reset.py` | Testa restauracao de resultado. |
| `tests/test_aneel_client.py` | Testa CSV latin-1, delimitador `;` e Fio B vigente da CPFL-PIRATINING. |

## Testes

A release adicionou cobertura para:

- restauracao de resultado apos restart;
- CSV ANEEL com chunks quebrados, delimitador `;` e encoding latin-1;
- linhas vigentes de Fio B da CPFL-PIRATINING.
