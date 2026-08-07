# -*- coding: utf-8 -*-
"""
Testes de consistência do dataset sintético do caso Coroa Premium.

Validam que o CSV gerado sustenta os números citados no corpo do case
(DSDM-AMBEV-MOD2-001) e que os dois padrões plantados (H1 e H2) existem e
são detectáveis pelos cruzamentos que a aula pede.

Rodar: .venv/bin/python -m pytest dados/tests/ -v
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

CSV = Path(__file__).parent.parent / "Coroa_Premium_PDV_Performance.csv"

COLUNAS = [
    "pdv_id", "regiao", "uf", "municipio", "tipo_estabelecimento",
    "tier_historico", "volume_q4_2024_hl", "volume_q4_2025_hl",
    "delta_volume_yoy_pct", "share_ardor_pct", "gasto_posm_trim_brl",
    "visitas_promotor_mes", "posm_instalado_cod", "nps_dono_q4_2024",
    "nps_dono_q4_2025", "meses_no_programa", "concorrentes_premium_no_pdv",
    "evento_ativacional_2025",
]


@pytest.fixture(scope="module")
def df():
    frame = pd.read_csv(CSV)
    # Regra "nada medido nunca lê como sucesso": qualquer teste abaixo só faz
    # sentido se o arquivo de fato tem linhas
    assert len(frame) > 0, "CSV vazio: nada foi medido"
    return frame


# ---------- Estrutura ----------

def test_dimensoes(df):
    assert len(df) == 3847
    assert list(df.columns) == COLUNAS


def test_sem_nulos_e_ids_unicos(df):
    assert not df.isna().any().any()
    assert df["pdv_id"].is_unique


def test_dominios_basicos(df):
    assert set(df["regiao"]) == {"Sudeste", "Sul", "Centro-Oeste", "Nordeste"}
    assert set(df["tier_historico"]) == {"A", "B", "C"}
    assert df["volume_q4_2024_hl"].min() > 0
    assert df["volume_q4_2025_hl"].min() > 0
    assert df["visitas_promotor_mes"].between(1, 10).all()
    assert df["meses_no_programa"].between(1, 47).all()
    assert df["concorrentes_premium_no_pdv"].between(0, 5).all()
    assert df["evento_ativacional_2025"].isin([0, 1]).all()


def test_delta_consistente_com_volumes(df):
    recalculado = (df["volume_q4_2025_hl"] / df["volume_q4_2024_hl"] - 1) * 100
    assert (df["delta_volume_yoy_pct"] - recalculado).abs().max() < 0.1


# ---------- Números citados no case ----------

def delta_agregado(frame):
    return (frame["volume_q4_2025_hl"].sum() / frame["volume_q4_2024_hl"].sum() - 1) * 100


def test_queda_nacional_18_7(df):
    assert delta_agregado(df) == pytest.approx(-18.7, abs=0.2)


@pytest.mark.parametrize("regiao,alvo", [
    ("Sudeste", -23.1), ("Sul", -14.4), ("Centro-Oeste", -19.8), ("Nordeste", 3.2),
])
def test_deltas_regionais(df, regiao, alvo):
    sub = df[df["regiao"] == regiao]
    assert len(sub) > 0, f"nenhum PDV na região {regiao}"
    assert delta_agregado(sub) == pytest.approx(alvo, abs=0.3)


def test_sudeste_58_pct_do_volume(df):
    share = (df.loc[df["regiao"] == "Sudeste", "volume_q4_2024_hl"].sum()
             / df["volume_q4_2024_hl"].sum())
    assert share == pytest.approx(0.58, abs=0.01)


def test_41_pct_dos_pdvs_abaixo_de_menos_15(df):
    frac = (df["delta_volume_yoy_pct"] < -15).mean()
    assert 0.39 <= frac <= 0.43


def test_tier_a_28_pct_dos_pdvs_e_64_pct_do_volume(df):
    a = df[df["tier_historico"] == "A"]
    assert len(a) / len(df) == pytest.approx(0.28, abs=0.005)
    share_vol = a["volume_q4_2024_hl"].sum() / df["volume_q4_2024_hl"].sum()
    assert share_vol == pytest.approx(0.64, abs=0.015)


def test_73_pct_com_concorrente(df):
    frac = (df["concorrentes_premium_no_pdv"] >= 1).mean()
    assert 0.71 <= frac <= 0.75


def test_gasto_posm_soma_5_14_mi(df):
    total = df["gasto_posm_trim_brl"].sum()
    assert 4_900_000 <= total <= 5_450_000


def test_nps_dono_cai_na_faixa_do_case(df):
    queda_media = (df["nps_dono_q4_2025"] - df["nps_dono_q4_2024"]).mean()
    assert -14 <= queda_media <= -8


# ---------- H1: queda concentrada por pressão competitiva ----------

def test_h1_cross_tab_delta_por_concorrentes(df):
    poucos = df[df["concorrentes_premium_no_pdv"] <= 1]["delta_volume_yoy_pct"].mean()
    muitos = df[df["concorrentes_premium_no_pdv"] >= 3]["delta_volume_yoy_pct"].mean()
    assert poucos > -8, "PDVs com 0-1 concorrente deveriam cair pouco"
    assert muitos < -30, "PDVs com 3+ concorrentes deveriam concentrar a queda"
    assert poucos - muitos > 25, "o contraste do cross-tab precisa ser inequívoco"


def test_h1_nordeste_tem_menos_concorrencia(df):
    ne = df[df["regiao"] == "Nordeste"]["concorrentes_premium_no_pdv"].mean()
    resto = df[df["regiao"] != "Nordeste"]["concorrentes_premium_no_pdv"].mean()
    assert ne < resto - 0.8


# ---------- H2: visita do promotor não converte em tier C ----------

def corr_visitas_delta(frame, tier):
    sub = frame[frame["tier_historico"] == tier]
    assert len(sub) > 100, f"amostra insuficiente no tier {tier}"
    return np.corrcoef(sub["visitas_promotor_mes"], sub["delta_volume_yoy_pct"])[0, 1]


def test_h2_tier_c_correlacao_negativa(df):
    assert -0.65 <= corr_visitas_delta(df, "C") <= -0.35


def test_h2_tier_a_correlacao_positiva(df):
    assert 0.35 <= corr_visitas_delta(df, "A") <= 0.70


# ---------- A armadilha didática da agregação ----------

def test_media_simples_diverge_da_ponderada(df):
    """O case cita -18,7% (queda do volume total). A média simples dos deltas
    por PDV é deliberadamente diferente: é a armadilha de "delta médio" que a
    aula usa para discutir ambiguidade de prompt. O teste protege a existência
    e o tamanho dessa divergência."""
    media_simples = df["delta_volume_yoy_pct"].mean()
    ponderada = delta_agregado(df)
    assert ponderada == pytest.approx(-18.7, abs=0.2)
    assert media_simples - ponderada > 2.0, "a divergência didática sumiu"


# ---------- O teste precisa conseguir falhar ----------

def test_validacao_reprova_dataset_corrompido(df):
    """Prova de que as checagens centrais não passam com dado quebrado
    (lição: teste que nunca falhou pode não testar nada)."""
    quebrado = df.copy()
    quebrado["volume_q4_2025_hl"] = quebrado["volume_q4_2024_hl"]  # delta zero
    assert delta_agregado(quebrado) != pytest.approx(-18.7, abs=0.2)
    poucos = quebrado[quebrado["concorrentes_premium_no_pdv"] <= 1]
    muitos = quebrado[quebrado["concorrentes_premium_no_pdv"] >= 3]
    contraste = (poucos["volume_q4_2025_hl"] / poucos["volume_q4_2024_hl"]).mean() - \
                (muitos["volume_q4_2025_hl"] / muitos["volume_q4_2024_hl"]).mean()
    assert abs(contraste) < 0.01, "sem delta não pode haver contraste H1"
