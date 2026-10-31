"""Confere os DOIs em api.crossref.org e grava o que voltou.

Uso: python codigo/07_referencias.py
Saída: dados/referencias_conferidas.json
Só entra em REFERENCIAS.md o que voltar com título batendo.
"""

from __future__ import annotations

import json
import sys
import time
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from comum import DADOS

CANDIDATAS = [
    ("10.1016/S0022-1694(01)00420-6",
     "The case for probabilistic forecasting in hydrology"),
    ("10.1029/2005WR004093",
     "Particle filtering and ensemble Kalman filtering for state updating with hydrological conceptual rainfall-runoff models"),
    ("10.5194/hess-16-3863-2012",
     "Advancing data assimilation in operational hydrologic forecasting: progresses, challenges, and emerging opportunities"),
    ("10.1029/2010WR009137",
     "Multiscale error analysis, correction, and predictive uncertainty estimation in a flood forecasting system"),
    ("10.5194/hess-22-6005-2018",
     "Rainfall–runoff modelling using Long Short-Term Memory (LSTM) networks"),
    ("10.1038/s41586-024-07145-1",
     "Global prediction of extreme floods in ungauged watersheds"),
    ("10.5194/hess-26-4013-2022",
     "Flood forecasting with machine learning models in an operational framework"),
    ("10.1029/2003WR002540",
     "A stochastic approach for assessing the uncertainty of rainfall-runoff simulations"),
    ("10.5194/hess-22-4815-2018",
     "Toward continental hydrologic-hydrodynamic modeling in South America"),
]


def normalizar(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    for ch in "‐‑‒–—―−":
        s = s.replace(ch, "-")
    return " ".join(s.lower().split())


def main() -> None:
    out = []
    for doi, titulo_esperado in CANDIDATAS:
        url = f"https://api.crossref.org/works/{requests.utils.quote(doi, safe='')}"
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "conferencia-doi/1.0"})
            ok = r.status_code == 200
            msg = r.json()["message"] if ok else {}
        except Exception as e:  # noqa: BLE001
            ok, msg = False, {"erro": str(e)}
        titulo = (msg.get("title") or [""])[0]
        confere = normalizar(titulo_esperado) == normalizar(titulo)
        out.append({
            "doi": doi,
            "titulo_esperado": titulo_esperado,
            "titulo_crossref": titulo,
            "revista": (msg.get("container-title") or [""])[0],
            "ano": (msg.get("issued", {}).get("date-parts", [[None]])[0][0]),
            "autores": [" ".join(filter(None, [a.get("given"), a.get("family")]))
                        for a in msg.get("author", [])][:3],
            "status_http": r.status_code if "r" in dir() else None,
            "confere": bool(ok and confere),
        })
        print(f"{'OK ' if ok and confere else 'FALHA'} {doi} -> {titulo[:90]}")
        time.sleep(0.4)

    with open(DADOS / "referencias_conferidas.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n{sum(x['confere'] for x in out)}/{len(out)} conferem")


if __name__ == "__main__":
    main()
