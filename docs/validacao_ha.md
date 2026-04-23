# Validacao no Home Assistant

Checklist objetivo para validar a integracao no ambiente real.

## 1. Instalacao e carga

1. Instalar via HACS.
2. Reiniciar Home Assistant.
3. Confirmar que a integracao aparece em `Dispositivos e Servicos`.

## 2. Fluxo de configuracao

1. Selecionar concessionaria suportada (`CPFL-PIRATINING`, `CPFL-PAULISTA` ou `CELESC`).
2. Informar entidade de consumo acumulado.
3. Se houver entidade de geracao, preencher tambem tipo de fornecimento.
4. Confirmar criacao sem erro.

## 3. Device e entidades

1. Verificar criacao do device `Tarifas Energia Brasil - <Concessionaria>`.
2. Validar entidades base:
   - TE/TUSD convencional
   - tarifa convencional bruta/final
   - tarifa branca por posto
   - PIS/COFINS/ICMS
   - bandeira e adicional
   - Fio B bruto/final
3. Validar entidades por quebra ativa (daily/weekly/monthly).

## 4. Atributos de coleta

Em sensores de origem externa, validar atributos:

- `ultima_coleta`
- `dataset`
- `resource_id`
- `metodo_acesso`
- `usou_fallback`
- `tentativas`
- `mensagem_erro`

## 5. Fallback e ultimo valor valido

1. Simular indisponibilidade da fonte (ex.: bloqueio de internet local).
2. Forcar atualizacao.
3. Confirmar que sensores mantem ultimo valor valido e registram erro em atributo.

## 6. Creditos SCEE

1. Configurar entidade de geracao acumulada.
2. Simular aumento de geracao e consumo em ciclos sucessivos.
3. Confirmar:
   - consumo de credito mais antigo primeiro;
   - previsao de creditos atualizando;
   - manutencao do saldo apos reinicio do Home Assistant.
