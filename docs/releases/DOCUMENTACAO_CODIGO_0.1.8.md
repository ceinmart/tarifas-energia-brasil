<!--
Versao: 0.1.8
Criado em: 2026-04-28 10:16:07 -03:00
Criado por: Codex
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil
-->

# Manual tecnico do codigo - Tarifas Energia Brasil

Versao documentada: 0.1.8  
Gerado em: 2026-04-28 10:16:07 -03:00  
Criado por: Codex  
Projeto/pasta: ha.ext.tarifas / tarifas_energia_brasil

Este documento registra a correcao de release `0.1.8`, publicada para preservar valores anteriores dos sensores quando a coleta externa inicial falha apos restart do Home Assistant.

## Causa

No diagnostico recebido, a config entry carregou, mas a primeira coleta falhou por indisponibilidade de conexao com `dadosabertos.aneel.gov.br`. O coordinator ficou com `last_update_success = false` e `snapshot = null`.

Como os sensores herdavam disponibilidade diretamente de `CoordinatorEntity`, a falha do coordinator tornava todos os sensores indisponiveis mesmo quando havia ultimo estado conhecido no mecanismo nativo de restauracao do Home Assistant.

Tambem havia uma janela em que o coordinator agendava a persistencia antes de aplicar o novo `ResultadoCalculo` em `self.data`, permitindo salvar `last_snapshot` vazio apos uma coleta bem-sucedida.

## Correcoes

- `TarifasEnergiaBrasilSensor` passa a herdar de `RestoreSensor`.
- `async_added_to_hass()` tenta restaurar primeiro `async_get_last_sensor_data()` e, como fallback de migracao, `async_get_last_state()`.
- Valores restaurados `unknown`, `unavailable`, vazios ou nulos sao ignorados.
- Sensores numericos convertem o estado restaurado para `float`; sensores textuais mantem o texto.
- `available` passa a retornar verdadeiro quando existe snapshot atual ou valor restaurado.
- `_async_update_data()` passa a agendar a persistencia apenas depois de `self.data = snapshot` e da atualizacao dos diagnosticos dinamicos.

## Impacto

Depois desta versao, se o Home Assistant tiver um ultimo estado valido salvo para as entidades da integracao, os sensores devem iniciar com esse valor enquanto a extensao tenta atualizar ANEEL, bandeira e tributos em background.

Quando a proxima coleta externa for bem-sucedida, o coordinator tambem passa a salvar corretamente o snapshot proprio usado pela integracao em reinicios futuros.

## Testes

Validacao local usada na release:

```powershell
python -m pytest
python -m ruff check custom_components tests
python -m ruff format --check custom_components tests
git diff --check
```

Resultado:

- suite completa com `80 passed`;
- lint sem erros;
- formatacao validada;
- diff sem problemas de espacos.
