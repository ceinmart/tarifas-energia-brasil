# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.2  
Gerado em: 2026-04-27 14:45:00 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra o estado tecnico da release `0.1.2`. Alteracoes historicas completas ficam no `CHANGELOG.md`.

## Atualizacao 0.1.2

A versao `0.1.2` corrige o bootstrap da integracao no Home Assistant. A entrada deixa de bloquear o setup aguardando a primeira coleta externa completa, evitando cancelamento pelo timeout global do Home Assistant quando ANEEL ou CSV estiverem lentos.

## Ciclo de setup

Fluxo a partir desta versao:

1. `async_setup_entry()` cria o coordinator.
2. As plataformas sao encaminhadas para o Home Assistant.
3. Os listeners de estado sao registrados.
4. A primeira atualizacao e agendada em background.
5. Se a primeira atualizacao falhar ou for cancelada, a integracao permanece carregada.
6. Novas tentativas ocorrem pelos ciclos normais do `DataUpdateCoordinator`.

## Motivo tecnico

Downloads CSV grandes da ANEEL podem levar mais de um minuto. Executar a primeira coleta como parte bloqueante do setup podia causar:

```text
asyncio.exceptions.CancelledError: Global task timeout: Bootstrap stage 2 timeout
```

Com a coleta em background, esse erro nao impede a entrada de ser carregada.

## Modulos afetados

| Modulo | Mudanca |
|---|---|
| `__init__.py` | Agenda `_async_refresh_after_setup()` sem bloquear `async_setup_entry()`. |
| `tests/test_init_setup.py` | Garante que `async_config_entry_first_refresh()` nao e chamado de forma bloqueante no setup. |

## Testes

A release adicionou cobertura para garantir que o setup agenda a primeira atualizacao sem bloquear o bootstrap do Home Assistant.
