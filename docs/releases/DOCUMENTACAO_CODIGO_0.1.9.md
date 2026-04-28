<!--
Versao: 0.1.9
Criado em: 2026-04-28 13:50:41 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil
-->

# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.9  
Gerado em: 2026-04-28 13:50:41 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra a correcao de release `0.1.9`, publicada para tornar a coleta externa mais resistente a oscilacoes temporarias do portal de Dados Abertos da ANEEL.

## Causa

No diagnostico recebido em `2026-04-28`, o Home Assistant tentou atualizar os dados logo apos a publicacao de novo CSV de tarifas da ANEEL. O portal retornou `500 INTERNAL SERVER ERROR` para `datastore_search`, `datastore_search_sql` e tambem para o download CSV do dataset de tarifas.

Como a configuracao estava com frequencia diaria e nao havia snapshot valido em cache, o coordinator registrava a proxima tentativa apenas para o dia seguinte. Na pratica, uma oscilacao curta do portal podia deixar os sensores sem atualizacao por muitas horas.

Tambem foi observado que chamadas `datastore_search` com paginas grandes e contagem total podiam falhar de forma intermitente no CKAN, inclusive com erro de limite de conexoes do banco.

## Correcoes

- `TarifasEnergiaBrasilCoordinator` passa a manter a cadencia configurada em `_configured_update_interval`.
- Quando a coleta falha sem snapshot valido, `_failure_retry_interval()` reduz temporariamente a proxima tentativa para no maximo 15 minutos.
- Quando uma coleta posterior tem sucesso, `_restore_regular_update_interval()` restaura a frequencia configurada pelo usuario.
- `AneelClient._datastore_search_records()` passa a usar `DATASTORE_SEARCH_PAGE_LIMIT = 1000`.
- As consultas `datastore_search` passam a enviar `include_total=false`, evitando a contagem total do CKAN em cada pagina.
- A versao declarada foi alinhada em `const.py`, `manifest.json` e README.

## Impacto

Se o portal ANEEL falhar durante o bootstrap e ainda nao existir ultimo snapshot valido, a integracao nao fica presa ate o proximo ciclo diario: ela tenta novamente em ate 15 minutos. Depois que a coleta volta a funcionar, a frequencia normal configurada pelo usuario e restaurada.

As consultas primarias ao CKAN tambem ficam menos pesadas, diminuindo a chance de cair para o fallback CSV grande quando o datastore esta apenas sobrecarregado.

## Validacao manual

Comandos usados para comparar o comportamento externo do portal:

```powershell
curl.exe -L --silent --show-error --max-time 180 -o NUL -w "http_code=%{http_code}; size_download=%{size_download}; time_total=%{time_total}`n" "https://dadosabertos.aneel.gov.br/dataset/5a583f3e-1646-4f67-bf0f-69db4203e89e/resource/fcf2906c-7c32-4b9b-a637-054e7a5234f4/download/tarifas-homologadas-distribuidoras-energia-eletrica.csv"
curl.exe --silent --show-error --max-time 60 -o NUL -w "http_code=%{http_code}; size_download=%{size_download}; time_total=%{time_total}`n" "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search?resource_id=fcf2906c-7c32-4b9b-a637-054e7a5234f4&limit=1000&offset=3000&include_total=false&filters=%7B%22SigAgente%22%3A%22CPFL-PIRATINING%22%7D"
```

## Testes

Validacao local usada na release:

```powershell
python -m pytest -q
```

Resultado:

- suite completa com sucesso.
