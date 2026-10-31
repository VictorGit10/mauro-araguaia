"""Montagem das variáveis de entrada (features) disponíveis na data de emissão t.

Regra de ouro: toda variável é calculada com a série truncada em t
(`series.loc[:t]`) e com previsões emitidas até t. O teste de vazamento
(`test_vazamento.py`) verifica isso por perturbação do futuro.

As previsões devem ser de UM modelo só (uma linha por data de emissão).
Para comparar vários modelos, o pipeline roda uma tabela por modelo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"

HORIZONTE = 7  # dias

# Variáveis usadas pelos modelos de aprendizado de máquina.
FEATURES_ML = [
    "h0", "h1", "dh1", "dh3", "dh7", "h_roll7_mean", "h_roll7_sd",
    "u0", "u1", "u2", "u3", "du1", "du3", "u_roll7_mean",
    "chuva_d0_2", "chuva_d3_6", "chuva_d7_14", "chuva_d15_29", "chuva_d30_59",
    "previsao", "previsao_menos_h0",
    "e7", "e14", "e21", "e28", "e_media4",
    "doy_sin", "doy_cos",
]

# Corretor enxuto: só erros já verificados e variação recente da cota.
FEATURES_ENXUTO = ["e7", "e14", "dh1", "dh3"]

# Variáveis do modelo autorregressivo de erros (apenas erros já verificados).
FEATURES_AR = ["e7", "e14"]


def _at(serie: pd.Series, data: pd.Timestamp) -> float:
    try:
        return float(serie.loc[data])
    except KeyError:
        return np.nan


def construir_linha(series: pd.DataFrame, t: pd.Timestamp, previsoes: pd.DataFrame) -> dict:
    """Uma linha de variáveis para a emissão em t. Só enxerga dados até t.

    `previsoes` deve conter um único modelo (uma linha por data de emissão).
    """
    s = series.loc[:t]
    p = previsoes[previsoes["data_emissao"] <= t]
    mapa = dict(zip(p["data_emissao"], p["previsao"]))

    h = s["nivel_alvo"]
    u = s["nivel_montante"]
    r = s["chuva_bacia_mm"]

    def d(offset: int) -> pd.Timestamp:
        return t - pd.Timedelta(days=offset)

    h0, h1 = _at(h, t), _at(h, d(1))
    u0, u1, u2, u3 = _at(u, t), _at(u, d(1)), _at(u, d(2)), _at(u, d(3))

    janela_h = h.loc[d(6):t]
    janela_u = u.loc[d(6):t]

    def soma_chuva(n: int, inicio: int = 0) -> float:
        """Soma n dias, do dia t-inicio para trás (inclusive)."""
        return float(r.loc[d(inicio + n - 1):d(inicio)].sum())

    doy = t.dayofyear
    previsao = mapa.get(t, np.nan)

    # Erro da previsão emitida em t-k, verificado em (t-k)+HORIZONTE.
    # Só entra se o alvo já é conhecido em t (k >= horizonte).
    erros = {k: np.nan for k in (7, 14, 21, 28)}
    for k in erros:
        emissao = d(k)
        alvo = d(k - HORIZONTE)
        if emissao in mapa and alvo in h.index:
            erros[k] = float(h.loc[alvo] - mapa[emissao])

    e_lista = list(erros.values())
    e_media4 = float(np.mean(e_lista)) if np.all(np.isfinite(e_lista)) else np.nan

    return {
        "data_emissao": t,
        "data_alvo": t + pd.Timedelta(days=HORIZONTE),
        "h0": h0,
        "h1": h1,
        "dh1": h0 - h1,
        "dh3": h0 - _at(h, d(3)),
        "dh7": h0 - _at(h, d(7)),
        "h_roll7_mean": float(janela_h.mean()),
        "h_roll7_sd": float(janela_h.std()),
        "u0": u0,
        "u1": u1,
        "u2": u2,
        "u3": u3,
        "du1": u0 - u1,
        "du3": u0 - u3,
        "u_roll7_mean": float(janela_u.mean()),
        # Janelas de chuva em dias antes de t, inclusive o próprio dia t.
        "chuva_d0_2": soma_chuva(3, 0),
        "chuva_d3_6": soma_chuva(4, 3),
        "chuva_d7_14": soma_chuva(8, 7),
        "chuva_d15_29": soma_chuva(15, 15),
        "chuva_d30_59": soma_chuva(30, 30),
        "previsao": previsao,
        "previsao_menos_h0": previsao - h0 if np.isfinite(previsao) and np.isfinite(h0) else np.nan,
        "e7": erros[7],
        "e14": erros[14],
        "e21": erros[21],
        "e28": erros[28],
        "e_media4": e_media4,
        "doy_sin": np.sin(2 * np.pi * doy / 365.25),
        "doy_cos": np.cos(2 * np.pi * doy / 365.25),
    }


def montar_features(series: pd.DataFrame, previsoes: pd.DataFrame,
                     datas: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    if previsoes["data_emissao"].duplicated().any():
        raise ValueError(
            "há mais de uma previsão para a mesma data de emissão; "
            "separe os modelos e chame montar_features uma vez por modelo")
    datas = datas if datas is not None else pd.DatetimeIndex(series.index)
    linhas = [construir_linha(series, t, previsoes) for t in datas]
    return pd.DataFrame(linhas)


def adicionar_observado(tab: pd.DataFrame, series: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta a cota observada no dia alvo e o erro da previsão original."""
    tab = tab.copy()
    tab["observado"] = series["nivel_alvo"].reindex(tab["data_alvo"]).to_numpy()
    tab["erro"] = tab["observado"] - tab["previsao"]
    return tab
