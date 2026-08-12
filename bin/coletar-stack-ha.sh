#!/usr/bin/env bash
# ==============================================================================
# Script: coletar-stack-ha.sh
# Versao: v4
# Criado em: 2026-08-12 12:35 -03:00
# Alterado em: 2026-08-12 14:10 -03:00
# Criado por: Codex (ChatGPT)
# Projeto / pasta: tarifas_energia_brasil
# Finalidade: Capturar pilhas Python do Home Assistant durante bloqueio do event loop.
# Modo de uso: ./coletar-stack-ha.sh --help
# Ambiente alvo: Linux box, executado como root no host Docker.
# Observacao: DRY-RUN por padrao; --apply e um py-spy previamente validado sao obrigatorios.
# ==============================================================================

set -euo pipefail

CONTAINER="ha"
OUTPUT_ROOT="/dados/tmp/ha-diagnostics"
PY_SPY="${PY_SPY:-}"
DURATION=15
RATE=20
APPLY=0

_usage() {
    cat <<'EOF'
Uso:
  ./coletar-stack-ha.sh [--py-spy CAMINHO] [--duration SEGUNDOS] [--rate HZ]
  ./coletar-stack-ha.sh --apply --py-spy CAMINHO [--duration SEGUNDOS] [--rate HZ]

Sem --apply, apenas valida container, PID, arquitetura, ptrace e py-spy.
Com --apply, grava tres dumps de pilha e um profile Speedscope curto.

Opcoes:
  --apply              Executa a captura.
  --py-spy CAMINHO     Binario py-spy aarch64 previamente obtido e validado.
  --duration N         Duracao do profile, entre 5 e 60 segundos (default: 15).
  --rate N             Amostras por segundo, entre 1 e 50 (default: 20).
  --help               Mostra esta ajuda.

O script nao instala pacotes, nao reinicia o HA e nao envia sinais ao processo.
EOF
}

_die() {
    printf 'ERRO: %s\n' "$*" >&2
    exit 1
}

_positive_integer_in_range() {
    local value="$1"
    local minimum="$2"
    local maximum="$3"
    [[ "$value" =~ ^[0-9]+$ ]] || return 1
    (( value >= minimum && value <= maximum ))
}

_parse_args() {
    while (($#)); do
        case "$1" in
            --apply)
                APPLY=1
                shift
                ;;
            --py-spy)
                (($# >= 2)) || _die "--py-spy exige um caminho."
                PY_SPY="$2"
                shift 2
                ;;
            --duration)
                (($# >= 2)) || _die "--duration exige um valor."
                DURATION="$2"
                shift 2
                ;;
            --rate)
                (($# >= 2)) || _die "--rate exige um valor."
                RATE="$2"
                shift 2
                ;;
            --help|-h)
                _usage
                exit 0
                ;;
            *)
                _die "Opcao desconhecida: $1"
                ;;
        esac
    done
}

_resolve_ha_pid() {
    docker top "$CONTAINER" -eo pid,args 2>/dev/null |
        awk '$0 ~ /python3 -m homeassistant( |$)/ {print $1; exit}'
}

_main() {
    _parse_args "$@"
    _positive_integer_in_range "$DURATION" 5 60 ||
        _die "--duration deve estar entre 5 e 60."
    _positive_integer_in_range "$RATE" 1 50 ||
        _die "--rate deve estar entre 1 e 50."

    command -v docker >/dev/null 2>&1 || _die "docker nao encontrado."
    local ha_pid
    ha_pid="$(_resolve_ha_pid)"
    [[ "$ha_pid" =~ ^[0-9]+$ ]] ||
        _die "processo 'python3 -m homeassistant' nao localizado no container ha."

    local architecture ptrace_scope command_line
    architecture="$(uname -m)"
    ptrace_scope="$(cat /proc/sys/kernel/yama/ptrace_scope 2>/dev/null || printf 'indisponivel')"
    command_line="$(tr '\0' ' ' < "/proc/$ha_pid/cmdline")"
    printf 'container=%s\npid_host=%s\narquitetura=%s\nptrace_scope=%s\ncomando=%s\n' \
        "$CONTAINER" "$ha_pid" "$architecture" "$ptrace_scope" "$command_line"

    [[ -n "$PY_SPY" ]] || _die "informe --py-spy CAMINHO; nenhuma ferramenta sera baixada."
    [[ -f "$PY_SPY" && -x "$PY_SPY" ]] || _die "py-spy nao e arquivo executavel: $PY_SPY"
    "$PY_SPY" --version

    if (( APPLY == 0 )); then
        printf 'DRY-RUN: pre-requisitos validos; use --apply somente durante a falha.\n'
        exit 0
    fi

    local timestamp output_dir metadata dump_index
    timestamp="$(date '+%Y%m%d-%H%M%S%z')"
    output_dir="$OUTPUT_ROOT/ha-profile-$timestamp"
    mkdir -p "$output_dir"
    metadata="$output_dir/contexto.txt"
    {
        date --iso-8601=seconds
        printf 'container=%s\npid_host=%s\narquitetura=%s\nptrace_scope=%s\ncomando=%s\n' \
            "$CONTAINER" "$ha_pid" "$architecture" "$ptrace_scope" "$command_line"
        docker stats --no-stream --format \
            '{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}} PIDS={{.PIDs}}' "$CONTAINER"
    } > "$metadata"

    for dump_index in 1 2 3; do
        "$PY_SPY" dump --pid "$ha_pid" > "$output_dir/stack-$dump_index.txt" 2>&1
        (( dump_index == 3 )) || sleep 2
    done
    "$PY_SPY" record --pid "$ha_pid" --duration "$DURATION" --rate "$RATE" \
        --format speedscope --output "$output_dir/profile.speedscope.json"

    printf 'Coleta concluida: %s\n' "$output_dir"
}

_main "$@"
