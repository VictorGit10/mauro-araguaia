# Correções pedidas após a conferência (31/10/2026)

O trabalho foi conferido: os testes passam e as métricas se reproduzem. São ajustes de texto e de rastreabilidade. As regras de `REGRAS-COMUNS.md` continuam valendo. Ao terminar, acrescente ao `RELATORIO.md` uma seção **"Correções de 31/10"** com o que mudou.

## 1. Número sem script
A seção 1 diz que em Aruanã (25200000) os máximos de 2024–2025 ficaram abaixo do treino, com "verificação exploratória, não salva em script". Pela regra 2, isso precisa de script. Escreva `codigo/09_aruana.py`, que baixa (ou reaproveita) a série de Aruanã e imprime os máximos anuais e o P90 do treino, e cite a saída. Se o download for grande ou falhar, troque a frase por "não conferido" e explique.

## 2. O controle embaralhado na cheia muda a leitura
No geral, a correção embaralhada tem habilidade 0,315 contra 0,407 do Kalman, e o relatório conclui que "a maior parte do ganho vem do viés médio". Mas em `dados/metricas.csv`, **nos dias de cheia**, a embaralhada tem habilidade 0,229 contra 0,438 do Kalman: ali o momento da correção pesa bem mais. Acrescente isso à seção 7, com os números, sem exagerar (é um evento só).

## 3. Intervalo de confiança da cheia
A seção 8 cita "0,429 a 0,497 de habilidade para o Kalman" na cheia, mas esse intervalo não está nas tabelas. Mostre de qual arquivo/script ele sai (ou gere-o em `06_avaliacao.py` e salve em `dados/`). Mantenha a ressalva de que o bootstrap reamostra dias e não eventos.

## 4. Não mexa
Dados, previsão substituta, correções e teste de vazamento estão conferidos. Só rode de novo o que for preciso para os itens acima e confira que `dados/metricas.csv` continua idêntico.
