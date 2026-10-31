# AGENTS.md

As instruções para agentes de IA neste projeto estão em **`CLAUDE.md`** — leia esse arquivo primeiro.

Resumo: os dados vêm da ANA (webservice antigo, sem login) e da chuva ERA5 fixa via Open-Meteo; os scripts rodam na ordem `01` a `10`, e o invariante central é que nenhuma variável de entrada pode usar informação posterior à data de emissão `t` (verificado por `codigo/test_vazamento.py`). Cada valor da coluna `modelo` é um sistema de previsão independente, com correções e métricas próprias.
