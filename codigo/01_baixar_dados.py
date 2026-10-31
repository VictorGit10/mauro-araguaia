"""Baixa a série de 15 min de duas estações do Araguaia (alvo e montante) da ANA.

Uso:  python codigo/01_baixar_dados.py
Saída: dados/bruto/<codigo>_<ano>.csv.gz  e  dados/estacoes.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from comum import ANO_FIM, ANO_INI, DADOS, ESTACOES, baixar_serie_bruta

if __name__ == "__main__":
    total_bytes = 0
    for papel, meta in ESTACOES.items():
        print(f"== {meta['nome']} ({meta['codigo']}, {papel}) ==")
        for ano in range(ANO_INI, ANO_FIM + 1):
            arq = baixar_serie_bruta(meta["codigo"], ano)
            total_bytes += arq.stat().st_size
            print(f"  {ano}: {arq.stat().st_size/1e6:6.2f} MB (comprimido)")

    DADOS.mkdir(exist_ok=True)
    pd.DataFrame(ESTACOES).T.to_csv(DADOS / "estacoes.csv", index=False)
    print(f"\nTotal em disco (comprimido): {total_bytes/1e6:.1f} MB")
