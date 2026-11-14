"""Boas práticas oficiais de Google e Bing (13/nov/2026): lastmod real, sitemap enxuto e guias com fontes."""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lastmod

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.isdir(PASTA)


def test_registrar_mantem_a_data_se_o_conteudo_nao_mudou_e_avanca_se_mudou():
    m = {}
    d1 = lastmod.registrar(m, "k", "<p>a</p>", agora="2026-01-01T00:00:00+00:00")
    assert lastmod.registrar(m, "k", "<p>a</p>", agora="2026-02-02T00:00:00+00:00") == d1 == "2026-01-01T00:00:00+00:00"
    assert lastmod.registrar(m, "k", "<p>b</p>", agora="2026-03-03T00:00:00+00:00") == "2026-03-03T00:00:00+00:00"


def test_data_br():
    assert lastmod.data_br("2026-11-13T14:00:00+00:00") == "13/11/2026"


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_sitemap_tem_lastmod_iso_com_hora_e_sem_changefreq_priority():
    with open(os.path.join(PASTA, "sitemap.xml"), encoding="utf-8") as f:
        xml = f.read()
    assert "<changefreq>" not in xml and "<priority>" not in xml  # o Bing ignora; o Google também
    lms = re.findall(r"<lastmod>([^<]+)</lastmod>", xml)
    assert len(lms) == xml.count("<loc>") > 100
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", x) for x in lms)
    assert len(set(lms)) > 1, "todas as URLs com a mesma data = lastmod falso"


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_manifesto_cobre_todas_as_urls_do_sitemap():
    m = lastmod.carregar()
    with open(os.path.join(PASTA, "sitemap.xml"), encoding="utf-8") as f:
        urls = re.findall(r"<loc>([^<]+)</loc>", f.read())
    faltando = [u for u in urls if "url:" + u not in m]
    assert not faltando, faltando[:5]


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_todo_guia_mostra_data_de_atualizacao_e_fontes_oficiais():
    guias = [n for n in os.listdir(PASTA) if n.startswith("aprenda-") and n.endswith(".html")]
    assert len(guias) >= 10
    for nome in guias:
        with open(os.path.join(PASTA, nome), encoding="utf-8") as f:
            h = f.read()
        assert re.search(r"Texto atualizado em \d{2}/\d{2}/\d{4}", h), nome
        externos = [u for u in re.findall(r'href="(https?://[^"]+)"', h)
                    if re.search(r"gov\.br|bcb\.gov|caixa\.gov|procon", u)]
        assert externos, f"{nome}: guia sem nenhuma fonte oficial"


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_fontes_dos_guias_sao_https_e_sem_duplicata():
    from gerador_veiculos import FONTES_GUIAS
    for slug, fontes in FONTES_GUIAS.items():
        urls = [u for u, _ in fontes]
        assert len(urls) == len(set(urls)), slug
        assert all(u.startswith("https://") for u in urls), slug


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_guias_com_exemplo_calculado_trazem_numeros_do_simulador():
    for slug in ("aprenda-tabela-price", "aprenda-entrada-ideal-financiamento-veiculo", "aprenda-amortizacao-extra-veiculo",
                 "aprenda-iof-financiamento-veiculo", "aprenda-o-que-e-cet"):
        with open(os.path.join(PASTA, slug + ".html"), encoding="utf-8") as f:
            h = f.read()
        assert "Exemplo calculado" in h and len(re.findall(r"R\$ [\d.]+,\d{2}", h)) >= 2, slug


def test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo():
    import exemplos_guias
    from gerador_veiculos import calcular_pmt_price
    jp, mp, _ = exemplos_guias._price_com_extra(50_000, 48, 1.9, 12, 10_000, "prazo", calcular_pmt_price)
    jq, mq, _ = exemplos_guias._price_com_extra(50_000, 48, 1.9, 12, 10_000, "parcela", calcular_pmt_price)
    assert mp < 48 and mq == 48 and jp < jq


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_hubs_oferecem_link_para_copiar_e_compartilhar():
    hubs = [n for n in os.listdir(PASTA) if n.startswith("hub-") and n.endswith(".html")]
    assert len(hubs) >= 30
    for n in hubs:
        with open(os.path.join(PASTA, n), encoding="utf-8") as f:
            h = f.read()
        assert "Link para esta página" in h and "&lt;a href=" in h, n
        assert h.count('rel="noopener nofollow"') >= 4, n
