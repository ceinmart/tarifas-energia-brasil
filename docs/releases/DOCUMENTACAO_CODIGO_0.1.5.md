# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.5  
Gerado em: 2026-04-27 20:45:00 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra o estado tecnico da release `0.1.5`. Alteracoes historicas completas ficam no `CHANGELOG.md`.

## Atualizacao 0.1.5

A versao `0.1.5` corrige a persistencia do timeout na coleta de Fio B via alternativo CSV.

O problema observado em campo era:

```text
csv_xml: TimeoutError
```

Mesmo com timeout de `600s`, a coleta de Fio B podia expirar porque o fluxo anterior tentava baixar e filtrar todos os recursos anuais (`2026`, `2025`, `2024`) antes de analisar se algum deles ja continha Fio B convencional vigente. Como o CSV de `2025` pode ter centenas de MB, e o de `2024` tambem e grande, o tempo total podia ultrapassar o limite em hardware mais lento.

## Mudanca no fluxo de Fio B

`fetch_fio_b()` passa a trabalhar recurso por recurso:

1. tenta o metodo configurado;
2. dentro do metodo, consulta um resource anual por vez;
3. adiciona os registros filtrados ao conjunto parcial;
4. executa `_parse_fio_b_records()` apos cada resource;
5. se encontrar Fio B convencional vigente, retorna sem baixar resources antigos desnecessarios;
6. se um resource falhar, registra o erro e segue para o proximo resource do mesmo metodo.

Para o alternativo CSV, foi adicionado criterio de encerramento antecipado: quando uma linha filtrada permite selecionar Fio B convencional vigente com rank maximo, a leitura do CSV e interrompida sem esperar o fim do arquivo.

## Logs de validacao de download

Os logs do CSV agora permitem validar se o download esta realmente acontecendo:

- `ANEEL CSV download iniciado`: resource, URL, timeout e filtros;
- `ANEEL CSV resposta recebida`: resource e `Content-Length` informado pelo servidor;
- `ANEEL CSV download em andamento`: bytes baixados durante o stream;
- `ANEEL CSV stream concluido`: total de bytes recebidos;
- `ANEEL CSV parse finalizado`: linhas lidas e registros filtrados;
- `ANEEL CSV leitura interrompida apos criterio suficiente`: indica que a coleta encontrou dado suficiente e encerrou cedo.

Essas mensagens aparecem no log do Home Assistant com o logger `custom_components.tarifas_energia_brasil.aneel_client`.

## Validacao externa

Para validar fora da integracao que a ANEEL esta entregando bytes do CSV, pode ser usado:

```powershell
curl.exe -L -I --max-time 60 "https://dadosabertos.aneel.gov.br/dataset/613e6b74-1a4b-4c48-a231-096815e96bd5/resource/a4060165-3a0c-404f-926c-83901088b67c/download/componentes-tarifarias-2025.csv"
```

Ou, para observar stream de bytes buscando a concessionaria:

```powershell
curl.exe -L --silent --show-error --max-time 180 "https://dadosabertos.aneel.gov.br/dataset/613e6b74-1a4b-4c48-a231-096815e96bd5/resource/a4060165-3a0c-404f-926c-83901088b67c/download/componentes-tarifarias-2025.csv" | rg -m 1 "CPFL-PIRATINING.*TUSD_FioB"
```

O primeiro comando valida headers e tamanho. O segundo valida download em streaming, sem salvar o arquivo completo.

## Modulos afetados

| Modulo | Mudanca |
|---|---|
| `aneel_client.py` | Fio B passa a ser validado resource por resource; CSV ganha progresso em bytes e encerramento antecipado. |
| `tests/test_aneel_client.py` | Testa que Fio B CSV para no primeiro resource valido e nao baixa resource antigo desnecessario. |

## Testes

Validacao local usada na release:

```powershell
python -m ruff check custom_components tests
python -m pytest
```

Resultado esperado desta versao:

- lint sem erros;
- suite completa com `78 passed`.
