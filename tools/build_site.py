#!/usr/bin/env python3
"""
Monta o diretorio publicado no GitHub Pages a partir de uma lista explicita.

Por que lista explicita e nao "sobe a pasta inteira": este diretorio de
trabalho tem material institucional (guia do programa, business case, .pptx
originais) que nao pode ir para um site publico. Uma allowlist erra para o
lado de deixar de publicar; uma denylist erra para o lado de vazar. O
.gitignore ja barra esses arquivos, mas ele protege o repositorio, nao o
artefato do Pages, que e montado do checkout e poderia incluir qualquer coisa
que aparecesse ali depois.

Alem de copiar, o script CONFERE as referencias locais do site montado. O deck
usa caminhos relativos (`../assets/...`), entao um arquivo esquecido na
allowlist nao quebra nada localmente, onde a pasta inteira existe: quebra so
no site publicado, com imagem faltando no meio da aula. A conferencia roda
sobre o _site/, nunca sobre a arvore de trabalho.

Uso:
    python3 tools/build_site.py            # monta em _site/
    python3 tools/build_site.py saida/     # monta no diretorio indicado
"""

import os
import re
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Arquivos avulsos: (origem, destino dentro do site).
ARQUIVOS = [
    ("index.html", "index.html"),
    ("aulas/modulo2.html", "aulas/modulo2.html"),
    ("materiais/caderno-de-prompts-modulo2.docx", "materiais/caderno-de-prompts-modulo2.docx"),
    ("notebooks/modulo2_tarde.ipynb", "notebooks/modulo2_tarde.ipynb"),
    ("dados/Coroa_Premium_PDV_Performance.csv", "dados/Coroa_Premium_PDV_Performance.csv"),
]

# Diretorios copiados por inteiro.
DIRETORIOS = [("assets", "assets")]

# Lixo de sistema e cache que nao tem por que subir junto com os diretorios.
IGNORAR = shutil.ignore_patterns(".DS_Store", "__pycache__", "*.pyc", ".ipynb_checkpoints")

# Referencia local em HTML. Esquemas remotos, ancoras e data: URIs ficam fora:
# a conferencia e sobre arquivo que precisa existir no artefato.
REF_HTML = re.compile(r"""(?:href|src)\s*=\s*["']([^"'#][^"']*)["']""")
REF_CSS = re.compile(r"""url\(\s*["']?([^"')]+)["']?\s*\)""")
REMOTA = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")


def montar(destino):
    """Copia a allowlist para `destino`, do zero. Devolve a lista de faltantes."""
    if os.path.exists(destino):
        shutil.rmtree(destino)
    os.makedirs(destino)

    faltando = []
    for origem, alvo in ARQUIVOS:
        caminho = os.path.join(RAIZ, origem)
        if not os.path.exists(caminho):
            faltando.append(origem)
            continue
        final = os.path.join(destino, alvo)
        os.makedirs(os.path.dirname(final), exist_ok=True)
        shutil.copy2(caminho, final)

    for origem, alvo in DIRETORIOS:
        caminho = os.path.join(RAIZ, origem)
        if not os.path.isdir(caminho):
            faltando.append(origem + "/")
            continue
        shutil.copytree(caminho, os.path.join(destino, alvo), ignore=IGNORAR)

    return faltando


def _referencias(caminho):
    with open(caminho, encoding="utf-8", errors="ignore") as fh:
        texto = fh.read()
    padrao = REF_CSS if caminho.endswith(".css") else REF_HTML
    for ref in padrao.findall(texto):
        ref = ref.strip()
        if not ref or ref.startswith("#") or REMOTA.match(ref):
            continue
        yield ref.split("#")[0].split("?")[0]


def conferir(destino):
    """Devolve [(arquivo, referencia)] de todo alvo local que nao existe no site."""
    quebradas = []
    for pasta, subs, nomes in os.walk(destino):
        subs[:] = [s for s in subs if s not in {"vendor"}]
        for nome in sorted(nomes):
            if not nome.endswith((".html", ".css")):
                continue
            caminho = os.path.join(pasta, nome)
            rel = os.path.relpath(caminho, destino)
            for ref in _referencias(caminho):
                alvo = os.path.normpath(os.path.join(pasta, ref))
                if not os.path.exists(alvo):
                    quebradas.append((rel, ref))
    return quebradas


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "_site")
    destino = os.path.abspath(destino)

    faltando = montar(destino)
    if faltando:
        print("Arquivo da allowlist nao encontrado no repositorio:")
        for item in faltando:
            print("  %s" % item)
        return 1

    quebradas = conferir(destino)
    if quebradas:
        print("Referencia local sem arquivo correspondente em %s:" % destino)
        for arquivo, ref in quebradas:
            print("  %s -> %s" % (arquivo, ref))
        print("\nInclua o arquivo na allowlist de tools/build_site.py ou corrija o caminho.")
        return 1

    total = sum(len(nomes) for _, _, nomes in os.walk(destino))
    print("Site montado em %s (%d arquivos), referencias locais conferem." % (destino, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
