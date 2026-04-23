# Concessionarias

## Suportadas na pre-release

- CPFL-PIRATINING
- CPFL-PAULISTA
- CELESC

## Mapeadas, fora do fluxo de configuracao

- RGE SUL
- CEMIG-D
- ENEL SP

Extratores internos parciais ja implementados:

- `RGE SUL`: parser HTML para PIS/COFINS/ICMS (mantida pendencia de validacao mensal aberta).
- `CEMIG-D`: parser HTML para PIS/COFINS (ICMS em fallback com pendencia de validacao oficial).

## Regra de suporte

A concessionaria so deve aparecer no fluxo de configuracao quando a extracao de:

- PIS
- COFINS
- ICMS

estiver validada de ponta a ponta.

## Observacao tecnica

Extratores web podem sofrer quebra por mudanca de layout. Nesses casos:

1. manter ultimo valor valido;
2. registrar diagnostico;
3. ajustar parser;
4. revalidar com fixture/teste.

Fixtures iniciais de parser:

- `tests/fixtures/cpfl_pis_cofins_sample.html`
- `tests/fixtures/celesc_tributos_sample.html`
