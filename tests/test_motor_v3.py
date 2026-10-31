"""Motor v3 (31/out/2026): projeção Price, série por banco, páginas mensais,
metodologia, resposta direta no hub e links entre vizinhas."""
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gerador_veiculos import (
    MESES_INDEXAVEIS_MENSAL, SLUG_INDICE_MENSAL, calcular_pmt_price, carregar_historico, gerar_tabela_amortizacao,
    posicao_no_mercado, projecao_price, serie_do_banco, slug_mes,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.isdir(PASTA)


def _ler(nome):
    return open(os.path.join(PASTA, nome), encoding="utf-8").read()


def test_projecao_price_fecha_com_a_tabela_de_amortizacao():
    linhas = projecao_price(40_000, 48, 1.9)
    tabela = gerar_tabela_amortizacao(40_000, 48, 1.9)
    ultimo = linhas[-1]
    assert ultimo["mes"] == 48 and ultimo["saldo"] < 0.01
    assert ultimo["juros"] == pytest.approx(sum(l["juros"] for l in tabela), rel=1e-9)
    assert ultimo["parcelas_pagas"] == pytest.approx(calcular_pmt_price(40_000, 48, 1.9) * 48, rel=1e-9)
    assert [x["mes"] for x in linhas] == [12, 24, 36, 48]
    assert [x["mes"] for x in projecao_price(10_000, 12, 2.0)] == [6, 12]


def test_posicao_no_mercado_nao_cita_concorrente():
    ranking = [{"banco": b, "cet": c} for b, c in (("A", 20.0), ("B", 22.0), ("C", 24.0), ("D", 26.0))]
    frase = posicao_no_mercado(ranking, 22.0)
    assert "2ª posição entre 4 bancos" in frase and "mediana" in frase
    assert posicao_no_mercado(ranking[:2], 20.0) == ""


def test_serie_do_banco_tem_no_maximo_12_meses_em_ordem():
    pontos = serie_do_banco(carregar_historico(), "Caixa")
    assert 3 <= len(pontos) <= 12
    assert [m for m, _ in pontos] == sorted(m for m, _ in pontos)


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_paginas_individuais_tem_blocos_proprios_e_continuam_indexaveis():
    nome = "financiamento-carro-novo-banco-do-brasil-60-mil-48-meses.html"
    html = _ler(nome)
    assert "Como a dívida evolui ao longo do contrato" in html
    assert "Taxa do Banco do Brasil nos últimos meses" in html
    assert "Valores vizinhos no Banco do Brasil" in html
    assert "posição entre" in html
    assert 'name="robots" content="noindex' not in html
    assert f"/{nome[:-5]}</loc>" in _ler("sitemap.xml")
    tab = lambda h: re.search(r"<tbody>(.*?)</tbody>", h[h.index("Como a dívida evolui"):], re.S).group(1)
    assert tab(html) != tab(_ler("financiamento-carro-novo-banco-do-brasil-80-mil-48-meses.html"))


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_paginas_mensais_existem_com_indexacao_certa():
    meses = sorted({r["mes_referencia"] for r in carregar_historico()})
    assert len(meses) >= 12
    sitemap = _ler("sitemap.xml")
    for mes in meses:
        html = _ler(slug_mes(mes) + ".html")
        recente = mes in meses[-MESES_INDEXAVEIS_MENSAL:]
        assert ('name="robots" content="noindex,follow"' not in html) == recente, mes
        assert (f"/{slug_mes(mes)}</loc>" in sitemap) == recente, mes
        assert "<table" in html
    assert f"/{SLUG_INDICE_MENSAL}</loc>" in sitemap


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_pagina_mensal_faq_visivel_igual_ao_json_ld():
    html = _ler(slug_mes(sorted({r["mes_referencia"] for r in carregar_historico()})[-1]) + ".html")
    blocos = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    faq = next(json.loads(b) for b in blocos if '"FAQPage"' in b)
    for q in faq["mainEntity"]:
        assert q["name"] in html and q["acceptedAnswer"]["text"] in html


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_metodologia_hub_footer_e_llms():
    met = _ler("metodologia.html")
    assert "401101" in met and "TIR" in met and "contato@datalabglobal.com" in met and "0,0082%" in met
    assert "/metodologia</loc>" in _ler("sitemap.xml")
    hub = _ler("hub-banco-do-brasil-carro-novo.html")
    assert re.search(r"Taxa do Banco do Brasil hoje para carro novo: \d+,\d{2}% ao mês", hub)
    assert 'content="Taxa do Banco do Brasil hoje' in hub
    assert 'href="/metodologia"' in _ler("index.html")
    assert "taxas-financiamento-veiculos" in _ler("llms.txt")
