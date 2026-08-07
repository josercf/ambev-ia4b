// Quiz interativo dos decks. O JS nao declara cor nenhuma: as classes de
// estado (.certa, .errada, .revelada) sao estilizadas em inteli-theme.css,
// senao tools/check_brand.py acusa cor literal.
(function () {
  'use strict';

  function responder(quiz, opcao) {
    if (quiz.dataset.respondido === 'sim') return;
    quiz.dataset.respondido = 'sim';

    var certa = opcao.dataset.correct === 'true';
    opcao.classList.add(certa ? 'certa' : 'errada');

    if (!certa) {
      // querySelectorAll, nao querySelector: um quiz pode ter mais de uma
      // opcao correta (erro de autoria plausivel ao longo de 14 aulas), e
      // querySelector devolveria so a primeira, deixando a(s) outra(s) sem
      // revelar.
      var gabarito = quiz.querySelectorAll('[data-correct="true"]');
      for (var k = 0; k < gabarito.length; k++) {
        gabarito[k].classList.add('revelada');
      }
    }

    var feedback = document.createElement('p');
    feedback.className = 'quiz-feedback';
    feedback.textContent = certa
      ? (opcao.dataset.correctMsg || 'Correto.')
      : (opcao.dataset.incorrectMsg || 'Nao e essa.');
    quiz.appendChild(feedback);
  }

  function ligar() {
    var quizzes = document.querySelectorAll('.quiz-container');
    for (var i = 0; i < quizzes.length; i++) {
      (function (quiz) {
        var opcoes = quiz.querySelectorAll('.quiz-options > li');
        for (var j = 0; j < opcoes.length; j++) {
          (function (opcao) {
            opcao.setAttribute('role', 'button');
            opcao.setAttribute('tabindex', '0');
            opcao.addEventListener('click', function () { responder(quiz, opcao); });
            opcao.addEventListener('keydown', function (e) {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                responder(quiz, opcao);
              }
            });
          })(opcoes[j]);
        }
      })(quizzes[i]);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ligar);
  } else {
    ligar();
  }

  // Exposto para o inteli-print.js revelar o gabarito no modo de impressao
  window.IntelIQuiz = { responder: responder };
})();
