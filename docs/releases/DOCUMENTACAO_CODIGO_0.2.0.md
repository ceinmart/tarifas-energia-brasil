<!--
Versão: v1
Criado em: 2026-08-10 15:15 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas-energia-brasil
Finalidade: Documentar as mudanças técnicas da release 0.2.0.
-->

# Documentação técnica — versão 0.2.0

## Resumo

A versão `0.2.0` reduz a carga automática provocada pelos arquivos CSV da ANEEL.
O ciclo normal usa `datastore_search`; somente o Fio B possui fallback automático
em Parquet. O CSV permanece disponível como atualização manual em background.

## Coleta automática

- Tarifas: somente `datastore_search`.
- Bandeira tarifária: somente `datastore_search`.
- Fio B: `datastore_search` e, em falha, Parquet.
- O Parquet é limitado a 100 MiB, gravado em arquivo temporário e consultado
  localmente com `duckdb==1.5.5`, fora do event loop do Home Assistant.
- Recursos anuais são consultados por vigência, incluindo o arquivo de 2025 para
  valores ainda vigentes em 2026.

## Atualização CSV manual

Foram adicionadas duas actions:

- `tarifas_energia_brasil.atualizar_via_csv`: inicia a atualização em background
  para `tarifas`, `fio_b`, `bandeira` ou `todos`.
- `tarifas_energia_brasil.cancelar_atualizacao_csv`: cancela a tarefa CSV ativa da
  entrada informada.

O CSV é processado em streaming com blocos de 64 KiB. Não existe limite total de
tamanho nem timeout total enquanto a transferência continua avançando. Permanecem
timeouts de conexão e inatividade para detectar servidor travado.

Somente uma tarefa CSV pode existir por entrada. Cancelamentos e falhas descartam
resultados parciais e preservam o último snapshot completo publicado nos sensores.

## Logs

- Ativação e resultado de fallback são registrados em `WARNING`.
- Início, recurso, URL, tamanho informado, progresso, registros examinados,
  encerramento antecipado, conclusão e cancelamento do CSV são registrados em
  `INFO`.
- Falhas definitivas são registradas em `ERROR`.

## Migração

- Entradas antigas com prioridade `csv_xml` são migradas para `datastore_search`.
- O multiplicador do fallback CSV foi removido da interface e deixa de influenciar
  a execução.
- Valores legados ainda presentes são ignorados com segurança.

## Validação

- 102 testes automatizados aprovados.
- Ruff aprovado.
- Python CI aprovado.
- Hassfest aprovado.
- Validação HACS aprovada.

## Referências

- [Changelog completo](./CHANGELOG.md)
- [Release v0.2.0](https://github.com/ceinmart/tarifas-energia-brasil/releases/tag/v0.2.0)
