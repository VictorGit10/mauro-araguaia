# Conferência independente — pasta `mauro` (previsão de nível 7 dias, rio Araguaia)

Conferência feita **depois** do trabalho da outra IA e das correções de `CORRECOES.md`.
Não refiz o trabalho: verifiquei. Não alterei nenhum arquivo da pasta (ver §0.3).

**Resumo:** o trabalho está sólido. Os números conferem, os testes passam, as três correções
pedidas foram realmente feitas e o relatório é honesto nas ressalvas. Encontrei, porém,
**um defeito que quebra o uso principal do pacote** (trocar o substituto pelas previsões do
pesquisador), **um erro de especificação nas variáveis de erro defasado** (o método (c) "AR
dos erros" não é AR de erros), **a falta do intervalo de confiança entre métodos** — que é
exatamente o que o `PEDIDO.md` pede — e **algumas divergências de texto com o código**
(janelas de chuva, origem da série de chuva, amostra da cheia). Detalhe e evidência abaixo.

---

## 0. Como foi feito

### 0.1 Ambiente

Python 3.14.3, pandas 2.3.3, numpy 2.4.4, scikit-learn 1.8.0, matplotlib 3.10.9.

### 0.2 O que rodei

Para **não mexer** em `dados/`, copiei a pasta inteira para
`<pasta>\mauro` e rodei lá (os scripts escrevem em
`dados/` e `figuras/`). Na pasta original só rodei o que não escreve nada
(`test_vazamento.py`) e consultas de leitura.

| Comando | Onde | Resultado |
|---|---|---|
| `python codigo/test_vazamento.py` | cópia | 5/5 testes passam, "Todos os testes passaram." |
| `python codigo/08_resumo_dados.py` | cópia | números conferem com o relatório |
| `python codigo/09_aruana.py` | cópia (usa cache) | P90 4,92 m; máximas 4,90 / 4,57 m |
| `python codigo/04_previsao_referencia.py` | cópia | `previsao_referencia.csv` **byte-idêntico** (md5 `b3a849094cf0cea83ef29b8ba65329d7`) |
| `python codigo/05_correcoes.py` | cópia | métricas reproduzem |
| `python codigo/06_avaliacao.py` | cópia | `metricas.csv` reproduz até 1e-16 (ver §2) |
| `python codigo/05_correcoes.py --previsao <CSV externo>` | cópia | 2 testes do fluxo de troca (§6.1) |
| `https://api.crossref.org/works/<doi>` (9 DOIs) | rede | 9/9 conferem |
| `https://archive-api.open-meteo.com/v1/archive` (4 chamadas pequenas) | rede | origem da série de chuva (§5.2) |
| SOAP `DadosHidrometeorologicos` — 1 mês de 3 estações | rede | 17350000 sem registros; as outras duas OK |

**Não** rodei `01_baixar_dados.py` nem `02_chuva_bacia.py` (baixariam tudo de novo), nem
`09_aruana.py` do zero (usei o cache de `dados/aruana/`), nem nada de Earth Engine.

### 0.3 Nada foi alterado

`md5sum dados/metricas.csv` no começo e no fim da conferência: **efabccd4751e724d7f5921db238263f0**
(é o mesmo hash que o próprio `RELATORIO.md` §12 afirma). As datas de modificação de todos os
arquivos da pasta continuam anteriores a esta conferência. O único arquivo novo é este.

---

## 1. As correções de `CORRECOES.md` foram feitas de verdade?

**Sim. As quatro, e conferidas por evidência.**

### Correção 1 — número sem script (Aruanã) — **FEITA** ✔

- `codigo/09_aruana.py` existe (99 linhas), baixa/reaproveita a série de 15 min de 25200000,
  aplica as mesmas regras de agregação do pipeline principal (`n < 20` leituras → falha,
  limites 0–20 m, interpolação de até 3 dias) e grava `dados/aruana_resumo.json`.
- **Rodei**: `P90 da cota diária no treino (2014–2021): 4.92 m`; `2024: máx = 4.90 m, dias ≥ P90 = 0`;
  `2025: máx = 4.57 m, dias ≥ P90 = 0`. Confere com `RELATORIO.md` §1 (linha 27), §9 (linha 201)
  e `README.md` linha 18.
- A frase "verificação exploratória, não salva em script" **saiu** do relatório e do README (conferi).
- O cache ficou em `dados/aruana/` (12 arquivos, 1,28 MB), fora de `dados/bruto/`, exatamente como
  o `CLAUDE.md` linha 17 promete — e `08_resumo_dados.py` continua contando 24 arquivos / 2,44 MB. ✔
- *Detalhe honesto do relatório:* o `09` só reproduz P90/máximas; ele não reproduz o "número de
  dias acima do P90" do modelo de reserva. Está tudo coerente.

### Correção 2 — controle embaralhado na cheia — **FEITA** ✔

- `dados/metricas.csv`, subconjunto `cheia`: `correcao_embaralhada` habilidade **0,228727**;
  `kalman` **0,438026**. Diferença 0,209 — exatamente o que a correção pediu.
- O texto novo está em `RELATORIO.md` §7 item 2 (linha 166) e no item 12 (linha 252), com a
  ressalva de que é um evento só. ✔
- Confere também com a §12 do relatório: "0,229 contra 0,438" — número certo, arquivo certo.

### Correção 3 — intervalo de confiança da cheia — **FEITA** ✔

- O intervalo **existia** mesmo em `dados/bootstrap.csv`; o que faltava era a citação. Agora o
  relatório §8 (linha 181) diz o arquivo (`dados/bootstrap.csv`), as colunas
  (`habilidade_ic95_inf` / `habilidade_ic95_sup`), o subconjunto (`cheia`) e o método (`kalman`),
  e adiciona a tabela da linha 185.
- Conferi os valores no CSV: `kalman / cheia` → `habilidade 0,450`, `IC95 0,429 a 0,497`. ✔
  `rf / cheia` → 0,236 (0,235 a 0,237); `hgb / cheia` → −0,125 (−0,722 a +0,145). ✔
- A ressalva "o bootstrap reamostra dias, não eventos" foi mantida (linha 181). ✔

### Correção 4 — "não mexa" — **CUMPRIDA** ✔

- `md5sum dados/metricas.csv` = `efabccd4751e724d7f5921db238263f0`, o mesmo valor declarado na §12
  do relatório. Verificado por mim antes e depois.
- Regenerando do zero em cópia, `metricas.csv` reproduz com diferença máxima de **1,1e-16** na
  coluna de habilidade e **0** em n/RMSE/MAE/viés — ou seja, o arquivo é o mesmo, só muda o
  último dígito em ponto flutuante.
- `previsao_referencia.csv` e `modelo_referencia.json` saem **byte-idênticos** (md5 iguais).
- `bootstrap.csv`, `metricas_walkforward.csv`, `metricas_reserva.csv`, `metricas_completo.csv`
  reproduzem com diferença máxima 0 (víés ≤ 8,3e-17).

---

## 2. Números (mais de 8 conferidos, todos contra script ou arquivo de dados)

Todos reproduzidos por mim na cópia da pasta.

| # | Número no `RELATORIO.md` | Onde está | Conferi como | Resultado |
|---|---|---|---|---|
| 1 | 4.383 dias, 2014-01-01 a 2025-12-31 | §1 | `08_resumo_dados.py` | ✔ igual |
| 2 | 4.217 / 4.152 dias válidos (alvo/montante) | §1 | `08_resumo_dados.py` | ✔ igual |
| 3 | 387.941 / 412.205 registros de 15 min | §1 | `08_resumo_dados.py` | ✔ igual |
| 4 | 24 arquivos brutos, 2,44 MB | §1 | `08_resumo_dados.py` | ✔ igual |
| 5 | Chuva média da bacia 1.380 mm/ano | §1 | `08_resumo_dados.py` | ✔ igual |
| 6 | Lacunas 166 (máx. 90) e 231 (máx. 115) dias; 4 lacunas > 3 dias em cada | §1 | `08_resumo_dados.py` | ✔ igual |
| 7 | Substituto: treino n=2.739 RMSE 0,164 MAE 0,115 viés 0,000; val. 721/0,145/0,108/+0,073; teste 681/0,175/0,135/+0,088 | §2 | `04_previsao_referencia.py` | ✔ igual |
| 8 | Tabela de erros: 4.383 linhas, 4.141 com erro observado | §3 | `05_correcoes.py` | ✔ igual |
| 9 | 229 emissões com modelo de reserva; 111 dias de reserva no teste | §2 | `05_correcoes.py`, `06_avaliacao.py` | ✔ igual (e conferi o mês: fev–abr/2024 e fev–mar/2025) |
| 10 | Kalman com q = 0,001 e r = 1,0 escolhidos na validação | §5 | `05_correcoes.py` + `dados/kalman_grade.csv` | ✔ igual |
| 11 | 731 emissões no teste = 584 cota-cota + 111 reserva + 36 sem previsão; 556 na amostra comum; 31 de cheia | §6 | `dados/previsoes_corrigidas.csv` | ✔ igual |
| 12 | Tabela de métricas gerais (RMSE/MAE/viés/habilidade dos 8 métodos) | §6.1 | `dados/metricas.csv` | ✔ igual (1e-16) |
| 13 | Tabela de métricas na cheia (6 métodos + 2 controles) | §6.2 | `dados/metricas.csv` | ✔ igual (1e-16) |
| 14 | Bootstrap geral (ΔRMSE e IC95 dos 5 métodos) | §6.3 | `dados/bootstrap.csv` | ✔ igual (diferença 0) |
| 15 | Walk-forward: RF 0,251 de habilidade, Kalman 0,407 | §6.4 | `dados/metricas_walkforward.csv` | ✔ igual |
| 16 | Reserva: original 0,200; Kalman 0,251; RF 0,220; persistência 0,250 | §7 item 3 | `dados/metricas_reserva.csv` | ✔ igual |
| 17 | P90 do treino = 6,97 m; um evento, 19/01–09/03/2025, 50 dias; 0 dias acima do P90 em 2024 | §8 | `06_avaliacao.py` + série observada | ✔ igual (P90 = 6,969 m; 0 dias em 2024, 50 em 2025) |
| 18 | Embaralhada 0,315 (geral) e 0,229 (cheia) | §7 | `dados/metricas.csv` | ✔ igual |
| 19 | Correção média do Kalman +0,089 m; do RF +0,014 m | §7 | `dados/resumo.json` | ✔ igual |
| 20 | Aruanã: P90 4,92; máximas 4,90 (2024) e 4,57 (2025); 0 dias acima | §1, §9 | `09_aruana.py` | ✔ igual |
| 21 | md5 de `dados/metricas.csv` = `efabcc…` | §12 | `md5sum` | ✔ igual |
| 22 | 9/10–9/9 DOIs conferidos | §9, `REFERENCIAS.md` | Crossref, feito por mim | ✔ 9/9, título, revista e ano batem |
| 23 | "130 datas testadas" no teste de vazamento | §4 | `test_vazamento.py` | ✔ igual |

**Nenhum número que conferi estava errado.** Isso é raro e vale dizer: a rastreabilidade exigida
pela regra 2 das `REGRAS-COMUNS.md` foi cumprida de verdade.

---

## 3. Testes

`python codigo/test_vazamento.py` — **5/5 passam** (saída completa na cópia):

```
- test_futuro_perturbado_nao_muda_features
  ok: 130 datas testadas; nenhuma variável mudou ao perturbar o futuro
- test_tabela_salva_confere_com_recalculo
  ok: tabela_erros.csv reproduz as features recalculadas
- test_erro_mais_recente_e_do_t_menos_7
  ok: e7 = observado(t) - previsão emitida em t-7
- test_previsao_nao_muda_com_futuro
  ok: previsão de 7 dias reproduzida sem olhar o futuro
- test_leak_proposital_e_pego
  ok: vazamento proposital detectado na variável ['obs_futuro']

Todos os testes passaram.
```

A estratégia (perturbar todo o futuro e exigir que nada mude) é sólida, e o **caso errado
proposital é realmente pego** — que é o que dá valor ao resto. Não achei vazamento de futuro em
nenhuma variável do `features.py`: todas truncam a série em `t` (`series.loc[:t]`) e as previsões
em `data_emissao <= t`.

---

## 4. Método

**O invariante central (nenhuma variável olha depois de `t`) está correto.** A divisão é
cronológica, o ajuste das correções é só no treino (walk-forward com corte em 1º de janeiro),
o limiar de cheia é calculado só no treino, e o Kalman usa apenas `e7` (erro já verificado).
Nada disso está vazando.

Os problemas de método que encontrei:

### 4.1 [importante] `e14`, `e21` e `e28` não são os erros das emissões `t−14`, `t−21`, `t−28`

`codigo/features.py`, linhas 65–70:

```python
for k in erros:
    emissao = d(k)
    alvo = t                      # <-- mesmo alvo para todo k
    if emissao in mapa and alvo in h.index:
        erros[k] = float(h.loc[alvo] - mapa[emissao])
```

A previsão emitida em `t−k` tem alvo `t−k+7`. Então o erro dela é
`observado(t−k+7) − previsão(t−k)`. Para `k = 7` isso dá `observado(t) − previsão(t−7)` — e
está certo (é a regra-chave). Para `k = 14` o correto seria `observado(t−7) − previsão(t−14)`,
mas o código calcula `observado(t) − previsão(t−14)`.

**Conferi numericamente** (4.112 linhas de 2014 a 2025):

| Variável | O que o código calcula | Diferença média para a definição correta |
|---|---|---|
| `e7` | `obs(t) − prev(t−7)` | **0** (correto) |
| `e14` | `obs(t) − prev(t−14)` | 0,24 m (máx. 1,30 m) |
| `e21` | `obs(t) − prev(t−21)` | (máx. 2,13 m) |
| `e28` | `obs(t) − prev(t−28)` | (máx. 3,24 m) |

Ou seja, `e14` é "variação de cota em 7 dias **mais** erro da emissão antiga", não o erro da
emissão antiga. O `RELATORIO.md` §3 (linhas 60–61) afirma o contrário:
"`e14`, `e21` e `e28` são os erros das emissões `t−14`, `t−21` e `t−28`".

**Por que importa:** (a) o método (c) do `PEDIDO.md` — "modelo autorregressivo dos erros, com
defasagens de 7 dias ou mais" — **não é um AR dos erros**; (b) quatro das 28 variáveis do RF/HGB
(`e14`, `e21`, `e28`, `e_media4`) estão deslocadas do que o texto diz que são;
(c) o `CLAUDE.md` linha 39 registra a invariante só para `e7`, então o problema passou despercebido.

**Não é vazamento** (`observado(t)` é conhecido em `t`) — é erro de especificação e de
documentação. **Quanto muda o resultado:** testei a correção em cópia (alvo = `t − k + 7`):

| Método | Habilidade geral (como está) | Habilidade geral (corrigido) | Cheia (como está) | Cheia (corrigido) |
|---|---|---|---|---|
| AR dos erros | −0,011 | +0,001 | 0,036 | 0,020 |
| Random Forest | 0,140 | 0,166 | 0,237 | 0,258 |
| Gradient boosting | 0,096 | 0,163 | 0,036 | 0,213 |
| Kalman | 0,407 | 0,407 | 0,438 | 0,438 |

As conclusões do relatório **não mudam** (o Kalman continua na frente), mas o método (c) rodado
não é o método (c) do pedido.

### 4.2 [importante] Falta o intervalo de confiança **entre métodos** — é o que o pedido pede

`PEDIDO.md` item 7: "dê um intervalo de confiança por bootstrap em blocos para **a diferença
entre métodos**". O `06_avaliacao.py` (linhas 218–225) só faz bootstrap de cada método
**contra a previsão original**. A conclusão central do relatório — "Kalman > aprendizado de
máquina", "o ganho grande é do do Kalman" — nunca é acompanhada de um intervalo.

Rodei o mesmo bootstrap em blocos de 30 dias (mesmo código, mesma semente 42) sobre os arquivos
da pasta, mas com a **diferença pareada entre métodos**:

| Ajuste fixo (556 dias) | ΔRMSE (outro − Kalman) | IC95 | P(outro melhor) |
|---|---|---|---|
| Random Forest | +0,027 m | **+0,002 a +0,048** | 0,019 |
| Gradient boosting | +0,031 m | **+0,001 a +0,055** | 0,022 |
| Persistência | +0,046 m | +0,027 a +0,068 | 0,000 |
| AR dos erros | +0,041 m | +0,025 a +0,056 | 0,000 |
| RF − HGB | +0,004 m | −0,005 a +0,013 | 0,202 |

Na cheia (31 dias): RF − Kalman = +0,044 m (IC95 +0,030 a +0,057).

**A boa notícia é que a conclusão do relatório sobrevive** (o Kalman é melhor que o RF também com
IC pareado). A má notícia é que o documento afirma a comparação sem o intervalo e sem o par.

### 4.3 [importante] O modo walk-forward (o mais próximo da operação) não tem bootstrap nenhum

O `README.md` §5 item 7 diz que o walk-forward "é o que mais se parece com a operação", e a
§6.4 destaca que o RF passa de 0,140 para 0,251 de habilidade. Esse 0,251 aparece **sem
nenhuma incerteza**, enquanto o relatório diz (para o ajuste fixo) que "com este tamanho de
amostra, não dá para afirmar que o ganho é real". Rodando o bootstrap nos arquivos da pasta:

| Walk-forward (556 dias) | ΔRMSE vs original | IC95 | Habilidade | IC95 |
|---|---|---|---|---|
| AR dos erros | −0,015 | −0,019 a −0,011 | 0,171 | 0,137 a 0,209 |
| **Random Forest** | −0,024 | **−0,043 a −0,003** | 0,261 | **0,038 a 0,496** |
| Gradient boosting | −0,020 | −0,042 a +0,003 | 0,218 | −0,037 a 0,470 |
| Kalman | −0,039 | −0,056 a −0,023 | 0,408 | 0,271 a 0,545 |

Ou seja: **no walk-forward o ganho do Random Forest até é estatisticamente sustentado**
(IC95 da habilidade 0,038 a 0,496, não cruza zero), ao contrário da leitura que o relatório
transmite. E o pareado Kalman − RF no walk-forward geral é +0,016 m (IC95 −0,011 a +0,039):
**não dá para separar os dois** no conjunto dos dias (na cheia dá: +0,051, IC95 +0,027 a +0,070).
Isso é material para a pergunta do pesquisador ("a IA oferece ganho adicional?") e não está no
material.

### 4.4 [importante] A amostra de 31 dias de cheia não é o evento inteiro — e o texto não diz isso

O evento tem 50 dias. Destes, **19 foram excluídos da amostra comum** porque a estação a
montante falhou (12/02 a 26/03/2025), e os 19 excluídos são exatamente a **perna de recessão**
(cotas de 8,27 m descendo a 7,01 m); o pico (8,63 m) está nos 31 retidos.

Consequência: o RMSE de 0,360 m (original) e 0,270 m (Kalman) na cheia respondem
**"subida e pico de uma cheia com dado de montante disponível"**, não "cheia". Como o relatório
reconhece que o bootstrap da cheia é enganosamente estreito, esta seleção enviesada ainda agrava o
problema. O texto (`RELATORIO.md` §8, `README.md` §7 item 1) menciona o problema do dado de
montante, mas nunca diz que 19 dos 50 dias do evento não entram nas métricas de cheia.

### 4.5 [importante] "Garantir dado de montante vale mais que qualquer modelo de correção" é mais forte do que os dados mostram

`RELATORIO.md` §7 (linha 169) e item 3: "O item 3 é, na prática, o achado mais útil para o
doutorado: **garantir dado de montante na cheia vale mais que qualquer modelo de correção**."

O que foi medido (`dados/metricas_reserva.csv`) é que **uma correção calibrada no sistema
cota-cota não transfere para o sistema de reserva**. Isso não é a mesma coisa: os dois dias são
sistemas de previsão *diferentes*, com viés de sinal contrário (principal +0,112; reserva −0,035)
e RMSE diferente (0,171 vs 0,200), em 111 dias. Não há comparação controlada do tipo
"com dado de montante vs sem dado de montante, com o mesmo modelo de correção". A conclusão
plausível e defensável é *"cada sistema de previsão precisa da sua própria correção"* — que o
relatório também diz — e não *"vale mais que qualquer modelo de correção"*.

### 4.6 [menor] A grade de `(q, r)` do Kalman parou no canto da grade

`dados/kalman_grade.csv`: o melhor par é `q = 0,001` (o **menor** da grade) com `r = 1,0` (o
**maior**). Ou seja, a busca foi truncada nos dois extremos. E o par escolhido significa
"processo quase parado, observação quase irrelevante" — o filtro fica praticamente um **viés
médio constante**. Isso explica, e é coerente com, o resultado do controle embaralhado (0,315
contra 0,407). Vale registrar no relatório: (a) a grade não explorou `q < 0,001` nem `r > 1`;
(b) o "Kalman" aqui é essencialmente "somar o viés médio", que é justamente o que a §7 discute.

### 4.7 [menor] O bootstrap da cheia é quase degenerado

31 dias → `n_blocos = ceil(31/30) = 2` blocos (15 e 16 dias). Existem só **3 reamostragens
distintas** ([b0,b0], [b0,b1], [b1,b1]) — daí o IC "0,429 a 0,497" de 0,068 de largura. O
relatório já avisa que o IC é enganosamente estreito; falta dizer que ele vem de 3 combinações
possíveis, e que o corte `[:n]` (`06_avaliacao.py` linha 79) deixa uma das reamostragens com 30
dias em vez de 31 (as outras duas com 31), o que desloca levemente a média da habilidade.

### 4.8 [menor] A linha do Kalman na tabela de walk-forward é idêntica por construção

`kalman_wf` = `kalman` (0,132 / 0,407), porque um filtro de Kalman já é causal: não há nada a
"reajustar". A tabela da §6.4 pode sugerir um segundo experimento independente; convém uma
frase dizendo que essa linha é a mesma, por construção.

---

## 5. Honestidade do relatório

### 5.1 O que está certo (e é incomum)

- O relatório **não esconde as fraquezas**: diz que um evento não é amostra, que o bootstrap
  reamostra dias e não eventos, que o IC da cheia é enganosamente estreito, que o volume
  baixado **não** foi registrado por script, que o datum não foi verificado, que a cota de
  alerta oficial do SGB não foi usada, que a chuva não é o MERGE e que a previsão é substituta.
  A §11 ("Onde a IA generativa ajudou e onde não ajuda") é honesta e útil.
- Os números de Aruanã, que antes eram "verificação exploratória", agora têm script (correção 1) —
  a rastreabilidade melhorou de verdade.
- Nenhum nome ou e-mail de pessoa nas entregas (regra 7 das `REGRAS-COMUNS.md` conferida por
  busca em todo o `.md`: só aparece em `REGRAS-COMUNS.md`, que é entrada, não saída). ✔
- A figura `figuras/serie_teste.png` está coerente com as tabelas: série observada, original,
  corrigidas, faixa de cheia e painel de erro.

### 5.2 [importante] A origem da série de chuva está escrita errado em 4 arquivos

`RELATORIO.md` §1, `README.md` §1, `CLAUDE.md` linha 13 e `REFERENCIAS.md` linha 41 dizem
**"ERA5-Land, ~9 km"**. O script `codigo/02_chuva_bacia.py` (linhas 45–56) **não passa
`models=`** — logo usa o padrão da API do Open-Meteo, que é o "Best Match": **ERA5 (0,25°,
~25 km) até 2016 e ECMWF IFS HRES (9 km) de 2017 em diante**.

Conferi contra a API (4 chamadas pequenas):

| Verificação | Resultado |
|---|---|
| Valores gravados em `dados/bruto/chuva_openmeteo_-13.64_-50.78.csv` (2024-01-01..10) | `[11.7, 5.2, 28.1, 42.8, 29.0, 9.8, 18.9, 43.4, 35.5, 13.6]` |
| Chamada **padrão** (a que o script fez) | `[11.7, 5.2, 28.1, 42.8, 29.0, 9.8, 18.9, 43.4, 35.5, 13.6]` → **idêntico** |
| `models=era5` | `[17.4, 14.1, 26.8, 12.3, 29.1, 3.8, 10.1, 29.1, 11.7, 22.1]` → diferente |
| `models=era5_land` | `[None, …]` → esse endpoint **não** devolve precipitação para ERA5-Land |
| Em 2020 (depois de 2017) | padrão = `ecmwf_ifs`, e difere do `era5` → a série **muda de modelo em 2017** |

Três consequências: (a) a procedência declarada está errada; (b) a série de chuva tem uma
**descontinuidade de modelo em 2017**, e o relatório fala dela como se fosse homogênea;
(c) o "Best Match" muda quando o IFS é atualizado — reexecutar `02` daqui a alguns anos **não
reproduz** os mesmos números, o que contraria a promessa de procedimento reproduzível.

### 5.3 [menor] "Falhou justamente nas cheias de 2024 e 2025" — em 2024 não houve cheia

`RELATORIO.md` §2 (linha 49) chama os dias de reserva de "justamente fevereiro–abril de 2024 e
de 2025, isto é, **durante as cheias**", e §9/§7 e `README.md` §7 item 1 dizem que a estação a
montante "falhou justamente nas cheias de 2024 e 2025 (62 e 43 dias)". Conferi:

- Falta de montante em 2024: **08/02 a 09/04/2024** (62 dias) — estação chuvosa.
- Falta de montante em 2025: **12/02 a 26/03/2025** (43 dias) — **dentro** do evento de cheia. ✔
- Dias acima do P90 em 2024: **zero**. A própria §8 do relatório diz "Em 2024 não houve nenhum
  dia acima do limiar."

Ou seja, em 2024 não houve cheia nenhuma pelo critério do próprio relatório; a falha foi na
estação chuvosa, não numa cheia. A frase supera o que os dados mostram.

### 5.4 [menor] Descrição da fórmula do substituto não bate com o código

`RELATORIO.md` §2 (linha 37) escreve
`f(cota(t), cota(t−1), cota(t)−cota(t−3), cota montante em t, t−1, t−2, t−3, dia do ano)`.
O código (`04_previsao_referencia.py` linha 27) usa `["h0","h1","dh3","u0","u1","u2","du3","doy_sin","doy_cos"]`:
`u3` não entra sozinho — entra só como diferença `du3 = u0 − u(t−3)`.

### 5.5 [menor] O `README.md` §6 mistura dois denominadores

"Amostra comum a todos os métodos: **556 dias** de teste (de **731** possíveis)". Os 731 são as
emissões do teste **incluindo** o modelo de reserva e as 36 sem previsão; no sistema cota-cota
são 584. O `RELATORIO.md` §6 diz certo ("556 dias de 584 possíveis no sistema cota-cota");
o README precisa da mesma distinção.

### 5.6 Não achei exagero no número "Kalman ganha mais"

O relatório não vende o Kalman como "a IA que resolve": ele diz explicitamente que o ganho
veio de remover viés e que o controle embaralhado mostra que o timing pesa pouco no conjunto
dos dias. Com a §12 e a §7 item 2 atualizadas, essa leitura está honesta. O que falta é o
intervalo do §4.2/§4.3 e a qualificação da amostra da cheia (§4.4).

---

## 6. Utilidade para a pessoa (o `CONTEXTO.md` está respondido?)

### 6.1 [crítico] O fluxo documentado de "colocar as suas previsões" **quebra**

O `CONTEXTO.md` diz que o pesquisador compara **três** modelos (cota-cota, regressão e Random
Forest) e quer "rodar tudo de novo" com as previsões dele. O `PEDIDO.md` item 8 e o
`README.md` §4 documentam o formato do CSV para isso. Testei os dois caminhos que o README
descreve:

**(a) CSV no formato exato do README (`data_emissao,data_alvo,previsao`, sem `modelo`)** — o
README diz que a coluna `modelo` é *opcional*. O script quebra:

```
$ python codigo/05_correcoes.py --previsao dados/externo_sem_modelo.csv
ValueError: Found array with 0 sample(s) (shape=(0, 2)) while a minimum of 1 is required by LinearRegression.
```

Causa: `05_correcoes.py` linha 49 preenche `modelo = "informado"` quando a coluna falta, e a
linha 134 filtra `sistema = tab["modelo"].eq("cota_cota")` — que fica **todo falso**. O ajuste
das correções (linha 140) recebe uma tabela vazia e o `LinearRegression` explode. O erro não
diz nada sobre a causa.

**(b) CSV com `modelo` = `cota_cota` / `regressao` / `rf` (exatamente os nomes sugeridos no
README)** — roda sem erro, mas **descarta silenciosamente dois dos três sistemas**:

```
Tabela de erros: 4383 linhas, 4141 com erro observado
Previsões por modelo: {'cota_cota': 1396, 'regressao': 1396, 'rf': 1396}
walk-forward 2022: ajustado com 914 linhas, previsto 365 dias      <-- era 2621 linhas
Teste: 231 emissões; amostra comum a todos os métodos: 222           <-- era 584 / 556
```

O motivo é o mesmo filtro `sistema = tab["modelo"].eq("cota_cota")` (linha 134) e, em
`06_avaliacao.py` linha 136, `test = test_all[test_all["modelo"] == "cota_cota"]`. Só as linhas
rotuladas **exatamente** "cota_cota" entram no treino e na avaliação; as linhas "regressao" e
"rf" desaparecem **sem aviso**, e o relatório final sai como se fosse um sistema só.

Isto é exatamente o oposto do que o pesquisador precisa (comparar os três modelos), e é o passo 1
do plano dele ("trocar o CSV pelas previsões reais dos três modelos do artigo"). **O que fazer:**
tornar o "sistema principal" um parâmetro (ex.: `--sistema` / `--modelo-principal`), ou agrupar
por sistema e avaliar cada um, e **falhar com mensagem clara** quando nenhum rótulo casar com o
esperado. (Uma correção mínima: se a coluna `modelo` não existir, tratar o CSV inteiro como
um único sistema.)

### 6.2 O que está bem entregue

- A estrutura do pedido está atendida: uma estação, uma série de 12 anos com evento de cheia
  no teste, um substituto treinado só no treino, os cinco métodos (a)–(e), divisão cronológica
  com walk-forward, cheia/não cheia, bootstrap em blocos, figura, formato de CSV de entrada,
  9 referências com DOI conferido, `README.md` + `CLAUDE.md`/`AGENTS.md` para a IA dele seguir.
- O `CONTEXTO.md` pede "erros de previsões anteriores já verificadas" como entrada: está feito e
  testado (`e7`).
- O `CONTEXTO.md` pede "evitar o uso indevido de informações futuras": está feito, com teste
  automatizado e caso errado proposital — é a parte mais forte do pacote.
- O `CONTEXTO.md` quer saber se "a IA oferece ganho adicional, especialmente durante as cheias":
  o material permite responder, mas com três ressalvas que precisam aparecer no texto:
  (a) **um** evento; (b) o Kalman (tradicional) ganha mais que os dois métodos de ML, com IC
  pareado agora calculado (§4.2); (c) no walk-forward geral, Kalman e RF **não** se separam
  (IC cruza zero), o que é a resposta mais honesta à pergunta dele.

### 6.3 O que ainda falta para a pergunta dele

1. Intervalo da diferença entre métodos (§4.2) e do walk-forward (§4.3).
2. Composição da amostra de cheia explicitada (§4.4).
3. Comparação controlada "com vs sem dado de montante" ou retirada da frase forte (§4.5).
4. Correção (ou recomeço) das defasagens de erro (§4.1).
5. A chuva como **ERA5-Land** está errado; se ele usar MERGE depois, a coluna
   `chuva_bacia_mm` precisa ser trocada e o pipeline rerodado (o `CLAUDE.md` já avisa disso).

---

## 7. Lista de problemas (gravidade, evidência, o que fazer)

| # | Gravidade | Problema | Evidência | O que fazer |
|---|---|---|---|---|
| 1 | **crítico** | Fluxo de troca das previsões quebra (CSV sem `modelo`) ou descarta 2 dos 3 sistemas em silêncio (CSV com `modelo` = cota_cota/regressao/rf) | `05_correcoes.py:49,134,140`; `06_avaliacao.py:136`; traceback do `ValueError`; "ajustado com 914 linhas" e "231 emissões" no teste com 3 modelos | Parametrizar o sistema principal (`--sistema`), ou avaliar por sistema; erro explícito quando nenhum rótulo casar; corrigir o README |
| 2 | **importante** | `e14`/`e21`/`e28` não são os erros das emissões antigas (`alvo = t` para todo k) | `features.py:65-70`; 4.112 linhas conferidas (diferença média 0,24 m em `e14`, máx. 3,24 m em `e28`); `RELATORIO.md:60-61` afirma o contrário | `alvo = t − k + 7`; atualizar §3 do relatório, README e CLAUDE; rerodar 04→05→06 e o teste de vazamento |
| 3 | **importante** | Não há IC da **diferença entre métodos** (item 7 do PEDIDO), nem bootstrap do walk-forward | `06_avaliacao.py:218-225` só compara com a original; §6.4 sem incerteza | Adicionar bootstrap pareado (e do walk-forward). Números que eu calculei: fixo RF−Kalman +0,027 (IC +0,002 a +0,048); walk-forward RF−Kalman +0,016 (IC −0,011 a +0,039, **não separável**) |
| 4 | **importante** | A amostra de cheia (31 dias) exclui 19 dos 50 dias do evento (perna de recessão, sem dado de montante); o texto não diz isso | `dados/previsoes_corrigidas.csv` (19 linhas `sem_montante` com alvo 19/02 a 09/03/2025, cotas 8,27→7,01 m; pico 8,63 m nos retidos) | Uma frase na §8 e no README §7: "subida e pico, com montante disponível" |
| 5 | **importante** | "Garantir dado de montante vale mais que qualquer modelo de correção" não é demonstrado (sistemas diferentes, viés de sinal oposto) | `dados/metricas_reserva.csv` (viés −0,035) vs `dados/metricas.csv` (viés +0,112), 111 dias, sistemas distintos | Trocar por "cada sistema de previsão precisa da sua própria correção" ou fazer a comparação controlada |
| 6 | **importante** | Origem da chuva escrita errado em 4 arquivos: não é ERA5-Land (~9 km), é o "Best Match" (ERA5 até 2016 + IFS 9 km de 2017 em diante) | `02_chuva_bacia.py:45-56` sem `models=`; valores gravados idênticos à chamada padrão e ≠ `era5`; `era5_land` devolve `null` | Fixar `models=` explicitamente, rerodar 02→03→05→06, corrigir `RELATORIO.md:25`, `README.md:15`, `CLAUDE.md:13`, `REFERENCIAS.md:41` |
| 7 | **menor** | Janelas de chuva com nome errado: `p7`=4 dias, `p15`=8, `p30`=15, `p60`=30 (blocos não sobrepostos, todos terminando em `t`) | `features.py:60-61,92-96`; conferido dia a dia (ex.: 2023-06-15: `p60`=35,775 = soma de 30 dias de t−59 a t−30) | Renomear as variáveis ou corrigir a descrição em `RELATORIO.md:94` |
| 8 | **menor** | Grade do Kalman truncada no canto (q=0,001 e r=1,0 são os extremos); o filtro é praticamente um viés médio | `dados/kalman_grade.csv`; coeficientes em `config_correcoes.json` | Registrar que a busca parou no limite e que o Kalman aqui é "somar o viés" (coerente com o controle embaralhado) |
| 9 | **menor** | O IC da cheia vem de só 3 reamostragens distintas (2 blocos) e uma das reamostragens tem 30 dias em vez de 31 | `06_avaliacao.py:64-101` (BLOCO=30, 31 dias, `[:n]`) | Dizer no texto; para cheias, o certo é validação cruzada por evento (o próprio relatório sugere isso) |
| 10 | **menor** | A linha do Kalman na tabela de walk-forward é igual à do ajuste fixo por construção, sem aviso | `dados/metricas_walkforward.csv` (`kalman_wf` = `kalman`) | Uma frase explicativa |
| 11 | **menor** | Descrição da fórmula do substituto não bate com `BASE` do `04` (`u3` entra só como `du3`) | `RELATORIO.md:37` vs `04_previsao_referencia.py:27` | Corrigir a fórmula no relatório |
| 12 | **menor** | `README.md` §6 mistura denominadores (556 de 731); e "falhou nas cheias de 2024" (2024 não teve cheia) | `README.md:93,115`; série observada: 0 dias ≥ P90 em 2024; falta de montante 08/02–09/04/2024 | Corrigir as duas frases |

**Nada disso invalida a conclusão principal** (Kalman > ML neste substituto, com IC pareado
favorável; um evento de cheia só; ganho é sobretudo remoção de viés). Os itens 1 e 2 são os que
exigem ação antes de o pacote ser usado pelo pesquisador.

---

## 8. O que está certo (para não restar dúvida)

- **Zero vazamento de futuro** nas variáveis de entrada; o teste de perturbação é bem construído
  e o caso errado proposital é pego.
- **Todos os números que conferi reproduzem**, alguns byte-idênticos; a regra 2 das
  `REGRAS-COMUNS.md` foi cumprida.
- **As três correções de `CORRECOES.md` foram feitas de verdade**, com a evidência no lugar certo,
  e a §12 do relatório registra o que mudou.
- **As 9 referências conferem** no Crossref (verifiquei uma por uma, título/revista/ano).
- A **figura** está coerente com as tabelas e com a definição de cheia.
- O relatório é **honesto** nas ressalvas mais difíceis: evento único, IC enganoso, viés, datum não
  verificado, volume não medido, chuva não-MERGE, previsão substituta.
- A **separação treino/validação/teste** é cronológica e o ajuste das correções nunca toca no teste.
- Nenhum dado pessoal nas saídas.

## 9. O que não consegui verificar

- **"A API nova do HidroWeb exige token por cadastro"** — não testei (exigiria credenciais, regra 4).
- **Volume total baixado** — o relatório assume ~200 MB; medi ~727 KB de XML por estação-mês
  (≈ 8,7 MB por estação-ano), o que daria ~315 MB no total (compatível com o limite de 1 GB),
  mas **não é** a medição do download original. Continua "não conferido", como o relatório diz.
- **"17350000 sem dados no período"** — consultei só **janeiro/2024** (0 registros, resposta vazia);
  o período inteiro não foi verificado. (A estação também não aparece no inventário da ANA.)
- **Mudança de datum / revisão de curva-chave / salto de sensor** — o próprio relatório marca como
  não verificado; não verifiquei (é conhecimento de campo).
- **Cota de alerta oficial do SGB** para esta estação — não verificada (idem).
- **MERGE** — não baixado, como registrado.
- **Earth Engine** — nenhuma chamada no código da pasta; não pude auditar o histórico da máquina.
- **Distância "a ~250 km"** entre as estações: em linha reta, pelas coordenadas do inventário, são
  **225 km** (São Félix → Bandeirantes). É compatível com ~250 km ao longo do rio; não é problema.
- **Comportamento do pacote com as previsões reais do pesquisador** — não testei com dados de um
  terceiro sistema de verdade; só com rótulos sintéticos (§6.1).
