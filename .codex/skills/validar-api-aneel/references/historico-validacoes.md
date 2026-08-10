<!--
Versão: v1
Criado em: 2026-08-10 16:00 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas-energia-brasil
Finalidade: Resumir incidentes ANEEL do projeto que devem orientar futuras revalidações.
-->

# Histórico de validações ANEEL

Usar este arquivo como índice. Confirmar os detalhes nas fontes citadas e no código atual antes de concluir.

## Regressões obrigatórias

| Origem | Situação observada | Verificação atual |
|---|---|---|
| `docs/releases/DOCUMENTACAO_CODIGO_0.1.3.md` | O CKAN não retornava Fio B da CPFL-PIRATINING, embora o CSV tivesse linhas vigentes; CSV podia usar latin-1, `;` e linhas quebradas entre chunks. | Comparar DataStore e arquivo, validar encoding/delimitador/streaming e confirmar seleção de Fio B vigente. |
| `docs/releases/DOCUMENTACAO_CODIGO_0.1.5.md` | Downloads anuais grandes excediam o tempo e baixavam anos desnecessários. | Validar recurso por recurso, ordem por vigência, progresso e encerramento antecipado ao encontrar linha suficiente. |
| `docs/releases/DOCUMENTACAO_CODIGO_0.1.9.md` | DataStore, SQL e CSV retornaram HTTP 500 durante publicação; páginas grandes e contagem total pressionavam o CKAN. | Testar paginação com limite atual e `include_total=false`, observar intermitência e verificar preservação/retry sem tratar fallback como sucesso do primário. |
| `docs/releases/DOCUMENTACAO_CODIGO_0.2.0.md` | CSV automático gerava carga excessiva; fluxo passou a DataStore, Parquet automático só para Fio B e CSV manual cancelável. | Confirmar que os caminhos e a interface atuais respeitam essa separação e que cancelamento descarta resultado parcial. |
| `docs/releases/DOCUMENTACAO_CODIGO_0.2.1.md` | DuckDB não possuía wheel em Python 3.14/musl/ARM64; PyArrow tornou-se obrigatório e fallback de engine. | Confirmar requisitos do manifesto e executar o caminho Parquet com a engine realmente disponível, registrando a engine usada. |

## Invariantes do projeto

- Descobrir recursos atuais no catálogo ANEEL antes de testar IDs codificados.
- Validar vigência, campos e semântica; disponibilidade HTTP não basta.
- Tarifas e bandeiras usam DataStore no ciclo automático atual.
- Fio B tenta DataStore e pode usar Parquet automaticamente.
- CSV é uma atualização manual em background e cancelável na versão 0.2.x.
- Em falha externa, um snapshot válido anterior deve ser preservado.
- Recursos anuais devem ser selecionados por vigência; dados do ano anterior podem continuar válidos.
- `CPFL-PIRATINING` é o caso histórico principal para filtros e seleção residencial B1.

## Fontes adicionais

- `docs/fontes_de_dados.md`: inventário documentado de recursos e prioridade.
- `custom_components/tarifas_energia_brasil/aneel_client.py`: comportamento canônico do cliente.
- `custom_components/tarifas_energia_brasil/const.py`: métodos expostos e concessionárias.
- `custom_components/tarifas_energia_brasil/coordinator.py`: fallback, preservação e agendamento.
- `tests/test_aneel_client.py`: contratos de parsing, streaming, paginação e engines.
- `docs/releases/CHANGELOG.md`: evolução completa das releases.
