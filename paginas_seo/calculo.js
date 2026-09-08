// Gerado por gerador_veiculos.py (gerar_calculo_js) — não editar à mão
// sem também atualizar o lado Python e tests/test_calculo_js.mjs.
'use strict';

function unformatCurrency(val) { return typeof val === 'number' ? val : Number(String(val).replace(/\D/g, '')) / 100; }
function formatCurrency(val) { return (val).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function formatarReais(val) { return 'R$ ' + formatCurrency(val); }

function initMask(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    let rawVal = unformatCurrency(input.value);
    if (rawVal > 0) input.value = formatCurrency(rawVal);
    input.addEventListener('input', function (e) {
        let raw = unformatCurrency(e.target.value);
        e.target.value = formatCurrency(raw);
    });
}

// Só reinicia a animação de pulso quando o valor realmente muda — evita
// reiniciar em toda chamada de atualizarSimulacao(), inclusive quando
// nada mudou (lição do irmão: WCAG/prefers-reduced-motion já tratados no
// CSS via @media, isso aqui evita o pulso "nervoso" de re-disparar à toa).
function atualizarValor(id, texto) {
    const el = document.getElementById(id);
    if (!el || el.innerText === texto) return;
    el.innerText = texto;
    el.classList.remove('valor-pulse');
    void el.offsetWidth; // força reflow, senão o navegador não reinicia a animação
    el.classList.add('valor-pulse');
}

// --- Motor de cálculo (espelha gerador_veiculos.py) -------------------

function calcularPmtPrice(valorFinanciado, prazoMeses, taxaAm) {
    if (valorFinanciado <= 0 || prazoMeses <= 0) return 0;
    const i = taxaAm / 100;
    if (i === 0) return valorFinanciado / prazoMeses;
    const fator = Math.pow(1 + i, prazoMeses);
    return valorFinanciado * (i * fator) / (fator - 1);
}

function calcularIofVeiculo(valorFinanciado, prazoMeses) {
    if (valorFinanciado <= 0 || prazoMeses <= 0) return 0;
    const ALIQUOTA_FIXA = 0.0038, ALIQUOTA_DIARIA = 0.000082;
    const dias = Math.min(prazoMeses * 30, 365);
    return valorFinanciado * (ALIQUOTA_FIXA + ALIQUOTA_DIARIA * dias);
}

const TARIFA_REGISTRO_CONTRATO = 120.00;
const SEGURO_PRESTAMISTA_MENSAL = 0.00035;

function calcularCetVeiculo(valorFinanciado, prazoMeses, taxaAm) {
    if (valorFinanciado <= 0 || prazoMeses <= 0) return 0;
    const taxaMensal = taxaAm / 100;
    const pmt = calcularPmtPrice(valorFinanciado, prazoMeses, taxaAm);
    const iof = calcularIofVeiculo(valorFinanciado, prazoMeses);

    let saldo = valorFinanciado;
    const fluxo = [];
    for (let m = 0; m < prazoMeses; m++) {
        const juros = saldo * taxaMensal;
        const amortizacao = pmt - juros;
        const seguro = saldo * SEGURO_PRESTAMISTA_MENSAL;
        fluxo.push(pmt + seguro);
        saldo -= amortizacao;
    }
    const valorLiquidoRecebido = valorFinanciado - iof - TARIFA_REGISTRO_CONTRATO;
    const vpl = (r) => {
        let total = -valorLiquidoRecebido;
        for (let i = 0; i < fluxo.length; i++) total += fluxo[i] / Math.pow(1 + r, i + 1);
        return total;
    };
    let lo = 0, hi = 0.08;
    for (let i = 0; i < 60; i++) {
        const mid = (lo + hi) / 2;
        if (vpl(mid) > 0) lo = mid; else hi = mid;
    }
    const tirMensal = (lo + hi) / 2;
    return Math.round(((Math.pow(1 + tirMensal, 12) - 1) * 100) * 100) / 100;
}

function gerarTabelaAmortizacao(valorFinanciado, prazoMeses, taxaAm) {
    const taxaMensal = taxaAm / 100;
    const pmt = calcularPmtPrice(valorFinanciado, prazoMeses, taxaAm);
    let saldo = valorFinanciado;
    const linhas = [];
    for (let mes = 1; mes <= prazoMeses; mes++) {
        const juros = saldo * taxaMensal;
        const amortizacao = pmt - juros;
        saldo = Math.max(0, saldo - amortizacao);
        linhas.push({ mes, parcela: pmt, juros, amortizacao, saldo });
    }
    return linhas;
}

// Simula o mesmo financiamento (Tabela Price) com amortização extra
// recorrente: a cada `periodicidade` meses, abate `aporte` direto do
// saldo devedor (nunca deixando saldo negativo), mantendo a MESMA
// parcela fixa original (pmtFixo) — a folga vira prazo mais curto, não
// parcela menor. Espelha simularComAmortizacaoRecorrente do projeto
// irmão, mas sem o branch SAC/PRICE: financiamento de veículo (CDC) no
// Brasil só usa Tabela Price, não existe SAC nessa modalidade.
function simularComAmortizacaoRecorrente(valorFinanciado, prazoMeses, taxaAm, aporte, periodicidade, pmtFixo) {
    const taxaMensal = taxaAm / 100;
    let saldo = valorFinanciado, jurosTotal = 0, meses = 0;
    while (saldo > 0.005 && meses < prazoMeses) {
        meses++;
        const juros = saldo * taxaMensal;
        jurosTotal += juros;
        let amortizacaoBase = pmtFixo - juros;
        if (amortizacaoBase > saldo) amortizacaoBase = saldo;
        saldo -= amortizacaoBase;
        if (aporte > 0 && periodicidade > 0 && saldo > 0 && meses % periodicidade === 0) {
            const abate = Math.min(aporte, saldo);
            saldo -= abate;
        }
    }
    return { jurosTotal, meses };
}

function calcularRendaSugerida(parcela) {
    return parcela > 0 ? parcela / 0.30 : 0;
}

// Ranking só pra achar a posição do banco no mercado (posição neutra) —
// NUNCA usado pra montar uma lista de concorrentes com link. Cada banco
// usa a MESMA entradaPct (regra é por categoria, não por banco, nesta
// v1) e seu próprio prazoMax/taxaAm. cetAtual/bancoChaveAtual sobrescrevem
// a entrada do banco desta página no ranking, pra nunca mostrar dois CETs
// diferentes do mesmo banco na mesma tela (mesmo cuidado do Python).
//
// marcadorPct é interpolação linear do CET real contra o mínimo/máximo
// real da faixa (valor, não ranking) — espelha renderizar_faixa_mercado
// no Python; ver docstring de lá pro raciocínio completo (testado e
// revertido de "fração do ranking" no mesmo dia, a pedido do usuário:
// com todo marcador igualmente espaçado a barra perdia a noção de o
// quanto os bancos realmente se aproximam ou distanciam em taxa).
function calcularFaixaMercado(bancosCategoria, valorLive, prazoLive, entradaPct, cetAtual, bancoChaveAtual) {
    const ranking = bancosCategoria.map(b => {
        const prazoB = Math.min(prazoLive, b.prazoMax);
        const financiadoB = valorLive * (1 - entradaPct);
        const cet = (b.chave === bancoChaveAtual) ? cetAtual : calcularCetVeiculo(financiadoB, prazoB, b.taxaAm);
        return { chave: b.chave, cet };
    });
    ranking.sort((a, b) => a.cet - b.cet);
    const n = ranking.length;
    const cetMin = ranking[0].cet, cetMax = ranking[n - 1].cet;
    const spread = cetMax - cetMin;
    let marcadorPct = spread > 0 ? Math.round(((cetAtual - cetMin) / spread) * 100) : 50;
    marcadorPct = Math.max(2, Math.min(98, marcadorPct));
    return { cetMin, cetMax, marcadorPct };
}

function linhaTabelaHtml(l) {
    return '<tr class="border-b border-white/5"><td class="py-2 px-3">' + l.mes + '</td>' +
        '<td class="py-2 px-3 text-right">' + formatarReais(l.parcela) + '</td>' +
        '<td class="py-2 px-3 text-right text-amber-400">' + formatarReais(l.juros) + '</td>' +
        '<td class="py-2 px-3 text-right text-sky-400">' + formatarReais(l.amortizacao) + '</td>' +
        '<td class="py-2 px-3 text-right">' + formatarReais(l.saldo) + '</td></tr>';
}

// --- Orquestração da página individual (slider valor + prazo) ---------

function iniciarSimulador(dados) {
    const sliderValor = document.getElementById('slider_valor');
    const inputValor = document.getElementById('input_valor');
    const sliderPrazo = document.getElementById('slider_prazo');
    const labelPrazo = document.getElementById('label_prazo');
    const inputAmortizar = document.getElementById('input_amortizar');
    const sliderAmortizar = document.getElementById('slider_amortizar');
    const sliderPeriodicidade = document.getElementById('slider_periodicidade');
    const labelPeriodicidade = document.getElementById('label_periodicidade');
    if (!sliderValor || !sliderPrazo) return; // página sem simulador interativo

    initMask('input_valor');
    if (inputAmortizar) initMask('input_amortizar');

    function atualizar() {
        const valor = Math.max(dados.valorMin, Math.min(dados.valorMax, unformatCurrency(inputValor.value)));
        const prazo = Math.min(dados.prazoMaxBanco, Math.max(12, Number(sliderPrazo.value)));
        const entrada = valor * dados.entradaPct;
        const financiado = valor - entrada;
        const pmt = calcularPmtPrice(financiado, prazo, dados.taxaAm);
        const cet = calcularCetVeiculo(financiado, prazo, dados.taxaAm);
        const totalPago = pmt * prazo;
        const totalJuros = totalPago - financiado;
        const rendaSugerida = calcularRendaSugerida(pmt);

        atualizarValor('res_entrada', formatarReais(entrada));
        atualizarValor('res_financiado', formatarReais(financiado));
        atualizarValor('res_parcela', formatarReais(pmt));
        atualizarValor('res_cet', cet.toFixed(2).replace('.', ',') + '% a.a.');
        atualizarValor('res_total_pago', formatarReais(totalPago));
        atualizarValor('res_total_juros', formatarReais(totalJuros));
        atualizarValor('res_renda', formatarReais(rendaSugerida));
        labelPrazo.innerText = prazo + ' meses';

        const tabela = gerarTabelaAmortizacao(financiado, prazo, dados.taxaAm);
        const tbodyVisivel = document.getElementById('tabela_visivel');
        const tbodyResto = document.getElementById('tabela_resto');
        const blocoResto = document.getElementById('bloco_tabela_resto');
        const resumoResto = document.getElementById('resumo_tabela_resto');
        if (tbodyVisivel) tbodyVisivel.innerHTML = tabela.slice(0, 6).map(linhaTabelaHtml).join('');
        if (tbodyResto) tbodyResto.innerHTML = tabela.slice(6).map(linhaTabelaHtml).join('');
        if (blocoResto) blocoResto.hidden = tabela.length <= 6;
        if (resumoResto) resumoResto.innerText = 'Ver tabela completa (' + prazo + ' meses)';

        // Amortização extra recorrente (Zona "Valor a Amortizar"): a cada N
        // meses, abate um valor fixo do saldo devedor, mantendo a MESMA
        // parcela — o ganho vira prazo mais curto e menos juros pagos, não
        // parcela menor. Espelha a Zona B do projeto irmão (financiamento
        // imobiliário), sem o toggle SAC/PRICE porque CDC de veículo só
        // usa Tabela Price.
        if (inputAmortizar && sliderAmortizar && sliderPeriodicidade) {
            let aporte = unformatCurrency(inputAmortizar.value);
            let amortizacaoMaxima = Math.max(0, financiado);
            if (aporte > amortizacaoMaxima) {
                aporte = amortizacaoMaxima;
                inputAmortizar.value = formatCurrency(aporte);
            }
            sliderAmortizar.max = amortizacaoMaxima;
            sliderAmortizar.value = aporte;

            const periodicidade = parseInt(sliderPeriodicidade.value, 10) || 1;
            if (labelPeriodicidade) labelPeriodicidade.innerText = 'a cada ' + periodicidade + (periodicidade === 1 ? ' mês' : ' meses');

            const resultadoNovo = simularComAmortizacaoRecorrente(financiado, prazo, dados.taxaAm, aporte, periodicidade, pmt);
            const economiaJuros = Math.max(0, totalJuros - resultadoNovo.jurosTotal);
            const mesesEliminados = Math.max(0, prazo - resultadoNovo.meses);

            atualizarValor('res_economia', formatarReais(economiaJuros));
            let anosRestantes = Math.floor(mesesEliminados / 12), mesesRestantes = mesesEliminados % 12, textoTempo = '';
            if (anosRestantes > 0) textoTempo += anosRestantes + (anosRestantes === 1 ? ' Ano' : ' Anos');
            if (anosRestantes > 0 && mesesRestantes > 0) textoTempo += ' e ';
            if (mesesRestantes > 0 || (anosRestantes === 0 && mesesRestantes === 0)) textoTempo += mesesRestantes + (mesesRestantes === 1 ? ' Mês' : ' Meses');
            atualizarValor('res_impacto', textoTempo);
            const barNovoPrazo = document.getElementById('bar_novo_prazo');
            if (barNovoPrazo) barNovoPrazo.style.width = ((resultadoNovo.meses / prazo) * 100) + '%';
        }

        if (dados.bancosCategoria && dados.bancosCategoria.length) {
            const { cetMin, cetMax, marcadorPct } = calcularFaixaMercado(dados.bancosCategoria, valor, prazo, dados.entradaPct, cet, dados.bancoChave);
            const marcador = document.getElementById('faixa_marcador');
            const rotuloMin = document.getElementById('faixa_min');
            const rotuloMax = document.getElementById('faixa_max');
            const texto = document.getElementById('faixa_texto');
            const cetFmt = cet.toFixed(2).replace('.', ',');
            const cetMinFmt = cetMin.toFixed(2).replace('.', ',');
            const cetMaxFmt = cetMax.toFixed(2).replace('.', ',');
            if (marcador) { marcador.style.left = marcadorPct + '%'; marcador.title = dados.bancoNome + ': ' + cetFmt + '%'; }
            if (rotuloMin) rotuloMin.innerText = cetMinFmt + '% menor CET';
            if (rotuloMax) rotuloMax.innerText = cetMaxFmt + '% maior CET';
            if (texto) {
                const cta = '<a href="' + dados.linkAfiliado + '" target="_blank" rel="noopener sponsored" class="text-sky-400 underline hover:text-sky-300 block mt-2 font-semibold">' +
                    (marcadorPct <= 15 ? 'Falar com um especialista →' : 'É esse trabalho que fazemos por você, sem custo →') + '</a>';
                texto.innerHTML = (marcadorPct <= 15
                    ? ('O ' + dados.bancoNome + ' está entre as condições <strong class="text-sky-400">mais competitivas</strong> que acompanhamos (' + cetFmt + '% de CET). Vale confirmar essa condição e agilizar a aprovação sem custo.')
                    : ('Nas condições simuladas, o CET no mercado costuma variar entre <strong class="text-sky-400">' + cetMinFmt + '%</strong> e <strong class="text-sky-400">' + cetMaxFmt + '%</strong> — aqui no ' + dados.bancoNome + ' está em ' + cetFmt + '%.')
                ) + cta;
            }
        }
    }

    sliderValor.addEventListener('input', function () { inputValor.value = formatCurrency(Number(this.value)); atualizar(); });
    inputValor.addEventListener('blur', function () { const val = unformatCurrency(this.value); sliderValor.value = val; atualizar(); });
    sliderPrazo.addEventListener('input', atualizar);
    if (sliderAmortizar) sliderAmortizar.addEventListener('input', function () { inputAmortizar.value = formatCurrency(Number(this.value)); atualizar(); });
    if (inputAmortizar) inputAmortizar.addEventListener('blur', function () { const val = unformatCurrency(this.value); sliderAmortizar.value = val; atualizar(); });
    if (sliderPeriodicidade) sliderPeriodicidade.addEventListener('input', atualizar);
    atualizar();
}
