#!/usr/bin/env python3
"""
Valida a fidelidade ao Brandbook Inteli 2025.

Cinco regras, cada uma amarrada a uma pagina do brandbook:

1. cor-fora-da-paleta   p.66  hex declarado no brand que nao esta na paleta oficial
2. cor-literal          p.66  cor literal declarada fora do arquivo de tokens
3. fonte-fora-do-brand  p.69  font-family declarado fora do arquivo de tokens
4. cor-de-outro-segmento p.68 lilas (Escolas) e verde claro (Graduacao);
   este acervo e do segmento Exec/Pos, cuja cor de segmento e o verde
   escuro #066d73
5. emoji                p.88  a iconografia da marca e o Material Symbols

Uso:
    python3 tools/check_brand.py
"""
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAND = os.path.join("assets", "css", "inteli-brand.css")

PALETA = {
    "#2e2640", "#ff4545", "#90a5e5", "#89cea5", "#066d73",
    "#b2b6bf", "#caced6", "#e6eaeb", "#ffffff",
}
# p.68: pertencem a Escolas e a Graduacao, nao a Exec/Pos
OUTRO_SEGMENTO = {"#90a5e5", "#89cea5"}

EXTENSOES = (".html", ".css", ".js")
# "vendor" fica de fora: e codigo de terceiros (Reveal.js vendorizado para a
# aula nao depender de rede), nao acervo nosso. O tema sobrescreve as cores
# dele via tokens; validar o arquivo upstream so geraria ruido.
# "_site" tambem sai: e copia do acervo montada por tools/build_site.py, entao
# so duplicaria cada achado e ainda reprovaria o proprio inteli-brand.css, que
# la dentro nao esta mais no caminho que o isenta das regras.
IGNORAR = {".git", "node_modules", "__pycache__", ".ipynb_checkpoints", "vendor", ".venv",
           "_site"}

# Valor de declaracao CSS: tudo entre o ":" e o ";" ou o fim do bloco.
# Escanear hex solto daria falso positivo em href="#dados", cujas letras sao
# todas digitos hexadecimais validos.
DECLARACAO = re.compile(r"(?:^|[;{\"'])\s*[-a-zA-Z]+\s*:\s*([^;{}\"']*)")
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FONT_FAMILY = re.compile(r"font-family\s*:")
# Blocos de emoji e simbolos pictograficos. As setas (U+2190 a U+21FF) ficam
# de fora de proposito: sao tipografia, nao emoji, e aparecem em textos como
# "Sprint 1 -> Sprint 2".
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")


def _normalizar(hexa):
    """Expande #abc para #aabbcc e baixa a caixa, para comparar com a paleta."""
    h = hexa.lower()
    if len(h) == 4:
        return "#" + "".join(c * 2 for c in h[1:])
    return h


def _arquivos(raiz):
    for pasta, subs, nomes in os.walk(raiz):
        subs[:] = [s for s in subs if s not in IGNORAR]
        for nome in sorted(nomes):
            if nome.endswith(EXTENSOES):
                caminho = os.path.join(pasta, nome)
                yield caminho, os.path.relpath(caminho, raiz)


def varrer(raiz):
    """Devolve a lista de achados. Lista vazia significa acervo fiel ao brandbook."""
    achados = []
    for caminho, rel in _arquivos(raiz):
        eh_brand = rel.replace(os.sep, "/") == BRAND.replace(os.sep, "/")
        with open(caminho, encoding="utf-8") as fh:
            linhas = fh.read().splitlines()

        for n, linha in enumerate(linhas, start=1):
            for valor in DECLARACAO.findall(linha):
                for bruto in HEX.findall(valor):
                    hexa = _normalizar(bruto)
                    if hexa in OUTRO_SEGMENTO:
                        achados.append({
                            "arquivo": rel, "linha": n,
                            "regra": "cor-de-outro-segmento",
                            "detalhe": "%s e do segmento Escolas ou Graduacao (p.68)" % bruto,
                        })
                    elif eh_brand and hexa not in PALETA:
                        achados.append({
                            "arquivo": rel, "linha": n,
                            "regra": "cor-fora-da-paleta",
                            "detalhe": "%s nao esta na paleta oficial (p.66)" % bruto,
                        })
                    elif not eh_brand:
                        achados.append({
                            "arquivo": rel, "linha": n,
                            "regra": "cor-literal",
                            "detalhe": "%s deveria vir de var(--inteli-*)" % bruto,
                        })

            if not eh_brand and FONT_FAMILY.search(linha):
                achados.append({
                    "arquivo": rel, "linha": n,
                    "regra": "fonte-fora-do-brand",
                    "detalhe": "font-family so pode ser declarado em %s" % BRAND,
                })

            achado_emoji = EMOJI.search(linha)
            if achado_emoji:
                achados.append({
                    "arquivo": rel, "linha": n, "regra": "emoji",
                    "detalhe": "%r: a iconografia da marca e o Material Symbols (p.88)"
                               % achado_emoji.group(0),
                })

    return achados


def main():
    achados = varrer(RAIZ)
    if not achados:
        print("Brandbook: paleta, tipografia, segmento e iconografia conferem.")
        return 0
    for a in achados:
        print("%s:%d  %s  %s" % (a["arquivo"], a["linha"], a["regra"], a["detalhe"]))
    print("\n%d violacao(oes) do brandbook." % len(achados))
    return 1


if __name__ == "__main__":
    sys.exit(main())
