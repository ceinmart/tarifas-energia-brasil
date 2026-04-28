<!--
Versao: 0.1.7
Criado em: 2026-04-28 00:00:00 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil
-->

# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.7  
Gerado em: 2026-04-28 00:00:00 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra a correcao de release `0.1.7`, publicada apos falha do hassfest na release `0.1.6`.

## Atualizacao 0.1.7

O hassfest apontou dois problemas:

1. a plataforma de diagnosticos estava usando o componente `diagnosticos`, resultado de uma traducao indevida de API externa do Home Assistant;
2. a integracao implementava `async_setup`, mas nao declarava `CONFIG_SCHEMA`.

## Correcoes

- `diagnostics.py` volta a importar `homeassistant.components.diagnostics`.
- A funcao exposta volta ao nome reservado `async_get_config_entry_diagnostics`, exigido pelo Home Assistant.
- `manifest.json` declara `diagnostics` em `dependencies`.
- `__init__.py` passa a declarar:

```python
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
```

Essa declaracao informa ao Home Assistant e ao hassfest que a integracao nao aceita configuracao YAML propria e deve ser configurada por config entry.

## Testes

Validacao local usada na release:

```powershell
python -m pytest
python -m ruff check custom_components tests
python -m ruff format --check custom_components tests
git diff --check
```

Resultado esperado:

- suite completa com `78 passed`;
- lint sem erros;
- formatacao validada;
- diff sem problemas de espacos.
