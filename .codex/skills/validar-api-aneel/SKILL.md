---
name: validar-api-aneel
description: Avaliar ao vivo a API e os Dados Abertos da ANEEL usados pelo projeto Tarifas Energia Brasil e verificar se a versão atual da integração Home Assistant permanece funcional e compatível. Usar quando pedirem para revalidar a API da ANEEL, testar compatibilidade da extensão, conferir todos os meios de acesso disponíveis, validar acesso básico aos dados ou sustentar uma afirmação de compatibilidade integral com a situação atual da API.
---

<!--
Versão: v1
Criado em: 2026-08-10 16:00 -03:00
Criado por: Codex (ChatGPT)
Projeto / pasta: tarifas-energia-brasil
Finalidade: Padronizar a revalidação da API ANEEL e da compatibilidade da integração.
-->

# Validar API ANEEL

Executar a validação a partir da raiz deste repositório. Tratar o código atual como fonte canônica para versão, recursos, métodos e filtros; não reutilizar IDs ou expectativas históricos sem confirmá-los no estado atual.

## Preparar o inventário

1. Confirmar a raiz Git e registrar data/hora da coleta.
2. Ler `custom_components/tarifas_energia_brasil/manifest.json`, `const.py`, `aneel_client.py`, `coordinator.py`, `services.yaml`, `docs/fontes_de_dados.md` e `tests/test_aneel_client.py`.
3. Extrair:
   - versão declarada no manifesto e em `const.py`;
   - datasets, resource IDs, anos e formatos usados;
   - métodos selecionáveis, automáticos, alternativos e manuais;
   - filtros, campos consumidos, timeouts, paginação e limites;
   - concessionárias habilitadas no fluxo.
4. Comparar manifesto, constantes, documentação e implementação. Registrar qualquer divergência antes dos testes.
5. Ler [historico-validacoes.md](references/historico-validacoes.md) e transformar cada incidente aplicável em uma verificação de regressão.

## Conferir a publicação atual da ANEEL

Usar internet e fontes oficiais da ANEEL. Consultar `package_show` ou a página oficial de cada dataset para descobrir os recursos publicados atualmente, seus formatos, URLs, datas e estado do DataStore. Não assumir que o resource ID mais recente continua sendo o codificado.

Comparar o catálogo atual com o inventário do código. Classificar recursos removidos, substituídos, renomeados, desatualizados ou novos. Para recursos anuais, confirmar que a lista implementada cobre a vigência necessária, e não apenas o ano civil atual.

## Executar os testes

Executar em camadas e preservar evidências objetivas de status HTTP, tempo, tamanho, esquema, quantidade de registros e amostras sanitizadas.

1. Rodar os testes focados em ANEEL e depois a suíte completa:

   ```powershell
   python -m pytest -q tests/test_aneel_client.py
   python -m pytest -q
   python -m ruff check custom_components tests
   ```

2. Testar ao vivo cada caminho efetivamente disponível na versão atual, derivado do código e do catálogo:
   - DataStore básico para tarifas, Fio B, acionamento e adicional de bandeira;
   - paginação e filtros exatamente como a integração os envia;
   - fallback automático, como Parquet, usando o mesmo resource, engine, limite e parser da integração;
   - CSV manual para cada dataset aceito pela action, usando o próprio cliente e seus critérios de cancelamento ou encerramento antecipado;
   - qualquer método novo que o código exponha ou que o catálogo oficial ofereça e seja relevante à integração.
3. Exercitar `AneelClient.fetch_tarifas()`, `fetch_fio_b()` e `fetch_bandeira()` com a data corrente e ao menos uma concessionária atualmente habilitada. Preferir `CPFL-PIRATINING` para preservar a série histórica, mas não limitar a validação a ela quando o pedido exigir cobertura total.
4. Confirmar que o resultado contém registros vigentes e semanticamente úteis, não apenas resposta HTTP 200:
   - TE e TUSD convencionais positivas;
   - postos da Tarifa Branca esperados quando disponíveis;
   - Fio B residencial B1, `Tarifa de Aplicação`, com vigência correta;
   - bandeira da competência e adicional coerente;
   - conversão R$/MWh para R$/kWh e seleção de linha compatíveis com os parsers.
5. Repetir ou paginar o suficiente para detectar respostas parciais, erros 500 intermitentes e diferenças entre DataStore e arquivo. Não baixar arquivos grandes sem necessidade: usar o streaming, limites e encerramento antecipado já implementados. Não alterar o Home Assistant real para uma validação básica.

Se um caminho exigir dependência opcional indisponível, instalar somente no ambiente virtual local do projeto quando isso estiver dentro do pedido. Caso contrário, registrar o caminho como não testado; não inferir sucesso.

## Avaliar compatibilidade

Separar os resultados em:

- `PASSOU`: caminho executado com dados vigentes e parser compatível;
- `PASSOU COM RESSALVA`: funcional, mas com oscilação, lentidão ou fallback;
- `FALHOU`: erro reproduzível, esquema incompatível, recurso ausente ou dado inválido;
- `NÃO TESTADO`: execução inviável; explicar objetivamente o motivo.

Declarar `100% compatível` somente quando todos os caminhos disponíveis relevantes, os três fluxos funcionais e as regressões históricas aplicáveis tiverem passado, sem item não testado. Um HTTP 200 isolado nunca comprova compatibilidade integral.

## Entregar o relatório

Informar de forma concisa:

1. conclusão e nível de confiança;
2. versão da integração e instante da validação;
3. matriz por dataset e método com resultado, latência e evidência;
4. compatibilidade de schema, filtros, vigência e parsers;
5. regressões históricas verificadas;
6. divergências entre API atual, código, testes e documentação;
7. limitações e correções recomendadas, sem implementar mudanças não solicitadas.

Incluir links das fontes oficiais consultadas e comandos reproduzíveis. Distinguir claramente fato observado, análise e recomendação. Nunca ocultar falha de um método porque outro fallback funcionou.
