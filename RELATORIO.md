# Relatório — correção de erros de previsão de nível (7 dias), Araguaia

**Pedido:** um procedimento reproduzível que compare previsões originais e corrigidas por métodos tradicionais e por aprendizado de máquina, usando só informação disponível no momento da previsão e sem vazar o futuro.

**Entrega:** pipeline rodando com dados públicos, teste automatizado de vazamento, comparação de métodos por sistema de previsão, avaliação por cheia/não cheia, bootstrap pareado, figura e formato de CSV para o pesquisador trocar o substituto pelas previsões dele.

> Todos os números deste relatório saíram de scripts desta pasta. A coluna "fonte" ou o nome do arquivo indica qual.

---

## 1. Dados e por que esta estação

| Item | Valor | Fonte |
|---|---|---|
| Estação alvo | São Félix do Araguaia (MT), ANA **26350000** | `dados/estacoes.csv` |
| Estação a montante | Bandeirantes (Nova Crixás-GO), ANA **25700000** | `dados/estacoes.csv` |
| Período | 2014-01-01 a 2025-12-31, **4.383 dias** | `08_resumo_dados.py` |
| Dias com nível válido (alvo / montante) | **4.217 / 4.152** | `08_resumo_dados.py` |
| Registros de 15 min lidos | **387.941** e **412.205** | `08_resumo_dados.py` |
| Arquivos brutos comprimidos | **24**, **2,44 MB** | `08_resumo_dados.py` |
| Chuva média da bacia | **1.355 mm/ano** (ERA5 fixo) | `08_resumo_dados.py` |

**Nível:** webservice SOAP antigo da ANA (`http://telemetriaws1.ana.gov.br/ServiceANA.asmx`, `DadosHidrometeorologicos`), sem login. A API nova exige token por cadastro e não foi usada (regra 4).

**Chuva:** Open-Meteo com **`models=era5` fixo**, 8 pontos na bacia a montante. O ERA5-Land foi testado e não devolve precipitação nessa API (nulos); o modelo fixo é o ERA5 (~30 km). Sem `models`, a API usa o "Best Match" (ERA5 até 2016, IFS depois), o que quebra a homogeneidade — era o erro da versão anterior.

**Ablação da chuva** (`10_ablation_chuva.py`, mesma amostra de 528 datas): a chuva muda em **2.211 dias** e a média anual passa de 1.380 (Best Match) para 1.355 mm (ERA5), mas as métricas quase não mudam:

| Método | RMSE ERA5 (m) | RMSE Best Match (m) | Diferença |
|---|---|---|---|
| Persistência | 0,180 | 0,180 | 0,000 |
| AR | 0,172 | 0,172 | 0,000 |
| Kalman | 0,132 | 0,132 | 0,000 |
| Random Forest | 0,162 | 0,156 | −0,006 |
| Gradient boosting | 0,173 | 0,160 | −0,014 |
| Corretor enxuto | 0,164 | 0,164 | 0,000 |

Os métodos que não usam chuva ficam idênticos — é o controle que mostra que a ablação está correta. A chuva só entra nos dois modelos de ML, e o efeito é pequeno.

**Por que São Félix:** a primeira escolha foi Aruanã (25200000) com Barra do Garças. O P90 do treino de Aruanã é **4,92 m** e as máximas de 2024 e 2025 foram **4,90 m** e **4,57 m**, com **zero dias** acima do P90 (`09_aruana.py`; `dados/aruana_resumo.json`). Sem evento de cheia no teste, a pergunta central ficaria sem resposta. São Félix tem série longa, montante a ~250 km e **uma cheia real em 2025**.

**Falhas nos dados:** o nível do alvo tem **166 dias faltantes** (maior lacuna: 90 dias); o da montante tem **231** (maior lacuna: 115). Quatro lacunas passam de 3 dias em cada estação; falhas de até 3 dias são interpoladas.

---

## 2. Previsão substituta (não são as previsões do pesquisador)

Regressão cota-cota ajustada **somente em 2014–2021**:

`cota(t+7) = f(cota(t), cota(t−1), cota(t)−cota(t−3), montante(t), montante(t−1), montante(t−2), montante(t)−montante(t−3), dia do ano)`

| Período | n | RMSE (m) | MAE (m) | Viés (m) |
|---|---|---|---|---|
| Treino (2014–2021) | 2.739 | 0,164 | 0,115 | 0,000 |
| Validação (2022–2023) | 721 | 0,145 | 0,108 | +0,073 |
| Teste (2024–2025) | 681 | 0,175 | 0,135 | +0,088 |

Fonte: `04_previsao_referencia.py`; coeficientes em `dados/modelo_referencia.json`.

O ponto central: o viés é **zero no treino**, **+0,073 na validação** e **+0,113 no teste**. A previsão passa a subestimar a cota, e os modelos ajustados no treino não percebem isso. É aí que entra o Kalman.

Quando a montante está sem dado, entra um **modelo de reserva** sem cotas de montante. São **229 previsões** em todo o período, **111 no teste**, concentradas em fev–abr/2024 e fev–mar/2025.

---

## 3. Tabela de erros, um sistema por modelo

`dados/tabela_erros.csv` tem **4.188 linhas** (3.959 do cota-cota e 229 do modelo de reserva) e **4.141 com erro observado** (fonte: `05_correcoes.py`).

Correção importante desta rodada: **cada valor de `modelo` é processado separadamente**. As features, os erros verificados, o ajuste, o Kalman e o walk-forward de um modelo não enxergam as previsões do outro. Antes, o dicionário de previsões sobrescrevia modelos e os primeiros 28 dias depois de uma falha da montante usavam erros do modelo de reserva. Agora não.

A regra do erro verificado:

- `e7 = observado(t) − previsão emitida em t−7` (alvo `t`);
- `e14 = observado(t−7) − previsão emitida em t−14`;
- `e21 = observado(t−14) − previsão emitida em t−21`;
- `e28 = observado(t−21) − previsão emitida em t−28`.

Antes, `e14/e21/e28` comparavam a previsão antiga com a cota de **hoje**. O teste `test_erros_verificados_na_data_certa` confere as quatro definições em três datas escolhidas à mão. Todas as métricas foram refeitas.

Sistema com menos de **200 linhas de treino** não ajusta AR/RF/HGB/corretor enxuto; fica só com persistência e Kalman, e o script avisa. É o caso do modelo de reserva (118 linhas com erro observado, 104 com `e7` e `e14`).

---

## 4. Teste de vazamento

`codigo/test_vazamento.py`. Estratégia: **perturbar todo o futuro** — tudo depois de `t` recebe +999 m (nível) e +99 mm (chuva), e as previsões emitidas depois de `t` viram −999. Se qualquer variável de entrada mudar, ela olhou o futuro.

| Teste | Resultado |
|---|---|
| Perturbar o futuro não muda nenhuma variável | 130 datas, nenhuma mudou |
| A tabela salva bate com o recálculo | ok |
| `e7` é o erro da previsão emitida em `t−7` | ok |
| `e7/e14/e21/e28` conferem com a definição em 3 datas | ok |
| A previsão de 7 dias se reproduz sem olhar o futuro | ok |
| **Caso errado proposital** (`obs_futuro` em `t+7`) | **detectado** |

O último teste garante que a perturbação tem poder de detectar vazamento.

---

## 5. Métodos comparados

| Código | Método | Entradas |
|---|---|---|
| (a) `previsao_original` | previsão substituta, sem correção | — |
| (b) `persistencia` | soma o último erro verificado | `e7` |
| (c) `ar` | regressão dos erros com defasagens ≥ 7 dias | `e7`, `e14` |
| (d) `kalman` | filtro de Kalman escalar sobre o viés | `e7`, sequencial |
| (e) `rf` | Random Forest prevendo o erro | 28 variáveis conhecidas em `t` |
| (e) `hgb` | Gradient boosting prevendo o erro | mesmas 28 variáveis |
| (f) `rf_enxuto` | corretor enxuto: erros recentes + variação da cota | `e7`, `e14`, `dh1`, `dh3` |

As variáveis de (e) incluem cota atual, variações de 1/3/7 dias, médias de 7 dias, cotas de montante (t a t−3), chuva em janelas de 0–2, 3–6, 7–14, 15–29 e 30–59 dias, a previsão, erros verificados e dia do ano. Lista em `codigo/features.py`.

Ajuste das correções: **só no treino**, por modelo. O `(q, r)` do Kalman foi escolhido na validação, com grade ampliada: `q ∈ {1e−5 … 1}` e `r ∈ {1e−3 … 100}`. Para o cota-cota, escolheu **q = 1e−5 e r = 0,1** — ainda no limite inferior de `q` (ver seção 6.4).

---

## 6. Resultados no teste (2024–2025)

Sistema cota-cota: **584 emissões** no teste, **528 na amostra comum** a todos os métodos, **31 dias de cheia**. O modelo de reserva tem 111 emissões e 97 na amostra comum.

### 6.1 Todos os dias (528 dias)

| Método | n | RMSE (m) | MAE (m) | Viés (m) | Habilidade |
|---|---|---|---|---|---|
| Previsão original | 528 | 0,172 | 0,132 | +0,113 | 0,000 |
| Persistência do erro | 528 | 0,180 | 0,113 | 0,000 | −0,092 |
| AR dos erros | 528 | 0,172 | 0,132 | +0,113 | 0,005 |
| **Kalman no viés** | 528 | **0,132** | **0,086** | +0,013 | **0,415** |
| Random Forest | 528 | 0,162 | 0,115 | +0,102 | 0,114 |
| Gradient boosting | 528 | 0,173 | 0,127 | +0,112 | −0,012 |
| Corretor enxuto | 528 | 0,164 | 0,118 | +0,101 | 0,093 |
| *Controle:* previsão ingênua (cota de hoje) | 528 | 0,336 | 0,221 | +0,036 | −2,810 |
| *Controle:* correção embaralhada | 528 | 0,135 | 0,086 | +0,013 | 0,387 |

Fonte: `dados/metricas.csv`.

### 6.2 Cheia (31 dias: subida e pico)

| Método | n | RMSE (m) | MAE (m) | Viés (m) | Habilidade |
|---|---|---|---|---|---|
| Previsão original | 31 | 0,360 | 0,271 | +0,262 | 0,000 |
| Persistência | 31 | 0,418 | 0,329 | −0,062 | −0,349 |
| AR dos erros | 31 | 0,356 | 0,267 | +0,258 | 0,024 |
| **Kalman** | 31 | **0,280** | **0,193** | +0,117 | **0,396** |
| Random Forest | 31 | 0,300 | 0,215 | +0,205 | 0,307 |
| Gradient boosting | 31 | 0,324 | 0,273 | +0,268 | 0,193 |
| Corretor enxuto | 31 | 0,334 | 0,261 | +0,261 | 0,141 |
| *Controle:* embaralhada | 31 | 0,303 | 0,210 | +0,157 | 0,294 |

Fonte: `dados/metricas.csv`.

### 6.3 A IA oferece ganho adicional? (diferença pareada)

Bootstrap em blocos, 2.000 reamostragens, mesma amostra nos dois métodos. Δ positivo = A melhor que B.

| Comparação | Δ habilidade | IC95 | P(A melhor) |
|---|---|---|---|
| Kalman − original | +0,421 | 0,268 a 0,581 | 1,000 |
| RF − Kalman | **−0,316** | **−0,650 a −0,023** | 0,020 |
| HGB − Kalman | **−0,446** | **−0,854 a −0,097** | 0,006 |
| Corretor enxuto − Kalman | −0,328 | −0,498 a −0,130 | 0,005 |
| RF − original | +0,105 | −0,173 a 0,336 | 0,798 |
| Corretor enxuto − original | +0,092 | −0,024 a 0,220 | 0,934 |
| AR − original | +0,004 | −0,008 a 0,014 | 0,744 |
| Persistência − original | −0,072 | −0,402 a 0,318 | 0,321 |
| RF − corretor enxuto | +0,012 | −0,191 a 0,170 | 0,579 |

Na cheia (blocos de 7 dias):

| Comparação | Δ habilidade | IC95 |
|---|---|---|
| Kalman − original | +0,453 | 0,334 a 0,767 |
| RF − Kalman | −0,110 | −0,349 a −0,012 |
| HGB − Kalman | −0,394 | −1,483 a −0,010 |
| RF − original | +0,343 | 0,200 a 0,645 |
| HGB − original | +0,059 | −0,765 a 0,333 |
| Corretor enxuto − original | +0,095 | −0,220 a 0,220 |
| RF − corretor enxuto | +0,248 | 0,081 a 0,670 |

Fonte: `dados/bootstrap_diferencas.csv`.

**Resposta curta:** sim para o RF contra a original (ponto), não para "a IA supera o método tradicional". O RF melhora a original, mas o IC cruza zero; contra o Kalman, no ajuste fixo, o RF e o HGB são **piores** de forma significativa — mas no walk-forward a diferença deixa de ser separável (seção 6.5). Na cheia, o RF ganha da original, mas perde do Kalman.

### 6.4 Por que o Kalman ganha

O viés da previsão substituta é 0,000 no treino, +0,073 na validação e +0,113 no teste (`04_previsao_referencia.py` e `dados/metricas.csv`). Os modelos ajustados no treino não acompanham essa mudança; o Kalman estima o viés com os erros recentes e o desconta.

Com `q = 1e−5` e `r = 0,1`, o ganho estacionário é `K ≈ √(q/r) = 0,01`, o que dá memória de ~100 dias. A grade ampliada escolheu o limite inferior de `q`; testamos outros pontos na mesma amostra (`dados/kalman_sensibilidade.csv`):

| q | r | RMSE teste (m) | Memória aprox. (dias) |
|---|---|---|---|
| 1e−5 | 0,1 | 0,132 | 100 |
| 1e−4 | 0,1 | 0,133 | 32 |
| 1e−3 | 1,0 | 0,133 | 32 |
| 1e−3 | 0,1 | 0,138 | 10 |
| 1e−2 | 1,0 | 0,138 | 10 |

A conclusão não depende da memória entre 32 e 100 dias: o ponto da rodada anterior (`q = 1e−3`, `r = 1`, memória ~32 dias) dá 0,133 m, praticamente o mesmo. Mesmo com a grade ampliada, o ótimo ficou no **limite inferior de `q`** (r = 0,1, no interior da grade) — sinal de que o filtro quer um viés quase constante. O ganho vem de **corrigir o nível do viés**, não de uma sintonia fina do filtro. O controle embaralhado confirma: 0,387 contra 0,415 no geral; na cheia, 0,294 contra 0,396.

### 6.5 Walk-forward (refit a cada 1º de janeiro)

| Método | n | RMSE (m) | Viés (m) | Habilidade |
|---|---|---|---|---|
| AR | 528 | 0,154 | +0,085 | 0,197 |
| Random Forest | 528 | 0,147 | +0,066 | 0,276 |
| Gradient boosting | 528 | 0,152 | +0,070 | 0,219 |
| Corretor enxuto | 528 | 0,149 | +0,067 | 0,250 |
| Kalman | 528 | 0,132 | +0,013 | 0,415 |

Na cheia: AR 0,324 (0,192), RF 0,309 (0,265), **HGB 0,285 (0,374)**, enxuto 0,331 (0,158), Kalman 0,280 (0,396). Fonte: `dados/metricas_walkforward.csv`.

Pares no walk-forward, **geral**: RF − Kalman = −0,139 (−0,382 a +0,111); HGB − Kalman = −0,204 (−0,617 a +0,137); enxuto − Kalman = −0,160 (−0,270 a +0,029). **Nenhum se separa de zero.** Na cheia: RF − Kalman = −0,166 (−0,522 a −0,030); HGB − Kalman = −0,108 (−0,707 a 0,091); enxuto − Kalman = −0,316; AR − original = +0,225 (0,158 a 0,394).

Leitura: no ajuste fixo o Kalman supera RF e HGB de forma significativa; **com refit anual essa vantagem deixa de ser separável no conjunto dos dias**. O HGB melhora com o refit e chega perto do Kalman na cheia, mas o IC também não separa. O Kalman do walk-forward é **idêntico** ao do ajuste fixo por construção: o filtro é causal e não usa treino, então refit anual não o altera.

### 6.6 Modelo de reserva (dias sem montante)

97 dias comuns, 12 de cheia:

| Método | RMSE (m) | Viés (m) | Habilidade |
|---|---|---|---|
| Previsão original | 0,211 | −0,043 | 0,000 |
| Persistência | 0,254 | +0,002 | −0,442 |
| Kalman | 0,246 | −0,018 | −0,359 |

Na cheia (12 dias): original 0,158 m; Kalman 0,263 m (habilidade −1,773). Fonte: `dados/metricas.csv`.

Com 118 linhas de treino, o modelo de reserva não ajusta ML. E as correções, mesmo calibradas nos erros **dele**, pioram: o viés desse sistema muda de sinal e o filtro não acompanha. Isso é o que foi medido.

---

## 7. Os controles

1. **Previsão ingênua (repetir a cota de hoje):** RMSE 0,336 m, contra 0,172 m do substituto. Mostra que a comparação não é trivial.
2. **Correção embaralhada:** as correções do Kalman trocadas entre datas. No geral, habilidade 0,387 contra 0,415 do Kalman; na cheia, 0,294 contra 0,396. Ou seja: **a maior parte do ganho é o nível do viés**, e o ganho de "timing" é de 0,028 no geral e 0,102 na cheia. Continua sendo um evento só.
3. **Ablação da chuva:** métodos que não usam chuva ficam idênticos ao trocar ERA5 por Best Match; RF e HGB mudam −0,006 e −0,014 m. A chuva importa pouco para este resultado.

---

## 8. Cheias: quantos eventos e o que isso permite concluir

- Critério: cota observada ≥ **P90 do treino = 6,97 m** (`06_avaliacao.py`).
- **Um único evento**: 19/01/2025 a 09/03/2025, **50 dias**. Em 2024 não houve nenhum dia acima do limiar.
- A amostra principal do cota-cota cobre **31 dias de subida e pico** (19/01 a 18/02). Os **19 dias de descida** (19/02 a 09/03) ficaram fora porque a estação a montante falhou de 12/02 a 26/03; 12 deles aparecem no modelo de reserva (onde as correções pioram) e 7 não têm nem erro verificado dentro desse sistema.

**O que permite concluir:** o procedimento funciona, e nesse evento o Kalman reduziu o RMSE de 0,360 para 0,280 m (habilidade 0,396) e o RF para 0,300 m (0,307). É uma demonstração.

**O que NÃO permite concluir:** nada sobre "ganho médio em cheias". Um evento não é amostra. O IC da diferença na cheia, mesmo com blocos de 7 dias, tem só ~5 blocos e **não representa a variabilidade entre eventos**; ele mede incerteza entre dias do mesmo evento. Para a pergunta do artigo seriam necessários vários anos com cheia no teste, ou validação cruzada por evento.

Também não usei a cota de alerta oficial do SGB; P90 é uma definição estatística, sensível ao período de treino.

---

## 9. O que não foi possível, o que deu errado e o que ficou de fora

| Item | Situação |
|---|---|
| API nova do HidroWeb | Exige token por cadastro; não usada (regra 4). O webservice antigo funcionou sem login. |
| Primeira estação testada (17350000) | Retornou "Sem dados para esta estação no período". Descartada. |
| Aruanã (25200000) | P90 do treino 4,92 m; máximas 4,90 m (2024) e 4,57 m (2025); zero dias acima. Trocada por São Félix (`09_aruana.py`). |
| MERGE/CPTEC | Não baixado: ~4.400 arquivos de 1–2 MB (6–7 GB) e dependência de `eccodes` no Windows. O pesquisador já tem a chuva processada; o caminho é `03_montar_series.py --chuva`. |
| Volume de download | 24 respostas anuais do pipeline principal + 12 de Aruanã + 8 de chuva Best Match para a ablação. O total trafegado **não foi registrado por script**; pela ordem de grandeza do XML (~8 MB por estação-ano), fica em ~350 MB — **não conferido**, abaixo de 1 GB. Em disco: 2,44 MB comprimidos (`08_resumo_dados.py`). |
| Google Earth Engine | Não foi necessário; **0 chamadas**. |
| Referências | 3 candidatas foram descartadas: Seo et al. (2003) não retornou no Crossref; Shamseldin & O'Connor devolveu outro artigo; Todini (2008) deu 404. Ficaram 9 conferidas. |
| Estação a montante | Falhas de 62 dias (fev–abr/2024) e 43 dias (fev–mar/2025). Em 2024 não houve cheia; em 2025 a falha corta a descida do evento. |
| Datum | Não verifiquei mudanças de datum/referência de nível. Se houver, a série tem que ser corrigida antes de qualquer modelagem. |
| Antecedência diferente de 7 dias | O código está fixo em 7; os três pontos a mudar estão no README (seção 5). |

---

## 10. Limites do trabalho

- A previsão é **substituta**. Nada aqui avalia os modelos do pesquisador.
- Chuva de reanálise (ERA5), média de 8 pontos, não a chuva média da bacia com máscara.
- Um evento de cheia, e só a subida/pico na amostra principal.
- Período de teste seco em relação ao treino.
- Amostra comum de 528 de 584 emissões do cota-cota; os demais dias ficaram fora por falhas de dado ou variável ausente.
- O modelo de reserva tem 118 linhas de treino e não permite ML; suas correções pioram.
- Sem busca ampla de hiperparâmetros; os modelos de ML são deliberadamente simples.
- Sem validação com cotas de alerta oficiais.
- **Convenção de tempo:** a emissão em `t` usa a média do dia `t` inteiro. Se a operação emite de manhã, só há dado até `t−1`; o procedimento continua válido, mas com as variáveis deslocadas e números diferentes.

---

## 11. Onde a IA generativa ajudou e onde não ajuda

**Ajudou (e muito) na parte mecânica:**
- usar o webservice antigo da ANA sem cadastro e parsear o XML;
- agregar ~800 mil registros de 15 min em série diária, com regras explícitas de falha;
- montar a tabela `t → t+7` por sistema de previsão e o teste de vazamento por perturbação do futuro, inclusive o caso errado proposital;
- encontrar e corrigir o erro de data dos lags `e14/e21/e28`;
- rodar bootstrap pareado, ablação de chuva e a figura;
- levantar as referências e conferir os DOIs.

**Não ajuda — e pode atrapalhar:**
- **decidir o que é cheia.** P90 é defensável, mas a cota de alerta oficial é decisão hidrológica, com consequência operacional.
- **decidir se um evento basta.** A IA tende a reportar "melhorou 25%" com confiança que os dados não sustentam. Foi preciso o controle embaralhado para mostrar que quase todo o ganho é viés médio.
- **saber se o datum mudou, se a curva-chave foi revisada, se a telemetria tem salto de sensor.**
- **escolher o método do artigo.** "Kalman > RF" vale para este substituto, nesta estação, com estas variáveis. No modelo do doutorado pode inverter.
- **escolher a chuva certa.** A troca de modelo de reanálise não mudou as métricas aqui, mas isso não garante o mesmo no MERGE.
- **interpretar o ganho na cheia.** Com um evento, qualquer número é frágil. A IA pode produzir a tabela, não a conclusão.

Próximos passos, na ordem: (1) trocar o CSV pelas previsões reais dos três modelos, um de cada vez; (2) rodar o teste de vazamento em cada um; (3) separar a avaliação por evento de cheia; (4) só então decidir se vale incluir a correção por IA no artigo.

---

## 12. Correções de 31/10

> **Nota da 2ª rodada:** os números desta seção são os daquela rodada. A 2ª rodada corrigiu o cálculo do AR e separou os modelos; os valores abaixo não valem mais. O registro fica para mostrar o que mudou.

1. **Número sem script (Aruanã).** Criei `codigo/09_aruana.py`: P90 do treino 4,92 m; máximas 4,90 m (2024) e 4,57 m (2025); zero dias acima. Saída em `dados/aruana_resumo.json`.
2. **Controle embaralhado na cheia.** Na rodada anterior, a embaralhada tinha 0,229 contra 0,438 do Kalman; o texto passou a dizer que, na cheia, o momento pesa mais.
3. **IC da cheia.** O intervalo passou a ser citado com arquivo e colunas (`dados/bootstrap.csv`), com a ressalva de que o bootstrap reamostra dias, não eventos.
4. **Nada mais foi mexido.** O MD5 de `dados/metricas.csv` era `efabccd4751e724d7f5921db238263f0`.

---

## 13. Correções de 31/10 (2ª rodada)

Esta rodada mexeu no que precisava mudar para o procedimento servir ao uso real: trocar as previsões e comparar modelos. Tudo foi rodado de novo.

### 13.1 Um sistema por modelo (crítico)

- `05_correcoes.py` agora agrupa as previsões por `modelo` e roda `montar_features`, ajuste, Kalman, walk-forward e saída **por modelo**. Cada tabela tem só as datas em que aquele modelo emitiu.
- Sem a coluna `modelo`, tudo vira um sistema `informado`. Com três modelos, os três são processados.
- A checagem de duplicidade é por (`data_emissao`, `modelo`). Horizonte constante é verificado por modelo.
- O dicionário de previsões não sobrescreve mais modelos; a montagem é feita uma vez por sistema.
- **Treino mínimo de 200 linhas** para AR/RF/HGB/corretor enxuto; abaixo disso, só persistência e Kalman, com aviso. O modelo de reserva (118 linhas com erro observado, 104 com `e7`/`e14`) cai nesse caso.
- Filtro vazio e CSV vazio agora dão erro com mensagem.
- Teste novo: `codigo/test_multimodelo.py` roda o 05 com (a) um modelo sem coluna `modelo` e (b) três modelos nas mesmas datas, um deles com treino curto. Os três chegam ao fim; o curto fica só com persistência e Kalman.

**Efeito no substituto:** `cota_cota` e `sem_montante` são agora dois sistemas. O `cota_cota` tem 584 emissões no teste e 528 na amostra comum; o `sem_montante`, 111 e 97. O Kalman de cada um só recebe erros do próprio sistema. Antes, o cota-cota emprestava erros do reserva nos primeiros 28 dias após a volta da montante.

### 13.2 AR dos erros corrigido

O erro de uma previsão emitida em `t−k` é verificado em `t−k+7`, não em `t`. A fórmula foi corrigida em `features.py` e o teste `test_erros_verificados_na_data_certa` confere `e7`, `e14`, `e21` e `e28` contra a definição em três datas (uma de cheia). Todos os números foram refeitos. O AR, que antes tinha habilidade −0,011, agora tem +0,005 — ainda sem ganho prático.

### 13.3 Incerteza da diferença entre métodos

Novo `dados/bootstrap_diferencas.csv`, com a diferença pareada de habilidade (A − B) na mesma reamostragem:
- geral: blocos de 30 dias;
- cheia: blocos de **7 dias** (o horizonte), porque com 30 dias sobrariam 2 blocos.

Pares mínimos pedidos: RF−Kalman, HGB−Kalman, AR−original, Kalman−original, no ajuste fixo e no walk-forward, e na cheia. Também incluí RF−original, HGB−original, enxuto−Kalman, enxuto−original, persistência−original e RF−enxuto.

Resultado principal: Kalman−original = +0,421 (0,268 a 0,581); RF−Kalman = −0,316 (−0,650 a −0,023); HGB−Kalman = −0,446 (−0,854 a −0,097). Na cheia, Kalman−original = +0,453 (0,334 a 0,767) e RF−Kalman = −0,110 (−0,349 a −0,012). O IC da cheia continua sendo de dias, não de eventos.

### 13.4 Chuva homogênea e entrada para o MERGE

- `02_chuva_bacia.py` fixa `models=era5`. O ERA5-Land não devolve precipitação nessa API (nulos), então o modelo fixo é o ERA5 (~30 km), não o ERA5-Land. O texto e os rótulos foram corrigidos.
- **Ablação** (`10_ablation_chuva.py`): a chuva muda em 2.211 dias; média anual 1.355 (ERA5) contra 1.380 mm (Best Match). Métricas na mesma amostra: RF 0,162 → 0,156 m; HGB 0,173 → 0,160 m; persistência, AR, Kalman e enxuto idênticos (não usam chuva). O efeito é pequeno e não muda a conclusão.
- `03_montar_series.py --chuva arquivo.csv` aceita `data,chuva_bacia_mm` para plugar o MERGE processado. Dias faltantes são preenchidos com 0 e o script avisa.
- As janelas foram renomeadas para o que são: `chuva_d0_2`, `chuva_d3_6`, `chuva_d7_14`, `chuva_d15_29`, `chuva_d30_59`.

### 13.5 Textos e explicação do Kalman

- **Cheia:** o texto agora diz que a amostra principal são os **31 dias de subida e pico** (19/01–18/02); os **19 dias de descida** (19/02–09/03) ficaram fora por falha da montante. A frase "cheia de 2024" foi removida — em 2024 não houve dia acima do P90.
- **Montante:** a afirmação foi moderada. O que foi medido é que aplicar correções calibradas no cota-cota aos dias sem montante piora (RMSE 0,211 → 0,246), não que "dado de montante vale mais que qualquer modelo".
- **Por que o Kalman ganha:** viés 0,000 no treino, +0,073 na validação, +0,113 no teste; o filtro acompanha essa mudança de nível. Grade ampliada (`q` até 1e−5, `r` até 100) escolheu q = 1e−5, r = 0,1, ainda no limite de `q`; a sensibilidade mostra RMSE 0,132–0,138 para memória entre 10 e 100 dias, então a conclusão não depende da sintonia. Tabela em `dados/kalman_sensibilidade.csv`.
- **Denominadores:** 584 emissões do cota-cota no teste, 528 na amostra comum, 31 de cheia; 111/97/12 no modelo de reserva.

### 13.6 Como aplicar ao modelo do doutorado

Seção nova no README com: formato do CSV, rodar um modelo por vez, o que muda se a antecedência não for 7 dias (a regra vira `t − H`), como trocar a chuva e o que esperar ao corrigir um modelo que já é ML ou que já usa montante e chuva. Para isso, foi incluído o **corretor enxuto** (só erros recentes e variação da cota): habilidade 0,093 (IC −0,024 a 0,220), semelhante ao RF completo (0,114; IC −0,173 a 0,336) e abaixo do Kalman. Os dois são indistintos de zero.

### 13.7 Conferências

- `test_vazamento.py`: todos os testes passaram, incluindo o novo teste dos erros.
- `test_multimodelo.py`: 1 modelo e 3 modelos rodaram até o fim; o de treino curto ficou só com persistência e Kalman.
- `dados/metricas.csv` **mudou**, como esperado: MD5 antigo `efabccd4751e724d7f5921db238263f0`, novo `55e2116a32297c526dcd4445c2758a70` (estável entre reruns; o Random Forest passou a usar `n_jobs=1`).
- Nenhum dado de cota foi alterado; a chuva foi trocada pelo modelo fixo e a ablação mostra o efeito.
