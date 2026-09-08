// Teste de paridade JS <-> Python: compara a saída de calculo.js (o
// motor que roda no navegador) com valores de referência calculados
// pelo motor Python (gerador_veiculos.py) para os MESMOS cenários.
//
// Por que isso existe: o projeto irmão duplica a fórmula à mão em Python
// e em JavaScript sem nenhuma trava automatizada — uma divergência entre
// os dois já causou um bug real lá ("Comparação com o Mercado" congelada
// no cenário padrão). Aqui, calculo.js é um arquivo único (não repetido
// em cada página), o que já reduz o risco, mas ainda existem DUAS
// implementações da mesma fórmula (Python gera o HTML estático, JS
// recalcula ao vivo) — este teste é a trava que falta pro irmão.
//
// Os valores de referência abaixo foram gerados rodando o motor Python
// pros mesmos 5 cenários (ver comando no histórico do projeto: python -c
// "from gerador_veiculos import ..." para cada caso). Se a fórmula mudar
// de um lado, atualize os dois lados e regere esses valores de novo.
//
// Rodar com: node tests/test_calculo_js.mjs
// (precisa que paginas_seo/calculo.js já exista — rode
// `python gerador_veiculos.py` antes se ainda não gerou o site.)

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import vm from 'node:vm';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const caminhoCalculoJs = path.join(__dirname, '..', 'paginas_seo', 'calculo.js');

let codigoJs;
try {
    codigoJs = readFileSync(caminhoCalculoJs, 'utf-8');
} catch (e) {
    console.error(`Não achei ${caminhoCalculoJs} — rode "python gerador_veiculos.py" antes deste teste.`);
    process.exit(1);
}

const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(codigoJs, sandbox);

const CASOS = [
    { financiado: 20000, prazo: 48, taxaAm: 1.86, pmt: 633.601211, iof: 674.600000, cet: 28.240000 },
    { financiado: 20000, prazo: 12, taxaAm: 1.86, pmt: 1874.969115, iof: 666.400000, cet: 35.320000 },
    { financiado: 64000, prazo: 48, taxaAm: 2.07, pmt: 2116.348924, iof: 2158.720000, cet: 31.170000 },
    { financiado: 5600, prazo: 24, taxaAm: 2.46, pmt: 311.729818, iof: 188.888000, cet: 42.840000 },
    { financiado: 30000, prazo: 60, taxaAm: 3.35, pmt: 1166.535984, iof: 1011.900000, cet: 52.440000 },
];

const TOLERANCIA = 0.02; // 2 centavos / 0,02 p.p. — folga de arredondamento, não de fórmula
let falhas = 0;

function assertProximo(rotulo, esperado, obtido, tol = TOLERANCIA) {
    const diff = Math.abs(esperado - obtido);
    if (diff > tol) {
        console.error(`FALHOU: ${rotulo} — esperado ${esperado}, obtido ${obtido} (diff ${diff.toFixed(4)})`);
        falhas++;
    } else {
        console.log(`ok: ${rotulo} (${obtido})`);
    }
}

for (const c of CASOS) {
    const pmt = sandbox.calcularPmtPrice(c.financiado, c.prazo, c.taxaAm);
    const iof = sandbox.calcularIofVeiculo(c.financiado, c.prazo);
    const cet = sandbox.calcularCetVeiculo(c.financiado, c.prazo, c.taxaAm);
    const rotulo = `financiado=${c.financiado} prazo=${c.prazo} taxa=${c.taxaAm}`;
    assertProximo(`pmt(${rotulo})`, c.pmt, pmt);
    assertProximo(`iof(${rotulo})`, c.iof, iof);
    assertProximo(`cet(${rotulo})`, c.cet, cet);
}

// Sanidade adicional: gerarTabelaAmortizacao soma as amortizações até
// fechar (aprox) o valor financiado, e a parcela de cada linha bate com
// calcularPmtPrice (regressão pro bug de "parcela mudando ao longo do
// prazo" — Price tem que ser sempre fixa).
{
    const tabela = sandbox.gerarTabelaAmortizacao(20000, 24, 1.86);
    const pmtEsperado = sandbox.calcularPmtPrice(20000, 24, 1.86);
    const somaAmortizacao = tabela.reduce((s, l) => s + l.amortizacao, 0);
    const todasParcelasIguais = tabela.every(l => Math.abs(l.parcela - pmtEsperado) < 0.001);
    assertProximo('tabela: soma das amortizações == valor financiado', 20000, somaAmortizacao, 0.5);
    if (!todasParcelasIguais) {
        console.error('FALHOU: gerarTabelaAmortizacao não manteve a parcela fixa em todas as linhas (Price)');
        falhas++;
    } else {
        console.log('ok: gerarTabelaAmortizacao mantém parcela fixa (Price)');
    }
    if (tabela.length !== 24) {
        console.error(`FALHOU: gerarTabelaAmortizacao devolveu ${tabela.length} linhas, esperado 24`);
        falhas++;
    } else {
        console.log('ok: gerarTabelaAmortizacao devolve uma linha por mês');
    }
}

if (falhas > 0) {
    console.error(`\n${falhas} verificação(ões) falhou/falharam.`);
    process.exit(1);
}
console.log('\nTodas as verificações de paridade JS <-> Python passaram.');
