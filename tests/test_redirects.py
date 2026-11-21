"""Enxugamento (21/11/2026): o _redirects cobre toda página que saiu, cada destino existe e não redireciona de novo (sem cadeia nem laço),
nenhuma URL do sitemap é origem de redirecionamento e as regras cabem nos limites do Cloudflare Pages."""
import os
import re

import pytest

import gerador_veiculos as g
from bancos_veiculos import bancos_para_categoria

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.isfile(os.path.join(SAIDA, "_redirects"))


def _regras():
    regras = []
    with open(os.path.join(SAIDA, "_redirects"), encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#"):
                continue
            origem, destino, status = linha.split()
            if status == "200":  # reescrita (sem redirecionar): só a do arquivo de verificação do Yandex
                assert origem == "/yandex_90c15c3be650b0ed.html" and destino == "/yandex_90c15c3be650b0ed", linha
                continue
            assert status == "301", linha
            regras.append((origem, destino))
    return regras


def _casa(origem, caminho):
    padrao = "^" + re.escape(origem).replace(r"\*", ".*") + "$"
    return re.match(padrao, caminho) is not None


def _destino(regras, caminho):
    for origem, destino in regras:
        if _casa(origem, caminho):
            return destino
    return None


def _urls_removidas():
    """Todas as URLs (sem .html) que existiam antes do enxugamento e hoje redirecionam."""
    urls = []
    for p in g.gerar_grade_paginas():
        urls.append("/" + p["slug"])
    for c in g.CATEGORIAS:
        for v in g.VALORES_POR_CATEGORIA[c]:
            urls.append("/" + g.slug_renda(c, v))
            for prazo in g.PRAZOS_MESES:
                if g.pagina_comparacao_existe(c, v, prazo):
                    urls.append("/" + g.slug_comparacao(c, v, prazo))
    for b in bancos_para_categoria("usado"):
        urls.append(f"/hub-{g.slugificar_banco(b)}-carro-usado")
    meses = sorted({r["mes_referencia"] for r in g.historico_cache()})
    for m in meses[:-g.MESES_INDEXAVEIS_MENSAL]:
        urls.append("/" + g.slug_mes(m))
    return urls


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_regras_cabem_nos_limites_do_cloudflare_pages():
    regras = _regras()
    din = [r for r in regras if "*" in r[0] or ":" in r[0]]
    assert len(din) <= g.LIMITE_REDIRECTS_DINAMICOS and len(regras) - len(din) <= g.LIMITE_REDIRECTS_ESTATICOS
    assert len(set(o for o, _ in regras)) == len(regras), "origem repetida"
    # só um asterisco por regra (limite do Cloudflare Pages)
    assert all(o.count("*") <= 1 for o, _ in regras)


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_toda_url_removida_redireciona_para_uma_pagina_que_existe():
    regras = _regras()
    removidas = _urls_removidas()
    assert len(removidas) >= 960
    sem_regra, destino_ruim = [], []
    for u in removidas:
        for caminho in (u, u + ".html"):
            d = _destino(regras, caminho)
            if d is None:
                sem_regra.append(caminho)
            elif not os.path.isfile(os.path.join(SAIDA, d.lstrip("/") + ".html")):
                destino_ruim.append((caminho, d))
    assert not sem_regra, sem_regra[:5]
    assert not destino_ruim, destino_ruim[:5]
    # a página órfã que existia sem ser gerada mais (taxas de outubro/2024) tem destino
    assert _destino(regras, "/taxas-financiamento-veiculos-outubro-2024") == "/taxas-financiamento-veiculos"


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_sem_cadeia_sem_laco_e_nada_do_sitemap_redireciona():
    regras = _regras()
    for origem, destino in regras:
        assert origem != destino
        assert _destino(regras, destino) is None, f"cadeia: {origem} -> {destino} -> {_destino(regras, destino)}"
    with open(os.path.join(SAIDA, "sitemap.xml"), encoding="utf-8") as f:
        urls = re.findall(r"<loc>https://veiculos\.datalabglobal\.com([^<]*)</loc>", f.read())
    assert len(urls) >= 40
    for u in urls:
        caminho = u or "/"
        assert _destino(regras, caminho) is None, f"URL do sitemap redireciona: {caminho}"
        assert _destino(regras, caminho + ".html") is None


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_nenhum_html_de_pagina_removida_continua_publicado_e_nenhuma_pagina_viva_casa_regra():
    regras = _regras()
    for nome in os.listdir(SAIDA):
        if not nome.endswith(".html"):
            continue
        base = nome[:-5]
        for caminho in ("/" + base, "/" + nome):
            assert _destino(regras, caminho) is None, f"{nome} existe e também é origem de redirecionamento"


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_yandex_responde_200_no_endereco_com_html():
    """O Cloudflare Pages redireciona /x.html para /x (308); a regra de reescrita (200) mantém o endereço com .html que o Yandex pede."""
    with open(os.path.join(SAIDA, "_redirects"), encoding="utf-8") as f:
        assert "/yandex_90c15c3be650b0ed.html /yandex_90c15c3be650b0ed 200" in f.read().splitlines()
