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


# ---- motor v3b: renda, llms-full, ItemList/Dataset, medição ----
import gerador_veiculos as gv  # noqa: E402


def test_renda_minima_cai_com_mais_entrada_e_prazo_maior():
    r20 = gv.renda_minima("novo", 80_000, 0.20, 48)
    r50 = gv.renda_minima("novo", 80_000, 0.50, 48)
    r60 = gv.renda_minima("novo", 80_000, 0.20, 60)
    assert r50["renda"] < r20["renda"] and r60["renda"] < r20["renda"]
    assert r20["renda"] >= r20["parcela"] / 0.30 - 50


def test_entradas_respeitam_o_minimo_da_categoria():
    assert gv._entradas_da_categoria("novo") == [0.20, 0.30, 0.50]
    assert gv._entradas_da_categoria("usado") == [0.30, 0.50]
    assert gv._entradas_da_categoria("moto") == [0.30, 0.50]


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_paginas_de_renda_no_sitemap_com_faq_igual_ao_json_ld():
    sitemap = _ler("sitemap.xml")
    total = 0
    for cat in gv.CATEGORIAS:
        for v in gv.VALORES_POR_CATEGORIA[cat]:
            slug = gv.slug_renda(cat, v)
            html = _ler(slug + ".html")
            assert f"/{slug}</loc>" in sitemap and 'content="noindex' not in html
            blocos = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
            faq = next(json.loads(b) for b in blocos if '"FAQPage"' in b)
            for q in faq["mainEntity"]:
                assert q["name"] in html and q["acceptedAnswer"]["text"] in html
            total += 1
    assert total == 16 and f"/{gv.SLUG_INDICE_RENDA}</loc>" in sitemap
    moto = _ler(gv.slug_renda("moto", 18_000) + ".html")
    assert "20% de entrada" not in moto  # moto só aceita a partir de 30%


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_llms_full_itemlist_dataset_e_medicao_desligada():
    full = _ler("llms-full.txt")
    assert "Taxas usadas nas simulações hoje" in full and "% ao mês" in full and "401101" in full
    comp = _ler(gv.slug_comparacao("novo", 100_000, 48) + ".html")
    lista = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', comp, re.S) if '"ItemList"' in b]
    assert lista and all("url" not in it for it in lista[0]["itemListElement"])
    mensal = _ler(slug_mes(sorted({r["mes_referencia"] for r in carregar_historico()})[-1]) + ".html")
    assert '"Dataset"' in mensal and "temporalCoverage" in mensal
    assert gv.UMAMI_WEBSITE_ID
    home = _ler("index.html")
    assert f'data-website-id="{gv.UMAMI_WEBSITE_ID}"' in home and 'data-domains="veiculos.datalabglobal.com"' in home
    assert "/medicao.js" in home and os.path.exists(os.path.join(PASTA, "medicao.js"))
    assert "ftudo.com" in _ler("medicao.js") and "cta-financiatudo" in _ler("medicao.js")
    assert "cloud.umami.is" in _ler("_headers") and "gateway.umami.is" in _ler("_headers")


def test_tags_de_medicao_so_com_id_e_seletor_do_parceiro(monkeypatch, tmp_path):
    monkeypatch.setattr(gv, "UMAMI_WEBSITE_ID", "")
    assert gv.tags_medicao() == []
    monkeypatch.setattr(gv, "UMAMI_WEBSITE_ID", "abc-123")
    tags = "".join(gv.tags_medicao())
    assert 'data-website-id="abc-123"' in tags and 'data-do-not-track="true"' in tags and "/medicao.js" in tags
    assert "abc-123" in gv.render_head("T", "d", "https://x/", [])
    gv.gerar_medicao_js(str(tmp_path))
    js = (tmp_path / "medicao.js").read_text(encoding="utf-8")
    assert "ftudo.com" in js and "cta-financiatudo" in js and "usou-simulador" in js


# ---- guias de 31/out/2026 ----
GUIAS_NOVOS = ("aprenda-quitacao-antecipada-financiamento-veiculo", "aprenda-portabilidade-financiamento-veiculo",
               "aprenda-score-e-taxa-financiamento-veiculo", "aprenda-entrada-ideal-financiamento-veiculo")


def test_numeros_dos_guias_sao_coerentes():
    assert gv._SALDO_Q < gv._RESTANTE_Q  # o desconto de juros existe
    assert gv._PMT_P2 < gv._PMT_P1 and gv._PMT_S2 > gv._PMT_S1
    assert abs(gv._saldo_apos(40_000, 48, 2.0, 0) - 40_000) < 0.01 and gv._saldo_apos(40_000, 48, 2.0, 48) == 0


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_guias_novos_no_sitemap_hub_e_com_fonte():
    sitemap, hub = _ler("sitemap.xml"), _ler("aprenda.html")
    for slug in GUIAS_NOVOS:
        html = _ler(slug + ".html")
        assert f"/{slug}</loc>" in sitemap and f'href="{slug}"' in hub
        if slug != GUIAS_NOVOS[3]:  # o da entrada só traz contas, sem regra legal a citar
            assert "Fonte" in html
    assert "art. 52, § 2º" in _ler(GUIAS_NOVOS[0] + ".html")
    assert "Resolução CMN 4.292/2013" in _ler(GUIAS_NOVOS[1] + ".html")
    assert "Lei 12.414/2011" in _ler(GUIAS_NOVOS[2] + ".html")


def test_pagina_de_dados_abertos_aponta_para_o_kaggle():
    import os as _os
    caminho = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "paginas_seo", "dados-abertos.html")
    if not _os.path.exists(caminho):
        import pytest as _pytest
        _pytest.skip("paginas_seo/ não gerada")
    html = open(caminho, encoding="utf-8").read()
    assert html.count("https://www.kaggle.com/datasets/rodolfodelfino/") >= 2  # link visível + sameAs do Dataset


def test_titulos_dos_hubs_trazem_taxa_e_cabem_em_60_caracteres():
    import glob as _glob, os as _os, re as _re
    pasta = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "paginas_seo")
    hubs = _glob.glob(_os.path.join(pasta, "hub-*.html"))
    if not hubs:
        import pytest as _pytest
        _pytest.skip("paginas_seo/ não gerada")
    for f in hubs:
        t = _re.search(r"<title>(.*?)</title>", open(f, encoding="utf-8").read()).group(1)
        assert len(t) <= 60 and t.lower().startswith("taxa"), (f, t)


def test_home_tem_tabela_de_taxas_do_dia_igual_aos_hubs():
    import os as _os, re as _re
    raiz = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    caminho = _os.path.join(raiz, "paginas_seo", "index.html")
    if not _os.path.exists(caminho):
        import pytest as _pytest
        _pytest.skip("paginas_seo/ não gerada")
    html = open(caminho, encoding="utf-8").read()
    assert html.count("<table") >= 2 and "hoje, por banco" in html
    # sem tabelas repetidas: cada <tbody> aparece uma vez
    corpos = _re.findall(r"<tbody>(.*?)</tbody>", html, _re.S)
    assert len(corpos) == len(set(corpos))
    # a taxa de um banco na home é a mesma do hub dele
    m = _re.search(r'<a href="(hub-[a-z0-9-]+)" class="hover:text-sky-400">([^<]+)</a></th><td[^>]*>([\d,]+%)', html)
    hub = open(_os.path.join(raiz, "paginas_seo", m.group(1) + ".html"), encoding="utf-8").read()
    assert m.group(3) in hub


# ---- hubs/comparadores v3c: bloco "Mais sobre", WebPage JSON-LD e frase de resposta direta ----
def _pasta_gerada():
    import os as _os
    p = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "paginas_seo")
    if not _os.path.isdir(p):
        import pytest as _pytest
        _pytest.skip("paginas_seo/ não gerada")
    return p


def _json_ld(html):
    import json as _json, re as _re
    return [_json.loads(b) for b in _re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, _re.S)]


def test_hubs_tem_bloco_mais_sobre_com_links_que_existem():
    import glob as _glob, os as _os, re as _re
    pasta = _pasta_gerada()
    hubs = _glob.glob(_os.path.join(pasta, "hub-*.html"))
    assert len(hubs) >= 30
    for f in hubs:
        html = open(f, encoding="utf-8").read()
        assert "Mais sobre " in html, f
        bloco = html[html.index("Mais sobre "):]
        bloco = bloco[:bloco.index("</section>")]
        hrefs = _re.findall(r'href="([^"]+)"', bloco)
        assert len(hrefs) >= 7, f
        for h in hrefs:
            assert _os.path.exists(_os.path.join(pasta, h + ".html")), (f, h)


def test_webpage_json_ld_em_hubs_comparadores_e_home_sem_duplicar():
    import glob as _glob, os as _os
    pasta = _pasta_gerada()
    paginas = _glob.glob(_os.path.join(pasta, "hub-*.html")) + _glob.glob(_os.path.join(pasta, "comparador-*.html")) + [_os.path.join(pasta, "index.html")]
    assert len(paginas) >= 34
    for f in paginas:
        blocos = _json_ld(open(f, encoding="utf-8").read())
        webpages = [b for b in blocos if b.get("@type") == "WebPage"]
        assert len(webpages) == 1, f
        w = webpages[0]
        assert w["url"].startswith("https://veiculos.datalabglobal.com") and w["name"] and w["dateModified"]
        assert w["isPartOf"]["@type"] == "WebSite" and w["publisher"]["@id"] == "https://www.datalabglobal.com/#organization"


def test_comparador_tem_frase_de_resposta_igual_aos_dados_da_tabela():
    import os as _os, re as _re, html as _html
    from bancos_veiculos import bancos_para_categoria, corrigir_concordancia
    pasta = _pasta_gerada()
    for categoria, arquivo in (("novo", "comparador-carro-novo"), ("usado", "comparador-carro-usado"), ("moto", "comparador-moto")):
        caminho = _os.path.join(pasta, arquivo + ".html")
        if not _os.path.exists(caminho):
            continue
        pagina = _html.unescape(open(caminho, encoding="utf-8").read())
        bancos = sorted(bancos_para_categoria(categoria).values(), key=lambda d: (d["taxa_am"], d["nome_exibicao"]))
        fmt = lambda v: f"{v:.2f}".replace(".", ",") + "%"
        esperado_menor = corrigir_concordancia(f"é a do {bancos[0]['nome_exibicao']} ({fmt(bancos[0]['taxa_am'])} ao mês)")
        esperado_maior = corrigir_concordancia(f"a maior, a do {bancos[-1]['nome_exibicao']} ({fmt(bancos[-1]['taxa_am'])})")
        assert f"entre os {len(bancos)} bancos que acompanhamos" in pagina, arquivo
        assert esperado_menor in pagina and esperado_maior in pagina, arquivo
        assert _re.search(r"Em \d{2}/\d{2}/\d{4}, a menor taxa de financiamento de", pagina)
        # os mesmos números aparecem na lista de bancos da página
        assert fmt(bancos[0]["taxa_am"]).replace("%", "") in pagina
