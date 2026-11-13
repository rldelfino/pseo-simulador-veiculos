"""
Datas de modificação REAIS por página (sitemap.xml e "Atualizado em" dos guias).

Por que existe (13/nov/2026): as Diretrizes do Bing pedem `lastmod` verdadeiro e dizem que `changefreq` e
`priority` são ignorados; o Google trata `lastmod` falso como sinal de frescor falso, e o guia de conteúdo
útil do Google lista "mudar a data da página sem mudar o conteúdo" como sinal de conteúdo feito para
buscador. Antes, TODAS as URLs levavam a mesma data (a da última atualização de taxas).

Como funciona: `lastmod_manifest.json` (na raiz do repositório, commitado) guarda, por chave, o hash do
conteúdo e a data-hora (ISO 8601, UTC) em que esse conteúdo mudou pela última vez. Se o hash não mudou, a
data fica; se mudou (ou é novo), vale "agora". Assim a data só avança quando a página realmente muda.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

RAIZ = os.path.dirname(os.path.abspath(__file__))
CAMINHO_MANIFESTO = os.path.join(RAIZ, "lastmod_manifest.json")


def agora_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def carregar(caminho=CAMINHO_MANIFESTO):
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar(dados, caminho=CAMINHO_MANIFESTO):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")


def hash_de(conteudo):
    if isinstance(conteudo, str):
        conteudo = conteudo.encode("utf-8")
    return hashlib.sha256(conteudo).hexdigest()


def registrar(dados, chave, conteudo, agora=None):
    """Devolve a data-hora ISO da última mudança real de `conteudo` e atualiza `dados` se mudou."""
    h = hash_de(conteudo)
    reg = dados.get(chave)
    if reg and reg.get("hash") == h:
        return reg["lastmod"]
    dados[chave] = {"hash": h, "lastmod": agora or agora_iso()}
    return dados[chave]["lastmod"]


def data_br(iso):
    """'2026-11-13T14:00:00+00:00' -> '13/11/2026'."""
    return f"{iso[8:10]}/{iso[5:7]}/{iso[0:4]}"
