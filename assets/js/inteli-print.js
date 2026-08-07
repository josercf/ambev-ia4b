// ATENCAO, heranca da FIAP: o PDF gerado por este script (botao "Exportar
// PDF", URL com ?print-pdf) revela o gabarito de todos os quizzes do deck.
// Esse PDF traz a resposta certa marcada e NAO deve ser distribuido para a
// turma antes da aula.
//
// Injeta um botao flutuante que reabre a URL atual com ?print-pdf, o
// parametro que o proprio Reveal.js usa para empilhar os slides em modo de
// impressao. Quando esse parametro esta presente, revela a resposta certa
// de cada quiz usando window.IntelIQuiz (exposto por inteli-quiz.js) em vez
// de reimplementar a logica de resposta. O JS nao declara cor nem fonte
// nenhuma aqui: a aparencia do botao vem de .print-button em
// inteli-theme.css.
(function () {
  'use strict';

  function urlDeImpressao() {
    var semQuery = window.location.href.split('?')[0].split('#')[0];
    return semQuery + '?print-pdf' + (window.location.hash || '');
  }

  function criarBotao() {
    var botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'print-button';
    botao.textContent = 'Exportar PDF';
    botao.addEventListener('click', function () {
      window.open(urlDeImpressao(), '_blank');
    });
    document.body.appendChild(botao);
  }

  function revelarGabarito() {
    if (!window.IntelIQuiz) return;
    var quizzes = document.querySelectorAll('.quiz-container');
    for (var i = 0; i < quizzes.length; i++) {
      var quiz = quizzes[i];
      // querySelectorAll, nao querySelector: um quiz pode ter mais de uma
      // opcao correta, e o gabarito do PDF precisa marcar todas, senao o
      // professor confere a aula com um gabarito incompleto. So a primeira
      // chamada passa por window.IntelIQuiz.responder (que grava
      // dataset.respondido e escreve o paragrafo de feedback); as demais
      // opcoes corretas so precisam da classe visual, adicionada direto.
      var corretas = quiz.querySelectorAll('[data-correct="true"]');
      for (var j = 0; j < corretas.length; j++) {
        if (j === 0) {
          window.IntelIQuiz.responder(quiz, corretas[j]);
        } else {
          corretas[j].classList.add('certa');
        }
      }
    }
  }

  function estaEmModoImpressao() {
    return window.location.search.indexOf('print-pdf') !== -1;
  }

  function iniciar() {
    criarBotao();
    if (estaEmModoImpressao()) revelarGabarito();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', iniciar);
  } else {
    iniciar();
  }
})();
