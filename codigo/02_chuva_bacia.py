"""Chuva diária na bacia a montante, por reanálise aberta (Open-Meteo / ERA5).

MERGE do CPTEC entrega recortes diários em GRIB/netCDF; para 12 anos o volume
passa fácil de 1 GB e o recorte por bacia não é trivial. Como a chuva é opcional
no pedido, usamos uma alternativa aberta, sem cadastro e leve: a API pública
Open-Meteo, com 8 pontos na bacia a montante de São Félix do Araguaia, e a média
simples entre pontos como índice de chuva da bacia.

MODELO FIXO: `models=era5`. Sem esse parâmetro a API devolve o "Best Match"
(ERA5 até 2016, IFS depois), o que quebra a homogeneidade da série. O ERA5-Land
foi testado e não devolve precipitação nesta API (valores nulos); por isso o
modelo fixo é o ERA5 (~30 km), não o ERA5-Land (~9 km).

Isto NÃO é o MERGE. Para usar a chuva do MERGE do pesquisador, veja
`03_montar_series.py --chuva arquivo.csv`.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import requests

from comum import ANO_FIM, ANO_INI, BRUTO

URL = "https://archive-api.open-meteo.com/v1/archive"
MODELO = "era5"

# Pontos espalhados na bacia do Araguaia a montante de São Félix (inclui Rio das Mortes).
PONTOS = [
    (-13.64, -50.78),  # Bandeirantes
    (-13.20, -51.30),
    (-12.80, -51.80),
    (-12.40, -52.20),  # bacia do Rio das Mortes
    (-12.90, -52.60),
    (-12.00, -51.50),
    (-11.80, -50.90),  # proximidades de São Félix
    (-12.30, -50.70),
]


def baixar_ponto(lat: float, lon: float) -> pd.DataFrame:
    destino = BRUTO / f"chuva_{MODELO}_{lat:.2f}_{lon:.2f}.csv"
    if destino.exists():
        return pd.read_csv(destino, parse_dates=["data"])

    r = requests.get(
        URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": f"{ANO_INI}-01-01",
            "end_date": f"{ANO_FIM}-12-31",
            "daily": "precipitation_sum",
            "timezone": "UTC",
            "models": MODELO,
        },
        timeout=120,
    )
    r.raise_for_status()
    j = r.json()["daily"]
    d = pd.DataFrame({"data": pd.to_datetime(j["time"]), "chuva_mm": j["precipitation_sum"]})
    d["lat"], d["lon"], d["modelo"] = lat, lon, MODELO
    d.to_csv(destino, index=False)
    time.sleep(0.5)
    return d


def chuva_bacia() -> pd.DataFrame:
    partes = [baixar_ponto(lat, lon) for lat, lon in PONTOS]
    df = pd.concat(partes)
    if df["chuva_mm"].isna().any():
        n = int(df["chuva_mm"].isna().sum())
        raise ValueError(f"{n} dias sem chuva no arquivo do Open-Meteo; "
                         "verifique o modelo e o período")
    out = df.groupby("data")["chuva_mm"].mean().rename("chuva_bacia_mm").to_frame()
    out.index.name = "data"
    return out


if __name__ == "__main__":
    d = chuva_bacia()
    print(f"Modelo fixo: {MODELO}")
    print(f"Chuva da bacia: {d.index.min().date()} a {d.index.max().date()}, {len(d)} dias")
    print(f"Média anual (mm):\n{d.groupby(d.index.year)['chuva_bacia_mm'].sum().round(0).to_string()}")
