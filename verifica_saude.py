"""
Verificação semanal de saúde do site (roda no GitHub Actions, toda segunda).

Falha (e o GitHub avisa por e-mail) só quando algo importante quebra: sitemap
fora do tamanho esperado, página-chave fora do ar, página do sitemap com
noindex, AdSense de volta, chave do IndexNow ou arquivo do Bing sumidos, /embed
sem permissão de iframe. Tudo o mais fica no resumo do job (sem e-mail).

Uso: python verifica_saude.py --dominio https://veiculos.datalabglobal.com \
       --min-urls 700 --max-urls 1500 --chave-indexnow <chave> --paginas /metodologia,/dados-abertos
"""
import argparse
import os
import random
import re
import sys
import xml.etree.ElementTree as ET

import requests

TIMEOUT = 25
UA = {"User-Agent": "datalab-saude/1.0 (+https://www.datalabglobal.com/)"}


def get(url, **kw):
    return requests.get(url, headers=UA, timeout=TIMEOUT, **kw)


def verificar(dominio, min_urls, max_urls, chave, paginas, amostra=25):
    falhas, avisos, ok = [], [], []

    def checa(cond, msg_ok, msg_falha, grave=True):
        (ok if cond else (falhas if grave else avisos)).append(msg_ok if cond else msg_falha)

    try:
        sm = get(f"{dominio}/sitemap.xml")
        urls = [e.text for e in ET.fromstring(sm.content).iter() if e.tag.endswith("loc")]
    except Exception as e:  # rede ou XML inválido
        return [f"sitemap.xml ilegível: {e}"], [], []
    checa(sm.status_code == 200 and min_urls <= len(urls) <= max_urls,
          f"sitemap: {len(urls)} URLs", f"sitemap com {len(urls)} URLs (esperado {min_urls}-{max_urls}, HTTP {sm.status_code})")

    for p in paginas:
        r = get(dominio + p)
        checa(r.status_code == 200, f"{p}: 200", f"{p}: HTTP {r.status_code}")

    random.seed(os.environ.get("GITHUB_RUN_NUMBER", "0"))
    for u in random.sample(urls, min(amostra, len(urls))):
        r = get(u)
        corpo = r.text if r.status_code == 200 else ""
        checa(r.status_code == 200, "", f"URL do sitemap fora do ar: {u} (HTTP {r.status_code})")
        checa(not re.search(r'name="robots"[^>]*noindex', corpo), "", f"URL do sitemap com noindex: {u}")
        checa(f'rel="canonical" href="{u}"' in corpo or r.status_code != 200, "", f"canonical diferente da URL do sitemap: {u}", grave=False)

    home = get(dominio + "/").text
    checa("adsbygoogle" not in home, "sem AdSense", "AdSense voltou na home")
    robots = get(dominio + "/robots.txt").text
    checa("Sitemap:" in robots, "robots.txt com sitemap", "robots.txt sem linha Sitemap")
    if chave:
        r = get(f"{dominio}/{chave}.txt")
        checa(r.status_code == 200 and r.text.strip() == chave, "chave do IndexNow ok", "chave do IndexNow ausente ou diferente")
    r = get(f"{dominio}/BingSiteAuth.xml")
    checa(r.status_code == 200 and "<user>" in r.text, "BingSiteAuth.xml ok", "BingSiteAuth.xml ausente", grave=False)
    r = get(f"{dominio}/embed")
    cabecalho = r.headers.get("content-security-policy", "")
    checa(r.status_code == 200 and "frame-ancestors *" in cabecalho and "x-frame-options" not in r.headers,
          "/embed liberado para iframe", "/embed não está liberado para iframe (CSP/X-Frame-Options)", grave=False)
    return falhas, avisos, ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dominio", required=True)
    ap.add_argument("--min-urls", type=int, default=1)
    ap.add_argument("--max-urls", type=int, default=50000)
    ap.add_argument("--chave-indexnow", default="")
    ap.add_argument("--paginas", default="/")
    a = ap.parse_args()
    falhas, avisos, ok = verificar(a.dominio.rstrip("/"), a.min_urls, a.max_urls, a.chave_indexnow,
                                   [p for p in a.paginas.split(",") if p])
    linhas = [f"## Saúde de {a.dominio}", ""] + [f"- ✅ {m}" for m in ok if m] \
        + [f"- ⚠️ {m}" for m in avisos] + [f"- ❌ {m}" for m in falhas]
    texto = "\n".join(linhas)
    print(texto)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(texto + "\n")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
