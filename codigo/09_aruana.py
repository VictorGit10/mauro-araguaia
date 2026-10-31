"""Verificação citada no RELATORIO: por que Aruanã (25200000) foi descartada.

Baixa (ou reaproveita) a série de 15 min de Aruanã, agrega para o dia com as
mesmas regras do pipeline principal e imprime:
  - máxima cota de cada ano (2014–2025);
  - P90 da cota diária no treino (2014–2021);
  - quantos dias de 2024 e 2025 ficaram acima desse P90.

Guarda o bruto em dados/aruana/ (fora de dados/bruto/, para não alterar a
contagem de arquivos do pipeline principal no 08_resumo_dados.py).

Uso: python codigo/09_aruana.py
Saída: dados/aruana_resumo.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

from comum import ANO_FIM, ANO_INI, DADOS, chamar_ana, xml_para_linhas

CODIGO = "25200000"
NOME = "ARUANÃ"
TREINO_FIM = "2021-12-31"
CACHE = DADOS / "aruana"


def baixar_ano(ano: int) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / f"{CODIGO}_{ano}.csv.gz"
    if destino.exists():
        return pd.read_csv(destino, parse_dates=["DataHora"])
    xml = chamar_ana("DadosHidrometeorologicos", codEstacao=CODIGO,
                     dataInicio=f"01/01/{ano}", dataFim=f"31/12/{ano}")
    linhas = xml_para_linhas(xml)
    df = pd.DataFrame(linhas) if linhas else pd.DataFrame(columns=["DataHora", "Nivel"])
    for col in ("Nivel", "Chuva", "Vazao"):
        if col not in df:
            df[col] = None
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "DataHora" in df:
        df["DataHora"] = pd.to_datetime(df["DataHora"].str.strip(), errors="coerce")
    df.to_csv(destino, index=False, compression="gzip")
    time.sleep(0.3)
    return df


def serie_diaria() -> pd.DataFrame:
    partes = [baixar_ano(ano) for ano in range(ANO_INI, ANO_FIM + 1)]
    df = pd.concat(partes, ignore_index=True)
    df["data"] = df["DataHora"].dt.normalize()
    g = df.groupby("data")["Nivel"].agg(nivel="mean", n="count")
    g["nivel"] = g["nivel"] / 100.0  # cm -> m
    g.loc[g["n"] < 20, "nivel"] = np.nan
    g.loc[(g["nivel"] < 0) | (g["nivel"] > 20), "nivel"] = np.nan
    idx = pd.date_range(f"{ANO_INI}-01-01", f"{ANO_FIM}-12-31", freq="D")
    g = g.reindex(idx)
    g.index.name = "data"
    g["nivel"] = g["nivel"].interpolate(method="linear", limit=3, limit_area="inside")
    return g


if __name__ == "__main__":
    s = serie_diaria()
    p90 = float(s.loc[:TREINO_FIM, "nivel"].quantile(0.90))
    maximos = s.groupby(s.index.year)["nivel"].max().round(2)
    acima = (s.assign(acima=s["nivel"] >= p90)
               .groupby(s.index.year)["acima"].sum().astype(int))

    print(f"Estação {CODIGO} ({NOME}) — {s.index.min().date()} a {s.index.max().date()}")
    print(f"P90 da cota diária no treino (2014–2021): {p90:.2f} m\n")
    print("Máxima anual e dias acima do P90 do treino:")
    for ano in maximos.index:
        print(f"  {ano}: máx = {maximos.loc[ano]:5.2f} m   dias ≥ P90 = {acima.loc[ano]:3d}")

    resumo = {
        "estacao": {"codigo": CODIGO, "nome": NOME},
        "p90_treino_m": round(p90, 2),
        "maximos_anuais_m": {str(k): float(v) for k, v in maximos.items()},
        "dias_acima_p90": {str(k): int(v) for k, v in acima.items()},
        "max_2024_m": float(maximos.loc[2024]),
        "max_2025_m": float(maximos.loc[2025]),
        "dias_acima_p90_2024": int(acima.loc[2024]),
        "dias_acima_p90_2025": int(acima.loc[2025]),
        "arquivos_cache": len(list(CACHE.glob(f"{CODIGO}_*.csv.gz"))),
        "tamanho_cache_mb": round(sum(f.stat().st_size for f in CACHE.glob(f"{CODIGO}_*.csv.gz")) / 1e6, 2),
    }
    with open(DADOS / "aruana_resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    print(f"\nCache: {resumo['arquivos_cache']} arquivos, {resumo['tamanho_cache_mb']} MB comprimidos")
    print("Salvo em dados/aruana_resumo.json")
