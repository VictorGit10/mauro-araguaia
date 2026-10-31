"""Funções comuns: acesso ao webservice antigo da ANA, agregação diária e utilidades.

Fonte dos dados: webservice SOAP público da ANA (telemetria), sem cadastro:
    http://telemetriaws1.ana.gov.br/ServiceANA.asmx
Método usado: DadosHidrometeorologicos (nível de sensor, chuva, vazão a cada 15 min).
"""

from __future__ import annotations

import io
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from lxml import etree

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"
BRUTO = DADOS / "bruto"
FIGURAS = RAIZ / "figuras"

URL_ANA = "http://telemetriaws1.ana.gov.br/ServiceANA.asmx"

# Estações escolhidas (ver RELATORIO.md para a justificativa).
ESTACOES = {
    "alvo": {
        "codigo": "26350000",
        "nome": "SÃO FÉLIX DO ARAGUAIA",
        "rio": "Rio Araguaia",
        "municipio": "São Félix do Araguaia-MT",
        "lat": -11.6181,
        "lon": -50.6625,
        "papel": "estação alvo (jusante)",
    },
    "montante": {
        "codigo": "25700000",
        "nome": "BANDEIRANTES",
        "rio": "Rio Araguaia",
        "municipio": "Nova Crixás-GO",
        "lat": -13.6425,
        "lon": -50.7839,
        "papel": "estação a montante",
    },
}

ANO_INI = 2014
ANO_FIM = 2025


def chamar_ana(metodo: str, timeout: int = 300, **params) -> bytes:
    """Chama um método do webservice SOAP da ANA e devolve o XML bruto."""
    corpo = "".join(f"<{k}>{v}</{k}>" for k, v in params.items())
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap12:Envelope xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">'
        f'<soap12:Body><{metodo} xmlns="http://MRCS/">{corpo}</{metodo}></soap12:Body>'
        "</soap12:Envelope>"
    )
    r = requests.post(
        URL_ANA,
        data=envelope.encode("utf-8"),
        headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        timeout=timeout,
    )
    r.raise_for_status()
    return r.content


def xml_para_linhas(xml: bytes, tag: str = "DadosHidrometereologicos") -> list[dict]:
    """Converte o XML do serviço em uma lista de dicionários (uma linha por registro)."""
    raiz = etree.fromstring(xml)
    return [{filho.tag: filho.text for filho in el} for el in raiz.iter(tag)]


def baixar_serie_bruta(codigo: str, ano: int, forcar: bool = False) -> Path:
    """Baixa um ano de dados de 15 min de uma estação e guarda em CSV comprimido."""
    BRUTO.mkdir(parents=True, exist_ok=True)
    destino = BRUTO / f"{codigo}_{ano}.csv.gz"
    if destino.exists() and not forcar:
        return destino

    xml = chamar_ana(
        "DadosHidrometeorologicos",
        codEstacao=codigo,
        dataInicio=f"01/01/{ano}",
        dataFim=f"31/12/{ano}",
    )
    linhas = xml_para_linhas(xml)
    if not linhas:
        df = pd.DataFrame(columns=["CodEstacao", "DataHora", "Nivel", "Chuva", "Vazao"])
    else:
        df = pd.DataFrame(linhas)
        for col in ["Nivel", "Chuva", "Vazao"]:
            if col not in df:
                df[col] = None
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["DataHora"] = pd.to_datetime(df["DataHora"].str.strip(), errors="coerce")
    df.to_csv(destino, index=False, compression="gzip")
    time.sleep(0.3)
    return destino


def agregar_diario(codigo: str, anos: range | None = None) -> pd.DataFrame:
    """Lê os arquivos brutos e devolve série diária (média do nível, soma da chuva)."""
    anos = anos or range(ANO_INI, ANO_FIM + 1)
    partes = []
    for ano in anos:
        arq = BRUTO / f"{codigo}_{ano}.csv.gz"
        if not arq.exists():
            continue
        d = pd.read_csv(arq, parse_dates=["DataHora"])
        partes.append(d)
    if not partes:
        raise FileNotFoundError(f"sem dados brutos para {codigo}; rode 01_baixar_dados.py")
    df = pd.concat(partes, ignore_index=True)
    df["data"] = df["DataHora"].dt.normalize()

    # Nível: média dos registros válidos do dia. A leitura de 15 min é ruidosa,
    # a média diária é a mesma agregação usada nas séries diárias da ANA.
    nivel = df.groupby("data")["Nivel"].agg(
        nivel_medio="mean", nivel_min="min", nivel_max="max", n_leituras="count"
    )
    # Chuva: soma dos acumulados de 15 min (mm). Só soma onde há registro.
    chuva = df.groupby("data")["Chuva"].agg(chuva_mm="sum", n_chuva="count")
    out = nivel.join(chuva)
    out["codigo"] = codigo
    out = out.reset_index()
    # nível em cm -> m
    for c in ["nivel_medio", "nivel_min", "nivel_max"]:
        out[c] = out[c] / 100.0
    return out


def serie_diaria_completa(codigo: str) -> pd.DataFrame:
    """Série diária com calendário completo e interpolação curta de falhas.

    Regras (documentadas no README):
      - dia com menos de 20 leituras válidas (de ~96) é tratado como falha;
      - falhas de até 3 dias são interpoladas linearmente;
      - falhas maiores ficam como NaN (não inventamos dado).
    """
    d = agregar_diario(codigo)
    idx = pd.date_range(f"{ANO_INI}-01-01", f"{ANO_FIM}-12-31", freq="D")
    d = d.set_index("data").reindex(idx)
    d.index.name = "data"
    d["codigo"] = codigo

    d.loc[d["n_leituras"] < 20, ["nivel_medio", "nivel_min", "nivel_max"]] = np.nan
    # limites físicos plausíveis para o Araguaia (evita picos de sensor)
    d.loc[(d["nivel_medio"] < 0) | (d["nivel_medio"] > 20), "nivel_medio"] = np.nan

    d["nivel"] = d["nivel_medio"].interpolate(method="linear", limit=3, limit_area="inside")
    d["interpolado"] = d["nivel"].notna() & d["nivel_medio"].isna()

    # chuva diária: dias sem nenhum registro ficam NaN
    d.loc[d["n_chuva"] == 0, "chuva_mm"] = np.nan
    d["chuva_mm"] = d["chuva_mm"].clip(lower=0, upper=300)
    return d[["codigo", "nivel", "nivel_medio", "chuva_mm", "n_leituras", "n_chuva", "interpolado"]]


def carregar_series() -> pd.DataFrame:
    """DataFrame com colunas: data, nivel_alvo, chuva_alvo, nivel_montante, chuva_montante."""
    a = serie_diaria_completa(ESTACOES["alvo"]["codigo"])
    m = serie_diaria_completa(ESTACOES["montante"]["codigo"])
    df = pd.DataFrame(index=a.index)
    df["nivel_alvo"] = a["nivel"]
    df["chuva_alvo"] = a["chuva_mm"]
    df["nivel_montante"] = m["nivel"]
    df["chuva_montante"] = m["chuva_mm"]
    df.index.name = "data"
    return df
