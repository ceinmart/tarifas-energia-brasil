<!--
Versao: v1
Criado em: 2026-08-31 22:01 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas_energia_brasil
Finalidade: Documentar o isolamento Parquet, provisionamento DuckDB CLI e alertas da versao 0.2.3.
-->

# Documentacao tecnica 0.2.3

## Problema

O PyArrow 25 encerrava com `SIGILL` no processador Intel antigo do novo host do
Home Assistant. Como o leitor era importado no processo principal, uma biblioteca
nativa incompatível podia impedir a inicializacao da integracao.

Além disso, a API DataStore da ANEEL responde normalmente para tarifas e bandeiras,
mas atualmente nao possui registros de Fio B 2026 para `CPFL-PIRATINING`. Esse caso
exige que o fallback Parquet permaneça funcional.

## Alteracoes

- remove bibliotecas nativas dos requisitos obrigatorios da integracao;
- executa DuckDB modulo, DuckDB CLI e PyArrow em processos separados;
- limita tempo, stdout, stderr, memoria configurada do DuckDB e tamanho do Parquet;
- provisiona sob demanda o DuckDB CLI oficial 1.5.5 para Linux amd64/arm64,
  musl/glibc, com SHA-256 fixo, validacao de execucao e instalacao atomica em
  armazenamento persistente do HA;
- preserva o ultimo snapshot valido quando toda a coleta falha;
- mantem CSV exclusivamente manual;
- adiciona limite configuravel de idade dos dados, atributos de diagnostico e
  notificacao persistente com atalho para a action CSV manual.

## Fluxo resultante

1. API ANEEL.
2. DuckDB modulo em processo separado.
3. DuckDB CLI do PATH ou provisionado em processo separado.
4. PyArrow em processo separado.
5. Notificacao persistente e opcao de CSV manual.
6. Preservacao do ultimo resultado valido.

## Compatibilidade e validacao

- Home Assistant OS e Home Assistant Container usam o caminho persistente obtido
  por `hass.config.path`.
- Instalacoes Core antigas em Linux glibc podem funcionar em carater de
  compatibilidade.
- A suite da release possui 135 testes e Ruff aprovado.
- Consultas reais em 2026-08-31 confirmaram HTTP 200 no CKAN da ANEEL pelo host e
  pelo container HA. Tarifas e bandeiras foram processadas pela API; Fio B da
  CPFL-PIRATINING foi processado pelo Parquet.

Os detalhes de limites, seguranca, alertas e resultados do teste no processador
antigo estao em [Parquet isolado e alertas](../compatibilidade_parquet_e_alertas.md).
