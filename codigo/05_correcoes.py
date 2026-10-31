"""Tabela de erros e correções, um sistema de previsão por vez.

Cada valor da coluna `modelo` (ou o modelo único, se a coluna não existir) é
tratado como um sistema independente: features, erros verificados, ajuste das
correções, Kalman e walk-forward são feitos só com as previsões daquele modelo.

Entrada:  dados/series_diarias.csv + dados/previsao_referencia.csv
          (ou um CSV externo, no mesmo formato, com --previsao caminho.csv)
Saídas:   <saida>/tabela_erros.csv
          <saida>/previsoes_corrigidas.csv
          <saida>/previsoes_walkforward.csv
          <saida>/config_correcoes.json

Uso: python codigo/05_correcoes.py [--previsao dados/meu_csv.csv] [--saida dados]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline

from comum import DADOS
from features import (FEATURES_AR, FEATURES_ENXUTO, FEATURES_ML,
                      adicionar_observado, montar_features)

TREINO_FIM = "2021-12-31"
VAL_FIM = "2023-12-31"
MIN_TREINO = 200  # abaixo disso, AR/RF/HGB não são ajustados (só persistência e Kalman)

COLUNAS_ENTRADA = ["data_emissao", "data_alvo", "previsao"]

METODOS = ["previsao_original", "persistencia", "ar", "kalman", "rf", "hgb", "rf_enxuto"]


def carregar_previsoes(caminho: Path) -> pd.DataFrame:
    p = pd.read_csv(caminho, parse_dates=["data_emissao", "data_alvo"])
    faltando = [c for c in COLUNAS_ENTRADA if c not in p.columns]
    if faltando:
        raise ValueError(f"o CSV de previsões precisa das colunas {COLUNAS_ENTRADA}; "
                         f"faltam {faltando}")
    if "modelo" not in p.columns:
        p["modelo"] = "informado"
    p["modelo"] = p["modelo"].fillna("informado").astype(str)

    dup = p.duplicated(["data_emissao", "modelo"])
    if dup.any():
        exemplos = p.loc[dup, ["data_emissao", "modelo"]].head(3).to_dict("records")
        raise ValueError(
            "há mais de uma previsão para a mesma (data_emissao, modelo); "
            f"exemplos: {exemplos}")

    for mod, g in p.groupby("modelo"):
        h = (g["data_alvo"] - g["data_emissao"]).dt.days
        if h.nunique() != 1:
            raise ValueError(f"o modelo '{mod}' tem horizontes diferentes "
                             f"({sorted(h.unique().tolist())}); use um CSV por horizonte")
        if h.iloc[0] != 7:
            print(f"AVISO: o modelo '{mod}' tem horizonte de {h.iloc[0]} dias; "
                  "as features assumem 7 dias e o erro verificado em t-7")

    return p[COLUNAS_ENTRADA + ["modelo"]].sort_values(["modelo", "data_emissao"]).reset_index(drop=True)


def kalman_vies(tab: pd.DataFrame, q: float, r: float) -> np.ndarray:
    """Filtro de Kalman escalar sobre o viés. Em t, usa só o erro já verificado e7."""
    b, P = 0.0, 1.0
    out = []
    for e7 in tab["e7"].to_numpy():
        P += q
        if np.isfinite(e7):
            K = P / (P + r)
            b = b + K * (e7 - b)
            P = (1 - K) * P
        out.append(b)
    return np.array(out)


def ajustar_ar(tab: pd.DataFrame) -> LinearRegression:
    m = tab[FEATURES_AR + ["erro"]].dropna()
    return LinearRegression().fit(m[FEATURES_AR], m["erro"])


def ajustar_rf(tab: pd.DataFrame, features: list[str], semente: int = 42):
    m = tab[features + ["erro"]].dropna()
    modelo = make_pipeline(
        SimpleImputer(strategy="median"),
        RandomForestRegressor(n_estimators=400, min_samples_leaf=4, max_features=0.6,
                              random_state=semente, n_jobs=1),
    )
    return modelo.fit(m[features], m["erro"])


def ajustar_hgb(tab: pd.DataFrame):
    m = tab[FEATURES_ML + ["erro"]].dropna()
    modelo = HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=15,
        l2_regularization=1.0, min_samples_leaf=20, random_state=42)
    return modelo.fit(m[FEATURES_ML], m["erro"])


def escolher_kalman(tab: pd.DataFrame) -> tuple[float, float, pd.DataFrame]:
    """Escolhe (q, r) minimizando RMSE na validação. Teste não participa."""
    val = ((tab["data_emissao"] >= "2022-01-01") & (tab["data_emissao"] <= VAL_FIM)
           & tab["observado"].notna() & tab["previsao"].notna())
    if val.sum() < 30:
        grade = pd.DataFrame([{"q": 0.01, "r": 1.0, "rmse_validacao": np.nan}])
        return 0.01, 1.0, grade
    linhas = []
    for q in [1e-5, 1e-4, 1e-3, 1e-2, 0.1, 1.0]:
        for r in [1e-3, 1e-2, 0.1, 1.0, 10.0, 100.0]:
            b = kalman_vies(tab, q, r)
            pred = tab["previsao"].to_numpy() + b
            ok = val.to_numpy() & np.isfinite(pred)
            rmse = float(np.sqrt(np.mean((tab["observado"].to_numpy()[ok] - pred[ok]) ** 2)))
            linhas.append({"q": q, "r": r, "rmse_validacao": rmse})
    grade = pd.DataFrame(linhas).sort_values("rmse_validacao")
    melhor = grade.iloc[0]
    return float(melhor["q"]), float(melhor["r"]), grade


def processar_modelo(series: pd.DataFrame, p: pd.DataFrame, mod: str, saida: Path):
    tab = montar_features(series, p)
    tab = adicionar_observado(tab, series)
    # só os dias em que este modelo realmente emitiu previsão
    tab = tab[tab["previsao"].notna()].reset_index(drop=True)
    tab["modelo"] = mod
    tab["previsao_original"] = tab["previsao"]

    treino = tab[(tab["data_emissao"] <= TREINO_FIM) & tab["erro"].notna()]
    n_treino = len(treino)
    print(f"\n== modelo '{mod}': {len(p)} previsões, {n_treino} linhas de treino ==")

    # (b) persistência do erro
    tab["persistencia"] = tab["previsao"] + tab["e7"]

    # (d) Kalman sobre o viés (sempre roda; não depende de treino)
    q, r, grade = escolher_kalman(tab)
    tab["kalman"] = tab["previsao"] + kalman_vies(tab, q, r)
    q_no_limite = q in (1e-5, 1.0)
    r_no_limite = r in (1e-3, 100.0)
    print(f"  Kalman: q={q:g}, r={r:g} (validação; q/r no limite: {q_no_limite}/{r_no_limite})")

    # (c),(e) dependem de treino suficiente
    if n_treino < MIN_TREINO:
        for c in ("ar", "rf", "hgb", "rf_enxuto"):
            tab[c] = np.nan
        print(f"  treino insuficiente ({n_treino} < {MIN_TREINO}): só persistência e Kalman")
        ar = rf = hgb = rf_enx = None
    else:
        ar = ajustar_ar(treino)
        ok_ar = tab[FEATURES_AR].notna().all(axis=1)
        tab["ar"] = np.nan
        tab.loc[ok_ar, "ar"] = tab.loc[ok_ar, "previsao"] + ar.predict(tab.loc[ok_ar, FEATURES_AR])

        rf = ajustar_rf(treino, FEATURES_ML)
        tab["rf"] = tab["previsao"] + rf.predict(tab[FEATURES_ML])

        hgb = ajustar_hgb(treino)
        tab["hgb"] = tab["previsao"] + hgb.predict(tab[FEATURES_ML])

        rf_enx = ajustar_rf(treino, FEATURES_ENXUTO, semente=7)
        tab["rf_enxuto"] = tab["previsao"] + rf_enx.predict(tab[FEATURES_ENXUTO])
        print("  AR, RF, HGB e corretor enxuto ajustados")

    saida.mkdir(parents=True, exist_ok=True)
    grade.to_csv(saida / f"kalman_grade_{mod}.csv", index=False)

    # ---------------- walk-forward: refit a cada 1º de janeiro ----------------
    wf = tab[["data_emissao", "data_alvo", "observado", "modelo",
              "previsao_original", "persistencia"]].copy()
    for c in ("ar_wf", "rf_wf", "hgb_wf", "rf_enxuto_wf", "kalman_wf"):
        wf[c] = np.nan

    for ano in range(2022, 2026):
        corte = pd.Timestamp(f"{ano}-01-01")
        fit = tab[(tab["data_emissao"] < corte) & tab["erro"].notna()]
        dentro = (tab["data_emissao"] >= corte) & (tab["data_emissao"] < pd.Timestamp(f"{ano+1}-01-01"))
        if not dentro.any():
            continue
        alvo = tab[dentro]
        idx = alvo.index
        # Kalman não precisa de treino: roda em qualquer modelo, inclusive o de reserva
        b = kalman_vies(tab[tab["data_emissao"] < pd.Timestamp(f"{ano+1}-01-01")], q, r)
        wf.loc[idx, "kalman_wf"] = alvo["previsao"] + b[-len(alvo):]
        if len(fit) < MIN_TREINO:
            print(f"  walk-forward {ano}: treino insuficiente ({len(fit)} < {MIN_TREINO}); só Kalman")
            continue
        ar_wf = ajustar_ar(fit)
        ok = alvo[FEATURES_AR].notna().all(axis=1)
        wf.loc[idx[ok], "ar_wf"] = alvo.loc[ok, "previsao"] + ar_wf.predict(alvo.loc[ok, FEATURES_AR])

        rf_wf = ajustar_rf(fit, FEATURES_ML)
        wf.loc[idx, "rf_wf"] = alvo["previsao"] + rf_wf.predict(alvo[FEATURES_ML])

        hgb_wf = ajustar_hgb(fit)
        wf.loc[idx, "hgb_wf"] = alvo["previsao"] + hgb_wf.predict(alvo[FEATURES_ML])

        enx_wf = ajustar_rf(fit, FEATURES_ENXUTO, semente=7)
        wf.loc[idx, "rf_enxuto_wf"] = alvo["previsao"] + enx_wf.predict(alvo[FEATURES_ENXUTO])

        print(f"  walk-forward {ano}: ajuste com {len(fit)} linhas, previsão em {len(alvo)} dias")

    metodos_disponiveis = [m for m in METODOS if tab[m].notna().any()]
    config = {
        "modelo": mod,
        "n_previsoes": int(len(p)),
        "n_treino": int(n_treino),
        "min_treino": MIN_TREINO,
        "kalman_q": q,
        "kalman_r": r,
        "kalman_no_limite_da_grade": bool(q_no_limite or r_no_limite),
        "metodos_disponiveis": metodos_disponiveis,
    }
    return tab, wf, config


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--previsao", default=str(DADOS / "previsao_referencia.csv"),
                    help="CSV com data_emissao, data_alvo, previsao (metros) e, opcionalmente, modelo")
    ap.add_argument("--saida", default=str(DADOS), help="diretório das saídas")
    args = ap.parse_args()

    series = pd.read_csv(DADOS / "series_diarias.csv", index_col="data", parse_dates=True)
    prev = carregar_previsoes(Path(args.previsao))
    saida = Path(args.saida)

    if prev.empty:
        raise ValueError("o CSV de previsões está vazio")
    print(f"Previsões: {len(prev)} linhas, modelos: {sorted(prev['modelo'].unique())}")

    tabelas, walks, configs = [], [], []
    for mod, p in prev.groupby("modelo", sort=True):
        tab, wf, cfg = processar_modelo(series, p, mod, saida)
        tabelas.append(tab)
        walks.append(wf)
        configs.append(cfg)

    tab = pd.concat(tabelas, ignore_index=True)
    wf = pd.concat(walks, ignore_index=True)
    tab.to_csv(saida / "tabela_erros.csv", index=False)
    saida.joinpath("previsoes_corrigidas.csv").unlink(missing_ok=True)
    saida.joinpath("previsoes_walkforward.csv").unlink(missing_ok=True)
    tab[["data_emissao", "data_alvo", "observado", "e7", "modelo", *METODOS]].to_csv(
        saida / "previsoes_corrigidas.csv", index=False)
    wf.to_csv(saida / "previsoes_walkforward.csv", index=False)

    with open(saida / "config_correcoes.json", "w", encoding="utf-8") as f:
        json.dump({
            "arquivo_previsao": str(Path(args.previsao).name),
            "horizonte": 7,
            "treino_fim": TREINO_FIM,
            "validacao_fim": VAL_FIM,
            "min_treino": MIN_TREINO,
            "modelos": configs,
        }, f, ensure_ascii=False, indent=2)

    print(f"\nSaídas em {saida}: previsoes_corrigidas.csv ({len(tab)} linhas), "
          "previsoes_walkforward.csv, config_correcoes.json")


if __name__ == "__main__":
    main()
