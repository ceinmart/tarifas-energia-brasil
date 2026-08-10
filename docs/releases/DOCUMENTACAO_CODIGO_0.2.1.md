<!--
Versão: v1
Criado em: 2026-08-10 15:50 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas-energia-brasil
Finalidade: Documentar o hotfix de compatibilidade Parquet da release 0.2.1.
-->

# Documentação técnica — versão 0.2.1

## Resumo

A versão `0.2.1` corrige a inicialização no Home Assistant Container executado
com Python 3.14, musl e ARM64. O DuckDB não oferece wheel compatível com esse
ambiente e sua compilação falhava pela ausência de toolchain C++ no container.

## Engines Parquet

- `pyarrow==25.0.0` é o único requisito obrigatório de Parquet.
- Uma instalação DuckDB já existente continua sendo usada preferencialmente.
- Ausência ou falha do DuckDB aciona PyArrow e gera `WARNING`.
- O engine efetivamente usado é registrado em `INFO`.
- Se ambos falharem, a coleta gera erro controlado e orienta o uso da action CSV
  manual, preservando o snapshot anterior.

As consultas continuam fora do event loop, usam filtros de concessionária e
componente tarifário e removem o arquivo temporário ao final.

## Instalação da dependência

O HACS baixa os arquivos da integração. No primeiro carregamento após instalar a
versão `0.2.1`, o Home Assistant verifica o manifesto e instala o wheel PyArrow
antes do setup. A integração não tenta baixar nem compilar DuckDB.

O wheel PyArrow para CPython 3.14, `musllinux_1_2` e ARM64 tem aproximadamente
50 MiB. Ele é reutilizado enquanto a instalação compatível permanecer disponível;
uma nova transferência é necessária se a versão fixada mudar ou o cache/deps for
removido.

## Compatibilidade preservada

- Fluxo automático: `datastore_search`, com Parquet apenas para Fio B.
- CSV continua exclusivamente manual, em background e cancelável.
- Limite do download Parquet permanece em 100 MiB.
- Falhas externas não zeram sensores com snapshot válido.

## Referências

- [Changelog completo](./CHANGELOG.md)
- [Release v0.2.1](https://github.com/ceinmart/tarifas-energia-brasil/releases/tag/v0.2.1)
