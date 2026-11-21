"""Confere os links da home e das páginas principais: internos (servidor local, sem 404) e externos (pedido real, segue redirecionamento).

Sobe um servidor local em paginas_seo/ e usa o `requests` para os endereços externos (fora do CI: precisa de rede). Uso: python testar_links.py
Opção --tudo confere todas as páginas do sitemap (mais lento). Um link externo que bloqueia robô (403/429) é só avisado, não conta como falha.
"""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urldefrag, urljoin

import requests

import servidor_local

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "paginas_seo")
DOMINIO = "https://veiculos.datalabglobal.com"
# bases de API/pré-conexão (não são páginas para abrir): fontes do Google e o serviço de favicons
IGNORAR = ("https://fonts.googleapis.com", "https://fonts.gstatic.com", "https://www.google.com/s2/favicons")
UA = {"User-Agent": "Mozilla/5.0 (compatible; verificador-de-links-datalab/1.0)"}
FALHAS = []
AVISOS = []


def paginas():
    if "--tudo" in sys.argv:
        with open(os.path.join(PASTA, "sitemap.xml"), encoding="utf-8") as f:
            return [u.replace(DOMINIO, "") or "/" for u in re.findall(r"<loc>(.*?)</loc>", f.read())]
    return ["/", "/aprenda", "/comparador-carro-novo", "/comparador-carro-usado", "/comparador-moto", "/hub-caixa-carro-novo", "/metodologia", "/sobre",
            "/financiamento-veiculos", "/taxas-financiamento-veiculos", "/dados-abertos", "/atualizacoes", "/imprensa", "/incorporar"]


def links_de(html):
    return re.findall(r'(?:href|src)="([^"]+)"', html)


def externo(url):
    try:
        r = requests.get(url, headers=UA, timeout=25, allow_redirects=True, stream=True)
        r.close()
        return url, r.status_code
    except requests.RequestException as e:
        return url, "erro: %s" % type(e).__name__


def main():
    srv = servidor_local.subir()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    internos, externos = {}, {}
    for caminho in paginas():
        r = requests.get(base + caminho, timeout=20)
        if r.status_code != 200:
            FALHAS.append("%s -> %s" % (caminho, r.status_code))
            continue
        for ref in links_de(r.text):
            ref, _ = urldefrag(ref)
            if not ref or ref.startswith(("mailto:", "tel:", "data:", "javascript:")):
                continue
            url = urljoin(base + caminho, ref)
            if url.startswith(base):
                internos.setdefault(url, caminho)
            elif url.startswith("http") and not url.startswith(IGNORAR):
                externos.setdefault(url.split("?")[0] if "ftudo" not in url else url, caminho)
    for url, origem in sorted(internos.items()):
        c = requests.get(url, timeout=20).status_code
        if c != 200:
            FALHAS.append("interno %s (em %s) -> %s" % (url.replace(base, ""), origem, c))
    with ThreadPoolExecutor(8) as ex:
        for url, status in ex.map(externo, sorted(externos)):
            ok = isinstance(status, int) and status < 400
            bloqueio = status in (401, 403, 405, 429)
            print(("OK    " if ok else ("AVISO " if bloqueio else "FALHOU")), status, url)
            if bloqueio:
                AVISOS.append("%s -> %s" % (url, status))
            elif not ok:
                FALHAS.append("externo %s (em %s) -> %s" % (url, externos[url], status))
    srv.shutdown()
    print("\n%d página(s), %d link(s) interno(s), %d externo(s); %d falha(s), %d aviso(s)." % (len(paginas()), len(internos), len(externos), len(FALHAS), len(AVISOS)))
    for f in FALHAS:
        print(" -", f)
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
