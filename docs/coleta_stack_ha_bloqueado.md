<!--
Versao: v5
Criado em: 2026-08-12 12:35 -03:00
Alterado em: 2026-08-12 14:10 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas_energia_brasil
Finalidade: Orientar captura de pilhas Python durante bloqueio do Home Assistant no box.
-->

# Coleta de stack do Home Assistant bloqueado

## Objetivo

Identificar qual funcao ocupa a thread principal quando o Home Assistant continua
executando e consumindo CPU, mas a porta 8123 e o event loop deixam de responder.

Esta coleta deve ocorrer **durante a falha e antes de qualquer restart**. Uma captura
feita depois que o HA voltou ao normal nao confirma a causa do bloqueio.

## Estado conhecido em 2026-08-12

### Fatos observados

- host: `box`, acessado por `ssh rede-dmartins-root`;
- container: `ha`;
- processo principal: `python3 -m homeassistant --config /config`;
- arquitetura: `aarch64`;
- sistema base: Debian com glibc 2.36;
- `kernel.yama.ptrace_scope=1`;
- `py-spy`, `gdb`, `perf` e `pstack` nao estavam instalados no host.
- `/dados/tmp` e uma area temporaria compartilhada que contem tambem worktrees Git;
- `/dados/tmp/rede-dmartins` e a raiz do repositorio Rede-dmartins e nao deve receber
  ferramentas, scripts copiados, dumps, profiles ou pastas operacionais;
- a area dedicada para este procedimento e `/dados/tmp/ha-diagnostics`.

### Conclusao

Nao existe atualmente uma ferramenta pronta no `box` para obter a pilha de um
processo Python ja em execucao. O procedimento recomendado usa um binario standalone
do `py-spy`, compativel com Linux `aarch64`, preparado e validado **antes** do proximo
incidente. Nao instalar pacotes nem baixar ferramentas enquanto o HA estiver travado.

## Origem oficial e versao validada

- projeto oficial: <https://github.com/benfred/py-spy>;
- pagina de releases: <https://github.com/benfred/py-spy/releases>;
- release verificada em 2026-08-12: `v0.4.2`;
- release direta: <https://github.com/benfred/py-spy/releases/tag/v0.4.2>;
- metadados oficiais da release, incluindo o digest dos artefatos:
  <https://api.github.com/repos/benfred/py-spy/releases/latest>;
- artefato correto para o `box`:
  `py_spy-0.4.2-py2.py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`;
- SHA-256 publicado pela API do GitHub e conferido localmente:
  `142887e984a4e541071c99a4401ff8c3770f255d329dbd0f64e8c1dd51882cce`.

O wheel e um arquivo ZIP e contem o binario standalone em
`py_spy-0.4.2.data/scripts/py-spy`. Como o host possui glibc 2.36, ele satisfaz o
requisito `manylinux_2_17`. Se uma release mais nova for usada, nao reutilize o hash
acima: consulte a release, o nome do artefato e o digest correspondentes.

## Pre-requisitos

### No Windows

- PowerShell 5.1 ou posterior;
- acesso HTTPS ao GitHub;
- `ssh` e `scp` configurados para o alias `rede-dmartins-root`;
- acesso local ao repositorio `tarifas_energia_brasil`.

### No box

- execucao como `root`, necessaria para anexar a um processo existente com
  `ptrace_scope=1`;
- comandos `docker`, `mkdir`, `chmod` e `sha256sum`;
- arquitetura `aarch64` e glibc 2.17 ou posterior;
- cerca de 15 MiB livres para ferramenta, script e uma coleta curta.

A area operacional adotada neste runbook e `/dados/tmp/ha-diagnostics`, fora dos
repositorios existentes em `/dados/tmp`. Antes de escolher qualquer outro filho de
`/dados/tmp`, confirme que ele nao e um worktree Git nem uma pasta pertencente a outro
projeto. A area continua sendo temporaria e nao deve ser tratada como backup.

Nao e necessario instalar Python, pip, Rust, Cargo, compilador, `libunwind-dev` ou
pacotes dentro do container. O procedimento extrai o binario pronto no Windows e o
executa no host.

## Instalacao passo a passo

Execute os passos abaixo **antes** de um incidente.

### 1. Criar uma pasta temporaria no Windows

```powershell
$PySpyVersion = '0.4.2'
$PySpyWheelName = "py_spy-$PySpyVersion-py2.py3-none-manylinux_2_17_aarch64.manylinux2014_aarch64.whl"
$PySpyExpectedSha256 = '142887e984a4e541071c99a4401ff8c3770f255d329dbd0f64e8c1dd51882cce'
$PySpyTemp = Join-Path $env:TEMP "py-spy-$PySpyVersion-aarch64"
New-Item -ItemType Directory -Force -Path $PySpyTemp | Out-Null
$PySpyWheel = Join-Path $PySpyTemp $PySpyWheelName
$PySpyBinary = Join-Path $PySpyTemp 'py-spy'
```

Essas variaveis valem apenas na sessao atual do PowerShell e nao alteram o sistema.

### 2. Baixar diretamente da release oficial

```powershell
$PySpyUrl = "https://github.com/benfred/py-spy/releases/download/v$PySpyVersion/$PySpyWheelName"
Invoke-WebRequest -Uri $PySpyUrl -OutFile $PySpyWheel
```

Nao use sites de terceiros ou binarios enviados por mensagens.

### 3. Validar SHA-256 antes de extrair

```powershell
$PySpyActualSha256 = (Get-FileHash -Algorithm SHA256 $PySpyWheel).Hash.ToLowerInvariant()
if ($PySpyActualSha256 -ne $PySpyExpectedSha256) {
    throw "SHA-256 divergente: esperado=$PySpyExpectedSha256 obtido=$PySpyActualSha256"
}
"SHA-256 valido: $PySpyActualSha256"
```

Interrompa o procedimento se houver divergencia.

### 4. Extrair somente o executavel do wheel

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$PySpyArchive = [System.IO.Compression.ZipFile]::OpenRead($PySpyWheel)
try {
    $PySpyEntry = $PySpyArchive.Entries | Where-Object {
        $_.FullName -eq "py_spy-$PySpyVersion.data/scripts/py-spy"
    }
    if ($null -eq $PySpyEntry) { throw 'Executavel py-spy nao encontrado no wheel.' }
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile(
        $PySpyEntry,
        $PySpyBinary,
        $true
    )
} finally {
    $PySpyArchive.Dispose()
}
Get-Item $PySpyBinary
```

### 5. Criar a pasta operacional no box

```powershell
ssh rede-dmartins-root "mkdir -p /dados/tmp/ha-diagnostics/ferramentas"
```

Essa pasta fica fora da configuracao `/dados/ha` e fora do repositorio
`/dados/tmp/rede-dmartins`.

### 6. Copiar o binario e o coletor

Execute a partir da raiz do repositorio `tarifas_energia_brasil`:

```powershell
scp $PySpyBinary rede-dmartins-root:/dados/tmp/ha-diagnostics/ferramentas/py-spy
scp .\bin\coletar-stack-ha.sh rede-dmartins-root:/dados/tmp/ha-diagnostics/coletar-stack-ha.sh
```

### 7. Conferir o binario copiado e aplicar permissoes

```powershell
ssh rede-dmartins-root "sha256sum /dados/tmp/ha-diagnostics/ferramentas/py-spy; chmod 0755 /dados/tmp/ha-diagnostics/ferramentas/py-spy /dados/tmp/ha-diagnostics/coletar-stack-ha.sh"
```

O hash do binario extraido nao e igual ao hash do wheel. O objetivo deste comando e
registrar o binario efetivamente copiado. A verificacao de autenticidade foi feita no
wheel oficial no passo 3.

### 8. Validar versao e compatibilidade

```powershell
ssh rede-dmartins-root "/dados/tmp/ha-diagnostics/ferramentas/py-spy --version"
```

Resultado esperado para este procedimento:

```text
py-spy 0.4.2
```

Erros como `Exec format error` indicam arquitetura incorreta. Erros de carregador ou
glibc indicam artefato incompatível; nao continue para a captura.

### 9. Executar o coletor em DRY-RUN

```powershell
ssh rede-dmartins-root "/dados/tmp/ha-diagnostics/coletar-stack-ha.sh --py-spy /dados/tmp/ha-diagnostics/ferramentas/py-spy"
```

O resultado esperado termina com `DRY-RUN: pre-requisitos validos`. O DRY-RUN apenas
identifica o PID e executa `py-spy --version`; ele nao anexa ao processo do HA.

### 10. Remover os temporarios do Windows

Depois de validar a copia no `box`:

```powershell
Remove-Item -LiteralPath $PySpyTemp -Recurse -Force
```

Confirme antes que `$PySpyTemp` ainda aponta para a pasta temporaria criada no passo 1.
Nao versione o wheel, o executavel ou qualquer coleta.

## Coleta durante o incidente

### 1. Confirmar o sintoma sem aguardar indefinidamente

No Windows:

```powershell
ssh rede-dmartins-root "docker stats --no-stream --format '{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}} PIDS={{.PIDs}}' ha"
```

Se o HA estiver com CPU alta e sem resposta, execute imediatamente a coleta:

```powershell
ssh rede-dmartins-root "/dados/tmp/ha-diagnostics/coletar-stack-ha.sh --apply --py-spy /dados/tmp/ha-diagnostics/ferramentas/py-spy --duration 15 --rate 20"
```

O script:

- localiza o PID do comando `python3 -m homeassistant`, sem confundir o processo
  auxiliar `multiprocessing.resource_tracker`;
- grava contexto e `docker stats`;
- obtém tres dumps separados por dois segundos;
- amostra durante 15 segundos e produz `profile.speedscope.json`;
- nao reinicia o HA, nao envia sinais e nao altera `ptrace_scope`.

O `py-spy` usa `ptrace` e pode pausar o processo por periodos muito curtos durante
a captura. Por isso, limite a duracao e nao execute varias coletas em paralelo.

### 2. Copiar a coleta para o Windows

O comando informa um diretorio como:

```text
/dados/tmp/ha-diagnostics/ha-profile-YYYYMMDD-HHMMSS-0300
```

Copie apenas esse diretorio, substituindo o timestamp pelo valor real:

```powershell
scp -r rede-dmartins-root:/dados/tmp/ha-diagnostics/ha-profile-YYYYMMDD-HHMMSS-0300 C:\tmp\ha.ext\tarifas\coletas\
```

Nao grave a coleta dentro do repositorio Git. Revise o conteudo antes de compartilhar.

### 3. So depois decidir sobre restart

A captura nao reinicia nem recupera o HA. Depois que os arquivos forem copiados e
validados, o operador pode decidir separadamente se deve reiniciar o container.

## Como analisar

Nos arquivos `stack-1.txt`, `stack-2.txt` e `stack-3.txt`, procure a thread principal
e compare as pilhas:

- a mesma funcao no topo nas tres amostras sugere monopolizacao ou loop;
- pilhas em `coordinator.py`, `tarifa_branca_time.py` ou listeners da integracao
  fortalecem a correlacao com Tarifas Energia Brasil;
- pilhas em outro componente refutam essa atribuicao naquele incidente;
- pilhas diferentes ou espera de I/O exigem correlacao com CPU, log e profile.

Abra `profile.speedscope.json` em um visualizador compatível com Speedscope. A funcao
com maior largura acumulada consumiu mais tempo de CPU durante a janela amostrada.

## Falhas esperadas

### `Permission denied` ou erro de `ptrace`

Nao altere `ptrace_scope`, capabilities do container, Docker ou regras de seguranca
durante o incidente. Registre a mensagem completa como **PENDENTE VALIDAR**. Ajustar
essas permissoes seria uma mudanca de ambiente fora do escopo desta integracao.

### PID nao localizado

Execute apenas:

```bash
docker top ha -eo pid,ppid,comm,args
```

Confirme o comando principal real. Nao selecione automaticamente o primeiro processo
`python3`, pois pode ser um auxiliar.

### `py-spy` ausente ou incompatível

Nao tente instalar durante o bloqueio. Preserve as demais evidencias, incluindo
horario, CPU, log e estado persistido, e prepare a ferramenta posteriormente.

## Alternativas nao recomendadas sem preparacao

- nao enviar `SIGUSR1`, `SIGUSR2`, `SIGQUIT` ou outro sinal: sem handler previamente
  confirmado, o sinal pode encerrar o Home Assistant;
- nao usar `kill -9` antes da captura;
- nao instalar `gdb`, `perf` ou pacotes dentro do container durante a falha;
- nao mudar `auditd`, Docker, capabilities ou `ptrace_scope` apenas para coletar;
- nao executar profiling continuo em um host de recursos limitados.
