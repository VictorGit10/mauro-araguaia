"""Teste automatizado contra vazamento de futuro.

Roda com:  python codigo/test_vazamento.py   (ou pytest codigo/test_vazamento.py)

Ideia central: em vez de auditar linha por linha, perturbamos todo o futuro
(tudo depois de t vira um valor absurdo) e exigimos que as variáveis de entrada
da emissão t fiquem idênticas. Se qualquer variável mudar, ela usou informação
posterior a t e o teste falha.

O teste do erro proposital garante que a perturbação tem poder de detectar
vazamento. O teste dos erros confere, contra a definição, que e7/e14/e21/e28
usam o alvo certo (emissão t-k verificada em t-k+7).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from comum import DADOS
from features import montar_features

SERIES = pd.read_csv(DADOS / "series_diarias.csv", index_col="data", parse_dates=True)
PREV_TODAS = pd.read_csv(DADOS / "previsao_referencia.csv",
                         parse_dates=["data_emissao", "data_alvo"])
TABELA = pd.read_csv(DADOS / "tabela_erros.csv", parse_dates=["data_emissao", "data_alvo"])

MODELO = "cota_cota" if (PREV_TODAS["modelo"] == "cota_cota").any() else PREV_TODAS["modelo"].iloc[0]
PREV = PREV_TODAS[PREV_TODAS["modelo"] == MODELO].drop(columns=["modelo"]).reset_index(drop=True)
DATAS = pd.DatetimeIndex(SERIES.loc["2022-01-01":"2025-11-30"].index[::11])
TOL = 1e-9


def _perturbar(series: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    """Devolve a série com TODO o futuro depois de t trocado por valores absurdos."""
    s = series.copy()
    futuro = s.index > t
    for c in ("nivel_alvo", "nivel_montante"):
        s.loc[futuro, c] = s.loc[futuro, c] + 999.0
    s.loc[futuro, "chuva_bacia_mm"] = 999.0
    s.loc[futuro, "chuva_alvo"] = 999.0
    s.loc[futuro, "chuva_montante"] = 999.0
    return s


def _perturbar_previsoes(prev: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    p = prev.copy()
    p.loc[p["data_emissao"] > t, "previsao"] = -999.0
    return p


def _linha(series: pd.DataFrame, prev: pd.DataFrame, t: pd.Timestamp) -> dict:
    return montar_features(series, prev, pd.DatetimeIndex([t])).iloc[0].to_dict()


def _compara_linhas(a: dict, b: dict) -> list[str]:
    problemas = []
    for k in a:
        if k in ("data_emissao", "data_alvo"):
            continue
        va, vb = a[k], b[k]
        if pd.isna(va) and pd.isna(vb):
            continue
        if pd.isna(va) != pd.isna(vb) or abs(float(va) - float(vb)) > TOL:
            problemas.append(k)
    return problemas


def test_futuro_perturbado_nao_muda_features() -> None:
    """Perturbar tudo depois de t não pode mudar nenhuma variável da emissão t."""
    falhas = {}
    for t in DATAS:
        base = _linha(SERIES, PREV, t)
        pert = _linha(_perturbar(SERIES, t), _perturbar_previsoes(PREV, t), t)
        dif = _compara_linhas(base, pert)
        if dif:
            falhas[str(t.date())] = dif
    assert not falhas, f"vazamento de futuro nas variáveis: {falhas}"
    print(f"  ok: {len(DATAS)} datas testadas; nenhuma variável mudou ao perturbar o futuro")


def test_tabela_salva_confere_com_recalculo() -> None:
    """A tabela usada na modelagem tem de bater com o recálculo a partir da série."""
    falhas = {}
    for t in DATAS:
        linha = _linha(SERIES, PREV, t)
        salva = TABELA.loc[(TABELA["data_emissao"] == t) & (TABELA["modelo"] == MODELO)]
        if salva.empty:
            continue
        salva = salva.iloc[0].to_dict()
        dif = _compara_linhas(linha, salva)
        if dif:
            falhas[str(t.date())] = dif
    assert not falhas, f"tabela_erros.csv divergente em: {falhas}"
    print("  ok: tabela_erros.csv reproduz as features recalculadas")


def test_erro_mais_recente_e_do_t_menos_7() -> None:
    """A regra-chave: em t, o erro mais novo é o da previsão emitida em t-7."""
    for t in DATAS:
        if (t - pd.Timedelta(days=7)) not in set(PREV["data_emissao"]):
            continue
        linha = _linha(SERIES, PREV, t)
        if pd.isna(linha["e7"]):
            continue
        f_anterior = float(PREV.loc[PREV["data_emissao"] == t - pd.Timedelta(days=7), "previsao"].iloc[0])
        esperado = float(SERIES.loc[t, "nivel_alvo"] - f_anterior)
        assert abs(linha["e7"] - esperado) < TOL, f"e7 errado em {t.date()}"
    print("  ok: e7 = observado(t) - previsão emitida em t-7")


def test_erros_verificados_na_data_certa() -> None:
    """e_k = observado(t-k+7) - previsão emitida em t-k, para k = 7, 14, 21, 28.

    Três datas escolhidas à mão, incluindo uma em cheia e uma com falha de dado.
    """
    datas = [pd.Timestamp("2025-01-28"), pd.Timestamp("2024-11-20"),
             pd.Timestamp("2022-06-15")]
    mapa = dict(zip(PREV["data_emissao"], PREV["previsao"]))
    for t in datas:
        linha = _linha(SERIES, PREV, t)
        for k in (7, 14, 21, 28):
            emissao = t - pd.Timedelta(days=k)
            alvo = t - pd.Timedelta(days=k - 7)
            if emissao not in mapa or alvo not in SERIES.index:
                continue
            esperado = float(SERIES.loc[alvo, "nivel_alvo"] - mapa[emissao])
            if pd.isna(linha[f"e{k}"]) and pd.isna(esperado):
                continue
            assert abs(linha[f"e{k}"] - esperado) < TOL, (
                f"e{k} errado em {t.date()}: {linha[f'e{k}']} != {esperado} "
                f"(emissão {emissao.date()}, alvo {alvo.date()})")
    print("  ok: e7, e14, e21 e e28 conferem com a definição em 3 datas")


def test_previsao_nao_muda_com_futuro() -> None:
    """O valor previsto para t+7 não pode depender de nada depois de t."""
    from json import load
    with open(DADOS / "modelo_referencia.json", encoding="utf-8") as f:
        m = load(f)
    for t in DATAS:
        p0 = PREV[PREV["data_emissao"] == t]
        if p0.empty:
            continue
        f0 = float(p0["previsao"].iloc[0])
        linha = _linha(_perturbar(SERIES, t), _perturbar_previsoes(PREV, t), t)
        if not np.isfinite(linha["u0"]):
            coef, feats, b0 = m["coeficientes_reserva"], m["features_reserva"], m["intercepto_reserva"]
        else:
            coef, feats, b0 = m["coeficientes"], m["features"], m["intercepto"]
        f1 = b0 + sum(coef[k] * linha[k] for k in feats)
        assert abs(f0 - f1) < 5e-3, f"previsão de {t.date()} mudou com o futuro (dif={f0-f1:.6f})"
    print("  ok: previsão de 7 dias reproduzida sem olhar o futuro")


def test_leak_proposital_e_pego() -> None:
    """Caso errado de propósito: uma variável que usa o observado em t+7."""
    def com_vazamento(series: pd.DataFrame, prev: pd.DataFrame, t: pd.Timestamp) -> dict:
        linha = _linha(series, prev, t)
        alvo = t + pd.Timedelta(days=7)
        linha["obs_futuro"] = float(series.loc[alvo, "nivel_alvo"]) if alvo in series.index else np.nan
        return linha

    acusou, colunas = False, []
    for t in DATAS[:10]:
        base = com_vazamento(SERIES, PREV, t)
        pert = com_vazamento(_perturbar(SERIES, t), _perturbar_previsoes(PREV, t), t)
        colunas = _compara_linhas(base, pert)
        if colunas:
            acusou = True
            break
    assert acusou, "o teste NÃO pegou o vazamento proposital: o teste não serve"
    print(f"  ok: vazamento proposital detectado na variável {colunas}")


if __name__ == "__main__":
    testes = [
        test_futuro_perturbado_nao_muda_features,
        test_tabela_salva_confere_com_recalculo,
        test_erro_mais_recente_e_do_t_menos_7,
        test_erros_verificados_na_data_certa,
        test_previsao_nao_muda_com_futuro,
        test_leak_proposital_e_pego,
    ]
    print("Testes de vazamento de futuro")
    for teste in testes:
        print(f"- {teste.__name__}")
        teste()
    print("\nTodos os testes passaram.")
