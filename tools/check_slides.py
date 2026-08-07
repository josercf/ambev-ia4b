#!/usr/bin/env python3
"""
Valida os decks Reveal.js procurando conteudo que estoura o slide.

Tres checagens, porque sao tres defeitos diferentes:

1. ESTOURO. O tema fixa cada <section> em 1280x720. Qualquer elemento que
   ultrapasse essa caixa aparece cortado na projecao. Medir `scrollHeight` da
   section NAO detecta isso de forma confiavel, entao percorremos os
   descendentes e comparamos o retangulo de cada um com a area util do slide
   (ja descontado o padding).

2. SOBREPOSICAO. Um bloco posicionado em absoluto cabe dentro dos 720px e ainda
   assim cobre o bloco de cima, deixando texto ilegivel. Isso passa inteiro pela
   checagem de estouro. Aqui comparamos os filhos diretos da section entre si:
   como o layout deles e empilhado, qualquer intersecao real e defeito.

3. TITULO NO LOGO. O logo do Inteli fica fora da checagem 2 de proposito, senao
   todo slide daria falso positivo. O efeito colateral era um ponto cego: um
   titulo longo quebra a segunda linha por baixo do logo sem estourar os 720px
   e sem sobrepor filho direto da section. Apareceu nas Aulas 10 e 11 em
   31/07/2026, e so foi visto porque alguem abriu o slide no navegador.
   Comparamos as caixas de LINHA do titulo (nao a caixa do h2, que costuma ser
   larga e vazia a direita) com o retangulo do logo.

Uso:
    python3 tools/check_slides.py                      # todos os decks
    python3 tools/check_slides.py aulas/aula01.html
    python3 tools/check_slides.py --shots out/         # salva PNG dos slides com problema

Requer: pip install playwright && python3 -m playwright install chromium
"""
import http.server
import os
import socket
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LARGURA, ALTURA = 1280, 720
TOLERANCIA = 2  # px, para arredondamento de layout


def porta_livre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def servir(porta):
    handler = lambda *a, **k: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=RAIZ, **k
    )
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", porta), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# Executado no navegador: mede cada slide e devolve os elementos que vazam.
JS_MEDIR = """
() => {
  const secoes = [...document.querySelectorAll('.reveal .slides > section')];
  return secoes.map((sec, i) => {
    // Torna o slide mensuravel mesmo sem estar ativo
    const estiloAnterior = sec.getAttribute('style') || '';
    sec.style.display = 'block';
    sec.style.visibility = 'visible';
    sec.style.opacity = '1';

    const cs = getComputedStyle(sec);
    const padTop = parseFloat(cs.paddingTop);
    const padBottom = parseFloat(cs.paddingBottom);
    const padLeft = parseFloat(cs.paddingLeft);
    const padRight = parseFloat(cs.paddingRight);

    const base = sec.getBoundingClientRect();
    const limiteBaixo = base.top + 720 - padBottom;
    const limiteDireita = base.left + 1280 - padRight;

    const vazamentos = [];
    for (const el of sec.querySelectorAll('*')) {
      const ecs = getComputedStyle(el);
      if (ecs.display === 'none' || ecs.visibility === 'hidden') continue;
      // Rodape e barras sao posicionados de proposito na borda
      if (el.closest('.slide-footer, .top-bar, [class*="logo-header"]')) continue;
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;

      const excessoBaixo = r.bottom - limiteBaixo;
      const excessoDireita = r.right - limiteDireita;
      if (excessoBaixo > 2 || excessoDireita > 2) {
        vazamentos.push({
          tag: el.tagName.toLowerCase(),
          classe: (el.className && el.className.baseVal !== undefined
                    ? el.className.baseVal : el.className || '').toString().slice(0, 40),
          texto: (el.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
          abaixo: Math.round(excessoBaixo),
          direita: Math.round(excessoDireita),
        });
      }
    }

    // --- Sobreposicao entre os blocos empilhados do slide --------------
    // So os filhos diretos: comparar descendentes daria falso positivo, ja
    // que todo filho intersecta o proprio pai.
    const rotulo = (el) => {
      const c = (el.className && el.className.baseVal !== undefined
                  ? el.className.baseVal : el.className || '').toString().trim();
      return el.tagName.toLowerCase() + (c ? '.' + c.split(/\\s+/).join('.') : '');
    };

    const blocos = [...sec.children].filter((el) => {
      const ecs = getComputedStyle(el);
      if (ecs.display === 'none' || ecs.visibility === 'hidden') return false;
      // Decoracao de borda: sobrepoe de proposito
      if (el.matches('.slide-footer, .top-bar, [class*="logo-header"]')) return false;
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    });

    const sobreposicoes = [];
    for (let a = 0; a < blocos.length; a++) {
      for (let b = a + 1; b < blocos.length; b++) {
        const ra = blocos[a].getBoundingClientRect();
        const rb = blocos[b].getBoundingClientRect();
        const vertical = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
        const horizontal = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
        if (vertical > 2 && horizontal > 2) {
          sobreposicoes.push({
            a: rotulo(blocos[a]),
            b: rotulo(blocos[b]),
            px: Math.round(vertical),
            texto: (blocos[b].textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
          });
        }
      }
    }

    // COLISAO COM O LOGO. O logo fica de proposito fora da checagem acima, senao
    // todo slide daria falso positivo. O efeito colateral e um ponto cego: um
    // titulo longo quebra a segunda linha por baixo do logo sem estourar os
    // 720px e sem sobrepor filho direto da section. Aconteceu nas Aulas 10 e 11,
    // e so apareceu porque alguem olhou o slide no navegador.
    //
    // Medimos as caixas de LINHA do titulo, nao a caixa do h2: o h2 costuma ser
    // largo e vazio a direita, entao a caixa dele encosta no logo em todo slide.
    const MARGEM_LOGO = 15;
    const colisoes = [];
    const logo = sec.querySelector('[class*="logo-header"]');
    if (logo) {
      const rl = logo.getBoundingClientRect();
      if (rl.width > 0 && rl.height > 0) {
        for (const alvo of sec.querySelectorAll('h1, h2, h3')) {
          const faixa = document.createRange();
          faixa.selectNodeContents(alvo);
          for (const rt of faixa.getClientRects()) {
            if (rt.width < 1 || rt.height < 1) continue;
            const dx = Math.max(rl.left - rt.right, rt.left - rl.right);
            const dy = Math.max(rl.top - rt.bottom, rt.top - rl.bottom);
            // Só interessa quando as caixas se cruzam em uma das direções.
            if (dx >= MARGEM_LOGO || dy >= MARGEM_LOGO) continue;
            const folga = Math.round(Math.max(dx, dy));
            colisoes.push({
              alvo: rotulo(alvo),
              folga: folga,
              texto: (alvo.textContent || '').trim().replace(/\\s+/g, ' ').slice(0, 60),
            });
            break;
          }
        }
      }
    }

    sec.setAttribute('style', estiloAnterior);

    const titulo = sec.querySelector('h2');
    return {
      indice: i,
      titulo: titulo ? titulo.textContent.trim().slice(0, 55) : '(' + sec.className + ')',
      // so o vazamento mais grave por slide, para o relatorio nao explodir
      pior: vazamentos.sort((a, b) =>
        (b.abaixo + b.direita) - (a.abaixo + a.direita))[0] || null,
      total: vazamentos.length,
      sobreposicoes: sobreposicoes.sort((x, y) => y.px - x.px).slice(0, 3),
      colisoes: colisoes.sort((x, y) => x.folga - y.folga).slice(0, 2),
    };
  });
}
"""


def checar(page, url, nome, shots_dir=None, contador=None):
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(900)
    slides = page.evaluate(JS_MEDIR)

    # Contagem independente de quantos slides foram de fato medidos, para
    # main() poder exigir esse numero > 0 antes de reportar sucesso. Nao
    # depende do "return 1" alguns paragrafos abaixo estar certo: mesmo que
    # aquele branch regredisse por engano para "return 0", o total de slides
    # medidos continuaria refletindo a realidade (zero), e main() ainda
    # reprovaria.
    if contador is not None:
        contador["medidos"] += len(slides)

    print("\n%s  (%d slides)" % (nome, len(slides)))
    if not slides:
        # Nenhuma <section> encontrada nao e um deck limpo, e um deck que nao
        # carregou (404, URL errada, HTML sem slides...). Se isso voltasse 0
        # aqui, um caminho invalido passaria pelo portao de qualidade
        # silenciosamente, com exit code 0, sem examinar nada.
        print("  ERRO: nenhuma section encontrada, o deck nao carregou")
        return 1

    problemas = [s for s in slides
                 if s["pior"] or s.get("sobreposicoes") or s.get("colisoes")]
    if not problemas:
        print("  OK: nada estourando 1280x720, sem bloco sobreposto nem titulo no logo")
        return 0

    for s in problemas:
        print("  slide %-2d  %-52s" % (s["indice"], s["titulo"]))

        p = s["pior"]
        if p:
            eixo = []
            if p["abaixo"] > TOLERANCIA:
                eixo.append("%dpx abaixo do limite" % p["abaixo"])
            if p["direita"] > TOLERANCIA:
                eixo.append("%dpx a direita" % p["direita"])
            print("           ESTOURO: %s  <%s class=%r>"
                  % (", ".join(eixo), p["tag"], p["classe"]))
            print("           texto: %s" % p["texto"])

        for sob in s.get("sobreposicoes", []):
            print("           SOBREPOSICAO: %s cobre %s em %dpx"
                  % (sob["a"], sob["b"], sob["px"]))
            print("           texto coberto: %s" % sob["texto"])

        for col in s.get("colisoes", []):
            print("           TITULO NO LOGO: <%s> a %dpx do logo do Inteli"
                  % (col["alvo"], col["folga"]))
            print("           texto: %s" % col["texto"])

        if shots_dir:
            os.makedirs(shots_dir, exist_ok=True)
            page.evaluate("i => Reveal.slide(i, 0)", s["indice"])
            page.wait_for_timeout(500)
            destino = os.path.join(
                shots_dir, "%s-slide%02d.png" % (nome.replace(".html", ""), s["indice"])
            )
            page.screenshot(path=destino)
            print("           screenshot: %s" % destino)

    return len(problemas)


def _parse_args(argv):
    """Separa decks de opcoes. O --shots consome o proprio valor: sem isso o
    diretorio de screenshots entra na lista de decks, o servidor devolve 404,
    e o validador reporta sucesso sem ter medido nada."""
    decks, shots_dir = [], None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--shots":
            shots_dir = argv[i + 1] if i + 1 < len(argv) else "shots"
            i += 2
            continue
        if a.startswith("--"):
            i += 1
            continue
        decks.append(a)
        i += 1
    return decks, shots_dir


def _descobrir_decks(pasta_aulas):
    """Lista os nomes de arquivo elegiveis (.html, sem comecar com "_")
    dentro da pasta de aulas. Separado de main() para o teste de regressao
    poder exercitar uma pasta sem nenhum deck elegivel de verdade (uma pasta
    temporaria com so um arquivo "_algo.html", o mesmo formato do fixture do
    tema), sem depender do estado atual do repositorio nem criar um deck
    temporario dentro de aulas/ so para o teste ter o que achar."""
    return sorted(
        f for f in os.listdir(pasta_aulas)
        if f.endswith(".html") and not f.startswith("_")
    )


def main():
    decks, shots_dir = _parse_args(sys.argv[1:])

    if not decks:
        pasta = os.path.join(RAIZ, "aulas")
        decks = [os.path.join("aulas", f) for f in _descobrir_decks(pasta)]

    if not decks:
        # Pasta aulas/ sem nenhum arquivo elegivel (por exemplo, so o
        # fixture do tema, que o filtro acima exclui de proposito) nao pode
        # terminar em sucesso: sem isso, "nenhum deck encontrado" e "nada
        # estourou" ficam indistinguiveis, e o validador aprova um acervo
        # que ele nunca examinou.
        print("ERRO: nenhum deck encontrado em aulas/, nada foi validado.")
        return 1

    porta = porta_livre()
    httpd = servir(porta)
    problemas_totais = 0
    # Slides efetivamente medidos, independente de terem dado problema ou
    # nao. main() exige esse numero > 0 para reportar sucesso: assim "nada
    # medido" nao consegue se disfarcar de sucesso por construcao, mesmo se
    # algum caminho novo, ainda nao previsto, zerar problemas_totais sem
    # medir nada de verdade.
    contador = {"medidos": 0}

    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            page = navegador.new_page(viewport={"width": LARGURA, "height": ALTURA})
            for deck in decks:
                # Aceita caminho absoluto ou relativo: o servidor serve a partir da RAIZ
                rel = os.path.relpath(os.path.abspath(deck), RAIZ).replace(os.sep, "/")
                url = "http://127.0.0.1:%d/%s" % (porta, rel)
                try:
                    problemas_totais += checar(
                        page, url, os.path.basename(deck), shots_dir, contador
                    )
                except Exception as exc:
                    # Uma excecao aqui (navegacao que trava, pagina que
                    # derruba o processo do navegador etc.) nao pode
                    # desaparecer: conta como problema e o deck seguinte
                    # continua sendo verificado.
                    print("\n%s  ERRO ao verificar: %s" % (os.path.basename(deck), exc))
                    problemas_totais += 1
            navegador.close()
    finally:
        httpd.shutdown()

    print("\n" + "=" * 62)
    if contador["medidos"] == 0:
        print("Nenhum slide foi medido: o validador nao pode reportar sucesso sem medir nada.")
        return 1
    if problemas_totais:
        print("%d slide(s) com problema de layout, entre estouro e sobreposicao." % problemas_totais)
        return 1
    print("Todos os slides cabem em 1280x720, sem bloco sobreposto.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
