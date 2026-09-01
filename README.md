# Data Science for Decision Makers · Ambev · Módulo 2

Deck e materiais do Módulo 2, *Inteligência Artificial para Data Analytics*, do
programa Data Science for Decision Makers do Inteli Exec (turma DSDMT10 Ambev).

**Site publicado:** https://josercf.github.io/ambev-ia4b/

## O que tem aqui

| Caminho | Conteúdo |
| --- | --- |
| `index.html` | Página inicial do site, com links para o deck e os materiais |
| `aulas/modulo2.html` | Deck da aula em Reveal.js, 66 slides |
| `assets/` | Tema Inteli (CSS de marca), scripts do deck e Reveal.js vendorizado |
| `dados/` | Gerador e dataset sintético do case Coroa Premium |
| `notebooks/` | Análise da tarde em Python, alternativa ao Genie |
| `materiais/` | Caderno de prompts entregue ao aluno |
| `tools/` | Validadores de marca e de layout, e o build do site |

Reveal.js está vendorizado em `assets/vendor/` de propósito: a aula precisa rodar
sem depender de rede na sala.

O material de condução (plano de aula, notas com gabarito e ADRs) não está neste
repositório. Ele fica com o professor.

## Rodar localmente

```sh
python3 -m http.server 8931     # servir por http; file:// muda o comportamento do Reveal
open http://localhost:8931/
```

No macOS, `abrir-deck.command` faz os dois passos com um duplo clique.

## Validação

```sh
pip install -r requirements-dev.txt
python -m playwright install chromium

python tools/check_brand.py                     # paleta, tipografia e iconografia do brandbook
python tools/check_slides.py                    # estouro de slide, sobreposição, título sob o logo
python -m pytest dados/tests tools/tests -q     # dataset e build do site
python tools/build_site.py                      # monta _site/ e confere as referências locais
```

Os quatro rodam no CI a cada push em `main`
(`.github/workflows/pages.yml`). O deploy no Pages só acontece se todos passarem.

## Publicação

`tools/build_site.py` monta o site a partir de uma **allowlist**, não da pasta
inteira. O diretório de trabalho do professor tem material institucional e de
condução que não pode ir para um site público, e uma allowlist erra para o lado
de deixar de publicar. Para adicionar um arquivo ao site, inclua-o na lista em
`tools/build_site.py`; o próprio script falha se uma referência local do HTML
não existir no site montado.
