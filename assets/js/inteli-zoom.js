// Zoom de texto por teclado. "+" aumenta e "-" diminui --escala-texto do
// slide ativo em passos de 2px, "0" volta ao padrao. Serve para quem esta
// longe da tela, na sala grande. O JS nao declara cor nem fonte nenhuma
// aqui: so le e escreve a custom property, o valor visual vem do CSS.
(function () {
  'use strict';

  var PASSO = 2;
  // Limites explicitos: abaixo de 12px o texto nao se le projetado da sala
  // grande; acima de 32px o corpo do slide estoura os 720px de altura fixa
  // do tema. Sem isso "-" repetido levava a escala a negativo (o navegador
  // descarta font-size negativo e volta ao default, um efeito colateral da
  // spec de CSS, nao uma decisao do codigo).
  var MINIMO = 12;
  var MAXIMO = 32;

  function slideAtivo() {
    return document.querySelector('.reveal .slides section.present') ||
      document.querySelector('.reveal .slides section');
  }

  function escalaPadrao() {
    // Le o valor do token direto do :root em vez de fixar um numero: se o
    // piso de legibilidade mudar em inteli-brand.css, o fallback acompanha
    // em vez de divergir em silencio.
    var valor = getComputedStyle(document.documentElement)
      .getPropertyValue('--escala-texto').trim();
    var numero = parseFloat(valor);
    return isNaN(numero) ? MINIMO : numero;
  }

  function escalaAtual(slide) {
    var valor = getComputedStyle(slide).getPropertyValue('--escala-texto').trim();
    var numero = parseFloat(valor);
    return isNaN(numero) ? escalaPadrao() : numero;
  }

  function limitar(valor) {
    return Math.min(MAXIMO, Math.max(MINIMO, valor));
  }

  function ajustar(delta) {
    var slide = slideAtivo();
    if (!slide) return;
    var nova = limitar(escalaAtual(slide) + delta);
    slide.style.setProperty('--escala-texto', nova + 'px');
  }

  function resetar() {
    var slide = slideAtivo();
    if (!slide) return;
    slide.style.removeProperty('--escala-texto');
  }

  function foco_em_campo_editavel(alvo) {
    return alvo && (alvo.tagName === 'INPUT' || alvo.tagName === 'TEXTAREA' || alvo.isContentEditable);
  }

  document.addEventListener('keydown', function (e) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    if (foco_em_campo_editavel(e.target)) return;

    if (e.key === '+' || (e.key === '=' && e.shiftKey)) {
      e.preventDefault();
      ajustar(PASSO);
    } else if (e.key === '-') {
      e.preventDefault();
      ajustar(-PASSO);
    } else if (e.key === '0') {
      e.preventDefault();
      resetar();
    }
  });
})();
