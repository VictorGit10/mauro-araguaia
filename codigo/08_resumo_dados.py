"""Resumo de auditoria dos dados (números citados no RELATORIO.md).

Uso: python codigo/08_resumo_dados.py
Saída: dados/resumo_dados.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from comum import BRUTO, DADOS

if __name__ == "__main__":
    s = pd.read_csv(DADOS / "series_diarias.csv", index_col="data", parse_dates=True)
    resumo = {
        "periodo": [str(s.index.min().date()), str(s.index.max().date())],
        "dias": int(len(s)),
        "validos": {c: int(s[c].notna().sum()) for c in s.columns},
        "arquivos_brutos": len(list(BRUTO.glob("*.csv.gz"))),
        "tamanho_bruto_mb": round(sum(f.stat().st_size for f in BRUTO.glob("*.csv.gz")) / 1e6, 2),
        "registros_15min": {},
        "lacunas_nivel": {},
    }
    for codigo in ("26350000", "25700000"):
        arquivos = sorted(BRUTO.glob(f"{codigo}_*.csv.gz"))
        n = 0
        for a in arquivos:
            n += len(pd.read_csv(a, usecols=["DataHora"]))
        resumo["registros_15min"][codigo] = int(n)

    for col in ("nivel_alvo", "nivel_montante"):
        falta = s[col].isna()
        runs, ini = [], None
        for d, f in falta.items():
            if f and ini is None:
                ini = d
            elif not f and ini is not None:
                runs.append((d - ini).days)
                ini = None
        if ini is not None:
            runs.append((s.index[-1] - ini).days + 1)
        resumo["lacunas_nivel"][col] = {
            "total_dias": int(falta.sum()),
            "maior_lacuna_dias": int(max(runs) if runs else 0),
            "lacunas_maiores_3d": int(sum(1 for r in runs if r > 3)),
        }

    serie_teste = s.loc["2024-01-01":"2025-12-31", "nivel_alvo"]
    resumo["teste_dias_sem_nivel_alvo"] = int(serie_teste.isna().sum())
    resumo["chuva_bacia_media_anual_mm"] = round(float(s["chuva_bacia_mm"].sum() / 12), 0)

    with open(DADOS / "resumo_dados.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    print(json.dumps(resumo, ensure_ascii=False, indent=2))
