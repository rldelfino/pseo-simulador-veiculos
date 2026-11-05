(function () {
  function bloco(a) {
    if (a.closest('nav')) return 'topo';
    if (a.closest('footer')) return 'rodape';
    var s = a.closest('[id]');
    return s ? s.id : 'corpo';
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href*="ftudo.com"], a[href*="financiatudo"]');
    if (a && window.umami) umami.track('cta-financiatudo', { pagina: location.pathname, bloco: bloco(a) });
  }, true);
  var usou = false;
  document.addEventListener('input', function (e) {
    if (usou || !window.umami || !e.target.matches('input')) return;
    usou = true;
    umami.track('usou-simulador', { pagina: location.pathname });
  }, true);
})();
