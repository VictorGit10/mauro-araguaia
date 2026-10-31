"""Ablação da chuva: ERA5 fixo (atual) versus "Best Match" (o que havia antes).

O 02_chuva_bacia.py passou a fixar `models=era5`; antes, sem esse parâmetro, a
API devolvia o "Best Match" (ERA5 até 2016, IFS depois). Este script baixa a
série antiga, reconstrói a série diária e roda as correções do modelo cota-cota
com as duas chuvas, comparando na MESMA amostra de datas.

Uso: python codigo/10_ablation_chuva.py
Saída: dados/ablation_chuva.csv
"""

from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import requests

from comum import ANO_FIM, ANO_INI, BRUTO, DADOS

URL = "https://archive-api.open-meteo.com/v1/archive"
PONTOS = [
    (-13.64, -50.78), (-13.20, -51.30), (-12.80, -51.80), (-12.40, -52.20),
    (-12.90, -52.60), (-12.00, -51.50), (-11.80, -50.90), (-12.30, -50.70),
]
METODOS = ["persistencia", "ar", "kalman", "rf", "hgb", "rf_enxuto"]


def baixar_bestmatch(lat: float, lon: float) -> pd.DataFrame:
    destino = BRUTO / f"chuva_bestmatch_{lat:.2f}_{lon:.2f}.csv"
    if destino.exists():
        return pd.read_csv(destino, parse_dates=["data"])
    r = requests.get(URL, params={
        "latitude": lat, "longitude": lon,
        "start_date": f"{ANO_INI}-01-01", "end_date": f"{ANO_FIM}-12-31",
        "daily": "precipitation_sum", "timezone": "UTC",
    }, timeout=120)
    r.raise_for_status()
    j = r.json()["daily"]
    d = pd.DataFrame({"data": pd.to_datetime(j["time"]), "chuva_mm": j["precipitation_sum"]})
    d["lat"], d["lon"] = lat, lon
    d.to_csv(destino, index=False)
    time.sleep(0.5)
    return d


def chuva_bestmatch() -> pd.Series:
    df = pd.concat([baixar_bestmatch(lat, lon) for lat, lon in PONTOS])
    s = df.groupby("data")["chuva_mm"].mean().rename("chuva_bacia_mm")
    s.index.name = "data"
    return s


def metricas_comuns(tab: pd.DataFrame, metodos: list[str]) -> pd.DataFrame:
    test = tab[(tab["data_emissao"] >= "2024-01-01") & tab["observado"].notna()]
    comum = test.dropna(subset=["observado", *metodos]).copy()
    linhas = []
    for m in metodos:
        e = comum["observado"] - comum[m]
        linhas.append({"metodo": m, "n": len(comum),
                       "rmse": float(np.sqrt(np.mean(e ** 2))),
                       "vies": float(np.mean(e))})
    return pd.DataFrame(linhas), comum[["data_emissao"]]


if __name__ == "__main__":
    m05 = importlib.import_module("05_correcoes")
    series = pd.read_csv(DADOS / "series_diarias.csv", index_col="data", parse_dates=True)
    prev = pd.read_csv(DADOS / "previsao_referencia.csv",
                       parse_dates=["data_emissao", "data_alvo"])
    prev = prev[prev["modelo"] == "cota_cota"].drop(columns=["modelo"]).reset_index(drop=True)

    # cenário atual (ERA5 fixo): usa a saída já gerada
    atual = pd.read_csv(DADOS / "previsoes_corrigidas.csv",
                        parse_dates=["data_emissao", "data_alvo"])
    atual = atual[atual["modelo"] == "cota_cota"]
    met_atual, datas_atual = metricas_comuns(atual, METODOS)

    # cenário antigo (Best Match)
    print("Baixando a chuva 'Best Match' (a que era usada antes)...")
    s_bm = series.copy()
    s_bm["chuva_bacia_mm"] = chuva_bestmatch().reindex(series.index).fillna(0.0)
    tab_bm, _, _ = m05.processar_modelo(s_bm, prev, "cota_cota", DADOS / "ablation_chuva")
    met_bm, datas_bm = metricas_comuns(tab_bm, METODOS)

    # mesma amostra nos dois cenários
    datas = datas_atual.merge(datas_bm, on="data_emissao")["data_emissao"]
    a = atual[atual["data_emissao"].isin(datas)]
    b = tab_bm[tab_bm["data_emissao"].isin(datas)]
    linhas = []
    for m in METODOS:
        ea = a["observado"] - a[m]
        eb = b["observado"] - b[m]
        linhas.append({
            "metodo": m, "n": len(datas),
            "rmse_era5": float(np.sqrt(np.mean(ea ** 2))),
            "rmse_bestmatch": float(np.sqrt(np.mean(eb ** 2))),
            "diferenca_bm_menos_era5": float(np.sqrt(np.mean(eb ** 2)) - np.sqrt(np.mean(ea ** 2))),
        })
    out = pd.DataFrame(linhas)
    out.to_csv(DADOS / "ablation_chuva.csv", index=False)
    print("\nAblação da chuva (mesma amostra de datas):")
    print(out.round(3).to_string(index=False))

    chuva = {
        "media_anual_era5_mm": round(float(series["chuva_bacia_mm"].sum() / 12), 0),
        "media_anual_bestmatch_mm": round(float(s_bm["chuva_bacia_mm"].sum() / 12), 0),
        "dias_mudados": int((series["chuva_bacia_mm"] - s_bm["chuva_bacia_mm"]).abs().gt(0.01).sum()),
    }
    with open(DADOS / "ablation_chuva.json", "w", encoding="utf-8") as f:
        json.dump(chuva, f, ensure_ascii=False, indent=2)
    print("\nChuva:", chuva)
