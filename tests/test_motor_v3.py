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
def test_paginas_individuais_tem_blocos_proprios_mas_ficam_fora_do_indice():
    nome = "financiamento-carro-novo-banco-do-brasil-60-mil-48-meses.html"
    html = _ler(nome)
    assert "Como a dívida evolui ao longo do contrato" in html
    assert "Taxa do Banco do Brasil nos últimos meses" in html
    assert "Valores vizinhos no Banco do Brasil" in html
    assert "posição entre" in html
    # 13/nov/2026: a grade banco x valor x prazo saiu do índice (ver
    # PAGINAS_VALOR_INDEXAVEIS): continua no ar, com noindex,follow e fora do sitemap.
    assert 'name="robots" content="noindex,follow"' in html
    assert f"/{nome[:-5]}</loc>" not in _ler("sitemap.xml")
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


# ---- feed Atom, /atualizacoes e 'Como citar' (05/11/2026) ----
def _snap(data, taxas):
    return [{"data_referencia": data, "banco": b, "taxa_am": v, "taxa_aa": round(((1 + v / 100) ** 12 - 1) * 100, 2)} for b, v in taxas.items()]


def test_historico_semanal_idempotente_e_limitado_a_26_semanas(tmp_path):
    caminho = str(tmp_path / "hist.csv")
    bancos = {"Caixa": {"taxa_am": 1.01, "taxa_aa": 12.8}, "Banco Pan": {"taxa_am": 2.85, "taxa_aa": 40.1}}
    registrar = lambda d: gv.registrar_snapshot_semanal(d, caminho=caminho, bancos=bancos)
    registrar("2026-01-05")
    antes = open(caminho, encoding="utf-8").read()
    registrar("2026-01-05")  # mesma data: não muda nada
    assert open(caminho, encoding="utf-8").read() == antes
    from datetime import date, timedelta
    for k in range(1, 30):
        registrar((date(2026, 1, 5) + timedelta(weeks=k)).isoformat())
    linhas = gv.ler_historico_semanal(caminho)
    assert len({r["data_referencia"] for r in linhas}) == gv.SEMANAS_NO_HISTORICO
    assert min(r["data_referencia"] for r in linhas) > "2026-01-05"
    assert antes.splitlines()[0] == "data_referencia;banco;taxa_am;taxa_aa"


def test_atualizacoes_noindex_com_1_snapshot_e_indexavel_com_2(tmp_path):
    um = _snap("2026-11-02", {"Caixa": 1.01, "Banco Pan": 2.85})
    urls = gv.gerar_pagina_atualizacoes(str(tmp_path), "2026-11-02", um)
    html = (tmp_path / "atualizacoes.html").read_text(encoding="utf-8")
    assert urls == [] and 'name="robots" content="noindex,follow"' in html and "Primeira medição" in html
    dois = um + _snap("2026-11-09", {"Caixa": 1.05, "Banco Pan": 2.80})
    urls = gv.gerar_pagina_atualizacoes(str(tmp_path), "2026-11-09", dois)
    html = (tmp_path / "atualizacoes.html").read_text(encoding="utf-8")
    assert urls == [f"{gv.DOMINIO}/atualizacoes"] and "noindex" not in html
    assert "+0,04 p.p." in html and "−0,05 p.p." in html  # Caixa sobe 0,04; Pan cai 0,05
    assert "maior alta: Caixa" in html and "maior queda: Banco Pan" in html
    assert "caiu" not in html.split("<h1")[1][:600] or "p.p. frente" in html  # sem sinal duplicado em "caiu"


def test_feed_atom_valido_com_entradas_mensais_e_semanais(tmp_path):
    import xml.etree.ElementTree as ET
    sem = _snap("2026-10-26", {"Caixa": 1.00, "Banco Pan": 2.90}) + _snap("2026-11-02", {"Caixa": 1.01, "Banco Pan": 2.85})
    mensal = [{"mes_referencia": m, "inicio_periodo": f"{m}-20", "fim_periodo": f"{m}-28", "banco": b, "taxa_am": v, "taxa_aa": 1.0}
              for m in ("2026-08", "2026-09") for b, v in (("Caixa", 1.0), ("Banco Pan", 2.9))]
    gv.gerar_feed_atom(str(tmp_path), "2026-11-02", mensal, sem)
    raiz = ET.parse(tmp_path / "feed.xml").getroot()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    assert raiz.tag == "{http://www.w3.org/2005/Atom}feed" and raiz.find("a:id", ns).text == gv.URL_FEED
    entradas = raiz.findall("a:entry", ns)
    assert len(entradas) == 3  # 2 meses + 1 atualização semanal (a primeira data não tem anterior)
    ids = [e.find("a:id", ns).text for e in entradas]
    assert len(set(ids)) == 3 and any("#2026-11-02" in i for i in ids)
    import re
    for e in entradas:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00Z", e.find("a:updated", ns).text)
        assert e.find("a:summary", ns).text and e.find("a:title", ns).text


def test_feed_atom_escapa_caracteres_especiais(tmp_path, monkeypatch):
    import xml.etree.ElementTree as ET
    monkeypatch.setitem(gv.BANCOS_VEICULOS, "Banco & <Teste>", {**gv.BANCOS_VEICULOS["Caixa"], "nome_exibicao": 'Banco & "Teste" <1>'})
    sem = _snap("2026-10-26", {"Banco & <Teste>": 1.0}) + _snap("2026-11-02", {"Banco & <Teste>": 1.2})
    gv.gerar_feed_atom(str(tmp_path), "2026-11-02", [], sem)
    resumo = ET.parse(tmp_path / "feed.xml").getroot().find("{http://www.w3.org/2005/Atom}entry/{http://www.w3.org/2005/Atom}summary").text
    assert 'Banco & "Teste" <1>' in resumo


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_site_gerado_tem_feed_atualizacoes_e_como_citar():
    import glob, xml.etree.ElementTree as ET
    raiz = ET.parse(os.path.join(PASTA, "feed.xml")).getroot()
    assert len(raiz.findall("{http://www.w3.org/2005/Atom}entry")) >= 12
    assert "feed.xml" not in _ler("sitemap.xml")
    assert f"{gv.DOMINIO}/atualizacoes<" in _ler("sitemap.xml") and 'noindex' not in _ler("atualizacoes.html")
    for pagina in ("index.html", "imprensa.html", "hub-caixa-carro-novo.html", "metodologia.html"):
        assert 'type="application/atom+xml"' in _ler(pagina), pagina
    assert 'atom+xml' not in _ler("embed.html")
    hubs = glob.glob(os.path.join(PASTA, "hub-*.html"))
    assert len(hubs) == 32
    for f in hubs:
        h = open(f, encoding="utf-8").read()
        assert "Como citar este dado" in h and "<textarea readonly" in h and "CC BY 4.0" in h, f
        assert 'href="atualizacoes"' in h, f  # link do bloco 'Mais sobre'
    assert 'href="/atualizacoes"' in _ler("index.html") or 'href="atualizacoes"' in _ler("index.html")
    assert "atualizacoes" in _ler("llms.txt") and "feed.xml" in _ler("llms-full.txt")


def test_workflow_versiona_o_historico_semanal():
    wf = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".github", "workflows", "atualiza_taxas.yml"), encoding="utf-8").read()
    assert "historico_semanal.csv" in wf


def test_regra_de_indexacao_da_grade_valor_prazo():
    from gerador_veiculos import PAGINAS_VALOR_INDEXAVEIS, pagina_valor_indexavel
    assert PAGINAS_VALOR_INDEXAVEIS == frozenset()
    assert not pagina_valor_indexavel("novo", 100_000, 48)


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_sitemap_so_tem_paginas_de_valor_proprio():
    """Hubs, comparadores, guias, renda e meses ficam; a grade de simulações sai."""
    urls = re.findall(r"<loc>([^<]+)</loc>", _ler("sitemap.xml"))
    assert 120 <= len(urls) <= 220
    assert sum("/hub-" in u for u in urls) == 32
    assert sum("/comparador-" in u for u in urls) == 3
    # nenhuma página com banco no nome da simulação (as de comparação sem marca ficam)
    assert not any(re.search(r"/financiamento-(carro-novo|carro-usado|moto)-(?!\d)", u) for u in urls)
    # toda página indexável fora do sitemap seria erro de consistência: sem noindex nas do sitemap
    for u in urls[:40]:
        nome = u.rsplit("/", 1)[-1] or "index"
        arq = os.path.join(PASTA, nome + ".html")
        if os.path.exists(arq):
            assert 'name="robots" content="noindex' not in open(arq, encoding="utf-8").read(), u


def test_bloco_requisitos_de_aprovacao_e_honesto():
    from gerador_veiculos import html_requisitos_aprovacao
    h = html_requisitos_aprovacao("usado", "Itaú")
    assert "O Itaú costuma limitar a parcela" in h and "carro usado" in h
    assert "Registrato" in h and "Nenhuma simulação garante aprovação" in h
    assert "Os bancos costumam limitar a parcela" in html_requisitos_aprovacao("moto")
    assert "garantida" not in h.lower()


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_hubs_e_comparadores_trazem_o_bloco_de_requisitos():
    for nome in ("hub-itau-carro-usado.html", "hub-banco-inter-moto.html", "comparador-carro-novo.html", "comparador-moto.html"):
        assert "Antes de pedir a proposta" in _ler(nome), nome
