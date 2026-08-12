<!--
Versao: v1
Criado em: 2026-08-12 12:00 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas_energia_brasil
Finalidade: Documentar a investigacao e a correcao incremental da versao 0.2.2.
-->

# Documentacao tecnica 0.2.2

## Fatos observados

- O callback de mudanca de estado da `0.2.1` executa calculos incrementais de forma
  sincrona no event loop.
- Os segmentadores de periodo constroem listas proporcionais ao numero de dias entre
  a leitura anterior e a atual; nao havia limite superior para esse intervalo.
- `async_delay_save` recebe `_serialize_state` como callable. Portanto, o snapshot
  nao e serializado durante a chamada de agendamento do callback.
- O caminho incremental de `coordinator.py` nao mudou de `0.1.11` para `0.2.1`.
  A mudanca de `0.2.1` ficou no leitor Parquet e no requisito PyArrow.
- Benchmark local anterior a correcao: 4m30s = 0,24 ms; 10 anos = 0,21 s;
  100 anos = 2,08 s; aproximadamente 548 anos = 12,63 s.

## Conclusao

A complexidade temporal nao limitada foi reproduzida e poderia bloquear o event
loop com um timestamp persistido muito antigo ou corrompido. Contudo, o intervalo
de aproximadamente 4m30s presente na evidencia do incidente nao reproduz o bloqueio.
A causa raiz daquele incidente permanece **PENDENTE VALIDAR**.

A proxima evidencia necessaria e um stack dump ou profile de amostragem do processo
Python durante a falha, capaz de identificar a funcao que ocupa a thread principal.
O procedimento esta em [Coleta de stack do HA bloqueado](../coleta_stack_ha_bloqueado.md).

## Correcao

- intervalos maiores que 32 dias sao descartados e a leitura atual vira a nova base;
- timestamps iguais ou regressivos nao substituem uma referencia valida;
- eventos sem mudanca numerica nos tres totais retornam antes dos calculos;
- diagnosticos e warning tornam o descarte observavel.

O limite torna o trabalho do callback independente de lacunas arbitrariamente
longas. O delta descartado nao e distribuido porque sua atribuicao diaria, semanal,
mensal e por posto seria uma estimativa sem confiabilidade.

## Compatibilidade e teste seguro

A alteracao usa apenas APIs ja presentes na integracao e e compativel com o Home
Assistant 2026.7.2. Para validar no `box`, instalar a versao em uma janela controlada,
reiniciar somente por decisao do operador e acompanhar o log, os dois novos contadores
de diagnostico, CPU e responsividade da porta 8123. Nao foi feita alteracao automatica
no ambiente real durante esta investigacao.
