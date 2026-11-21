"""Testa o _redirects no motor de verdade do Cloudflare Pages (wrangler pages dev), fora do CI.

1) Suba o Pages local:  npx wrangler@3 pages dev paginas_seo --port 8791
2) Rode:                python testar_redirects.py [http://127.0.0.1:8791]
Confere, para toda URL que saiu do site (e a variante .html): resposta 301 com Location certo, destino com 200 direto (sem cadeia), e que as URLs
do sitemap novo respondem 200 sem redirecionar. Usa os mesmos cálculos de tests/test_redirects.py para listar as URLs removidas.
"""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
import test_redirects as tr  # noqa: E402

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8791").rstrip("/")
FALHAS = []
regras = tr._regras()


def checa_removida(caminho):
    esperado = tr._destino(regras, caminho)
    r = requests.get(BASE + caminho, allow_redirects=False, timeout=20)
    loc = r.headers.get("location", "")
    destino = re.sub(r"^https?://[^/]+", "", loc)
    erros = []
    if r.status_code != 301:
        erros.append("status %s (esperado 301)" % r.status_code)
    elif destino != esperado:
        erros.append("Location %s (esperado %s)" % (destino, esperado))
    else:
        r2 = requests.get(BASE + destino, allow_redirects=False, timeout=20)
        if r2.status_code != 200:
            erros.append("destino %s respondeu %s (cadeia ou 404)" % (destino, r2.status_code))
    return caminho, erros


def checa_viva(caminho):
    r = requests.get(BASE + caminho, allow_redirects=False, timeout=20)
    return caminho, ([] if r.status_code == 200 else ["status %s (esperado 200, sem redirecionar)" % r.status_code])


def main():
    removidas = []
    for u in tr._urls_removidas():
        removidas += [u, u + ".html"]
    with open(os.path.join(tr.SAIDA, "sitemap.xml"), encoding="utf-8") as f:
        vivas = [u or "/" for u in re.findall(r"<loc>https://veiculos\.datalabglobal\.com([^<]*)</loc>", f.read())]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(checa_removida, removidas)) + list(ex.map(checa_viva, vivas))
    for caminho, erros in res:
        for e in erros:
            FALHAS.append("%s: %s" % (caminho, e))
    print("%d URLs removidas (com e sem .html) e %d do sitemap conferidas; %d falha(s)." % (len(removidas), len(vivas), len(FALHAS)))
    for f in FALHAS[:30]:
        print(" -", f)
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
