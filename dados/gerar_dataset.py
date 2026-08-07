# -*- coding: utf-8 -*-
"""
Gerador do dataset sintético do caso Coroa Premium (Exhibit 2).

Produz dados/Coroa_Premium_PDV_Performance.csv com 3.847 linhas x 18 colunas,
calibrado para os números citados no corpo do case DSDM-AMBEV-MOD2-001:

- Queda agregada do programa (Q4/2025 vs Q4/2024): -18,7%
- Deltas regionais agregados: Sudeste -23,1% / Sul -14,4% / Centro-Oeste -19,8% /
  Nordeste +3,2%; Sudeste com 58% do volume do programa
- 41% dos PDVs com delta abaixo de -15%
- Tier A com 28% dos PDVs e 64% do volume
- 73% dos PDVs com ao menos uma marca premium concorrente ativada
- Gasto de POSM do trimestre somando ~R$ 5,14 milhões

Padrões plantados (as duas hipóteses não testadas de Daniel Yamada):

- H1: a queda é concentrada nos PDVs com 3+ concorrentes premium ativados;
  PDVs com 0-1 concorrente caem pouco. O Nordeste tem menos concorrentes,
  por isso é a única região positiva.
- H2: em PDVs de tier C, a frequência de visita do promotor NÃO se converte em
  resposta de volume (correlação negativa); em tier A a correlação é positiva.

Uso: .venv/bin/python dados/gerar_dataset.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

SEED = 20260804
N_PDVS = 3847

# Alvos citados no case
ALVO_DELTA_NACIONAL = -18.7
ALVO_DELTA_REGIAO = {"Sudeste": -23.1, "Sul": -14.4, "Centro-Oeste": -19.8, "Nordeste": 3.2}
ALVO_SHARE_VOLUME_SE = 0.58
ALVO_SHARE_VOLUME_TIER_A = 0.64

REGIOES = ["Sudeste", "Sul", "Centro-Oeste", "Nordeste"]
N_POR_REGIAO = {"Sudeste": 2000, "Sul": 850, "Centro-Oeste": 540, "Nordeste": 457}

UFS = {
    "Sudeste": (["SP", "RJ", "MG", "ES"], [0.52, 0.24, 0.18, 0.06]),
    "Sul": (["RS", "SC", "PR"], [0.38, 0.27, 0.35]),
    "Centro-Oeste": (["DF", "GO", "MT", "MS"], [0.38, 0.32, 0.16, 0.14]),
    "Nordeste": (["PE", "BA", "CE", "RN"], [0.34, 0.34, 0.22, 0.10]),
}

MUNICIPIOS = {
    "SP": ["São Paulo", "Campinas", "Santos", "Ribeirão Preto", "São José dos Campos"],
    "RJ": ["Rio de Janeiro", "Niterói", "Petrópolis"],
    "MG": ["Belo Horizonte", "Uberlândia", "Juiz de Fora"],
    "ES": ["Vitória", "Vila Velha"],
    "RS": ["Porto Alegre", "Caxias do Sul", "Pelotas"],
    "SC": ["Florianópolis", "Joinville", "Balneário Camboriú"],
    "PR": ["Curitiba", "Londrina", "Maringá"],
    "DF": ["Brasília"],
    "GO": ["Goiânia", "Anápolis"],
    "MT": ["Cuiabá"],
    "MS": ["Campo Grande"],
    "PE": ["Recife", "Olinda", "Caruaru"],
    "BA": ["Salvador", "Feira de Santana"],
    "CE": ["Fortaleza", "Juazeiro do Norte"],
    "RN": ["Natal"],
}

TIPOS = ["bar premium", "gastrobar", "restaurante", "pub", "choperia", "rooftop"]
P_TIPOS = [0.34, 0.20, 0.18, 0.14, 0.08, 0.06]

# Distribuição de concorrentes por região (0 a 5), antes do ajuste por tier.
# Nordeste deliberadamente com menos concorrentes (sustenta o +3,2% regional).
P_CONCORRENTES = {
    "Sudeste": [0.21, 0.27, 0.17, 0.16, 0.12, 0.07],
    "Sul": [0.30, 0.28, 0.15, 0.14, 0.09, 0.04],
    "Centro-Oeste": [0.32, 0.28, 0.14, 0.14, 0.08, 0.04],
    "Nordeste": [0.62, 0.21, 0.08, 0.05, 0.03, 0.01],
}

# H1: delta base (%) por contagem de concorrentes no PDV
DELTA_POR_CONCORRENTE = {0: -2.5, 1: -6.0, 2: -14.0, 3: -33.0, 4: -40.0, 5: -46.0}
SD_DELTA = {0: 6.0, 1: 6.5, 2: 7.0, 3: 8.0, 4: 8.0, 5: 8.0}
# Concorrência morde mais os bares de maior tráfego (tier A): é o que deixa o
# agregado (ponderado por volume) mais fundo que a mediana dos PDVs
AJUSTE_TIER = {"A": -3.0, "B": 0.0, "C": 1.0}

POSM_CODIGOS = ["FRZ", "LUM", "MES", "CHP", "BAL", "KVI"]


def gerar():
    rng = np.random.default_rng(SEED)

    linhas = []
    for regiao in REGIOES:
        n = N_POR_REGIAO[regiao]
        ufs, p_ufs = UFS[regiao]
        for _ in range(n):
            uf = rng.choice(ufs, p=p_ufs)
            linhas.append({"regiao": regiao, "uf": uf, "municipio": rng.choice(MUNICIPIOS[uf])})

    df = pd.DataFrame(linhas)
    n = len(df)
    assert n == N_PDVS

    df["tipo_estabelecimento"] = rng.choice(TIPOS, size=n, p=P_TIPOS)

    # Tiers históricos: A 1.077 (28%), B 1.320, C 1.450 (os ~1.450 "de
    # não-resposta" que o Caminho A propõe zerar)
    tiers = np.array(["A"] * 1077 + ["B"] * 1320 + ["C"] * 1450)
    rng.shuffle(tiers)
    df["tier_historico"] = tiers

    # Concorrentes: base regional + pressão extra em tier A (concorrência entra
    # nos bares de maior tráfego)
    conc = np.empty(n, dtype=int)
    for regiao in REGIOES:
        mask = (df["regiao"] == regiao).to_numpy()
        conc[mask] = rng.choice(6, size=mask.sum(), p=P_CONCORRENTES[regiao])
    extra_a = (df["tier_historico"] == "A").to_numpy() & (rng.random(n) < 0.35)
    conc = np.clip(conc + extra_a.astype(int), 0, 5)
    df["concorrentes_premium_no_pdv"] = conc

    # Volume Q4/2024 por tier (lognormal), depois calibrado
    base_tier = {"A": 95.0, "B": 34.0, "C": 12.0}
    sigma_tier = {"A": 0.42, "B": 0.40, "C": 0.45}
    vol24 = np.empty(n)
    for t in "ABC":
        mask = (df["tier_historico"] == t).to_numpy()
        vol24[mask] = base_tier[t] * rng.lognormal(0.0, sigma_tier[t], mask.sum())
    vol24 = np.clip(vol24, 2.5, None)

    # Evento ativacional e meses no programa
    df["evento_ativacional_2025"] = np.where(
        df["tier_historico"] == "A", rng.random(n) < 0.50, rng.random(n) < 0.30
    ).astype(int)
    fundador = rng.random(n) < 0.70
    df["meses_no_programa"] = np.where(fundador, 47, rng.integers(6, 47, size=n))

    # H1: delta por concorrentes + ajuste de tier + evento
    delta = np.array([
        rng.normal(DELTA_POR_CONCORRENTE[c], SD_DELTA[c]) for c in conc
    ])
    delta += np.array([AJUSTE_TIER[t] for t in df["tier_historico"]])
    delta += df["evento_ativacional_2025"].to_numpy() * 2.0
    delta = np.clip(delta, -75.0, 40.0)

    # Calibração 1: share de volume do tier A (64%) e das regiões (SE 58%,
    # demais resolvidos para fechar o -18,7% nacional dado os deltas regionais)
    w_co = 0.13
    d = ALVO_DELTA_REGIAO
    # resolve w_ne em: 0.58*dSE + wS*dS + wCO*dCO + wNE*dNE = -18.7, wS = 0.42 - wCO - wNE
    w_ne = (
        (ALVO_DELTA_NACIONAL - ALVO_SHARE_VOLUME_SE * d["Sudeste"]
         - (0.42 - w_co) * d["Sul"] - w_co * d["Centro-Oeste"])
        / (d["Nordeste"] - d["Sul"])
    )
    w_sul = 0.42 - w_co - w_ne
    share_regiao = {"Sudeste": 0.58, "Sul": w_sul, "Centro-Oeste": w_co, "Nordeste": w_ne}

    for _ in range(8):
        mask_a = (df["tier_historico"] == "A").to_numpy()
        share_a = vol24[mask_a].sum() / vol24.sum()
        vol24[mask_a] *= (ALVO_SHARE_VOLUME_TIER_A / share_a) * ((1 - share_a) / (1 - ALVO_SHARE_VOLUME_TIER_A))
        total = vol24.sum()
        for regiao in REGIOES:
            mask = (df["regiao"] == regiao).to_numpy()
            fator = share_regiao[regiao] * total / vol24[mask].sum()
            vol24[mask] *= fator

    # Volume Q4/2025 a partir do delta; calibração 2: força os agregados regionais
    vol25 = vol24 * (1 + delta / 100)
    for regiao in REGIOES:
        mask = (df["regiao"] == regiao).to_numpy()
        alvo = 1 + ALVO_DELTA_REGIAO[regiao] / 100
        atual = vol25[mask].sum() / vol24[mask].sum()
        vol25[mask] *= alvo / atual

    vol25 = np.clip(vol25, 1.0, None)

    df["volume_q4_2024_hl"] = np.round(vol24, 1)
    df["volume_q4_2025_hl"] = np.round(vol25, 1)
    df["delta_volume_yoy_pct"] = np.round(
        (df["volume_q4_2025_hl"] / df["volume_q4_2024_hl"] - 1) * 100, 1
    )

    delta_final = df["delta_volume_yoy_pct"].to_numpy()

    # Share da marca foco (Ardor Lager) por tier
    share_base = {"A": 29.0, "B": 22.0, "C": 15.0}
    share = np.array([rng.normal(share_base[t], 6.0) for t in df["tier_historico"]])
    df["share_ardor_pct"] = np.round(np.clip(share, 3.0, 55.0), 1)

    # Gasto POSM do trimestre (soma ~R$ 5,14 mi)
    gasto_base = {"A": 2400.0, "B": 1230.0, "C": 690.0}
    gasto = np.array([rng.normal(gasto_base[t], gasto_base[t] * 0.12) for t in df["tier_historico"]])
    df["gasto_posm_trim_brl"] = np.round(np.clip(gasto, 250, None), 0)

    # H2: visitas do promotor. Tier A: mais visitas onde o delta é melhor
    # (resposta real). Tier C: visitas concentradas nos PDVs que mais caem
    # (rota engessada, visita sem conversão) -> correlação negativa.
    visitas = np.empty(n)
    for t, base, acopl in (("A", 6.0, +0.65), ("B", 4.0, +0.30), ("C", 3.2, -0.60)):
        mask = (df["tier_historico"] == t).to_numpy()
        z = (delta_final[mask] - delta_final[mask].mean()) / max(delta_final[mask].std(), 1e-9)
        visitas[mask] = base + acopl * z + rng.normal(0, 0.9, mask.sum())
    df["visitas_promotor_mes"] = np.clip(np.round(visitas), 1, 10).astype(int)

    # POSM instalado: tier A com kit mais completo
    n_itens = {"A": (3, 6), "B": (2, 4), "C": (1, 3)}
    codigos = []
    for t in df["tier_historico"]:
        lo, hi = n_itens[t]
        k = int(rng.integers(lo, hi + 1))
        itens = rng.choice(POSM_CODIGOS, size=k, replace=False)
        codigos.append("|".join(sorted(itens)))
    df["posm_instalado_cod"] = codigos

    # NPS do dono do PDV (queda média ~11 pontos, pior onde há mais concorrente)
    nps24 = np.clip(rng.normal(62, 12, n), 5, 98)
    queda = rng.normal(8.0, 7.0, n) + np.where(conc >= 3, 6.0, 0.0) + np.where(conc == 2, 3.0, 0.0)
    nps25 = np.clip(nps24 - queda, -40, 98)
    df["nps_dono_q4_2024"] = np.round(nps24).astype(int)
    df["nps_dono_q4_2025"] = np.round(nps25).astype(int)

    df["pdv_id"] = [f"PDV-{i:05d}" for i in range(1, n + 1)]

    colunas = [
        "pdv_id", "regiao", "uf", "municipio", "tipo_estabelecimento",
        "tier_historico", "volume_q4_2024_hl", "volume_q4_2025_hl",
        "delta_volume_yoy_pct", "share_ardor_pct", "gasto_posm_trim_brl",
        "visitas_promotor_mes", "posm_instalado_cod", "nps_dono_q4_2024",
        "nps_dono_q4_2025", "meses_no_programa", "concorrentes_premium_no_pdv",
        "evento_ativacional_2025",
    ]
    df = df[colunas]

    # Embaralha as linhas para não entregar o dataset ordenado por região
    df = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)
    return df


def main():
    df = gerar()
    destino = Path(__file__).parent / "Coroa_Premium_PDV_Performance.csv"
    df.to_csv(destino, index=False)

    v24, v25 = df["volume_q4_2024_hl"].sum(), df["volume_q4_2025_hl"].sum()
    print(f"Linhas: {len(df)}  Colunas: {len(df.columns)}")
    print(f"Delta nacional agregado: {(v25 / v24 - 1) * 100:+.1f}%")
    for regiao, grupo in df.groupby("regiao"):
        d = (grupo["volume_q4_2025_hl"].sum() / grupo["volume_q4_2024_hl"].sum() - 1) * 100
        print(f"  {regiao}: {d:+.1f}%  (share vol 2024: {grupo['volume_q4_2024_hl'].sum() / v24:.1%})")
    print(f"PDVs com delta < -15%: {(df['delta_volume_yoy_pct'] < -15).mean():.1%}")
    a = df[df["tier_historico"] == "A"]
    print(f"Tier A: {len(a) / len(df):.1%} dos PDVs, {a['volume_q4_2024_hl'].sum() / v24:.1%} do volume")
    print(f"PDVs com concorrente: {(df['concorrentes_premium_no_pdv'] >= 1).mean():.1%}")
    print(f"Gasto POSM total: R$ {df['gasto_posm_trim_brl'].sum():,.0f}")
    print(f"Delta médio por PDV: {df['delta_volume_yoy_pct'].mean():+.1f}%")
    for t in "ABC":
        sub = df[df["tier_historico"] == t]
        c = np.corrcoef(sub["visitas_promotor_mes"], sub["delta_volume_yoy_pct"])[0, 1]
        print(f"Correlação visitas x delta (tier {t}): {c:+.2f}")
    tab = df.groupby(pd.cut(df["concorrentes_premium_no_pdv"], [-1, 1, 2, 5],
                            labels=["0-1", "2", "3+"]), observed=True)["delta_volume_yoy_pct"].mean()
    print("Delta médio por faixa de concorrentes:")
    print(tab.to_string())
    print(f"Gravado em: {destino}")


if __name__ == "__main__":
    main()
