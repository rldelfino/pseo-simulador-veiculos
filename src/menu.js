/* Menu do celular e botão "Voltar à simulação" das páginas internas. Sem JavaScript o menu continua abrindo e fechando (é um <details>) e o botão leva ao simulador. */
(function () {
  'use strict';

  // "Voltar à simulação": volta para onde a pessoa estava. Se veio da home, usa o histórico do navegador (a rolagem volta igual);
  // senão abre a home com os números da última simulação (guardados só nesta aba, sem cookie). Sem nada guardado, vai ao simulador.
  var botoes = document.querySelectorAll('a[data-volta]');
  var guardada = '';
  try { guardada = window.sessionStorage.getItem('he-sim') || ''; } catch (e) { guardada = ''; }
  if (/^\?[\w=&.,]*$/.test(guardada)) {
    Array.prototype.forEach.call(botoes, function (a) { a.setAttribute('href', '/' + guardada + '#simulador'); });
  }
  function veioDaHome() {
    try {
      if (!document.referrer || window.history.length < 2) return false;
      var u = new URL(document.referrer);
      return u.origin === window.location.origin && u.pathname === '/';
    } catch (e) { return false; }
  }
  Array.prototype.forEach.call(botoes, function (a) {
    a.addEventListener('click', function (e) {
      if (e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;
      if (veioDaHome()) { e.preventDefault(); window.history.back(); }
    });
  });

  var d = document.querySelector('header details');
  if (!d) return;
  document.addEventListener('click', function (e) {
    if (!d.open) return;
    // toque fora fecha; toque num link também (um link para a própria página, como /#simulador, não recarrega e deixaria o menu aberto)
    if (!d.contains(e.target) || (e.target.closest && e.target.closest('nav a'))) d.open = false;
  });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape' || !d.open) return;
    d.open = false;
    var s = d.querySelector('summary');
    if (s) s.focus();
  });
})();
