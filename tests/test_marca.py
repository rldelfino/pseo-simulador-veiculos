"""Marca padronizada da família (a mesma do 006): logo + wordmark levam ao site principal; o rótulo 'Veículos' leva à home do simulador, em todas as páginas."""
import os
import re

import pytest

import layout_home

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.isfile(os.path.join(SAIDA, "index.html"))


def test_logo_e_o_do_006():
    caminho = os.path.join(RAIZ, "..", "006-pseo-simulador-homeequity", "layout.py")
    if not os.path.isfile(caminho):
        pytest.skip("006 não está na máquina")  # CI: só no computador do dono
    with open(caminho, encoding="utf-8") as f:
        origem = f.read()
    assert layout_home.LOGO_INNER in origem
    assert "<ellipse" in layout_home.LOGO_SVG and 'viewBox="0 0 44 44"' in layout_home.LOGO_SVG
    assert '<span class="wm"><b>Datalab</b><i>GLOBAL</i></span>' in layout_home.marca()


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_toda_pagina_com_cabecalho_tem_a_marca_com_os_dois_links():
    sem, ruins = [], []
    for nome in sorted(os.listdir(SAIDA)):
        if not nome.endswith(".html") or nome.startswith("yandex_") or nome == "embed.html":
            continue
        with open(os.path.join(SAIDA, nome), encoding="utf-8") as f:
            h = f.read()
        brands = re.findall(r'<a href="([^"]+)" class="brand" aria-label="([^"]+)"', h)
        prods = re.findall(r'<a href="([^"]+)" class="prod" aria-label="([^"]+)">Veículos</a>', h)
        if not brands or not prods:
            sem.append(nome)
            continue
        if any(b[0] != "https://www.datalabglobal.com/" or "site principal" not in b[1] for b in brands) or any(p[0] != "/" for p in prods):
            ruins.append(nome)
        assert "logo-header.webp" not in h, nome  # a imagem antiga do cabeçalho saiu
    assert not sem, sem[:5]
    assert not ruins, ruins[:5]


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_home_tem_marca_no_cabecalho_e_no_rodape_e_um_caminho_de_volta_no_menu_do_celular():
    with open(os.path.join(SAIDA, "index.html"), encoding="utf-8") as f:
        h = f.read()
    assert h.count('class="brand"') == 2 and h.count('class="prod"') == 2
    menu = h[h.index('<details class="menu">'):h.index("</details>")]
    assert 'href="/">Início do simulador</a>' in menu
    css = open(os.path.join(SAIDA, "home.css"), encoding="utf-8").read()
    assert ".prod{display:none}" not in css  # o rótulo (link para a home do simulador) fica visível no celular
