/* Interface do simulador de financiamento de veículos (home). Só textContent e atributos SVG (nada de innerHTML).
   Depende de calculo.js (calcularPmtPrice, calcularCetVeiculo: o mesmo motor das páginas por banco, testado contra o Python)
   e do bloco JSON #dados-sim (taxas por banco, entrada mínima, limites de valor), gerado por gerador_veiculos.py.
   Sem cookies e sem dado pessoal: o simulador não envia nada para fora, só mede o uso (tipo e prazo) no Umami, sem identificar ninguém. */
(function () {
  'use strict';
  if (typeof calcularPmtPrice !== 'function' || typeof calcularCetVeiculo !== 'function') return;
  var bruto = document.getElementById('dados-sim');
  if (!bruto) return;
  var D;
  try { D = JSON.parse(bruto.textContent); } catch (e) { return; }

  var PRAZO_MIN = 12, PRAZO_MAX = 60, ENTRADA_MAX = 0.9;
  var ROT = { novo: 'carro novo', usado: 'carro usado', moto: 'moto' };
  var COMPARADOR = { novo: '/comparador-carro-novo', usado: '/comparador-carro-usado', moto: '/comparador-moto' };
  var MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  var estado = { cat: 'novo', valor: D.valores.novo.padrao, pct: D.entradaMin.novo, prazo: 48, banco: 'media', taxaProp: 0, conforto: 2000, extra: 300, unico: 5000, quando: 6 };
  var usou = false, abriuAmort = false, usouAmortExtra = false, usouTaxaProp = false;
  var timerUrl = null, timerCopiado = null;
  var BRL_NUM = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });
  var BRL_2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function $(id) { return document.getElementById(id); }
  function clamp(v, a, b) { return Math.min(b, Math.max(a, v)); }
  function limpar(no) { while (no.firstChild) no.removeChild(no.firstChild); }
  function evento(nome, dados) {
    try { if (window.umami && window.umami.track) window.umami.track(nome, dados); } catch (e) { /* medição nunca quebra o simulador */ }
  }
  function el(tag, classe, texto) {
    var e = document.createElement(tag);
    if (classe) e.className = classe;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }
  function brl(v) { return 'R$ ' + BRL_NUM.format(Math.round(v)); }
  function brl2(v) { return 'R$ ' + BRL_2.format(v); }
  function pct1(v) { return v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%'; }
  function mil(v) { return 'R$ ' + BRL_NUM.format(Math.round(v / 1000)) + ' mil'; }

  function lerNumero(texto) {
    var t = String(texto).replace(/[^\d.,]/g, '');
    if (t.indexOf(',') >= 0) t = t.replace(/\./g, '').replace(',', '.');
    else if (/\.\d{3}(\.|$)/.test(t)) t = t.replace(/\./g, '');
    var n = Number(t);
    return isFinite(n) ? n : 0;
  }

  // ---- regras do cenário ----
  function bancos() { return D.bancos[estado.cat]; }
  function mediaTaxa() {
    var l = bancos(), s = 0;
    l.forEach(function (b) { s += b.am; });
    return s / l.length;
  }
  function bancoSel() {
    if (estado.banco === 'media') return null;
    var achado = null;
    bancos().forEach(function (b) { if (b.k === estado.banco) achado = b; });
    return achado;
  }
  function prazoMaxSel() { var b = bancoSel(); return b ? b.pm : PRAZO_MAX; }
  function taxaPropria() { return estado.taxaProp >= 0.3 && estado.taxaProp <= 6; }
  function taxa() {
    if (taxaPropria()) return estado.taxaProp;
    var b = bancoSel();
    return b ? b.am : mediaTaxa();
  }
  function nomeTaxa() {
    if (taxaPropria()) return 'a taxa da sua proposta';
    var b = bancoSel();
    return b ? b.n : 'a média dos bancos';
  }
  function limiteValor() { return D.valores[estado.cat]; }
  function prazoEf() { return clamp(estado.prazo, PRAZO_MIN, prazoMaxSel()); }
  function entradaMin() { return D.entradaMin[estado.cat]; }
  function entradaReais() { return Math.round(estado.valor * estado.pct); }

  function ajustar() {
    var L = limiteValor();
    estado.valor = clamp(estado.valor, L.min, L.max);
    estado.pct = clamp(estado.pct, entradaMin(), ENTRADA_MAX);
  }

  // Conta de referência de um cenário: o mesmo motor do calculo.js.
  function simular(valor, pct, prazo, tx) {
    var entrada = valor * pct, fin = valor - entrada;
    var pmt = calcularPmtPrice(fin, prazo, tx);
    var total = pmt * prazo;
    return { valor: valor, entrada: entrada, fin: fin, prazo: prazo, taxa: tx, parcela: pmt, total: total, juros: total - fin, cet: calcularCetVeiculo(fin, prazo, tx) };
  }

  function preencherRange(r, valor) {
    var min = Number(r.min), max = Number(r.max);
    var v = clamp(valor, min, max);
    r.value = v;
    // Sem style inline nem CSSOM (a CSP não permite e o Safari reclama): o CSS tem uma regra por inteiro de 0 a 100, escolhida por data-p.
    r.setAttribute('data-p', String(Math.round(max > min ? ((v - min) / (max - min)) * 100 : 0)));
  }

  var NS = 'http://www.w3.org/2000/svg';
  var CIRC = 289.0265; // circunferência da rosca (raio 46)
  function svgEl(tag, atributos) {
    var e = document.createElementNS(NS, tag);
    Object.keys(atributos).forEach(function (k) { e.setAttribute(k, String(atributos[k])); });
    return e;
  }

  function desenharRosca(r) {
    var pj = r.total > 0 ? r.juros / r.total : 0;
    $('rosca-cred').setAttribute('stroke-dasharray', ((1 - pj) * CIRC).toFixed(1) + ' ' + CIRC.toFixed(2));
    $('rosca-pct').textContent = Math.round(pj * 100) + '%';
    $('rosca-cred-v').textContent = brl(r.fin);
    $('rosca-juros-v').textContent = brl(r.juros);
    $('rosca-svg').setAttribute('aria-label', 'Do total das parcelas, ' + Math.round(pj * 100) + '% é juros');
  }

  // ---- amortização ano a ano (Tabela Price) ----
  function anual(fin, prazo, tx) {
    var i = tx / 100, pmt = calcularPmtPrice(fin, prazo, tx), saldo = fin, linhas = [], ano = 0, j = 0, a = 0;
    for (var m = 1; m <= prazo; m++) {
      var juros = saldo * i, am = pmt - juros;
      saldo = Math.max(0, saldo - am);
      j += juros; a += am;
      if (m % 12 === 0 || m === prazo) { ano++; linhas.push({ ano: ano, juros: j, amortizacao: a, saldo: saldo < 0.005 ? 0 : saldo }); j = 0; a = 0; }
    }
    return linhas;
  }

  function desenharGrafAmort(linhas, fin) {
    var g = $('amort-graf');
    limpar(g);
    var n = linhas.length, W = 640, Hh = 220, topo = 12, base = Hh - 4, util = base - topo;
    var slot = W / n, larg = Math.max(4, Math.min(90, slot * 0.68));
    var maxAno = 0;
    linhas.forEach(function (x) { maxAno = Math.max(maxAno, x.juros + x.amortizacao); });
    var pontos = ['0,' + topo.toFixed(1)];
    linhas.forEach(function (x, k) {
      var x0 = k * slot + (slot - larg) / 2;
      var hA = (x.amortizacao / maxAno) * util, hJ = (x.juros / maxAno) * util;
      g.appendChild(svgEl('rect', { 'class': 'g-a', x: x0.toFixed(1), y: (base - hA).toFixed(1), width: larg.toFixed(1), height: Math.max(0, hA).toFixed(1) }));
      g.appendChild(svgEl('rect', { 'class': 'g-j', x: x0.toFixed(1), y: (base - hA - hJ).toFixed(1), width: larg.toFixed(1), height: Math.max(0, hJ).toFixed(1) }));
      pontos.push(((k + 1) * slot).toFixed(1) + ',' + (base - (x.saldo / fin) * util).toFixed(1));
    });
    g.appendChild(svgEl('polyline', { 'class': 'g-s', points: pontos.join(' ') }));
    $('amort-ano-fim').textContent = n === 1 ? 'Ano 1' : 'Ano ' + n;
    g.setAttribute('aria-label', 'Gráfico: no ano 1, ' + brl(linhas[0].juros) + ' de juros e ' + brl(linhas[0].amortizacao) + ' de amortização; no ano ' + n + ', ' +
      brl(linhas[n - 1].juros) + ' de juros e ' + brl(linhas[n - 1].amortizacao) + ' de amortização. O saldo devedor cai até zero.');
  }

  function celula(tag, texto, escopo) {
    var c = el(tag, '', texto);
    if (escopo) c.setAttribute('scope', escopo);
    return c;
  }

  function desenharAmort(r) {
    var linhas = anual(r.fin, r.prazo, r.taxa);
    var primeiro = linhas[0];
    var pj = Math.round((primeiro.juros / (primeiro.juros + primeiro.amortizacao)) * 100);
    $('amort-pct').textContent = pj + '%';
    $('amort-resumo').textContent = 'No primeiro ano, de ' + brl(primeiro.juros + primeiro.amortizacao) + ' pagos em parcelas, ' + brl(primeiro.juros) + ' são juros e só ' + brl(primeiro.amortizacao) +
      ' abatem a dívida. Por isso pagar a mais cedo faz diferença.';
    desenharGrafAmort(linhas, r.fin);
    var corpo = $('amort-corpo'), rodape = $('amort-rodape'), tj = 0, ta = 0;
    limpar(corpo); limpar(rodape);
    linhas.forEach(function (x) {
      var tr = el('tr');
      tr.appendChild(celula('th', 'Ano ' + x.ano, 'row'));
      tr.appendChild(celula('td', brl(x.juros)));
      tr.appendChild(celula('td', brl(x.amortizacao)));
      tr.appendChild(celula('td', brl(x.saldo)));
      corpo.appendChild(tr);
      tj += x.juros; ta += x.amortizacao;
    });
    var tf = el('tr');
    tf.appendChild(celula('th', 'Total', 'row'));
    tf.appendChild(celula('td', brl(tj)));
    tf.appendChild(celula('td', brl(ta)));
    tf.appendChild(celula('td', '—'));
    rodape.appendChild(tf);
    $('am-taxa-aa').textContent = pct1((Math.pow(1 + r.taxa / 100, 12) - 1) * 100);
  }

  // ---- pagar a mais: mesma parcela, prazo menor ----
  function simularPagarMais(fin, prazo, tx, extra, unico, quando) {
    var i = tx / 100, pmt = calcularPmtPrice(fin, prazo, tx), saldo = fin, juros = 0, m = 0, pago = 0;
    while (saldo > 0.005 && m < prazo) {
      m++;
      var j = saldo * i;
      juros += j;
      var parc = Math.min(pmt, saldo + j);
      pago += parc;
      saldo -= (parc - j);
      if (saldo > 0.005 && extra > 0) { var e = Math.min(extra, saldo); saldo -= e; pago += e; }
      if (m === quando && unico > 0 && saldo > 0.005) { var u = Math.min(unico, saldo); saldo -= u; pago += u; }
    }
    return { juros: juros, meses: m, total: pago };
  }
  function simularPagarMaisInicio(fin, prazo, tx, unico) {
    // amortização única "logo no início": antes da 1ª parcela
    var f = Math.max(0, fin - Math.min(unico, fin));
    var r = simularPagarMais(f, prazo, tx, 0, 0, -1);
    return r;
  }

  function dur(m) {
    var a = Math.floor(m / 12), r = m % 12, p = [];
    if (a > 0) p.push(a + (a === 1 ? ' ano' : ' anos'));
    if (r > 0 || a === 0) p.push(r + (r === 1 ? ' mês' : ' meses'));
    return p.join(' e ');
  }
  function rotQuando(q) { return q === 0 ? 'no início, antes da 1ª parcela' : 'daqui a ' + q + (q === 1 ? ' mês' : ' meses'); }

  function cartaoAm(titulo, big, bigRot, linhas, melhor) {
    var c = el('div', 'amc' + (melhor ? ' best' : ''));
    if (melhor) c.appendChild(el('span', 'tg', 'Maior economia'));
    c.appendChild(el('h4', '', titulo));
    c.appendChild(el('div', 'big num', big));
    c.appendChild(el('div', 'bl', bigRot));
    var ul = el('ul');
    linhas.forEach(function (l) { ul.appendChild(el('li', '', l)); });
    c.appendChild(ul);
    return c;
  }

  function desenharAmortExtra(r) {
    var cont = $('am-cartoes');
    limpar(cont);
    var q = Math.min(estado.quando, Math.max(0, r.prazo - 2));
    $('range-quando').max = String(Math.max(0, r.prazo - 2));
    $('quando-rot').textContent = rotQuando(q);
    var lista = [];
    function adiciona(titulo, res, linhas) { lista.push({ titulo: titulo, poup: r.juros - res.juros, linhas: linhas }); }
    function linhasDe(res) {
      return ['Termina ' + dur(r.prazo - res.meses) + ' antes (em ' + res.meses + ' parcelas)', 'Total pago: ' + brl(res.total)];
    }
    if (estado.extra > 0) {
      var re = simularPagarMais(r.fin, r.prazo, r.taxa, estado.extra, 0, 0);
      adiciona('Pagando ' + brl(estado.extra) + ' a mais todo mês', re, linhasDe(re));
    }
    if (estado.unico > 0) {
      var ru = q === 0 ? simularPagarMaisInicio(r.fin, r.prazo, r.taxa, estado.unico) : simularPagarMais(r.fin, r.prazo, r.taxa, 0, estado.unico, q);
      ru = { juros: ru.juros, meses: ru.meses, total: ru.total + (q === 0 ? Math.min(estado.unico, r.fin) : 0) };
      adiciona('Amortização única de ' + brl(estado.unico) + ', ' + rotQuando(q), ru, linhasDe(ru));
    }
    if (estado.extra > 0 && estado.unico > 0) {
      var rb = simularPagarMais(r.fin, r.prazo, r.taxa, estado.extra, estado.unico, q === 0 ? 1 : q);
      adiciona('Os dois juntos', rb, linhasDe(rb));
    }
    var melhor = 0;
    lista.forEach(function (c, k) { if (c.poup > lista[melhor].poup) melhor = k; });
    lista.forEach(function (c, k) { cont.appendChild(cartaoAm(c.titulo, brl(c.poup), 'a menos em juros', c.linhas, lista.length > 1 && k === melhor)); });
    $('am-texto').textContent = lista.length
      ? 'Conta com a taxa de ' + pct1(r.taxa) + ' ao mês e parcela fixa de ' + brl2(r.parcela) + '. Sem tarifas de liquidação antecipada nem custo de oportunidade.'
      : 'Informe um valor a pagar a mais para ver quanto você poupa.';
  }

  // ---- raio-x: o que muda com a mesma taxa ----
  function cartaoAlt(titulo, parcela, linhas, atual, destaque) {
    var d = el('div', 'alt' + (atual ? ' cur' : ''));
    d.appendChild(el('h3', '', titulo));
    d.appendChild(el('div', 'p num', brl2(parcela)));
    var info = el('div', 'd');
    linhas.forEach(function (l, i) { if (i) info.appendChild(document.createElement('br')); info.appendChild(document.createTextNode(l)); });
    if (destaque) { info.appendChild(document.createElement('br')); info.appendChild(el('span', destaque.cls, destaque.texto)); }
    d.appendChild(info);
    return d;
  }
  function difMensal(base, outra) {
    var d = outra.parcela - base.parcela;
    if (Math.abs(d) < 0.5) return { cls: 'up', texto: 'Parcela igual à atual' };
    return d < 0 ? { cls: 'dn', texto: brl(-d) + ' a menos por mês' } : { cls: 'up', texto: brl(d) + ' a mais por mês' };
  }

  function desenharRaio(r) {
    var c = estado.conforto, txt;
    if (c > 0) {
      var dif = r.parcela - c;
      txt = dif > 0
        ? 'Com a estimativa de ' + brl2(r.parcela) + ', este cenário fica ' + brl(dif) + ' acima do valor que você informou. Veja o que muda com a mesma taxa:'
        : 'Com a estimativa de ' + brl2(r.parcela) + ', este cenário cabe no valor que você informou (' + brl(-dif) + ' abaixo). Veja o que muda com a mesma taxa:';
    } else {
      txt = 'Com a estimativa de ' + brl2(r.parcela) + ' por mês, veja o que muda com a mesma taxa:';
    }
    $('raio-texto').textContent = txt;
    var alts = $('alts'), pmax = prazoMaxSel();
    limpar(alts);
    alts.appendChild(cartaoAlt('Este cenário', r.parcela, ['Entrada ' + brl(r.entrada), r.prazo + ' meses · total ' + brl(r.total)], true));
    var p2 = Math.min(ENTRADA_MAX, estado.pct + 0.1);
    if (p2 > estado.pct + 0.0001) {
      var a = simular(estado.valor, p2, r.prazo, r.taxa);
      alts.appendChild(cartaoAlt('Entrada maior (+10 pontos)', a.parcela, ['Entrada ' + brl(a.entrada), 'Juros no total: ' + brl(a.juros)], false, difMensal(r, a)));
    }
    var pz = r.prazo + 12 <= pmax ? r.prazo + 12 : r.prazo - 12;
    if (pz >= PRAZO_MIN && pz !== r.prazo) {
      var b = simular(estado.valor, estado.pct, pz, r.taxa);
      alts.appendChild(cartaoAlt(pz > r.prazo ? 'Prazo maior (+12 meses)' : 'Prazo menor (−12 meses)', b.parcela, [pz + ' meses', 'Juros no total: ' + brl(b.juros)], false, difMensal(r, b)));
    }
    var v2 = Math.max(limiteValor().min, Math.round(estado.valor * 0.9 / 1000) * 1000);
    if (v2 < estado.valor) {
      var cc = simular(v2, estado.pct, r.prazo, r.taxa);
      alts.appendChild(cartaoAlt('Veículo 10% mais barato', cc.parcela, ['Valor ' + brl(v2), 'Entrada ' + brl(cc.entrada)], false, difMensal(r, cc)));
    }
    $('renda-texto').textContent = 'Com a referência de até cerca de 30% da renda, a parcela estimada de ' + brl2(r.parcela) +
      ' pede uma renda mensal comprovada de cerca de ' + brl(r.parcela / 0.3) + ' (conta nossa, não é análise de crédito).';
  }

  // ---- comparativo por banco ----
  function linhaBanco(x, max, ehSel) {
    var linha = el('div', 'mrow' + (ehSel ? ' us' : ''));
    var mn = el('div', 'mn');
    if (ehSel) mn.appendChild(el('span', 'tg', 'Selecionado'));
    mn.appendChild(el('b', '', x.n));
    mn.appendChild(el('span', 'chip', pct1(x.am) + ' a.m.' + (x.prazo < estado.prazo ? ' · até ' + x.prazo + ' meses' : '')));
    linha.appendChild(mn);
    var mb = el('div', 'mb');
    var W = 400, wTot = Math.max(8, (x.total / max) * W), wFin = (x.fin / x.total) * wTot;
    var svg = svgEl('svg', { viewBox: '0 0 ' + W + ' 16', preserveAspectRatio: 'none', role: 'img', 'aria-label': x.n + ': ' + brl(x.fin) + ' financiados e ' + brl(x.juros) + ' de juros' });
    svg.appendChild(svgEl('rect', { x: 0, y: 2, width: wFin.toFixed(1), height: 12, rx: 3, fill: '#cbd5e1' }));
    svg.appendChild(svgEl('rect', { x: wFin.toFixed(1), y: 2, width: Math.max(0, wTot - wFin).toFixed(1), height: 12, rx: 3, fill: '#e3a96b' }));
    mb.appendChild(svg);
    linha.appendChild(mb);
    var mv = el('div', 'mv');
    mv.appendChild(el('b', 'num', brl2(x.parcela) + '/mês'));
    mv.appendChild(el('small', '', 'CET ' + pct1(x.cet) + ' a.a.'));
    linha.appendChild(mv);
    return linha;
  }

  function desenharComparativo(r) {
    var alvo = $('cm-linhas');
    limpar(alvo);
    var itens = bancos().map(function (b) {
      var p = Math.min(r.prazo, b.pm), s = simular(estado.valor, estado.pct, p, b.am);
      return { k: b.k, n: b.n, am: b.am, prazo: p, fin: s.fin, juros: s.juros, total: s.total, parcela: s.parcela, cet: s.cet };
    });
    itens.sort(function (a, b) { return a.cet - b.cet; });
    var max = 0;
    itens.forEach(function (x) { if (x.total > max) max = x.total; });
    itens.forEach(function (x) { alvo.appendChild(linhaBanco(x, max, estado.banco !== 'media' && x.k === estado.banco && !taxaPropria())); });
    var menor = itens[0], maior = itens[itens.length - 1];
    var gap = maior.juros - menor.juros;
    $('cm-gap-v').textContent = brl(gap);
    $('cm-gap').textContent = 'É a diferença nos juros pagos entre ' + maior.n + ' e ' + menor.n + ' neste cenário (' + brl(estado.valor) + ', entrada de ' + brl(entradaReais()) + '). Vale pedir mais de uma proposta.';
    $('cm-lead').textContent = 'Quanto o mesmo ' + ROT[estado.cat] + ' de ' + brl(estado.valor) + ' custa em cada banco, com a mesma entrada e o mesmo prazo, ordenado do menor para o maior CET.';
    var ac = $('a-comparador');
    ac.setAttribute('href', COMPARADOR[estado.cat]);
    ac.textContent = 'comparador de ' + ROT[estado.cat];
  }

  // ---- endereço compartilhável ----
  function lerEndereco() {
    try {
      var q = new URLSearchParams(window.location.search);
      var so = /^[\d.,]+$/;
      function num(nome) { var t = q.get(nome) || ''; return so.test(t) ? lerNumero(t) : 0; }
      var c = q.get('tipo');
      if (c === 'novo' || c === 'usado' || c === 'moto') { estado.cat = c; estado.valor = D.valores[c].padrao; estado.pct = D.entradaMin[c]; }
      if (num('valor') > 0) estado.valor = num('valor');
      if (num('entrada') > 0 && estado.valor > 0) estado.pct = num('entrada') / estado.valor;
      var p = Math.round(num('prazo'));
      if (p >= PRAZO_MIN && p <= PRAZO_MAX) estado.prazo = p;
      var bk = q.get('banco');
      if (bk && /^[\w .\-]{1,40}$/.test(bk)) estado.banco = bk;
      if (q.get('conforto') !== null) estado.conforto = num('conforto');
      var tp = num('taxa');
      if (tp >= 0.3 && tp <= 6) estado.taxaProp = tp;
      var bs = bancoSel();
      if (estado.banco !== 'media' && !bs) estado.banco = 'media';
    } catch (e) { /* endereço estranho: usa os valores padrão */ }
  }

  function enderecoDaSimulacao(comAncora) {
    var q = new URLSearchParams();
    q.set('tipo', estado.cat);
    q.set('valor', String(Math.round(estado.valor)));
    q.set('entrada', String(entradaReais()));
    q.set('prazo', String(estado.prazo));
    if (estado.banco !== 'media') q.set('banco', estado.banco);
    if (estado.conforto > 0) q.set('conforto', String(Math.round(estado.conforto)));
    if (taxaPropria()) q.set('taxa', String(estado.taxaProp).replace('.', ','));
    return window.location.origin + window.location.pathname + '?' + q.toString() + (comAncora ? '#simulador' : '');
  }

  function atualizarEndereco() {
    clearTimeout(timerUrl);
    timerUrl = setTimeout(function () {
      try { window.history.replaceState(null, '', enderecoDaSimulacao(false)); } catch (e) { /* sem histórico: o botão de copiar continua valendo */ }
    }, 400);
  }

  async function copiarLink() {
    var url = enderecoDaSimulacao(true);
    var ok = false;
    try { window.history.replaceState(null, '', enderecoDaSimulacao(false)); } catch (e) { /* ignora */ }
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(url); ok = true; }
    } catch (e) { /* tenta o plano B abaixo */ }
    if (!ok) {
      try {
        var t = document.createElement('textarea');
        t.value = url; t.setAttribute('readonly', ''); t.className = 'sr';
        document.body.appendChild(t); t.select();
        ok = document.execCommand('copy');
        document.body.removeChild(t);
      } catch (e) { ok = false; }
    }
    var msg = $('msg-copiado');
    msg.textContent = ok ? 'Link copiado. Quem abrir vê esta mesma simulação.' : 'Não deu para copiar sozinho. O link já está na barra de endereço do navegador.';
    clearTimeout(timerCopiado);
    timerCopiado = setTimeout(function () { msg.textContent = ''; }, 4000);
    evento('copiou-link', { tipo: estado.cat, prazo: estado.prazo });
  }

  // ---- desenho principal ----
  function desenhar(foco) {
    ajustar();
    var L = limiteValor(), prazo = prazoEf(), tx = taxa();
    var r = simular(estado.valor, estado.pct, prazo, tx);
    var emin = Math.round(estado.valor * entradaMin()), emax = Math.round(estado.valor * ENTRADA_MAX);

    $('cat-' + estado.cat).checked = true;
    if (foco !== 'valor') $('campo-valor').value = BRL_NUM.format(estado.valor);
    var rv = $('range-valor');
    rv.min = String(L.min); rv.max = String(L.max); rv.step = String(L.passo);
    preencherRange(rv, estado.valor);
    $('min-valor').textContent = mil(L.min);
    $('max-valor').textContent = mil(L.max);
    $('rot-valor').textContent = estado.cat === 'moto' ? 'preço da moto' : 'preço de tabela ou da loja';
    if (foco !== 'entrada') $('campo-entrada').value = BRL_NUM.format(entradaReais());
    var re = $('range-entrada');
    re.min = String(emin); re.max = String(emax); re.step = '500';
    preencherRange(re, entradaReais());
    $('min-entrada').textContent = mil(emin);
    $('max-entrada').textContent = mil(emax);
    $('rot-entrada').textContent = Math.round(estado.pct * 100) + '% do valor';
    if (foco !== 'prazo') $('campo-prazo').value = String(prazo);
    var rp = $('range-prazo');
    rp.min = String(PRAZO_MIN); rp.max = String(prazoMaxSel());
    preencherRange(rp, prazo);
    $('max-prazo').textContent = prazoMaxSel() + ' meses';
    $('rot-prazo').textContent = 'de ' + PRAZO_MIN + ' a ' + prazoMaxSel() + ' meses';
    $('campo-banco').value = estado.banco === 'media' ? 'Média dos bancos' : (bancoSel() ? bancoSel().n : 'Média dos bancos');
    $('rot-banco').textContent = taxaPropria() ? 'trocada pela taxa da proposta' : (bancoSel() ? pct1(bancoSel().am) + ' ao mês' : pct1(mediaTaxa()) + ' ao mês');
    $('hint-banco').textContent = taxaPropria()
      ? 'Usando a taxa da sua proposta (' + pct1(estado.taxaProp) + ' ao mês). Apague o campo da proposta para voltar à taxa do banco.'
      : (bancoSel()
        ? 'Taxa média do ' + bancoSel().n + ' no Banco Central: ' + pct1(bancoSel().am) + ' ao mês. Não é oferta: a sua pode ser diferente.'
        : 'Média simples das taxas dos ' + bancos().length + ' bancos que acompanhamos (Banco Central). Escolha um banco para usar a taxa dele.');

    $('r-parcela').textContent = brl2(r.parcela);
    $('r-sub').textContent = 'em ' + prazo + ' meses · taxa ' + pct1(tx) + ' a.m.';
    $('r-total').textContent = brl(r.total);
    $('r-cet').textContent = pct1(r.cet) + ' a.a.';
    $('r-resumo').textContent = 'Você financia ' + brl(r.fin) + ' e paga ' + brl(r.total) + ' no total: ' + brl(r.juros) + ' a mais em juros.';
    desenharRosca(r);

    $('c-valor').textContent = brl(estado.valor);
    $('c-financiado').textContent = brl(r.fin);
    $('c-entrada').textContent = brl(r.entrada);
    $('c-fin-pct').textContent = Math.round((1 - estado.pct) * 100) + '%';
    $('c-ent-rot').textContent = 'Entrada (' + Math.round(estado.pct * 100) + '%)';
    $('bar-fill').setAttribute('width', ((1 - estado.pct) * 100).toFixed(1) + '%');
    $('bar-mark').setAttribute('x', (entradaMin() * 100).toFixed(1) + '%');

    var hoje = new Date(), fim = new Date(hoje.getFullYear(), hoje.getMonth() + prazo, 1);
    $('k-quita').textContent = MESES[fim.getMonth()] + '/' + fim.getFullYear();
    $('k-quita-s').textContent = prazo + ' parcelas, se contratar este mês';
    $('k-juro1').textContent = 'R$ ' + BRL_2.format(r.juros / r.fin);
    $('k-aa').textContent = pct1((Math.pow(1 + tx / 100, 12) - 1) * 100);
    $('k-aa-s').textContent = taxaPropria() ? 'da taxa da sua proposta' : 'para comparar com outras taxas';

    if (foco !== 'conforto') $('campo-conforto').value = estado.conforto > 0 ? BRL_NUM.format(estado.conforto) : '';
    if (foco !== 'extra') $('campo-extra').value = BRL_NUM.format(estado.extra);
    if (foco !== 'unico') $('campo-unico').value = BRL_NUM.format(estado.unico);
    preencherRange($('range-quando'), Math.min(estado.quando, Math.max(0, prazo - 2)));

    desenharComparativo(r);
    desenharRaio(r);
    desenharAmort(r);
    desenharAmortExtra(r);
    atualizarEndereco();
    return r;
  }

  function interagiu() {
    if (usou) return;
    usou = true;
    evento('usou-simulador-veiculos', { tipo: estado.cat, prazo: estado.prazo });
  }
  function mexeuTaxaProp() { if (!usouTaxaProp) { usouTaxaProp = true; evento('usou-taxa-propria', { tipo: estado.cat }); } }
  function mexeuAmort() { if (!usouAmortExtra) { usouAmortExtra = true; evento('simulou-amortizacao', { tipo: estado.cat }); } }

  // ---- campos ----
  function ligarCampo(id, aplicar, foco, aoMexer) {
    var c = $(id), mexeu = aoMexer || interagiu;
    c.addEventListener('input', function (e) {
      var v = lerNumero(e.target.value);
      if (v > 0) { aplicar(v, false); mexeu(); desenhar(foco); }
    });
    c.addEventListener('blur', function (e) {
      aplicar(lerNumero(e.target.value), true);
      mexeu();
      desenhar();
    });
    c.addEventListener('keydown', function (e) { if (e.key === 'Enter') e.target.blur(); });
  }

  // Lista suspensa acessível (combobox ARIA). opcoes() devolve [{v, rot, sub}]; atual() o valor marcado; escolher(v) aplica.
  function ligarCombo(cfg) {
    var c = $(cfg.campo), lista = $(cfg.lista), caixa = $(cfg.caixa), btn = $(cfg.btn), ativo = null, ops = [];
    function aberta() { return !lista.hidden; }
    function montar() {
      limpar(lista);
      ops = cfg.opcoes();
      ops.forEach(function (o, k) {
        var li = el('li');
        li.id = cfg.lista + '-op-' + k;
        li.setAttribute('role', 'option');
        li.setAttribute('data-k', String(k));
        li.appendChild(el('span', '', o.rot));
        if (o.sub) li.appendChild(el('small', '', o.sub));
        lista.appendChild(li);
      });
    }
    function indiceDe(v) { for (var k = 0; k < ops.length; k++) if (ops[k].v === v) return k; return 0; }
    function marcar(k) {
      ativo = k;
      Array.prototype.forEach.call(lista.children, function (li, j) {
        li.setAttribute('aria-selected', ops[j].v === cfg.atual() ? 'true' : 'false');
        li.className = j === k ? 'ativo' : '';
      });
      var cur = lista.children[k];
      if (cur) {
        c.setAttribute('aria-activedescendant', cur.id);
        if (cur.offsetTop < lista.scrollTop) lista.scrollTop = cur.offsetTop;
        else if (cur.offsetTop + cur.offsetHeight > lista.scrollTop + lista.clientHeight) lista.scrollTop = cur.offsetTop + cur.offsetHeight - lista.clientHeight;
      }
    }
    function abrir() {
      montar();
      lista.hidden = false;
      c.setAttribute('aria-expanded', 'true');
      caixa.className = 'inp combo aberto';
      marcar(indiceDe(cfg.atual()));
      var cur = lista.children[indiceDe(cfg.atual())];
      if (cur) lista.scrollTop = Math.max(0, cur.offsetTop - lista.clientHeight / 2 + cur.offsetHeight / 2);
    }
    function fechar() {
      lista.hidden = true;
      c.setAttribute('aria-expanded', 'false');
      c.removeAttribute('aria-activedescendant');
      caixa.className = 'inp combo';
    }
    function escolher(k) { fechar(); cfg.escolher(ops[k].v); }
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && aberta()) fechar(); });
    c.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (!aberta()) { abrir(); return; }
        marcar(clamp(ativo + (e.key === 'ArrowDown' ? 1 : -1), 0, ops.length - 1));
      } else if (e.key === 'Enter' || e.key === ' ') {
        if (cfg.readonly || aberta() || e.key === 'Enter') {
          e.preventDefault();
          if (aberta()) escolher(ativo); else if (cfg.readonly) abrir(); else e.target.blur();
        }
      } else if (e.key === 'Escape') { if (aberta()) { e.preventDefault(); fechar(); } }
      else if (e.key === 'Tab') fechar();
    });
    if (cfg.readonly) c.addEventListener('click', function () { if (aberta()) fechar(); else abrir(); });
    c.addEventListener('input', function () { if (aberta()) fechar(); });
    btn.addEventListener('mousedown', function (e) { e.preventDefault(); });
    btn.addEventListener('click', function () { if (aberta()) fechar(); else { abrir(); if (cfg.readonly) c.focus(); } });
    lista.addEventListener('mousedown', function (e) { e.preventDefault(); });
    lista.addEventListener('click', function (e) {
      var li = e.target.closest ? e.target.closest('li') : null;
      if (li) escolher(Number(li.getAttribute('data-k')));
    });
    document.addEventListener('click', function (e) { if (aberta() && !caixa.contains(e.target)) fechar(); });
  }

  function ligarPrazo() {
    var c = $('campo-prazo'), msg = $('msg-prazo');
    ligarCombo({
      campo: 'campo-prazo', lista: 'lista-prazo', caixa: 'combo-prazo', btn: 'btn-prazo',
      opcoes: function () {
        var o = [];
        for (var m = PRAZO_MIN; m <= prazoMaxSel(); m += 6) o.push({ v: m, rot: m + ' meses', sub: m % 12 === 0 ? (m / 12) + (m === 12 ? ' ano' : ' anos') : '' });
        return o;
      },
      atual: function () { return prazoEf(); },
      escolher: function (v) { estado.prazo = v; msg.hidden = true; interagiu(); desenhar(); }
    });
    c.addEventListener('input', function (e) {
      var v = Math.round(lerNumero(e.target.value));
      if (v >= PRAZO_MIN && v <= prazoMaxSel()) { estado.prazo = v; msg.hidden = true; interagiu(); desenhar('prazo'); }
    });
    c.addEventListener('blur', function (e) {
      var v = Math.round(lerNumero(e.target.value)), max = prazoMaxSel();
      if (v >= PRAZO_MIN && v <= max) msg.hidden = true;
      else {
        v = clamp(v > 0 ? v : estado.prazo, PRAZO_MIN, max);
        msg.hidden = false; msg.textContent = 'O prazo vai de ' + PRAZO_MIN + ' a ' + max + ' meses. Ajustamos para ' + v + ' meses.';
      }
      estado.prazo = v; interagiu(); desenhar();
    });
    $('range-prazo').addEventListener('input', function (e) { estado.prazo = Number(e.target.value); msg.hidden = true; interagiu(); desenhar(); });
  }

  function ligarBanco() {
    ligarCombo({
      campo: 'campo-banco', lista: 'lista-banco', caixa: 'combo-banco', btn: 'btn-banco', readonly: true,
      opcoes: function () {
        var o = [{ v: 'media', rot: 'Média dos bancos', sub: pct1(mediaTaxa()) + ' a.m.' }];
        bancos().forEach(function (b) { o.push({ v: b.k, rot: b.n, sub: pct1(b.am) + ' a.m.' }); });
        return o;
      },
      atual: function () { return estado.banco; },
      escolher: function (v) {
        estado.banco = v;
        var max = prazoMaxSel(), msg = $('msg-prazo');
        if (estado.prazo > max) { msg.hidden = false; msg.textContent = 'O ' + bancoSel().n + ' financia até ' + max + ' meses. Ajustamos o prazo.'; }
        else msg.hidden = true;
        interagiu(); desenhar();
      }
    });
  }

  // Trocar o tipo de veículo volta ao valor e à entrada típicos dele (uma moto não custa o que um carro custa).
  function trocarCategoria(c) {
    estado.cat = c;
    estado.valor = D.valores[c].padrao;
    estado.pct = D.entradaMin[c];
    if (!bancoSel() && estado.banco !== 'media') estado.banco = 'media';
    $('msg-entrada').hidden = true;
  }

  function iniciar() {
    lerEndereco();
    Array.prototype.forEach.call(document.querySelectorAll('input[name="categoria"]'), function (rd) {
      rd.addEventListener('change', function (e) { trocarCategoria(e.target.value); interagiu(); desenhar(); });
    });
    ligarCampo('campo-valor', function (v, fim) {
      var L = limiteValor();
      if (v >= L.min || fim) estado.valor = clamp(v > 0 ? v : estado.valor, L.min, L.max);
    }, 'valor');
    $('range-valor').addEventListener('input', function (e) { estado.valor = Number(e.target.value); interagiu(); desenhar(); });
    ligarCampo('campo-entrada', function (v, fim) {
      var msg = $('msg-entrada'), p = v / estado.valor;
      if (p >= entradaMin() && p <= ENTRADA_MAX) { estado.pct = p; msg.hidden = true; return; }
      if (!fim) return;
      estado.pct = clamp(p > 0 ? p : estado.pct, entradaMin(), ENTRADA_MAX);
      msg.hidden = false;
      msg.textContent = p < entradaMin()
        ? 'A entrada mínima costuma ser ' + Math.round(entradaMin() * 100) + '% para ' + ROT[estado.cat] + ' (convenção de mercado; cada banco define). Ajustamos.'
        : 'A entrada vai até ' + Math.round(ENTRADA_MAX * 100) + '% do valor. Ajustamos.';
    }, 'entrada');
    $('range-entrada').addEventListener('input', function (e) {
      estado.pct = Number(e.target.value) / estado.valor; $('msg-entrada').hidden = true; interagiu(); desenhar();
    });
    ligarPrazo();
    ligarBanco();
    $('btn-copiar').addEventListener('click', copiarLink);

    if (taxaPropria()) { $('det-taxa').open = true; $('campo-taxa-prop').value = String(estado.taxaProp).replace('.', ','); }
    $('campo-taxa-prop').addEventListener('input', function (e) { estado.taxaProp = lerNumero(e.target.value); mexeuTaxaProp(); desenhar('taxaprop'); });
    $('campo-taxa-prop').addEventListener('blur', function () { desenhar(); });
    $('campo-taxa-prop').addEventListener('keydown', function (e) { if (e.key === 'Enter') e.target.blur(); });

    ligarCampo('campo-conforto', function (v, fim) {
      if (v > 0) estado.conforto = v; else if (fim) estado.conforto = 0;
    }, 'conforto');
    ligarCampo('campo-extra', function (v, fim) { if (v > 0) estado.extra = v; else if (fim) estado.extra = 0; }, 'extra', mexeuAmort);
    ligarCampo('campo-unico', function (v, fim) { if (v > 0) estado.unico = v; else if (fim) estado.unico = 0; }, 'unico', mexeuAmort);
    $('range-quando').addEventListener('input', function (e) { estado.quando = Number(e.target.value); mexeuAmort(); desenhar(); });
    function abriuAm(e) { if (e.target.open && !abriuAmort) { abriuAmort = true; evento('abriu-amortizacao', { tipo: estado.cat }); } }
    $('det-amort').addEventListener('toggle', abriuAm);
    $('det-amsim').addEventListener('toggle', abriuAm);

    var dlg = $('dlg-confirma');
    function devolverFoco() { try { $('btn-cta').focus({ preventScroll: true }); } catch (e) { /* ignora */ } }
    function fechar() { if (typeof dlg.close === 'function') dlg.close(); else { dlg.removeAttribute('open'); devolverFoco(); } }
    $('btn-cta').addEventListener('click', function () {
      evento('abriu-confirmacao', { tipo: estado.cat, prazo: estado.prazo });
      if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
    });
    dlg.addEventListener('close', devolverFoco);
    $('btn-voltar').addEventListener('click', fechar);
    // Só o clique fora da caixa fecha (o preenchimento interno do diálogo também é o próprio elemento: conferimos pelas coordenadas).
    dlg.addEventListener('click', function (e) {
      if (e.target !== dlg) return;
      var r = dlg.getBoundingClientRect();
      var fora = e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
      if (fora) fechar();
    });
    desenhar();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar); else iniciar();
})();
