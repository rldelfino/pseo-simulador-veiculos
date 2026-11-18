"""/analise-do-mes (18/nov/2026): último mês do Banco Central frente ao mesmo mês do ano anterior, banco a banco.
Tudo vem da série; a página muda sozinha a cada atualização. Os botões de citação levam o link em HTML."""
import csv
import os
import re

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.exists(os.path.join(PASTA, "analise-do-mes.html"))


def _ler(nome):
    return open(os.path.join(PASTA, nome), encoding="utf-8").read()


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_analise_do_mes_esta_no_sitemap_e_tem_o_basico():
    html = _ler("analise-do-mes.html")
    assert "/analise-do-mes</loc>" in _ler("sitemap.xml")
    assert html.count("<h1") == 1 and 'rel="canonical" href="https://veiculos.datalabglobal.com/analise-do-mes"' in html
    assert "noindex" not in html.lower()
    assert "<table" in html and "aria-label=" in html and html.count('scope="row"') >= 3


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_analise_do_mes_bate_com_a_serie_do_banco_central():
    """Cada banco da tabela tem as taxas do mesmo mês do ano anterior e do último mês, iguais às do CSV."""
    with open(os.path.join(RAIZ, "historico_taxas.csv"), encoding="utf-8") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    meses = sorted({r["mes_referencia"] for r in linhas})
    ult = meses[-1]
    ant = f"{int(ult[:4]) - 1}{ult[4:]}"
    html = _ler("analise-do-mes.html")
    tabela = re.search(r"<tbody>(.*?)</tbody>", html, re.S).group(1)
    achados = 0
    for r in linhas:
        if r["mes_referencia"] not in (ult, ant):
            continue
        v = f"{float(r['taxa_am']):.2f}".replace(".", ",")
        assert f">{v}<" in tabela, (r["banco"], r["mes_referencia"], v)
        achados += 1
    assert achados >= 6


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_botoes_de_citacao_copiam_o_link_em_html_nas_tres_paginas():
    for nome in ("analise-do-mes.html", "imprensa.html", "dados-abertos.html"):
        html = _ler(nome)
        assert "data-copiar=" in html and "Copiar link em HTML" in html and "Copiar citação" in html, nome
        assert re.search(r'data-copiar="&lt;a href=&quot;https://veiculos\.datalabglobal\.com/[a-z-]+&quot;&gt;Datalab Global&lt;/a&gt;"', html), nome
        assert "AAAA-MM-DD" in html


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_imprensa_e_dados_abertos_linkam_a_analise():
    assert 'href="analise-do-mes"' in _ler("imprensa.html")
    assert 'href="analise-do-mes"' in _ler("dados-abertos.html")
