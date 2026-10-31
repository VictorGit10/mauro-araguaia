"""Teste de ponta a ponta da troca de previsões: 1 modelo e 3 modelos.

Roda `05_correcoes.py` em dois CSVs de exemplo, gravando em diretórios
separados (não mexe nas saídas principais):
  1. um modelo, sem coluna `modelo`;
  2. três modelos nas mesmas datas (um deles com poucas linhas de treino).

Uso: python codigo/test_multimodelo.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from comum import DADOS

RAIZ = Path(__file__).resolve().parents[1]
BASE = DADOS / "teste_multimodelo"


def rodar(csv: Path, saida: Path) -> str:
    if saida.exists():
        for f in saida.glob("*"):
            f.unlink()
    cmd = [sys.executable, str(RAIZ / "codigo" / "05_correcoes.py"),
           "--previsao", str(csv), "--saida", str(saida)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise AssertionError(f"05_correcoes.py falhou para {csv.name}:\n{r.stdout}\n{r.stderr}")
    if not (saida / "previsoes_corrigidas.csv").exists():
        raise AssertionError(f"sem previsoes_corrigidas.csv para {csv.name}")
    return r.stdout


def main() -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    fonte = pd.read_csv(DADOS / "previsao_referencia.csv",
                        parse_dates=["data_emissao", "data_alvo"])
    cc = fonte[fonte["modelo"] == "cota_cota"][["data_emissao", "data_alvo", "previsao"]].copy()
    sm = fonte[fonte["modelo"] == "sem_montante"][["data_emissao", "data_alvo", "previsao"]].copy()

    caso1 = BASE / "um_modelo.csv"
    cc.to_csv(caso1, index=False)

    caso3 = BASE / "tres_modelos.csv"
    tres = pd.concat([
        cc.assign(modelo="modelo_unico_cota_cota"),
        sm.assign(modelo="modelo_sem_montante"),
        cc.assign(modelo="modelo_perturbado", previsao=cc["previsao"] + 0.05),
    ], ignore_index=True)
    tres.to_csv(caso3, index=False)

    print("Caso 1: um modelo, sem coluna 'modelo'")
    out1 = rodar(caso1, BASE / "saida_um")
    c1 = pd.read_csv(BASE / "saida_um" / "previsoes_corrigidas.csv")
    modelos1 = sorted(c1["modelo"].unique())
    assert modelos1 == ["informado"], f"esperava um modelo 'informado', veio {modelos1}"
    assert c1["previsao_original"].notna().any(), "sem previsões no caso 1"
    print(f"  ok: {len(c1)} linhas, modelo {modelos1[0]}")

    print("Caso 2: três modelos nas mesmas datas")
    out2 = rodar(caso3, BASE / "saida_tres")
    c3 = pd.read_csv(BASE / "saida_tres" / "previsoes_corrigidas.csv")
    modelos3 = sorted(c3["modelo"].unique())
    assert modelos3 == ["modelo_perturbado", "modelo_sem_montante", "modelo_unico_cota_cota"], modelos3
    for mod in modelos3:
        g = c3[c3["modelo"] == mod]
        assert g["previsao_original"].notna().any(), f"modelo {mod} sem previsões"
        assert g["persistencia"].notna().any(), f"modelo {mod} sem persistência"
        assert g["kalman"].notna().any(), f"modelo {mod} sem Kalman"
    # o modelo com poucas linhas de treino não deve ter Random Forest
    pequeno = c3[c3["modelo"] == "modelo_sem_montante"]
    assert pequeno["rf"].isna().all(), "modelo com treino curto não deveria ter RF"
    assert "treino insuficiente" in out2, "faltou o aviso de treino insuficiente"
    print(f"  ok: {len(c3)} linhas, modelos {modelos3}")
    print("  ok: modelo com treino curto ficou só com persistência e Kalman")

    cfg = json.loads((BASE / "saida_tres" / "config_correcoes.json").read_text(encoding="utf-8"))
    assert len(cfg["modelos"]) == 3, "configuração deveria listar 3 modelos"
    print("  ok: config_correcoes.json lista os 3 modelos")

    print("\nTodos os testes de troca de previsão passaram.")


if __name__ == "__main__":
    main()
