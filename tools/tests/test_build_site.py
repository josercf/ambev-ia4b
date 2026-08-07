"""
Testes do build do site publicado no GitHub Pages.

Dois defeitos motivaram estes testes, e os dois so apareceriam depois do deploy:

1. VAZAMENTO. O artefato do Pages e montado do checkout, nao do .gitignore.
   Um arquivo institucional ou o gabarito da tarde que caisse no diretorio
   seria publicado sem ninguem notar. Os testes de ausencia falham antes.

2. REFERENCIA QUEBRADA. O deck usa caminho relativo (`../assets/...`). Na
   maquina do professor a pasta inteira existe, entao qualquer esquecimento na
   allowlist passa; no site, a imagem some no meio da aula.
"""

import os
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "tools"))

import build_site  # noqa: E402


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    destino = str(tmp_path_factory.mktemp("site") / "_site")
    faltando = build_site.montar(destino)
    assert faltando == [], "allowlist aponta para arquivo inexistente: %s" % faltando
    return destino


def _todos(destino):
    for pasta, _, nomes in os.walk(destino):
        for nome in nomes:
            yield os.path.relpath(os.path.join(pasta, nome), destino).replace(os.sep, "/")


# --- o que precisa estar no site -------------------------------------------

@pytest.mark.parametrize("caminho", [
    "index.html",
    "aulas/modulo2.html",
    "materiais/caderno-de-prompts-modulo2.docx",
    "notebooks/modulo2_tarde.ipynb",
    "dados/Coroa_Premium_PDV_Performance.csv",
    "assets/css/inteli-brand.css",
    "assets/vendor/reveal/reveal.js",
])
def test_arquivo_publicado(site, caminho):
    assert os.path.exists(os.path.join(site, caminho)), "%s faltando no site" % caminho


def test_referencias_locais_resolvem(site):
    quebradas = build_site.conferir(site)
    assert quebradas == [], "referencias sem arquivo: %s" % quebradas


def test_index_leva_ao_deck(site):
    with open(os.path.join(site, "index.html"), encoding="utf-8") as fh:
        assert 'href="aulas/modulo2.html"' in fh.read()


# --- o que nao pode vazar ---------------------------------------------------

def test_sem_material_institucional(site):
    proibidas = (".pptx", ".pdf")
    vazou = [f for f in _todos(site) if f.lower().endswith(proibidas)]
    assert vazou == [], "material institucional no site: %s" % vazou


def test_sem_material_de_conducao(site):
    # Gabarito das hipoteses, infra da demo e desenho dos padroes plantados.
    marcas = ("notas-do-professor", "adrs/", "plano_aula", "estrutura_curricular")
    vazou = [f for f in _todos(site) if any(m in f.lower() for m in marcas)]
    assert vazou == [], "material de conducao no site: %s" % vazou


def test_sem_lixo_de_sistema(site):
    lixo = [f for f in _todos(site)
            if f.endswith((".DS_Store", ".pyc")) or "__pycache__" in f]
    assert lixo == [], "arquivo de cache ou de sistema no site: %s" % lixo


def test_apenas_o_deck_da_aula(site):
    # _fixture-tema.html e fixture de teste do tema, nao aula.
    aulas = sorted(f for f in _todos(site) if f.startswith("aulas/"))
    assert aulas == ["aulas/modulo2.html"]


# --- as duas travas funcionam mesmo -----------------------------------------

def test_conferir_acusa_referencia_quebrada(site, tmp_path):
    """Sem este teste, `conferir` poderia devolver [] por nao achar nada e passar."""
    copia = str(tmp_path / "copia")
    os.makedirs(copia)
    with open(os.path.join(copia, "pagina.html"), "w", encoding="utf-8") as fh:
        fh.write('<img src="assets/img/nao-existe.png">')
    assert build_site.conferir(copia) == [("pagina.html", "assets/img/nao-existe.png")]


def test_conferir_ignora_referencia_remota(tmp_path):
    copia = str(tmp_path / "remota")
    os.makedirs(copia)
    with open(os.path.join(copia, "pagina.html"), "w", encoding="utf-8") as fh:
        fh.write('<link href="https://fonts.googleapis.com/css2?family=Platypi">'
                 '<a href="#secao">ancora</a>')
    assert build_site.conferir(copia) == []


def test_montar_acusa_arquivo_ausente_da_allowlist(tmp_path, monkeypatch):
    monkeypatch.setattr(build_site, "ARQUIVOS", [("nao/existe.html", "existe.html")])
    monkeypatch.setattr(build_site, "DIRETORIOS", [])
    assert build_site.montar(str(tmp_path / "vazio")) == ["nao/existe.html"]
