"""Previsão de referência (SUBSTITUTA) de 7 dias, ajustada só no período de treino.

Não são as previsões do pesquisador. É um modelo cota-cota simples, com a cota
atual da estação alvo e cotas da estação a montante, para que o procedimento de
correção possa ser testado de ponta a ponta com dados públicos.

Uso:  python codigo/04_previsao_referencia.py
Saída: dados/previsao_referencia.csv  (data_emissao, data_alvo, previsao em metros)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from comum import DADOS, ESTACOES
from features import HORIZONTE, adicionar_observado, montar_features

TREINO_FIM = "2021-12-31"
BASE = ["h0", "h1", "dh3", "u0", "u1", "u2", "du3", "doy_sin", "doy_cos"]
# Se a estação a montante estiver sem dado no dia, usa um modelo sem montante
# (documentado no README). Sem isso, ~20% dos dias de teste ficariam sem previsão.
BASE_SEM_MONTANTE = ["h0", "h1", "dh3", "doy_sin", "doy_cos"]


def main() -> None:
    series = pd.read_csv(DADOS / "series_diarias.csv", index_col="data", parse_dates=True)
    vazio = pd.DataFrame(columns=["data_emissao", "previsao"])

    # Sem previsões ainda: só as variáveis observadas entram aqui.
    tab = montar_features(series, vazio)
    tab = adicionar_observado(tab, series)

    treino = tab[(tab["data_emissao"] <= TREINO_FIM) & tab[BASE + ["observado"]].notna().all(axis=1)]
    modelo = LinearRegression().fit(treino[BASE], treino["observado"])

    treino_fb = tab[(tab["data_emissao"] <= TREINO_FIM)
                    & tab[BASE_SEM_MONTANTE + ["observado"]].notna().all(axis=1)]
    modelo_fb = LinearRegression().fit(treino_fb[BASE_SEM_MONTANTE], treino_fb["observado"])

    tab["previsao"] = np.nan
    ok = tab[BASE].notna().all(axis=1)
    tab.loc[ok, "previsao"] = modelo.predict(tab.loc[ok, BASE])
    ok_fb = (~ok) & tab[BASE_SEM_MONTANTE].notna().all(axis=1)
    tab.loc[ok_fb, "previsao"] = modelo_fb.predict(tab.loc[ok_fb, BASE_SEM_MONTANTE])
    tab["modelo"] = np.select([ok, ok_fb], ["cota_cota", "sem_montante"], default="sem_dado")
    tab["fonte"] = "substituto_cota_cota"

    saida = tab.loc[ok | ok_fb, ["data_emissao", "data_alvo", "previsao", "modelo", "fonte"]].copy()
    saida.insert(0, "estacao", ESTACOES["alvo"]["codigo"])
    saida.to_csv(DADOS / "previsao_referencia.csv", index=False)

    # Desempenho do próprio substituto, por período (referência para o relatório).
    av = tab[(ok | ok_fb) & tab["observado"].notna()].copy()
    av["periodo"] = np.select(
        [av["data_emissao"] <= TREINO_FIM,
         av["data_emissao"] <= "2023-12-31"],
        ["treino", "validacao"], default="teste")
    resumo = {}
    for per, g in av.groupby("periodo"):
        e = g["observado"] - g["previsao"]
        resumo[per] = {
            "n": int(len(g)),
            "rmse": round(float(np.sqrt(np.mean(e ** 2))), 3),
            "mae": round(float(np.mean(np.abs(e))), 3),
            "vies": round(float(np.mean(e)), 3),
        }
        print(per, resumo[per])

    print("\nCoeficientes do modelo cota-cota (ajustado só em 2014-2021):")
    for nome, coef in zip(BASE, modelo.coef_):
        print(f"  {nome:12s} {coef: .4f}")
    print(f"  intercepto   {modelo.intercept_: .4f}")
    print("Coeficientes do modelo de reserva (sem montante):")
    for nome, coef in zip(BASE_SEM_MONTANTE, modelo_fb.coef_):
        print(f"  {nome:12s} {coef: .4f}")
    print(f"  intercepto   {modelo_fb.intercept_: .4f}")

    with open(DADOS / "modelo_referencia.json", "w", encoding="utf-8") as f:
        json.dump({
            "estacao_alvo": ESTACOES["alvo"],
            "estacao_montante": ESTACOES["montante"],
            "horizonte_dias": HORIZONTE,
            "treino": f"2014-01-01 a {TREINO_FIM}",
            "features": BASE,
            "coeficientes": dict(zip(BASE, modelo.coef_.round(5).tolist())),
            "intercepto": round(float(modelo.intercept_), 5),
            "features_reserva": BASE_SEM_MONTANTE,
            "coeficientes_reserva": dict(zip(BASE_SEM_MONTANTE, modelo_fb.coef_.round(5).tolist())),
            "intercepto_reserva": round(float(modelo_fb.intercept_), 5),
            "n_previsoes": {"cota_cota": int(ok.sum()), "sem_montante": int(ok_fb.sum())},
            "desempenho": resumo,
            "aviso": "previsão substituta, não são as previsões do pesquisador",
        }, f, ensure_ascii=False, indent=2)
    print(f"\n{len(saida)} previsões gravadas em dados/previsao_referencia.csv")


if __name__ == "__main__":
    main()
