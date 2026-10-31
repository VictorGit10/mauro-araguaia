"""Monta a série diária final (níveis das duas estações + chuva da bacia).

Uso:
  python codigo/03_montar_series.py
  python codigo/03_montar_series.py --chuva caminho/merge.csv

O CSV de chuva deve ter as colunas `data` (AAAA-MM-DD) e `chuva_bacia_mm`
(mm/dia, média da bacia a montante). Serve para plugar o MERGE do CPTEC já
processado pelo pesquisador, no lugar da reanálise do Open-Meteo.

Saída: dados/series_diarias.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from comum import DADOS, carregar_series


def carregar_chuva_externa(caminho: Path, idx: pd.DatetimeIndex) -> pd.Series:
    d = pd.read_csv(caminho)
    faltando = [c for c in ("data", "chuva_bacia_mm") if c not in d.columns]
    if faltando:
        raise ValueError(f"o CSV de chuva precisa das colunas ['data', 'chuva_bacia_mm']; "
                         f"faltam {faltando}")
    d["data"] = pd.to_datetime(d["data"])
    d = d.drop_duplicates("data").set_index("data")["chuva_bacia_mm"]
    s = d.reindex(idx)
    n_falta = int(s.isna().sum())
    if n_falta:
        print(f"AVISO: {n_falta} dias sem chuva no CSV externo; preenchidos com 0,0 mm")
        s = s.fillna(0.0)
    return s.rename("chuva_bacia_mm")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--chuva", default=None,
                    help="CSV com data,chuva_bacia_mm (ex.: chuva do MERGE já processada). "
                         "Sem esta opção, usa a reanálise do Open-Meteo.")
    args = ap.parse_args()

    df = carregar_series()
    if args.chuva:
        cb = carregar_chuva_externa(Path(args.chuva), df.index)
        print(f"Chuva externa: {args.chuva}")
    else:
        from importlib import import_module
        cb = import_module("02_chuva_bacia").chuva_bacia()
        print("Chuva: reanálise ERA5 (Open-Meteo), modelo fixo")
    df = df.join(cb, how="left")
    df["chuva_bacia_mm"] = df["chuva_bacia_mm"].fillna(0.0)

    df.to_csv(DADOS / "series_diarias.csv")
    print(f"Série diária: {df.index.min().date()} a {df.index.max().date()} ({len(df)} dias)")
    for c in df.columns:
        print(f"  {c:15s} válidos={df[c].notna().sum():5d}  "
              f"min={df[c].min():7.2f}  max={df[c].max():7.2f}")
    faltas = df["nivel_alvo"].isna() | df["nivel_montante"].isna()
    print(f"Dias sem nível em alguma das duas estações: {int(faltas.sum())}")


if __name__ == "__main__":
    main()
