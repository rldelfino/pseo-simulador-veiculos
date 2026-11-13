"""
Avisa o Bing (e os demais buscadores que adotam o IndexNow) das URLs do sitemap
assim que o site é atualizado, em vez de esperar o rastreamento natural.

Por que existe (auditoria de SEO, 29/out/2026): o site é novo e o Bing quase não
o rastreou ainda. O IndexNow é gratuito e acelera a descoberta. O Google NÃO
usa IndexNow (para ele continua valendo o sitemap + Search Console).

Como funciona: o arquivo paginas_seo/<chave>.txt, com a chave dentro, prova que o
site é nosso. Este script lê paginas_seo/sitemap.xml e envia as URLs em lotes de
até 10 mil para api.indexnow.org (compartilhado com Bing, Yandex e outros).

Uso: python indexnow.py [caminho_do_sitemap] [--horas N | --todas]
  (padrão: só as URLs cujo <lastmod> do sitemap é das últimas 6 horas, enviadas uma a uma)
Falha de rede NÃO derruba o pipeline: avisa e sai com código 0.

Mudança de 13/nov/2026: o Bing recomenda (Diretrizes, item 4) "evitar envios em lote quando possível"; envios
um a um, só do que mudou, atualizam mais rápido e poluem menos. Antes o script mandava TODAS as URLs em lote a
cada execução, e o painel do Bing alertava "IndexNow em modo batch". O lote continua como reserva quando muita
coisa muda de uma vez (mais de LIMITE_INDIVIDUAL URLs).
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

HOST = "veiculos.datalabglobal.com"
CHAVE = "1c5d2ac5ea7443060014bbe43cedbcf6"
LOCAL_DA_CHAVE = f"https://{HOST}/{CHAVE}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"
TAMANHO_LOTE = 10_000
LIMITE_INDIVIDUAL = 50
HORAS_PADRAO = 6


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


def urls_recentes(caminho="paginas_seo/sitemap.xml", horas=HORAS_PADRAO, agora=None):
    """URLs do sitemap cujo <lastmod> é das últimas `horas` (URL sem lastmod conta como alterada)."""
    agora = agora or datetime.now(timezone.utc)
    limite = agora - timedelta(hours=horas)
    with open(caminho, encoding="utf-8") as f:
        blocos = re.findall(r"<url>(.*?)</url>", f.read(), re.S)
    recentes = []
    for b in blocos:
        loc = re.search(r"<loc>([^<]+)</loc>", b)
        if not loc or not loc.group(1).startswith(f"https://{HOST}/"):
            continue
        lm = re.search(r"<lastmod>([^<]+)</lastmod>", b)
        if not lm:
            recentes.append(loc.group(1))
            continue
        try:
            quando = datetime.fromisoformat(lm.group(1).replace("Z", "+00:00"))
            if quando.tzinfo is None:
                quando = quando.replace(tzinfo=timezone.utc)
        except ValueError:
            recentes.append(loc.group(1))
            continue
        if quando >= limite:
            recentes.append(loc.group(1))
    return recentes


def enviar_url(url, endpoint=ENDPOINT):
    """Envio individual (GET), o formato 'streaming' que o Bing prefere."""
    qs = urllib.parse.urlencode({"url": url, "key": CHAVE, "keyLocation": LOCAL_DA_CHAVE})
    with urllib.request.urlopen(f"{endpoint}?{qs}", timeout=30) as resp:
        return resp.status


def main(caminho="paginas_seo/sitemap.xml", horas=None, individual_ate=0):
    urls = urls_do_sitemap(caminho) if horas is None else urls_recentes(caminho, horas)
    if not urls:
        print("⚠️  IndexNow: nenhuma URL alterada para enviar" if horas is not None else "⚠️  IndexNow: nenhuma URL no sitemap — nada a enviar")
        return 0
    if len(urls) <= individual_ate:
        ok = 0
        for u in urls:
            try:
                enviar_url(u)
                ok += 1
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                print(f"⚠️  IndexNow: falha ao enviar {u} ({e})")
            time.sleep(0.2)
        print(f"✅ IndexNow: {ok} de {len(urls)} URL(s) alteradas enviadas uma a uma")
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


def _cli(argv):
    caminho, horas = "paginas_seo/sitemap.xml", HORAS_PADRAO
    resto = list(argv)
    while resto:
        a = resto.pop(0)
        if a == "--todas":
            horas = None
        elif a == "--horas" and resto:
            horas = float(resto.pop(0))
        else:
            caminho = a
    return main(caminho, horas=horas, individual_ate=LIMITE_INDIVIDUAL)


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
