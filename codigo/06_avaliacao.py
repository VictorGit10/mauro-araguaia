"""Avaliação por modelo: métricas, cheias, bootstrap e figura.

Cada valor de `modelo` é avaliado separadamente (é um sistema de previsão
diferente). As métricas usam a amostra comum às correções disponíveis naquele
modelo, para comparar métodos nos mesmos dias.

Uso: python codigo/06_avaliacao.py
Saídas: dados/metricas.csv, metricas_walkforward.csv, metricas_completo.csv,
        bootstrap.csv, bootstrap_diferencas.csv, resumo.json,
        figuras/serie_teste.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from comum import DADOS, FIGURAS

TESTE_INI = "2024-01-01"
TESTE_FIM = "2025-12-31"
TREINO_FIM = "2021-12-31"
PERCENTIL_CHEIA = 90
N_BOOT = 2000
BLOCO_GERAL = 30
BLOCO_CHEIA = 7
SEMENTE = 42

METODOS = {
    "previsao_original": "Previsão original",
    "persistencia": "Persistência do erro",
    "ar": "AR dos erros (lag ≥ 7)",
    "kalman": "Kalman no viés",
    "rf": "Random Forest",
    "hgb": "Gradient boosting",
    "rf_enxuto": "Corretor enxuto (RF)",
}
METODOS_WF = {
    "ar_wf": "AR dos erros",
    "rf_wf": "Random Forest",
    "hgb_wf": "Gradient boosting",
    "rf_enxuto_wf": "Corretor enxuto (RF)",
    "kalman_wf": "Kalman",
}
PARES = [
    ("kalman", "previsao_original"),
    ("rf", "kalman"),
    ("hgb", "kalman"),
    ("ar", "previsao_original"),
    ("rf", "previsao_original"),
    ("hgb", "previsao_original"),
    ("rf_enxuto", "kalman"),
    ("rf_enxuto", "previsao_original"),
    ("persistencia", "previsao_original"),
    ("rf", "rf_enxuto"),
]


def metricas(obs: np.ndarray, pred: np.ndarray) -> dict:
    e = obs - pred
    return {
        "n": int(len(e)),
        "rmse": float(np.sqrt(np.mean(e ** 2))),
        "mae": float(np.mean(np.abs(e))),
        "vies": float(np.mean(e)),
    }


def blocos_indices(n: int, tam: int) -> list[np.ndarray]:
    return np.array_split(np.arange(n), int(np.ceil(n / tam)))


def bootstrap_absoluto(df: pd.DataFrame, cols: list[str], tam: int) -> pd.DataFrame:
    df = df.sort_values("data_alvo").reset_index(drop=True)
    n = len(df)
    blocos = blocos_indices(n, tam)
    rng = np.random.default_rng(SEMENTE)
    difs = {c: [] for c in cols}
    skills = {c: [] for c in cols}
    obs = df["observado"].to_numpy()
    base = df["previsao_original"].to_numpy()
    for _ in range(N_BOOT):
        idx = np.concatenate([blocos[i] for i in rng.integers(0, len(blocos), len(blocos))])[:n]
        o = obs[idx]
        mse_b = np.mean((o - base[idx]) ** 2)
        for c in cols:
            mse_c = np.mean((o - df[c].to_numpy()[idx]) ** 2)
            difs[c].append(np.sqrt(mse_c) - np.sqrt(mse_b))
            skills[c].append(1 - mse_c / mse_b)
    linhas = []
    for c in cols:
        d, s = np.array(difs[c]), np.array(skills[c])
        linhas.append({
            "metodo": c, "n": n, "bloco_dias": tam,
            "delta_rmse": float(np.mean(d)),
            "delta_rmse_ic95_inf": float(np.percentile(d, 2.5)),
            "delta_rmse_ic95_sup": float(np.percentile(d, 97.5)),
            "habilidade": float(np.mean(s)),
            "habilidade_ic95_inf": float(np.percentile(s, 2.5)),
            "habilidade_ic95_sup": float(np.percentile(s, 97.5)),
            "p_melhor": float(np.mean(d < 0)),
        })
    return pd.DataFrame(linhas)


def bootstrap_diferencas(df: pd.DataFrame, pares: list[tuple[str, str]],
                         tam: int) -> pd.DataFrame:
    """IC da diferença pareada de habilidade (A - B) na mesma reamostragem."""
    df = df.sort_values("data_alvo").reset_index(drop=True)
    n = len(df)
    blocos = blocos_indices(n, tam)
    rng = np.random.default_rng(SEMENTE)
    obs = df["observado"].to_numpy()
    base = df["previsao_original"].to_numpy()
    difs = {f"{a} - {b}": [] for a, b in pares}
    for _ in range(N_BOOT):
        idx = np.concatenate([blocos[i] for i in rng.integers(0, len(blocos), len(blocos))])[:n]
        o = obs[idx]
        mse_b = np.mean((o - base[idx]) ** 2)
        skills = {}
        for a, b in pares:
            for c in (a, b):
                if c not in skills:
                    mse_c = np.mean((o - df[c].to_numpy()[idx]) ** 2)
                    skills[c] = 1 - mse_c / mse_b
            difs[f"{a} - {b}"].append(skills[a] - skills[b])
    linhas = []
    for k, d in difs.items():
        d = np.array(d)
        linhas.append({
            "comparacao": k, "n": n, "bloco_dias": tam,
            "delta_habilidade": float(np.mean(d)),
            "ic95_inf": float(np.percentile(d, 2.5)),
            "ic95_sup": float(np.percentile(d, 97.5)),
            "p_a_melhor": float(np.mean(d > 0)),
        })
    return pd.DataFrame(linhas)


def eventos_cheia(serie: pd.Series, limiar: float, tolerancia: int = 2) -> list[dict]:
    acima = serie >= limiar
    grupos, inicio = [], None
    for data, flag in acima.items():
        if flag and inicio is None:
            inicio = data
        elif not flag and inicio is not None:
            grupos.append((inicio, data - pd.Timedelta(days=1)))
            inicio = None
    if inicio is not None:
        grupos.append((inicio, serie.index[-1]))
    juntos = []
    for g in grupos:
        if juntos and (g[0] - juntos[-1][1]).days <= tolerancia:
            juntos[-1] = (juntos[-1][0], g[1])
        else:
            juntos.append(g)
    return [{"inicio": a, "fim": b, "dias": int((b - a).days) + 1} for a, b in juntos]


def avaliar_modelo(mod: str, d: pd.DataFrame, w: pd.DataFrame, tab_err: pd.DataFrame,
                    limiar: float) -> dict:
    d = d[d["modelo"] == mod]
    w = w[w["modelo"] == mod]
    test_all = d[(d["data_emissao"] >= TESTE_INI) & (d["data_emissao"] <= TESTE_FIM)].copy()
    test_all = test_all[test_all["previsao_original"].notna()]
    test_all = test_all.merge(tab_err[["data_emissao", "modelo", "h0"]],
                              on=["data_emissao", "modelo"], how="left")
    disponiveis = [m for m in METODOS if test_all[m].notna().any()]
    comum = test_all.dropna(subset=["observado", *disponiveis]).copy()
    if comum.empty:
        raise ValueError(f"modelo '{mod}': amostra comum vazia — nenhum dia tem "
                         "observado e todas as correções disponíveis")
    comum["cheia"] = comum["observado"] >= limiar

    rng = np.random.default_rng(SEMENTE)
    comum["persistencia_cota"] = comum["h0"]
    if "kalman" in comum:
        comum["correcao_embaralhada"] = comum["previsao_original"] + rng.permutation(
            (comum["kalman"] - comum["previsao_original"]).to_numpy())

    todos = {**{k: v for k, v in METODOS.items() if k in disponiveis},
             "persistencia_cota": "Previsão ingênua (cota de hoje)"}
    if "correcao_embaralhada" in comum:
        todos["correcao_embaralhada"] = "Controle: correção embaralhada"

    linhas = []
    for sub, g in [("geral", comum), ("cheia", comum[comum["cheia"]]),
                   ("nao_cheia", comum[~comum["cheia"]])]:
        if g.empty:
            print(f"  AVISO: subconjunto '{sub}' vazio em '{mod}'; métricas não calculadas")
            continue
        base = g["observado"].to_numpy() - g["previsao_original"].to_numpy()
        mse0 = np.mean(base ** 2)
        for col, nome in todos.items():
            m = metricas(g["observado"].to_numpy(), g[col].to_numpy())
            mse = np.mean((g["observado"] - g[col]) ** 2)
            linhas.append({"modelo": mod, "subconjunto": sub, "metodo": col,
                           "nome": nome, **m, "habilidade": float(1 - mse / mse0)})
    met = pd.DataFrame(linhas)

    # robustez: cada método na sua amostra máxima
    cheio = test_all[test_all["observado"].notna()].copy()
    cheio["cheia"] = cheio["observado"] >= limiar
    linhas_full = []
    for sub, g in [("geral", cheio), ("cheia", cheio[cheio["cheia"]]),
                   ("nao_cheia", cheio[~cheio["cheia"]])]:
        for col in disponiveis:
            gg = g.dropna(subset=["observado", col])
            if gg.empty:
                continue
            m = metricas(gg["observado"].to_numpy(), gg[col].to_numpy())
            mse0 = np.mean((gg["observado"] - gg["previsao_original"]) ** 2)
            mse = np.mean((gg["observado"] - gg[col]) ** 2)
            linhas_full.append({"modelo": mod, "subconjunto": sub, "metodo": col,
                                **m, "habilidade": float(1 - mse / mse0)})
    met_full = pd.DataFrame(linhas_full)

    # bootstrap absoluto e pareado
    cols_boot = [c for c in disponiveis if c != "previsao_original"]
    boot = []
    for sub, g in [("geral", comum), ("cheia", comum[comum["cheia"]])]:
        if g.empty:
            continue
        tam = BLOCO_GERAL if sub == "geral" else BLOCO_CHEIA
        b = bootstrap_absoluto(g, cols_boot, tam)
        b["subconjunto"] = sub
        b["modelo"] = mod
        boot.append(b)
    boot = pd.concat(boot, ignore_index=True)

    pares = [(a, b) for a, b in PARES if a in disponiveis and b in disponiveis]
    difs = []
    for sub, g in [("geral", comum), ("cheia", comum[comum["cheia"]])]:
        if g.empty:
            continue
        tam = BLOCO_GERAL if sub == "geral" else BLOCO_CHEIA
        b = bootstrap_diferencas(g, pares, tam)
        b["subconjunto"] = sub
        b["modelo"] = mod
        b["ajuste"] = "fixo"
        difs.append(b)
    difs = pd.concat(difs, ignore_index=True)

    # walk-forward, mesmo tratamento
    tw = w[(w["data_emissao"] >= TESTE_INI) & (w["data_emissao"] <= TESTE_FIM)].copy()
    tw = tw[tw["previsao_original"].notna()]
    cols_wf = [m for m in METODOS_WF if tw[m].notna().any()]
    cw = tw.dropna(subset=["observado", "previsao_original", *cols_wf]).copy()
    cw["cheia"] = cw["observado"] >= limiar
    linhas_wf = []
    for sub, g in [("geral", cw), ("cheia", cw[cw["cheia"]]), ("nao_cheia", cw[~cw["cheia"]])]:
        base = g["observado"].to_numpy() - g["previsao_original"].to_numpy()
        mse0 = np.mean(base ** 2)
        for col in cols_wf:
            m = metricas(g["observado"].to_numpy(), g[col].to_numpy())
            mse = np.mean((g["observado"] - g[col]) ** 2)
            linhas_wf.append({"modelo": mod, "subconjunto": sub, "metodo": col,
                              "nome": METODOS_WF[col], **m,
                              "habilidade": float(1 - mse / mse0)})
    met_wf = pd.DataFrame(linhas_wf)

    # diferenças pareadas no walk-forward (A_wf - B_wf, com original como base)
    pares_wf = [(a + "_wf", b + "_wf") for a, b in PARES
                if a + "_wf" in cols_wf and b + "_wf" in cols_wf]
    pares_wf += [("kalman_wf", "previsao_original")]
    if "ar_wf" in cols_wf:
        pares_wf.append(("ar_wf", "previsao_original"))
    difs_wf = []
    for sub, g in [("geral", cw), ("cheia", cw[cw["cheia"]])]:
        if g.empty:
            continue
        tam = BLOCO_GERAL if sub == "geral" else BLOCO_CHEIA
        b = bootstrap_diferencas(g, pares_wf, tam)
        b["subconjunto"] = sub
        b["modelo"] = mod
        b["ajuste"] = "walk-forward"
        difs_wf.append(b)
    difs_wf = pd.concat(difs_wf, ignore_index=True)

    # dias de cheia do evento que ficaram fora da amostra
    fora = {}
    if mod == "cota_cota":
        eventos = eventos_cheia(
            pd.read_csv(DADOS / "series_diarias.csv", index_col="data", parse_dates=True)
            .loc[TESTE_INI:TESTE_FIM, "nivel_alvo"].dropna(), limiar)
        evento_dias = pd.DatetimeIndex([])
        for ev in eventos:
            evento_dias = evento_dias.union(pd.date_range(ev["inicio"], ev["fim"], freq="D"))
        dentro = pd.DatetimeIndex(comum["data_alvo"])
        faltam = evento_dias.difference(dentro)
        if len(faltam):
            fora = {"n": int(len(faltam)),
                    "inicio": str(faltam.min().date()), "fim": str(faltam.max().date())}

    return {
        "metricas": met, "metricas_completo": met_full,
        "bootstrap": boot, "diferencas": pd.concat([difs, difs_wf], ignore_index=True),
        "metricas_wf": met_wf, "comum": comum,
        "disponiveis": disponiveis, "n_teste": int(len(test_all)),
        "fora_amostra_cheia": fora,
    }


def kalman_vies_local(tab: pd.DataFrame, q: float, r: float) -> np.ndarray:
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


def sensibilidade_kalman(principal: str, comum: pd.DataFrame,
                          tab_err: pd.DataFrame) -> pd.DataFrame:
    """RMSE do Kalman para vários (q, r) na mesma amostra de teste.

    Mostra se a escolha da grade muda a conclusão e qual a memória do filtro.
    A memória aproximada é 1/K, com K ~ sqrt(q/r) no regime estacionário.
    """
    t = tab_err[tab_err["modelo"] == principal].sort_values("data_emissao").reset_index(drop=True)
    datas = set(comum["data_emissao"])
    linhas = []
    for q, r in [(1e-5, 0.1), (1e-4, 0.1), (1e-3, 1.0), (1e-2, 1.0), (1e-3, 0.1)]:
        b = kalman_vies_local(t, q, r)
        pred = t["previsao"].to_numpy() + b
        ok = t["data_emissao"].isin(datas).to_numpy() & np.isfinite(t["observado"].to_numpy())
        rmse = float(np.sqrt(np.mean((t["observado"].to_numpy()[ok] - pred[ok]) ** 2)))
        K = float(np.sqrt(q / r))
        linhas.append({"q": q, "r": r, "rmse_teste": rmse,
                       "ganho_estacionario_K": K, "memoria_aprox_dias": 1 / K})
    return pd.DataFrame(linhas)


def figura_cota_cota(comum: pd.DataFrame, limiar: float, eventos: list[dict]) -> None:
    t = comum.sort_values("data_alvo").set_index("data_alvo")
    t = t.reindex(pd.date_range(t.index.min(), t.index.max(), freq="D"))
    t.index.name = "data_alvo"
    t = t.reset_index()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                                   gridspec_kw={"height_ratios": [2.2, 1]})
    for ev in eventos:
        for ax in (ax1, ax2):
            ax.axvspan(ev["inicio"], ev["fim"], color="#f4c2c2", alpha=0.45, lw=0)

    ax1.plot(t["data_alvo"], t["observado"], color="black", lw=1.6, label="Observado")
    ax1.plot(t["data_alvo"], t["previsao_original"], color="#777777", lw=1.1, ls="--",
             label="Previsão original (substituta)")
    ax1.plot(t["data_alvo"], t["persistencia"], color="#e69f00", lw=0.9, alpha=0.9,
             label="Persistência do erro")
    ax1.plot(t["data_alvo"], t["ar"], color="#cc79a7", lw=0.9, alpha=0.9, label="AR dos erros")
    ax1.plot(t["data_alvo"], t["kalman"], color="#0072b2", lw=1.2, label="Kalman no viés")
    ax1.plot(t["data_alvo"], t["rf"], color="#009e73", lw=1.0, label="Random Forest")
    ax1.plot(t["data_alvo"], t["rf_enxuto"], color="#56b4e9", lw=1.0, ls=":",
             label="Corretor enxuto (RF)")
    ax1.set_ylabel("Cota (m)")
    ax1.set_title("São Félix do Araguaia (26350000) — previsão de 7 dias no período de teste "
                  "(2024–2025)\nFaixa rosa: cota acima do P90 do treino (cheia). "
                  "A amostra corrigida cobre a subida e o pico; a descida ficou sem dado de montante.")
    ax1.legend(ncol=4, fontsize=8, loc="upper left")
    ax1.grid(alpha=0.25)

    ax2.axhline(0, color="black", lw=0.7)
    ax2.plot(t["data_alvo"], t["observado"] - t["previsao_original"], color="#777777",
             lw=1.0, ls="--", label="Erro da original")
    ax2.plot(t["data_alvo"], t["observado"] - t["kalman"], color="#0072b2", lw=1.0,
             label="Erro após Kalman")
    ax2.plot(t["data_alvo"], t["observado"] - t["rf"], color="#009e73", lw=1.0,
             label="Erro após Random Forest")
    ax2.set_ylabel("Erro (m)")
    ax2.set_xlabel("Data do alvo (t+7)")
    ax2.legend(fontsize=8, ncol=3)
    ax2.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURAS / "serie_teste.png", dpi=160)
    plt.close(fig)


def main() -> None:
    d = pd.read_csv(DADOS / "previsoes_corrigidas.csv",
                    parse_dates=["data_emissao", "data_alvo"])
    w = pd.read_csv(DADOS / "previsoes_walkforward.csv",
                    parse_dates=["data_emissao", "data_alvo"])
    series = pd.read_csv(DADOS / "series_diarias.csv", index_col="data", parse_dates=True)
    tab_err = pd.read_csv(DADOS / "tabela_erros.csv", parse_dates=["data_emissao"])

    limiar = float(series.loc[:TREINO_FIM, "nivel_alvo"].quantile(PERCENTIL_CHEIA / 100))
    eventos = eventos_cheia(series.loc[TESTE_INI:TESTE_FIM, "nivel_alvo"].dropna(), limiar)
    print(f"Limiar de cheia (P{PERCENTIL_CHEIA} da cota observada no treino): {limiar:.2f} m")
    print(f"Eventos de cheia no teste: {len(eventos)}")
    for ev in eventos:
        print(f"  {ev['inicio'].date()} a {ev['fim'].date()} ({ev['dias']} dias)")

    resumo = {"limiar_cheia_m": round(limiar, 2),
              "eventos_cheia": [{k: (v.isoformat() if hasattr(v, "isoformat") else v)
                                 for k, v in e.items()} for e in eventos],
              "modelos": {}}
    mets, met_full, boots, difs, met_wfs = [], [], [], [], []

    for mod in sorted(d["modelo"].unique()):
        print(f"\n===== modelo: {mod} =====")
        r = avaliar_modelo(mod, d, w, tab_err, limiar)
        mets.append(r["metricas"])
        met_full.append(r["metricas_completo"])
        boots.append(r["bootstrap"])
        difs.append(r["diferencas"])
        met_wfs.append(r["metricas_wf"])
        print(f"teste: {r['n_teste']} emissões; amostra comum: {len(r['comum'])}; "
              f"cheia: {int(r['comum']['cheia'].sum())} dias; métodos: {r['disponiveis']}")
        if r["fora_amostra_cheia"]:
            f = r["fora_amostra_cheia"]
            print(f"  {f['n']} dias de cheia fora da amostra ({f['inicio']} a {f['fim']})")

        g = r["metricas"][r["metricas"].subconjunto == "geral"]
        print(g[["metodo", "n", "rmse", "mae", "vies", "habilidade"]].round(3).to_string(index=False))

        met = r["metricas"]
        def pega(sub, col, campo="rmse"):
            v = met[(met.subconjunto == sub) & (met.metodo == col)][campo]
            return None if v.empty else round(float(v.iloc[0]), 3)
        resumo["modelos"][mod] = {
            "n_teste": r["n_teste"],
            "n_amostra_comum": int(len(r["comum"])),
            "n_cheia": int(r["comum"]["cheia"].sum()),
            "metodos_disponiveis": r["disponiveis"],
            "rmse_geral": {c: pega("geral", c) for c in r["disponiveis"]},
            "habilidade_geral": {c: pega("geral", c, "habilidade") for c in r["disponiveis"]},
            "rmse_cheia": {c: pega("cheia", c) for c in r["disponiveis"]},
            "habilidade_cheia": {c: pega("cheia", c, "habilidade") for c in r["disponiveis"]},
            "fora_amostra_cheia": r["fora_amostra_cheia"],
        }

    met = pd.concat(mets, ignore_index=True)
    met.to_csv(DADOS / "metricas.csv", index=False)
    pd.concat(met_full, ignore_index=True).to_csv(DADOS / "metricas_completo.csv", index=False)
    boot = pd.concat(boots, ignore_index=True)
    boot.to_csv(DADOS / "bootstrap.csv", index=False)
    dif = pd.concat(difs, ignore_index=True)
    dif.to_csv(DADOS / "bootstrap_diferencas.csv", index=False)
    met_wf = pd.concat(met_wfs, ignore_index=True)
    met_wf.to_csv(DADOS / "metricas_walkforward.csv", index=False)

    # figura do sistema principal
    principal = "cota_cota" if "cota_cota" in d["modelo"].unique() else sorted(d["modelo"].unique())[0]
    base_principal = d[(d["modelo"] == principal) & (d["data_emissao"] >= TESTE_INI)
                       & (d["data_emissao"] <= TESTE_FIM)].copy()
    disp_principal = [m for m in METODOS if base_principal[m].notna().any()]
    comum = base_principal.dropna(subset=["observado", *disp_principal]).copy()
    comum = comum.merge(tab_err[["data_emissao", "modelo", "h0"]],
                        on=["data_emissao", "modelo"], how="left")
    sens = sensibilidade_kalman(principal, comum, tab_err)
    sens.to_csv(DADOS / "kalman_sensibilidade.csv", index=False)
    print("\nSensibilidade do Kalman a (q, r) na mesma amostra de teste:")
    print(sens.round(4).to_string(index=False))

    figura_cota_cota(comum, limiar, eventos)
    resumo["modelo_principal"] = principal

    with open(DADOS / "resumo.json", "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2, default=str)

    print("\nDiferenças pareadas (geral, ajuste fixo) — delta de habilidade e IC95:")
    print(dif[(dif.ajuste == "fixo") & (dif.subconjunto == "geral")][
        ["modelo", "comparacao", "delta_habilidade", "ic95_inf", "ic95_sup", "p_a_melhor"]
    ].round(3).to_string(index=False))
    print("\nDiferenças pareadas (cheia, blocos de 7 dias):")
    print(dif[(dif.subconjunto == "cheia")][
        ["modelo", "ajuste", "comparacao", "delta_habilidade", "ic95_inf", "ic95_sup"]
    ].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
