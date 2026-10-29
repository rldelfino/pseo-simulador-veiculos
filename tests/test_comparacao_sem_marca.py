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


# ---------------------------------------------------------------------------
# Histórico de taxas, comparadores com evolução e dados abertos
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_dados_abertos_batem_com_o_historico_e_so_tem_bancos_conhecidos():
    import csv
    from bancos_veiculos import BANCOS_VEICULOS
    from historico_taxas_veiculos import ler_historico
    hist = ler_historico()
    assert hist, "historico_taxas.csv vazio"
    assert {r["banco"] for r in hist} <= set(BANCOS_VEICULOS)
    with open(os.path.join(PASTA_SAIDA, "dados", "taxas-financiamento-veiculos.csv"), encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    assert len(linhas) == len(hist)
    for l in linhas:
        am, aa = float(l["taxa_juros_am_pct"]), float(l["taxa_juros_aa_pct"])
        assert 0.2 <= am <= 6.0 and 3.0 <= aa <= 70.0
        assert aa > am  # taxa anual composta é sempre maior que a mensal
    for nome in ("taxas-financiamento-veiculos.json", "datapackage.json", "README.md"):
        assert os.path.isfile(os.path.join(PASTA_SAIDA, "dados", nome)), nome


def test_historico_so_tem_meses_fechados():
    from datetime import date
    from historico_taxas_veiculos import ler_historico
    hoje = date.today()
    mes_atual = f"{hoje.year:04d}-{hoje.month:02d}"
    assert all(r["mes_referencia"] < mes_atual for r in ler_historico())


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_pagina_dados_abertos_tem_schema_dataset_e_esta_no_sitemap():
    import json
    html = open(os.path.join(PASTA_SAIDA, "dados-abertos.html"), encoding="utf-8").read()
    blocos = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)]
    ds = [b for b in blocos if b.get("@type") == "Dataset"]
    assert ds and ds[0]["license"] and ds[0]["distribution"] and ds[0]["temporalCoverage"]
    assert "/dados-abertos</loc>" in open(os.path.join(PASTA_SAIDA, "sitemap.xml"), encoding="utf-8").read()


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
@pytest.mark.parametrize("categoria", ["carro-novo", "carro-usado", "moto"])
def test_comparador_tem_mes_no_titulo_evolucao_so_com_bancos_da_categoria_e_faq(categoria):
    html = open(os.path.join(PASTA_SAIDA, f"comparador-{categoria}.html"), encoding="utf-8").read()
    titulo = re.search(r"<title>(.*?)</title>", html).group(1)
    assert len(titulo) <= 60 and re.search(r"[a-z]{3}/\d{4}", titulo), titulo
    assert "Como as taxas evoluíram" in html and "maior queda na taxa média contratada" in html
    if categoria != "moto":  # Honda e Yamaha só financiam moto
        assert "Banco Honda" not in html.split("Como as taxas evoluíram")[1].split("</table>")[0]


def test_resumo_historico_filtra_por_categoria_e_calcula_variacao():
    from gerador_veiculos import resumo_historico
    h = []
    for mes, honda, caixa in (("2026-01", 2.0, 1.5), ("2026-02", 2.4, 1.2)):
        h += [{"mes_referencia": mes, "inicio_periodo": mes + "-20", "fim_periodo": mes + "-28", "banco": "Banco Honda", "taxa_am": honda, "taxa_aa": 30.0},
              {"mes_referencia": mes, "inicio_periodo": mes + "-20", "fim_periodo": mes + "-28", "banco": "Caixa", "taxa_am": caixa, "taxa_aa": 20.0}]
    novo = resumo_historico(h, "novo")
    assert [x["banco"] for x in novo["linhas"]] == ["Caixa"]  # Honda não aplica a carro novo
    assert novo["maior_queda"]["variacao"] == pytest.approx(-0.3)
    moto = resumo_historico(h, "moto")
    assert {x["banco"] for x in moto["linhas"]} == {"Banco Honda", "Caixa"} and moto["maior_alta"]["banco"] == "Banco Honda"
    assert resumo_historico(h[:2], "novo") is None
