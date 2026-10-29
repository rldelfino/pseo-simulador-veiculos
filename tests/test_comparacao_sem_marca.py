"""
Páginas de comparação sem marca de banco (financiamento-{categoria}-{valor}-
mil-{prazo}-meses) — ver gerar_paginas_comparacao em gerador_veiculos.py
(auditoria de SEO, 29/out/2026).
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bancos_veiculos import bancos_para_categoria, entrada_minima
from gerador_veiculos import (
    CATEGORIAS, MIN_BANCOS_COMPARACAO, PRAZOS_MESES, VALORES_POR_CATEGORIA,
    calcular_cet_veiculo, calcular_pmt_price, linhas_comparacao, pagina_comparacao_existe, slug_comparacao,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_SAIDA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.isdir(PASTA_SAIDA)


def _todas():
    return [(c, v, p) for c in CATEGORIAS for v in VALORES_POR_CATEGORIA[c] for p in PRAZOS_MESES if pagina_comparacao_existe(c, v, p)]


def test_slug_nao_colide_com_slug_de_banco():
    assert slug_comparacao("novo", 60_000, 48) == "financiamento-carro-novo-60-mil-48-meses"
    assert slug_comparacao("moto", 8_000, 12) == "financiamento-moto-8-mil-12-meses"


def test_comparacao_nunca_inclui_banco_com_prazo_menor_que_o_pedido():
    for c, v, p in _todas():
        for x in linhas_comparacao(c, v, p):
            assert bancos_para_categoria(c)[x["banco"]]["prazo_max"] >= p


def test_minimo_de_bancos_por_pagina():
    for c, v, p in _todas():
        assert len(linhas_comparacao(c, v, p)) >= MIN_BANCOS_COMPARACAO


def test_linhas_ordenadas_por_cet_e_batem_com_calculo_direto():
    linhas = linhas_comparacao("novo", 60_000, 48)
    assert [x["cet"] for x in linhas] == sorted(x["cet"] for x in linhas)
    x = linhas[0]
    financiado = 60_000 * (1 - entrada_minima("novo"))
    taxa_am = bancos_para_categoria("novo")[x["banco"]]["taxa_am"]
    assert x["parcela"] == pytest.approx(calcular_pmt_price(financiado, 48, taxa_am))
    assert x["cet"] == pytest.approx(calcular_cet_veiculo(financiado, 48, taxa_am))


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_paginas_existem_estao_no_sitemap_e_tem_meta_dentro_do_limite():
    sitemap = open(os.path.join(PASTA_SAIDA, "sitemap.xml"), encoding="utf-8").read()
    assert "/financiamento-veiculos</loc>" in sitemap
    titulos = set()
    for c, v, p in _todas():
        slug = slug_comparacao(c, v, p)
        html = open(os.path.join(PASTA_SAIDA, slug + ".html"), encoding="utf-8").read()
        assert f"/{slug}</loc>" in sitemap, slug
        t = re.search(r"<title>(.*?)</title>", html).group(1)
        d = re.search(r'name="description" content="(.*?)"', html).group(1)
        assert len(t) <= 60 and len(d) <= 160 and not d.endswith(("...", "…")), (t, d)
        titulos.add(t)
    assert len(titulos) == len(_todas()) > 70
