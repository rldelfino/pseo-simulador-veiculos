"""
Avisa o Bing (e os demais buscadores que adotam o IndexNow) das URLs do sitemap
assim que o site é atualizado, em vez de esperar o rastreamento natural.

Por que existe (auditoria de SEO, 29/out/2026): o site é novo e o Bing quase não
o rastreou ainda. O IndexNow é gratuito e acelera a descoberta. O Google NÃO
usa IndexNow (para ele continua valendo o sitemap + Search Console).

Como funciona: o arquivo paginas_seo/<chave>.txt, com a chave dentro, prova que o
site é nosso. Este script lê paginas_seo/sitemap.xml e envia as URLs em lotes de
até 10 mil para api.indexnow.org (compartilhado com Bing, Yandex e outros).

Uso: python indexnow.py [caminho_do_sitemap]
Falha de rede NÃO derruba o pipeline: avisa e sai com código 0.
"""
import json
import re
import sys
import urllib.error
import urllib.request

HOST = "veiculos.datalabglobal.com"
CHAVE = "1c5d2ac5ea7443060014bbe43cedbcf6"
LOCAL_DA_CHAVE = f"https://{HOST}/{CHAVE}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
TAMANHO_LOTE = 10_000


def urls_do_sitemap(caminho="paginas_seo/sitemap.xml"):
    with open(caminho, encoding="utf-8") as f:
        urls = re.findall(r"<loc>([^<]+)</loc>", f.read())
    return [u for u in urls if u.startswith(f"https://{HOST}/")]


def montar_payload(urls):
    return {"host": HOST, "key": CHAVE, "keyLocation": LOCAL_DA_CHAVE, "urlList": list(urls)}


def enviar(payload, endpoint=ENDPOINT):
    req = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status


def main(caminho="paginas_seo/sitemap.xml"):
    urls = urls_do_sitemap(caminho)
    if not urls:
        print("⚠️  IndexNow: nenhuma URL no sitemap — nada a enviar")
        return 0
    for i in range(0, len(urls), TAMANHO_LOTE):
        lote = urls[i:i + TAMANHO_LOTE]
        try:
            status = enviar(montar_payload(lote))
            print(f"✅ IndexNow: {len(lote)} URL(s) enviadas (HTTP {status})")
        except urllib.error.HTTPError as e:
            print(f"⚠️  IndexNow: HTTP {e.code} ao enviar {len(lote)} URL(s) — {e.reason}")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"⚠️  IndexNow: falha de rede ({e}) — segue sem avisar o Bing")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
