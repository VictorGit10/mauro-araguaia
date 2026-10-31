# Segunda rodada de correções (31/10/2026)

As regras de `REGRAS-COMUNS.md` continuam valendo. Foram achados problemas por duas conferências independentes (`CONFERENCIA-MINIMAX.md` e uma análise de outra IA), confirmados no código. O critério de tudo: **servir ao que o pesquisador pediu no `CONTEXTO.md`** — procedimento reproduzível, só informação disponível na emissão, AR dos erros e Kalman como métodos tradicionais, ganho nas cheias, aplicar depois às previsões dele (cota-cota, regressão, RF; ele quer começar com **um** modelo).

Ao terminar, acrescente ao `RELATORIO.md` uma seção **"Correções de 31/10 (2ª rodada)"** com o que mudou e os números novos, e atualize README, CLAUDE.md/AGENTS.md e figuras onde os números aparecem. Rode `test_vazamento.py` no fim.

## 1. A troca pelas previsões dele precisa funcionar (crítico)
Hoje `05_correcoes.py` (linhas ~49 e ~134) e `06_avaliacao.py` (~136) filtram `modelo == "cota_cota"`. Sem a coluna `modelo` o ajuste fica vazio; com três modelos, dois são descartados sem aviso.
- Tratar **cada valor de `modelo` como um sistema próprio**: correções ajustadas, Kalman e métricas por modelo. Sem coluna `modelo`, tudo é um modelo só. O jeito limpo é separar por `modelo` **logo na entrada** e rodar `montar_features` dentro de um laço por modelo (`for mod, p in prev.groupby("modelo")`), porque hoje:
  - `carregar_previsoes` rejeita data de emissão repetida (`05_correcoes.py` ~linha 43): com 3 modelos nas mesmas datas, aborta. A checagem deve ser por (`data_emissao`, `modelo`);
  - `construir_linha` (`features.py` ~45) monta `mapa = dict(zip(data_emissao, previsao))`, que sobrescreve modelos;
  - no caso substituto, os primeiros 28 dias depois que a estação a montante volta usam `e7..e28` do modelo `sem_montante`.
- Modelo com poucas linhas de treino (o `sem_montante` tem 69 no treino; o walk-forward já pula abaixo de 200): exigir um mínimo para ajustar AR/RF/HGB e, abaixo dele, só diagnóstico (persistência e Kalman), dito na saída.
- Filtro que fique vazio = erro com mensagem clara.
- No caso substituto, `cota_cota` e `sem_montante` passam a ser dois sistemas. Explique no relatório como os dias `sem_montante` ficam (o Kalman de cada sistema só recebe erros do próprio sistema).
- Teste automatizado: CSV de exemplo com 1 modelo de nome qualquer, sem coluna `modelo`, e com 3 modelos; os três rodam até o fim.

## 2. AR dos erros calculado errado (importante)
Em `features.py`, o laço dos erros usa `alvo = t` para todo k: `e14/e21/e28` comparam a previsão antiga com a cota de hoje. O certo: o erro da previsão emitida em `t-k` é verificado em `t-k+7`, ou seja, `alvo = t - k + 7`. Corrija, acrescente um teste que confere `e7, e14, e21, e28` contra a definição em 3 datas escolhidas à mão, e rode de novo 04→05→06. Atualize todas as tabelas.

## 3. Incerteza da diferença entre métodos (importante)
A pergunta dele é "a IA oferece ganho adicional?". Isso exige o IC da **diferença pareada**: bootstrap em blocos de (habilidade A − habilidade B) para, no mínimo, RF − Kalman, HGB − Kalman, AR − original, Kalman − original, no ajuste fixo e no walk-forward, e na cheia. Salve em `dados/` e cite. Na cheia (31 dias), o bloco de 30 dias deixa só 2 blocos e o bootstrap degenera: use blocos de 7 dias (o horizonte) nesse subconjunto e diga que continua sendo um evento só.

## 4. Chuva: série homogênea e entrada para o MERGE dele
**Não baixe o MERGE**: são ~4.400 arquivos diários de 1–2 MB (6–7 GB) e dependem de `eccodes` no Windows; o pesquisador já tem a chuva do MERGE processada.
- Em `02_chuva_bacia.py`, fixe o modelo no Open-Meteo (`models=era5_land`; se não existir para todo o período, `era5`) para acabar com a troca de modelo em 2017. Hoje, sem `models=`, vem o "Best Match" (ERA5 até 2016, IFS depois), e o texto diz ERA5-Land. Rode de novo e corrija os rótulos. Diga quanto as métricas mudaram.
- Em `03_montar_series.py`, aceite `--chuva arquivo.csv` (colunas `data,chuva_bacia_mm`) para ele plugar a série do MERGE dele. Documente no README.
- Nomeie as janelas de chuva corretamente.

## 5. Textos
- A cheia avaliada são os **31 dias de subida e pico**; os 19 dias de descida (19/02–09/03/2025) caíram fora por falha da estação a montante. Diga isso onde a cheia aparece.
- Moderar "garantir dado de montante na cheia vale mais que qualquer modelo de correção": o que foi medido é que aplicar correções do `cota_cota` aos dias `sem_montante` piora.
- Tirar a "cheia de 2024" (não houve dia de cheia em 2024).
- Explicar por que o Kalman ganha: o viés é zero no treino e passa a +0,07/+0,09 m depois; o Kalman acompanha essa mudança com memória de ~1 mês (ganho estacionário ~0,03 com q=0,001 e r=1,0), e os modelos fixos no treino não. Dizer também que q e r ficaram no canto da grade e testar uma grade mais larga na validação.
- Denominadores conferidos no README (556 × 731 etc.).

## 6. Como aplicar ao modelo do doutorado
No README, uma seção curta: formato do CSV, rodar um modelo de cada vez, o que muda se a antecedência não for 7 dias (regra do último erro verificado vira `t - antecedência`), e como trocar a chuva. Um parágrafo sobre corrigir um modelo que **já é aprendizado de máquina** (o RF dele) ou que já usa cota de montante e chuva: o corretor só tem informação nova nos erros verificados e na atualização no tempo; vale testar também um corretor enxuto (erros recentes e variação recente da cota). Se der, rode essa versão enxuta no caso substituto e mostre o resultado.

## Não mexa
Dados de cota, teste de vazamento (só amplie), estrutura do pacote. Reconfira o MD5 de `dados/metricas.csv`: agora ele **vai** mudar (por causa do item 2); registre o antigo e o novo.
