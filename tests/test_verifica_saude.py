import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import verifica_saude as vs


class R:
    def __init__(self, status=200, text="", content=b"", headers=None):
        self.status_code, self.text, self.content, self.headers = status, text, content, headers or {}


def _site(monkeypatch, home="<html></html>", sitemap_urls=3, noindex_na_url=None):
    sm = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>https://x.test/p{i}</loc></url>" for i in range(sitemap_urls)) + "</urlset>").encode()

    def get(url, **kw):
        if url.endswith("/sitemap.xml"):
            return R(content=sm)
        if url.endswith("/robots.txt"):
            return R(text="Sitemap: https://x.test/sitemap.xml")
        if url.endswith("/CHAVE.txt"):
            return R(text="CHAVE")
        if url.endswith("/BingSiteAuth.xml"):
            return R(text="<users><user>X</user></users>")
        if url.endswith("/embed"):
            return R(headers={"content-security-policy": "frame-ancestors *"})
        if url == "https://x.test/":
            return R(text=home)
        corpo = f'<link rel="canonical" href="{url}">'
        if noindex_na_url and url.endswith(noindex_na_url):
            corpo += '<meta name="robots" content="noindex,follow">'
        return R(text=corpo)

    monkeypatch.setattr(vs, "get", get)


def test_site_saudavel_nao_falha(monkeypatch):
    _site(monkeypatch)
    falhas, avisos, ok = vs.verificar("https://x.test", 2, 10, "CHAVE", ["/p1"])
    assert falhas == [] and avisos == [] and ok


def test_detecta_adsense_noindex_no_sitemap_e_tamanho_fora_da_faixa(monkeypatch):
    _site(monkeypatch, home="<script src='adsbygoogle.js'>", noindex_na_url="/p1")
    falhas, _, _ = vs.verificar("https://x.test", 5, 10, "CHAVE", [])
    texto = " | ".join(falhas)
    assert "AdSense" in texto and "noindex" in texto and "sitemap com 3 URLs" in texto
