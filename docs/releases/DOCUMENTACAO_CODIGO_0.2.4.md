<!--
Versao: v1
Criado em: 2026-08-31 22:32 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas_energia_brasil
Finalidade: Documentar as correcoes de event loop e log da versao 0.2.4.
-->

# Documentacao tecnica 0.2.4

## Evidencia em producao

Na primeira coleta apos instalar a versao 0.2.3, o Home Assistant detectou uma
abertura de arquivo no event loop durante `platform.libc_ver()`. A operacao ocorreu
na selecao do artefato DuckDB CLI e nao impediu a coleta, mas violava as regras de
I/O assincrono do HA.

O processo isolado do modulo DuckDB tambem devolveu o traceback completo de
`ModuleNotFoundError`. A ausencia do modulo era esperada nesse host e o CLI assumiu
corretamente, portanto o traceback apenas dificultava a leitura do log.

## Correcoes

- `detect_duckdb_asset()` passa a executar integralmente via `asyncio.to_thread()`;
- erros de importacao do processo filho sao convertidos em `FileNotFoundError`
  curto, preservando engine e causa;
- engines opcionais ausentes passam a ser registradas em `INFO`;
- crashes, timeouts, saida invalida e erros do provisionamento continuam em
  `WARNING` e preservam os detalhes necessarios ao diagnostico.

## Validacao

- 136 testes aprovados;
- teste confirma que a deteccao de plataforma roda fora da thread do event loop;
- teste confirma que `ModuleNotFoundError` nao inclui traceback na mensagem final;
- Ruff, compilacao Python, HACS e Hassfest fazem parte da validacao da release.

O fluxo e os resultados permanecem iguais aos da 0.2.3: API ANEEL, DuckDB modulo,
DuckDB CLI, PyArrow e, por decisao manual do usuario, CSV.
