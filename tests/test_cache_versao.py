"""Cache-busting (14/nov/2026): styles.css, calculo.js e medicao.js levam ?v=<carimbo de build> na URL.
O Cloudflare guarda esses arquivos na borda/navegador por horas; sem o carimbo, o HTML novo podia chegar com CSS/JS antigo.
O carimbo NÃO pode contar como mudança de conteúdo no lastmod do sitemap."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gerador_veiculos as g

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _pagina(carimbo, extra=""):
    return ('<link rel="stylesheet" href="styles.css?v=' + carimbo + '"><script src="calculo.js?v=' + carimbo + '"></script>'
            '<script defer src="/medicao.js?v=' + carimbo + '"></script><p>x</p>' + extra)


def test_geradores_apontam_css_e_js_com_carimbo_de_versao(monkeypatch):
    assert re.fullmatch(r"\d{14}", g.VERSAO_BUILD)
    fonte = open(os.path.join(RAIZ, "gerador_veiculos.py"), encoding="utf-8").read()
    assert 'href="styles.css?v={VERSAO_BUILD}"' in fonte
    assert 'src="calculo.js?v={VERSAO_BUILD}"' in fonte and 'src="calculo.js"' not in fonte
    monkeypatch.setattr(g, "UMAMI_WEBSITE_ID", "abc-123")
    assert "/medicao.js?v=" + g.VERSAO_BUILD + '"' in "".join(g.tags_medicao())


def test_lastmod_do_sitemap_ignora_o_carimbo_mas_acompanha_mudanca_real(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "_MANIFESTO_LASTMOD", {})
    arq = tmp_path / "a.html"
    urls = [g.DOMINIO + "/a"]

    def gerar():
        g.gerar_sitemap(urls, "2026-01-01", str(tmp_path))

    arq.write_text(_pagina("20260101000000"), encoding="utf-8")
    gerar()
    antes = {k: dict(v) for k, v in g._MANIFESTO_LASTMOD.items()}
    arq.write_text(_pagina("20260202020202"), encoding="utf-8")
    gerar()
    assert g._MANIFESTO_LASTMOD == antes  # só o carimbo mudou: lastmod e hash intactos
    arq.write_text(_pagina("20260303030303", "<p>conteúdo novo</p>"), encoding="utf-8")
    gerar()
    assert g._MANIFESTO_LASTMOD != antes  # mudança real de conteúdo: o lastmod avança
