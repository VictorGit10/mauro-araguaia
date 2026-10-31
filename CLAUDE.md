# CLAUDE.md — contexto técnico para continuar este projeto

Este arquivo é para a IA que for continuar o trabalho. Leia também `README.md` (visão para gente) e `RELATORIO.md` (resultados e limites). `AGENTS.md` aponta para cá.

## Objetivo

Comparar previsões de nível de rio (horizonte 7 dias) com versões corrigidas por persistência do erro, AR dos erros, Kalman e aprendizado de máquina, **sem usar informação futura**, com separação cronológica de treino/validação/teste. A previsão de entrada é um **substituto** (regressão cota-cota) e deve ser trocada pelas previsões reais do pesquisador.

## Dados

- `dados/bruto/<codigo>_<ano>.csv.gz`: telemetria de 15 min crua (ANA).
- `dados/bruto/chuva_era5_<lat>_<lon>.csv`: chuva diária de 8 pontos (ERA5 fixo).
- `dados/bruto/chuva_bestmatch_*.csv`: chuva antiga, usada só na ablação `10_ablation_chuva.py`.
- `dados/series_diarias.csv`: série diária final (`nivel_alvo`, `chuva_alvo`, `nivel_montante`, `chuva_montante`, `chuva_bacia_mm`).
- Estação alvo **26350000** (São Félix do Araguaia); montante **25700000** (Bandeirantes), em `comum.py::ESTACOES`.
- `dados/inventario_telemetria.csv`: inventário de estações (só para escolher as estações).
- `dados/aruana/`: cache de Aruanã, usado só por `09_aruana.py`; fica fora de `dados/bruto/` para não alterar a contagem do `08_resumo_dados.py`.
- `dados/ablation_chuva/` e `dados/teste_multimodelo/`: saídas auxiliares dos scripts 10 e do teste; não são o resultado principal.

## Ordem dos scripts

```
01_baixar_dados.py       -> dados/bruto/*.csv.gz
02_chuva_bacia.py        -> dados/bruto/chuva_era5_*.csv
03_montar_series.py      -> dados/series_diarias.csv  (aceita --chuva arquivo.csv)
04_previsao_referencia.py-> dados/previsao_referencia.csv, modelo_referencia.json
05_correcoes.py          -> tabela_erros.csv, previsoes_corrigidas.csv, previsoes_walkforward.csv, config_correcoes.json
06_avaliacao.py          -> metricas*.csv, bootstrap*.csv, kalman_sensibilidade.csv, resumo.json, figuras/serie_teste.png
07_referencias.py        -> dados/referencias_conferidas.json
08_resumo_dados.py       -> dados/resumo_dados.json
09_aruana.py             -> dados/aruana_resumo.json
10_ablation_chuva.py     -> dados/ablation_chuva.csv/.json
test_vazamento.py        -> só verifica (exit code != 0 se falhar)
test_multimodelo.py      -> só verifica (1 e 3 modelos de ponta a ponta)
```

`03_montar_series.py` importa `02_chuva_bacia.py` via `importlib.import_module("02_chuva_bacia")` porque o nome começa com número. Não renomeie sem ajustar.

## Invariantes (não quebrar)

1. **Nenhuma variável de `features.py` pode olhar depois de `t`.** `construir_linha` recebe a série inteira mas faz `series.loc[:t]` e `previsoes[data_emissao <= t]`. Se adicionar variável nova, rode `python codigo/test_vazamento.py` — ele perturba o futuro e falha se algo mudar.
2. **Erro da previsão emitida em `t−k` é verificado em `t−k+H`**: `e7 = obs(t) − f(t−7)`, `e14 = obs(t−7) − f(t−14)`, `e21 = obs(t−14) − f(t−21)`, `e28 = obs(t−21) − f(t−28)`. Nunca use `obs(t)` para todos os lags (era o bug corrigido na 2ª rodada). O teste `test_erros_verificados_na_data_certa` cobre isso.
3. **Um `modelo` = um sistema.** `05_correcoes.py` agrupa por `modelo` e monta features uma vez por grupo. `montar_features` levanta erro se houver duas linhas para a mesma `data_emissao` — é proposital. Não junte previsões de modelos diferentes na mesma chamada.
4. **Treino mínimo de 200 linhas** para AR/RF/HGB/enxuto. Abaixo disso, só persistência e Kalman (é o caso do `sem_montante`, 118 linhas).
5. **Convenção de tempo:** a emissão em `t` usa a média do dia `t` inteiro. Para emissão matinal, desloque as variáveis em um dia.
6. **Divisão só cronológica** (treino ≤ 2021, validação 2022–2023, teste 2024–2025). Nada de `train_test_split` aleatório.
7. **Ajuste só com dados de treino** (ou walk-forward com corte em 1º de janeiro). O teste não participa de escolha de hiperparâmetro.
8. **Cheia = cota observada ≥ P90 do treino** (6,97 m). Não troque sem registrar.
9. **Toda métrica reportada tem que sair de um script.** Os números vêm de `dados/resumo.json`, `metricas*.csv`, `bootstrap*.csv`, `kalman_sensibilidade.csv`, `ablation_chuva.csv`, `resumo_dados.json`.

## Chuva

`02_chuva_bacia.py` usa `models=era5` fixo. **Não remova esse parâmetro**: sem ele a API entrega o "Best Match" (ERA5 até 2016, IFS depois) e a série deixa de ser homogênea. O ERA5-Land retorna nulos para precipitação nessa API. Para usar o MERGE do pesquisador: `03_montar_series.py --chuva arquivo.csv` com colunas `data,chuva_bacia_mm`.

Janelas de chuva em `features.py` (dias antes de `t`, inclusive `t`): 0–2, 3–6, 7–14, 15–29, 30–59. Os nomes (`chuva_d0_2`, etc.) refletem os cortes.

## Armadilhas já encontradas

- **Falhas na montante durante a cheia:** 62 dias em fev–abr/2024 e 43 dias em fev–mar/2025. O `sem_montante` cobre esses dias, mas tem treino curto e as correções pioram nele. Não misture os dois sistemas numa mesma métrica.
- **A amostra principal perde a descida da cheia de 2025:** são 31 dias de subida/pico (19/01–18/02) e 19 dias de descida fora (19/02–09/03). Não apresente o resultado da cheia como o evento inteiro.
- **Não generalize o controle embaralhado:** no geral ele fica em 0,387 contra 0,415 do Kalman; na cheia, 0,294 contra 0,396. A maior parte do ganho é viés nível, mas o timing pesa mais na cheia.
- **Kalman no limite da grade:** q = 1e−5, r = 0,1 (memória ~100 dias). A sensibilidade em `kalman_sensibilidade.csv` mostra 0,132–0,138 para memória 10–100 dias; não é sintonia fina.
- **Datum:** não foi verificado se as estações mudaram de referência de nível.
- **JSON com coeficientes arredondados:** `modelo_referencia.json` guarda 5 casas; o teste de previsão usa tolerância de 5e-3 m.
- **Console do Windows em cp1252:** scripts que imprimem acentos/≥ reconfiguram `sys.stdout`.
- **Cache de download:** `01` não rebaixa se o `.csv.gz` existe. Para forçar, apague os arquivos.
- **Webservice antigo da ANA:** SOAP 1.2 em `http://telemetriaws1.ana.gov.br/ServiceANA.asmx`, envelope em `comum.chamar_ana`. A API nova exige token por cadastro; não use credenciais.

## Como trocar as previsões

CSV com `data_emissao,data_alvo,previsao` (metros), uma linha por emissão, horizonte constante; coluna opcional `modelo` (cada valor é um sistema).

```bash
python codigo/05_correcoes.py --previsao caminho.csv --saida dados/meu_modelo
python codigo/06_avaliacao.py     # lê sempre dados/ (troque os arquivos ou adapte)
```

Hoje o `06` lê `dados/previsoes_corrigidas.csv`; para avaliar uma saída alternativa, copie os três CSVs para `dados/` ou ajuste o caminho. O `--saida` do 05 serve para não sobrescrever o resultado principal.

Se o CSV tiver três modelos, os três são processados e as métricas saem separadas por `modelo`.

## Como trocar de estação

1. Edite `comum.py::ESTACOES` e, se necessário, `ANO_INI/ANO_FIM`.
2. Apague `dados/bruto/` das estações antigas e rode 01→03.
3. Ajuste os `PONTOS` de chuva em `02_chuva_bacia.py` para a bacia a montante.
4. Rode 04→06 e confira se há pelo menos um evento de cheia no teste.

## Onde estão os números

| Arquivo | Conteúdo |
|---|---|
| `dados/metricas.csv` | métricas por modelo e subconjunto (geral, cheia, não cheia) |
| `dados/metricas_completo.csv` | cada método na sua amostra máxima |
| `dados/metricas_walkforward.csv` | walk-forward |
| `dados/bootstrap.csv` | IC absoluto do ΔRMSE e da habilidade |
| `dados/bootstrap_diferencas.csv` | IC da diferença pareada entre métodos |
| `dados/kalman_sensibilidade.csv` | RMSE para vários (q, r) e memória do filtro |
| `dados/ablation_chuva.csv` | ERA5 fixo vs Best Match |
| `dados/resumo.json` | resumo consolidado por modelo |
| `dados/resumo_dados.json` | auditoria da série |
| `dados/aruana_resumo.json` | P90 e máximas de Aruanã |
| `dados/log_execucao.txt` | log da última execução |

## Comandos de verificação

```bash
python codigo/test_vazamento.py
python codigo/test_multimodelo.py
python codigo/06_avaliacao.py
python codigo/08_resumo_dados.py
```

Se mudar `features.py`, rode `04`, `05`, `06` e os dois testes — nessa ordem.
