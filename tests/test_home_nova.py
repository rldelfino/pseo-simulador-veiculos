"""Home nova (20/11/2026): template do 006/007/008 em azul de veículos. Trava a CSP (sem style nem script inline), o arquivo do Yandex,
os links para os simuladores irmãos, o cenário padrão contra a conta de referência e o bloco de dados lido pelo home.js."""
import json
import os
import re

import pytest

import bancos_veiculos as bv
import gerador_veiculos as gv

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.isfile(os.path.join(SAIDA, "index.html"))


def _home():
    with open(os.path.join(SAIDA, "index.html"), encoding="utf-8") as f:
        return f.read()


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_home_sem_style_nem_script_inline():
    html = _home()
    assert " style=" not in html and "<style" not in html
    # único <script> sem src permitido: os blocos de dados (JSON e JSON-LD), que o navegador não executa
    for m in re.finditer(r"<script([^>]*)>", html):
        attrs = m.group(1)
        assert "src=" in attrs or "application/json" in attrs or "application/ld+json" in attrs, attrs
    assert " onclick=" not in html and "javascript:" not in html


def test_csp_da_home_nao_tem_unsafe_inline_e_o_resto_do_site_segue_igual():
    headers = gv.gerar_headers()
    bloco_home = headers.split("\n/\n", 1)[1].split("\n\n", 1)[0]
    assert "! Content-Security-Policy" in bloco_home and "unsafe-inline" not in bloco_home
    assert "script-src 'self' https://static.cloudflareinsights.com https://cloud.umami.is" in bloco_home and "object-src 'none'" in bloco_home
    assert "frame-ancestors 'none'" in bloco_home
    primeira = headers.split("\n\n", 1)[0]
    assert "X-Frame-Options: DENY" in primeira and "X-Content-Type-Options: nosniff" in primeira and "Strict-Transport-Security" in primeira


def test_arquivo_do_yandex_tem_o_conteudo_exato(tmp_path):
    gv.gerar_verificacao_yandex(str(tmp_path))
    esperado = ('<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n</head>\n'
                '<body>Verification: 90c15c3be650b0ed</body>\n</html>')
    with open(tmp_path / "yandex_90c15c3be650b0ed.html", "rb") as f:
        assert f.read() == esperado.encode("utf-8")


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_arquivo_do_yandex_esta_versionavel_e_fora_do_sitemap():
    assert os.path.isfile(os.path.join(SAIDA, "yandex_90c15c3be650b0ed.html"))
    with open(os.path.join(SAIDA, "sitemap.xml"), encoding="utf-8") as f:
        assert "yandex" not in f.read()
    with open(os.path.join(RAIZ, ".gitignore"), encoding="utf-8") as f:
        assert "yandex" not in f.read() and "*.html" not in f.read()


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_rodape_da_home_linka_os_irmaos_e_o_hub():
    html = _home()
    for url in ("https://homeequity.datalabglobal.com/", "https://autoequity.datalabglobal.com/", "https://condominio.datalabglobal.com/",
                "https://simulador.datalabglobal.com/", "https://emprestimo.datalabglobal.com/", "https://www.datalabglobal.com/"):
        assert f'href="{url}"' in html, url


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_mensagem_do_parceiro_e_agnostica_e_o_link_so_esta_na_tela_de_confirmacao():
    html = _home()
    dialogo = html.split('<dialog id="dlg-confirma"', 1)[1].split("</dialog>", 1)[0]
    assert gv.LINK_FINANCIA_TUDO in dialogo and "parceiro de crédito" in dialogo
    fora = html.replace(dialogo, "")
    assert gv.LINK_FINANCIA_TUDO not in fora
    texto = re.sub(r"<[^>]+>", " ", dialogo).lower()
    assert "ftudo" not in texto and "financiatudo" not in texto and "comiss" not in texto


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_cenario_padrao_do_html_bate_com_a_conta_de_referencia():
    d = gv.padrao_simulador_home()
    fin = 80_000 * 0.8
    taxas = [v["taxa_am"] for v in bv.bancos_para_categoria("novo").values()]
    tx = sum(taxas) / len(taxas)
    assert d["fin"] == fin and d["prazo"] == 48 and d["taxa"] == tx
    assert d["parcela"] == gv.calcular_pmt_price(fin, 48, tx)
    assert d["cet"] == gv.calcular_cet_veiculo(fin, 48, tx)
    html = _home()
    parcela = re.search(r'id="r-parcela">R\$ ([\d.]+,\d{2})<', html).group(1)
    assert parcela == gv._num_br(d["parcela"], 2)
    assert f'id="r-cet">{gv._num_br(d["cet"], 2)}% a.a.<' in html


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_bloco_de_dados_do_simulador_tem_as_taxas_de_cada_banco():
    html = _home()
    bruto = re.search(r'<script type="application/json" id="dados-sim">(.*?)</script>', html, re.S).group(1)
    dados = json.loads(bruto)
    assert dados["entradaMin"] == {"novo": 0.2, "usado": 0.3, "moto": 0.3}
    for categoria in ("novo", "usado", "moto"):
        esperado = bv.bancos_para_categoria(categoria)
        assert {b["k"] for b in dados["bancos"][categoria]} == set(esperado)
        for b in dados["bancos"][categoria]:
            assert b["am"] == esperado[b["k"]]["taxa_am"] and b["pm"] == esperado[b["k"]]["prazo_max"]
        taxas = [b["am"] for b in dados["bancos"][categoria]]
        assert taxas == sorted(taxas)
    assert {"Banco Honda", "Banco Yamaha"} <= {b["k"] for b in dados["bancos"]["moto"]}
    assert "Banco Honda" not in {b["k"] for b in dados["bancos"]["novo"]}


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_home_tem_h1_unico_titulo_curto_e_assets_com_versao():
    html = _home()
    assert html.count("<h1") == 1 and "Simulador de financiamento de <em>veículos</em>" in html
    titulo = re.search(r"<title>([^<]*)</title>", html).group(1)
    assert len(titulo) <= 60 and "Veículos" in titulo
    for arq in ("home.css", "home.js", "menu.js", "calculo.js"):
        assert re.search(r'(?:href|src)="/%s\?v=[\w]+"' % re.escape(arq), html), arq
    for arq in ("home.css", "home.js", "menu.js", "fonts/inter-latin.woff2", "fonts/playfair-display-latin.woff2"):
        assert os.path.isfile(os.path.join(SAIDA, arq)), arq
    for tipo in ("WebApplication", "FAQPage", "Organization", "BreadcrumbList", "WebSite", "WebPage"):
        assert f'"@type": "{tipo}"' in html, tipo
