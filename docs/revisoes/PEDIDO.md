# Pedido — correção dos erros de previsão de nível (7 dias), com dados públicos

Leia antes `REGRAS-COMUNS.md` e `CONTEXTO.md` (os dois estão nesta pasta).

## O que queremos
Não temos as previsões do pesquisador. Queremos **um procedimento reproduzível, rodando de ponta a ponta com dados públicos**, que ele possa reaproveitar trocando um arquivo de entrada pelas previsões dele. O foco é a parte que ele disse ser difícil: **usar só o que se sabe no momento da previsão** e **separar treino e avaliação sem vazar o futuro**.

Não é para decidir a metodologia do artigo dele. É para mostrar, com um caso real, como a comparação fica montada e que armadilhas aparecem.

## Passos
1. **Dados observados.** Escolha **uma estação** no Araguaia ou no Tocantins com série diária de cota longa (idealmente 10 anos ou mais, incluindo 2024–2025) e pelo menos uma estação a montante para um modelo cota-cota. Fontes possíveis: HidroWeb/ANA (veja se a API nova exige cadastro; se exigir, tente o webservice antigo de telemetria ou o download de séries e registre o que funcionou), sistemas de alerta do SGB. Registre os códigos das estações e a fonte.
2. **Chuva (opcional, se couber no limite de download).** MERGE do CPTEC, média diária na bacia a montante. Se ficar pesado, use poucos anos ou deixe registrado como passo seguinte.
3. **Previsão de referência (substituta).** Como não temos a dele, construa uma previsão simples de 7 dias (ex.: regressão cota-cota com a estação a montante e a cota atual), **ajustada só no período de treino**. Deixe claro em todo lugar que ela é um substituto.
4. **Tabela de erros.** Uma linha por data de emissão `t`: previsão para `t+7`, cota observada em `t+7`, erro. **Regra-chave:** na data `t`, o erro mais recente já verificado é o da previsão emitida em `t-7`. Escreva um **teste automatizado** (`codigo/test_vazamento.py`) que falha se qualquer variável de entrada usar informação posterior a `t`, e mostre que ele pega um caso errado proposital.
5. **Correções a comparar:**
   - (a) previsão original, sem correção;
   - (b) somar o último erro verificado (persistência do erro);
   - (c) modelo autorregressivo dos erros, com defasagens de 7 dias ou mais;
   - (d) filtro de Kalman simples sobre o viés, se viável no tempo;
   - (e) Random Forest e um gradient boosting prevendo o erro, com entradas conhecidas em `t` (cotas recentes, variação, chuva antecedente se houver, erros verificados).
6. **Divisão do tempo.** Só cronológica: treino, validação, teste; e também avaliação com origem móvel (walk-forward). Nada de divisão aleatória. Explique por quê no README.
7. **Métricas.** RMSE, MAE, viés e índice de habilidade em relação à previsão original. Separar **cheia** e não cheia (defina cheia de forma documentada: percentil alto do treino ou cota de alerta oficial, se for pública). **Conte quantos eventos de cheia** existem no período de teste e dê um intervalo de confiança por bootstrap em blocos para a diferença entre métodos. Se forem poucos eventos, diga com todas as letras o que isso permite e não permite concluir.
8. **Trocar pela previsão dele.** Documente o formato do CSV de entrada (colunas, datas, unidades) para ele colocar as previsões dos modelos dele e rodar tudo de novo.
9. **Referências.** 5 a 10 trabalhos sobre pós-processamento / correção de erro / atualização de previsões hidrológicas (AR dos erros, Kalman, aprendizado de máquina), com DOI conferido.

## Entregas
As de `REGRAS-COMUNS.md`, mais uma figura com a série observada, a previsão original e as corrigidas no período de teste, com as cheias marcadas.
