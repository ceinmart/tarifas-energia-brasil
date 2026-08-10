# Fontes de dados

## ANEEL

- Tarifas distribuidoras:
  - Dataset: `tarifas-distribuidoras-energia-eletrica`
  - Resource: `fcf2906c-7c32-4b9b-a637-054e7a5234f4`
- Componentes tarifarias (Fio B):
  - Resources: `e8717aa8-2521-453f-bf16-fbb9a16eea39`, `a4060165-3a0c-404f-926c-83901088b67c`, `70ac08d1-53fc-4ceb-9c22-3a3a2c70e9fa`
  - Parquet: `59c32c89-8e86-4122-a7cf-a0d5fa9d0ff5`, `2a7a5364-8bd7-4464-9c56-587d77329447`, `5a29d53f-b7a6-4436-8497-7de00214d8fb`
- Bandeiras:
  - Acionamento: `0591b8f6-fe54-437b-b72b-1aa2efd46e42`
  - Adicional: `5879ca80-b3bd-45b1-a135-d9b77c1d5b36`

## Concessionarias (tributos)

- CPFL Piratininga:
  - https://www.cpfl.com.br/piratininga/pis-cofins
- CPFL Paulista:
  - https://www.cpfl.com.br/paulista/pis-cofins
- CELESC:
  - https://www.celesc.com.br/tarifas-de-energia

## Prioridade e alternativo

1. `datastore_search`
2. Parquet automatico somente para Fio B
3. CSV somente por action manual cancelavel

Em falha geral de coleta, a integracao conserva ultimo valor valido.
