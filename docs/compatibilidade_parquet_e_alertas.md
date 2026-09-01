<!--
Versao: v2
Criado em: 2026-08-31 17:26 -03:00
Alterado em: 2026-08-31 22:01 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas-energia-brasil
Finalidade: Documentar o isolamento Parquet e os alertas de coleta da versao 0.2.3.
-->

# Parquet isolado e alertas de coleta — 0.2.3

Alteracoes publicadas na release 0.2.3 sobre a versao 0.2.2.

## Fluxo e seguranca

Tarifas e bandeiras continuam usando DataStore. Para Fio B:

1. API ANEEL (`datastore_search`).
2. Modulo DuckDB, em novo processo Python.
3. Executavel DuckDB CLI, em processo separado.
4. PyArrow, em novo processo Python.
5. Falha controlada e notificacao persistente; preservacao do ultimo snapshot.

Nao existe fallback CSV automatico. Fechar ou ignorar a notificacao nao inicia
download. As actions CSV manual e cancelamento permanecem disponiveis.

Cada leitor tem timeout de 120 segundos; cancelamento/timeout encerram e aguardam
o filho antes de remover o Parquet temporario. SIGILL e outros exits nao matam o
processo do HA. O worker desabilita core dumps em Linux. O Parquet baixado continua
limitado a 100 MiB; stdout filtrado e limitado a 16 MiB e stderr a 64 KiB.
DuckDB usa uma thread e memory_limit de 256 MB (nao e limite absoluto do RSS).
PyArrow usa uma thread; nao ha limite absoluto de RAM imposto a ele.
O PYTHONPATH do filho acompanha os caminhos Python do HA, incluindo deps externos.

## Instalacao dos leitores

Os leitores nativos passam a ser opcionais: `requirements` nao exige PyArrow.
Isso impede que a instalacao de uma biblioteca opcional bloqueie o setup e as
actions CSV. Bibliotecas ja instaladas nao sao desinstaladas por esta alteracao.

O HACS instala o codigo da integracao, mas nao incorpora binarios grandes ao pacote.
O DuckDB CLI e provisionado pela propria integracao somente quando a API ANEEL e o
modulo DuckDB ja falharam. Portanto, uma instalacao normal nao baixa o CLI durante
o setup nem compila codigo nativo.

- Modulos DuckDB/PyArrow: precisam estar disponiveis ao Python do HA, com binarios
  compativeis com arquitetura, libc, Python e instrucoes da CPU. Nao basta instalar
  o modulo no Python do host Debian. A integracao nao executa pip nem compilacao.
- CLI: primeiro usa `duckdb` administrado pelo usuario no PATH. Se estiver ausente,
  detecta Linux `amd64` ou `arm64` e `musl` ou `glibc`, baixa exclusivamente o
  artefato oficial DuckDB 1.5.5 permitido no codigo e confere seu SHA-256 fixo.
- O pacote comprimido tem limite de 32 MiB e o executavel, 100 MiB. O arquivo e
  extraido como temporario, recebe permissao `0700`, executa `SELECT version()` em
  processo isolado e so entao substitui atomicamente o destino definitivo.
- O destino e obtido por `hass.config.path` e segue o formato
  `/config/tarifas_energia_brasil/bin/1.5.5/<plataforma>/duckdb`. Ele sobrevive a
  atualizacoes HACS e a recriacao do container quando a configuracao HA e persistida.
- Uma trava por destino impede downloads simultaneos por varias entradas. Falha de
  rede, plataforma desconhecida, checksum, execucao ou timeout e controlada: o fluxo
  segue para PyArrow e nenhum arquivo parcial vira o executavel ativo.
- HA OS e Home Assistant Container sao os alvos suportados. Instalacoes Core antigas
  em Linux glibc podem funcionar com o mesmo caminho de configuracao, em carater de
  compatibilidade. Outros sistemas/arquiteturas simplesmente pulam esta alternativa.
- O primeiro provisionamento requer acesso HTTPS ao GitHub. Depois, o binario em
  cache e validado e reutilizado. O CSV continua estritamente manual.

Nenhum arquivo de producao foi substituido e nenhum HA foi reiniciado nesta tarefa.

## Idade e avisos

Campo no fluxo inicial e nas opcoes: **Alerta dados desatualizados em dias**,
de 1 a 365, padrao 3. Entradas existentes usam 3 ate alterar a opcao.

Os atributos basicos, mesmo sem atributos extras, incluem:

| Atributo | Significado |
|---|---|
| `ultima_coleta_bem_sucedida` | Mais antiga das datas de coleta dos conjuntos usados no snapshot |
| `ultima_atualizacao` | Alias da data acima; nao acompanha eventos de consumo nem tentativas falhas |
| `ultima_tentativa` | Data do ultimo ciclo de coleta concluido com sucesso ou erro, quando ha snapshot |
| `idade_dados_dias` | Idade do conjunto mais antigo, ou null quando desconhecida |
| `dados_desatualizados` | Limite atingido ou data ausente/invalida/futura |
| `usando_dados_anteriores` | Ultima coleta falhou e os dados anteriores foram preservados |

Datas ausentes em snapshots antigos nao sao inventadas. As datas de coleta ja
persistidas sobrevivem a reload/restart e sao usadas no calculo de idade.
A idade indica ha quanto tempo consultamos a fonte; nao garante que a propria
fonte publicou uma tarifa nova nem substitui os campos de vigencia tarifaria.

Falha de coleta gera aviso imediato, mesmo antes de atingir o prazo. O aviso
distingue dados ainda dentro do prazo de dados desatualizados. A idade tambem e
verificada a cada hora, independentemente da frequencia de coleta; nao baixa dados.

Uma notificacao `persistent_notification` por entrada evita duplicatas. Mensagens
identicas nao sao recriadas durante a mesma instancia do coordinator; uma mudanca
de situacao pode atualizar/reabrir o aviso. Uma coleta valida dentro do prazo
remove a notificacao. Ao recarregar a entrada, uma falha persistente pode reaparecer.
Problemas no servico de notificacao sao registrados sem invalidar a coleta.

## CSV a partir do aviso

A notificacao oferece link My Home Assistant para abrir a action
`tarifas_energia_brasil.atualizar_via_csv`. O frontend so permite selecionar a
action pelo link, nao preencher os demais campos nem executa-la automaticamente.
O usuario seleciona a entrada indicada na mensagem e `fio_b`, `tarifas`, `bandeira`
ou `todos`, depois clica em Executar acao. Caso o link My nao esteja configurado,
usar Ferramentas do desenvolvedor > Acoes (Ferramentas > Acoes em versoes recentes).
O usuario precisa das permissoes normais do HA para acessar essa ferramenta.

CSV continua em background, com uma tarefa por entrada, cancelavel e sem limite
total de download. A acao retornar nao significa que terminou. Progresso e sucesso
ficam no log INFO; falha em ERROR. Nao ha barra de progresso na notificacao.

## Validacao em 2026-08-31

- Suite local: 135 testes aprovados; Ruff aprovado.
- Testes com processos reais cobrem timeout, cancelamento, saida excessiva,
  falha do filho, consulta DuckDB modulo e leitura PyArrow com filtro.
- Testes cobrem ordem dos leitores, preservacao do snapshot e datas, limite
  configurado, datas desconhecidas, restauracao, deduplicacao e remocao do aviso,
  falha do servico de notificacao e cancelamento da verificacao periodica no unload.
- No notebook Core 2 Duo T6500, Python 3.14.6/musl do container HA:
  modulo DuckDB ausente; CLI 1.5.5 leu e filtrou um Parquet sintetico; PyArrow
  25.0.0 recebeu SIGILL. O novo orquestrador usou CLI com sucesso e, sem CLI,
  devolveu erro controlado apos SIGILL. O processo pai permaneceu vivo.
- HA permaneceu running, restart=0, iniciado em 2026-08-29T16:48:05.173391555Z.
- Comandos de verificacao: `.venv/Scripts/python.exe -m pytest`,
  `.venv/Scripts/python.exe -m ruff check .`; teste remoto com `ssh srv`,
  `docker exec -i ha python -B -` e copia temporaria do cliente/worker.
- Binario oficial testado: `duckdb_cli-linux-amd64-musl.zip`, release 1.5.5.
  SHA256 conferido contra o digest publicado pela API GitHub:
  `4261fe20bab47d92742d5e21eee979e9e81548442985b9e3327725e1f755c910`.
- Limitacoes: consulta ao catalogo ANEEL falhou por SSL EOF no ambiente local;
  nao foi executada validacao completa com Parquet atual da ANEEL, nem CSV real.
  Notificacoes foram testadas por doubles da API do HA, nao criadas em producao.
  Nao foi feita reativacao, reinicio, publicacao nem instalacao definitiva do CLI.

## Referencias

- [Notificacao persistente](https://www.home-assistant.io/actions/persistent_notification.create/)
- [Parametros do link My](https://github.com/home-assistant/my.home-assistant.io/blob/main/redirect.json)
- [Frontend da action](https://github.com/home-assistant/frontend/blob/dev/src/panels/config/tools/action/tools-action.ts)
- [DuckDB 1.5.5](https://github.com/duckdb/duckdb/releases/tag/v1.5.5)
- [DuckDB no Alpine](https://duckdb.org/docs/current/dev/building/linux)
