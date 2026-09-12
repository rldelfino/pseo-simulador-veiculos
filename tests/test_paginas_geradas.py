"""
Validação de integridade das páginas HTML geradas: 100% dos links
internos resolvem, 100% dos blocos JSON-LD são JSON válido, HTML sem
tags desbalanceadas, e a constante de domínio bate em todo lugar que
deveria (canonical, sitemap, robots, llms.txt). Ver checklist de
validação do projeto irmão (seção 3, item 8 do prompt de arquitetura).

Depende de 'paginas_seo/' já ter sido gerado (python gerador_veiculos.py).
Não roda por padrão junto com o resto da suíte se a pasta não existir
(skip), pra não quebrar CI num checkout limpo sem build.
"""
import html.parser
import json
import os
import re

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_SAIDA = os.path.join(RAIZ, "paginas_seo")

pytestmark = pytest.mark.skipif(not os.path.isdir(PASTA_SAIDA), reason="paginas_seo/ não gerada — rode python gerador_veiculos.py antes")


def _arquivos_html():
    return sorted(f for f in os.listdir(PASTA_SAIDA) if f.endswith(".html"))


class VerificadorBalanceamento(html.parser.HTMLParser):
    """Confere que toda tag aberta (não voidelement) tem seu fechamento
    correspondente, na ordem certa — pega tag esquecida/mal fechada sem
    precisar de um parser HTML completo de terceiros."""
    VOID = {"meta", "link", "img", "br", "hr", "input", "area", "base", "col", "embed", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.pilha = []
        self.erros = []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.pilha.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass  # tag self-closing (<tag/>) não entra na pilha

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.pilha or self.pilha[-1] != tag:
            self.erros.append(f"fechamento inesperado de </{tag}> (topo da pilha: {self.pilha[-1] if self.pilha else 'vazio'})")
            return
        self.pilha.pop()


def test_todo_link_interno_resolve_para_arquivo_existente():
    """Achado real (10/set/2026, checagem final de SEO): depois de tirar a
    extensão ".html" de canonical/hrefs internos (pra bater com o
    redirect automático do Cloudflare Pages, ver comentário em
    gerar_pagina_individual), a regex original desta função só
    reconhecia href/src terminado em extensão (.html/.css/.svg/.js) —
    href="{slug}" sem extensão nenhuma passava batido, SEM checagem
    nenhuma de link quebrado. Corrigido pra também validar href de
    página (sem extensão, ou "/" pra home) contra {slug}.html em disco —
    é a mesma verificação de sempre, só reconhecendo o formato de URL
    novo."""
    paginas_por_slug = {n[:-len(".html")] for n in _arquivos_html()}
    assets = {"styles.css", "logo.svg", "sitemap.xml", "calculo.js", "favicon.svg", "favicon.ico", "apple-touch-icon.png"}
    faltando = []
    for nome_arquivo in _arquivos_html():
        with open(os.path.join(PASTA_SAIDA, nome_arquivo), encoding="utf-8") as f:
            conteudo = f.read()
        for ref in re.findall(r'(?:href|src)="([^"#]*)"', conteudo):
            if not ref or ref.startswith(("http://", "https://", "mailto:", "tel:", "#", "data:")):
                continue  # link externo/âncora — fora do escopo desta checagem
            if ref == "/":
                continue  # home — sempre resolve (index.html sempre existe)
            ref_sem_query = ref.split("?", 1)[0]  # styles.css?v=... — cache-busting não é parte do path real
            if "." in ref_sem_query.rsplit("/", 1)[-1]:  # tem extensão: asset (.css/.svg/.js/.ico/.png) ou .html direto
                if ref_sem_query not in assets and ref_sem_query not in set(_arquivos_html()):
                    faltando.append(f"{nome_arquivo} -> {ref}")
            elif ref_sem_query.lstrip("/") not in paginas_por_slug:  # slug sem extensão: precisa ter {slug}.html em disco
                faltando.append(f"{nome_arquivo} -> {ref}")
    assert not faltando, f"{len(faltando)} link(s)/asset(s) interno(s) quebrado(s): {faltando[:20]}"


def test_calculo_js_existe_e_e_referenciado_pelas_paginas_individuais():
    assert os.path.isfile(os.path.join(PASTA_SAIDA, "calculo.js")), "calculo.js não foi gerado"
    paginas_individuais = [n for n in _arquivos_html() if n.startswith("financiamento-")]
    assert paginas_individuais, "nenhuma página individual encontrada pra checar"
    sem_calculo_js = [
        n for n in paginas_individuais
        if 'src="calculo.js"' not in open(os.path.join(PASTA_SAIDA, n), encoding="utf-8").read()
    ]
    assert not sem_calculo_js, f"páginas individuais sem calculo.js: {sem_calculo_js[:10]}"


def test_toda_pagina_tem_o_cta_de_afiliado():
    """O CTA de análise gratuita (link de afiliado) precisa aparecer em
    toda página de conteúdo — é o único caminho de conversão do site
    (modelo de negócio é por indicação, não por venda direta). 404.html
    é excluída de propósito: é página de erro (noindex), sem conteúdo de
    produto, não deveria empurrar conversão — mesmo padrão do projeto
    irmão."""
    LINK = "https://ftudo.com/rodolfo-financiamento-de-automoveis/"
    paginas = [n for n in _arquivos_html() if n != "404.html"]
    sem_cta = [n for n in paginas if LINK not in open(os.path.join(PASTA_SAIDA, n), encoding="utf-8").read()]
    assert not sem_cta, f"{len(sem_cta)} página(s) sem o link de afiliado: {sem_cta[:10]}"


def test_faixa_de_mercado_nunca_linka_direto_pra_pagina_de_outro_banco():
    """Trava específica do pedido do usuário: a seção de comparação com o
    mercado é uma barra neutra de posição — NUNCA uma lista com link
    clicável pra página de outro banco (isso afastaria o visitante sem
    gerar receita, já que a monetização é por indicação, não por qual
    banco o cliente escolhe). Verifica que dentro do bloco #faixa_texto
    (o texto/CTA da barra) só existe o link de afiliado, nenhum href pra
    financiamento-*.html ou hub-*.html de outro banco."""
    paginas_individuais = [n for n in _arquivos_html() if n.startswith("financiamento-")]
    problemas = []
    for nome_arquivo in paginas_individuais:
        with open(os.path.join(PASTA_SAIDA, nome_arquivo), encoding="utf-8") as f:
            conteudo = f.read()
        m = re.search(r'id="faixa_texto"[^>]*>(.*?)</p>', conteudo, re.DOTALL)
        if not m:
            problemas.append(f"{nome_arquivo}: sem bloco faixa_texto")
            continue
        hrefs = re.findall(r'href="([^"]+)"', m.group(1))
        hrefs_indevidos = [h for h in hrefs if h.startswith("financiamento-") or h.startswith("hub-")]
        if hrefs_indevidos:
            problemas.append(f"{nome_arquivo}: {hrefs_indevidos}")
    assert not problemas, f"{len(problemas)} página(s) com link de concorrente na faixa de mercado: {problemas[:10]}"


def test_comparador_linka_para_hub_de_todos_os_bancos_da_categoria():
    """Substitui o antigo test_comparador_nao_linka_para_hub_de_nenhum_banco
    (achado real, 07/set/2026: o usuário testou o site e reportou "não
    tem simulador nenhum" — investigando, a v1 do comparador de fato
    tirava TODO link pra qualquer hub, deixando as 876 páginas
    individuais alcançáveis só pelo sitemap.xml, órfãs de navegação
    normal e com sinal de importância interna praticamente zero pro
    Google). A regra de negócio original (nunca empurrar o visitante
    pra um CONCORRENTE) continua valendo e é testada à parte em
    test_faixa_de_mercado_nunca_linka_direto_pra_pagina_de_outro_banco
    — mas linkar pra uma página-hub NOSSA (que tem o mesmo CTA de
    afiliado) é o oposto de empurrar o visitante pra fora, é o que
    mantém ele dentro do funil. O projeto irmão (financiamento
    imobiliário) sempre fez assim; aqui tinha ficado restritivo demais."""
    comparadores = [n for n in _arquivos_html() if n.startswith("comparador-")]
    assert comparadores, "nenhuma página de comparador encontrada pra checar"
    # hrefs de página agora são sem ".html" (ver test_todo_link_interno_
    # resolve_para_arquivo_existente) — compara contra o slug, não o
    # nome de arquivo em disco.
    slugs_existentes = {n[:-len(".html")] for n in _arquivos_html()}
    problemas = []
    for nome_arquivo in comparadores:
        with open(os.path.join(PASTA_SAIDA, nome_arquivo), encoding="utf-8") as f:
            conteudo = f.read()
        hrefs_hub = sorted(set(h for h in re.findall(r'href="([^"]+)"', conteudo) if h.startswith("hub-")))
        if not hrefs_hub:
            problemas.append(f"{nome_arquivo}: nenhum link pra hub de banco (página fica um beco sem saída)")
            continue
        quebrados = [h for h in hrefs_hub if h not in slugs_existentes]
        if quebrados:
            problemas.append(f"{nome_arquivo}: link(s) pra hub que não existe(m): {quebrados}")
    assert not problemas, f"{len(problemas)} problema(s) de navegação comparador->hub: {problemas}"


def test_todo_bloco_json_ld_e_json_valido():
    invalidos = []
    for nome_arquivo in _arquivos_html():
        with open(os.path.join(PASTA_SAIDA, nome_arquivo), encoding="utf-8") as f:
            conteudo = f.read()
        for bloco in re.findall(r'<script type="application/ld\+json">(.*?)</script>', conteudo, re.DOTALL):
            try:
                json.loads(bloco)
            except json.JSONDecodeError as e:
                invalidos.append(f"{nome_arquivo}: {e}")
    assert not invalidos, f"{len(invalidos)} bloco(s) JSON-LD inválido(s): {invalidos[:10]}"


def test_toda_pagina_tem_pelo_menos_um_json_ld():
    """404.html excluída — página de erro (noindex) não precisa de schema,
    o Google nem deveria indexar ela pra usar esse dado."""
    paginas = [n for n in _arquivos_html() if n != "404.html"]
    sem_schema = [n for n in paginas if "application/ld+json" not in open(os.path.join(PASTA_SAIDA, n), encoding="utf-8").read()]
    assert not sem_schema, f"páginas sem nenhum JSON-LD: {sem_schema[:10]}"


def test_html_sem_tags_desbalanceadas():
    quebradas = {}
    for nome_arquivo in _arquivos_html():
        with open(os.path.join(PASTA_SAIDA, nome_arquivo), encoding="utf-8") as f:
            conteudo = f.read()
        v = VerificadorBalanceamento()
        v.feed(conteudo)
        if v.erros or v.pilha:
            quebradas[nome_arquivo] = v.erros + [f"não fechada: <{t}>" for t in v.pilha]
    assert not quebradas, f"{len(quebradas)} página(s) com HTML desbalanceado: {dict(list(quebradas.items())[:5])}"


def test_dominio_correto_em_todas_as_paginas():
    """Trava a lição #1 do checklist: a constante de domínio precisa bater
    com o subdomínio real (veiculos.datalabglobal.com) em TODA página, não
    só nalgumas — nenhuma referência ao domínio raiz ou ao domínio do
    produto irmão deveria aparecer em canonical/OG/JSON-LD."""
    DOMINIO_ESPERADO = "https://veiculos.datalabglobal.com"
    problemas = []
    for nome_arquivo in _arquivos_html():
        if nome_arquivo == "404.html":
            continue  # página de erro genérica, sem canonical de propósito (não é uma URL "real" a indexar)
        with open(os.path.join(PASTA_SAIDA, nome_arquivo), encoding="utf-8") as f:
            conteudo = f.read()
        m = re.search(r'rel="canonical" href="([^"]+)"', conteudo)
        if not m or not m.group(1).startswith(DOMINIO_ESPERADO):
            problemas.append(f"{nome_arquivo}: canonical={m.group(1) if m else None}")
        if "simulador.datalabglobal.com" in conteudo or ("datalabglobal.com" in conteudo and DOMINIO_ESPERADO not in conteudo):
            problemas.append(f"{nome_arquivo}: referência a domínio errado")
    assert not problemas, f"{len(problemas)} página(s) com domínio incorreto: {problemas[:10]}"


def test_sitemap_robots_llms_existem_e_citam_o_dominio_certo():
    for nome in ("sitemap.xml", "robots.txt", "llms.txt", "_headers"):
        caminho = os.path.join(PASTA_SAIDA, nome)
        assert os.path.isfile(caminho), f"{nome} não foi gerado"
    with open(os.path.join(PASTA_SAIDA, "sitemap.xml"), encoding="utf-8") as f:
        sitemap = f.read()
    assert "https://veiculos.datalabglobal.com" in sitemap
    assert "simulador.datalabglobal.com" not in sitemap
    with open(os.path.join(PASTA_SAIDA, "robots.txt"), encoding="utf-8") as f:
        robots = f.read()
    assert "Sitemap: https://veiculos.datalabglobal.com/sitemap.xml" in robots


def test_sitemap_lista_todas_as_paginas_geradas():
    """404.html excluída de propósito: não é uma URL de conteúdo real, o
    Cloudflare Pages só a serve automaticamente como fallback de erro —
    colocar ela no sitemap ativamente convidaria o Google a indexar uma
    página de erro, o oposto do que o meta robots=noindex dela já pede.

    URLs no sitemap SEM ".html" (achado real, 10/set/2026 — ver comentário
    em gerar_pagina_individual): o Cloudflare Pages redireciona a versão
    com extensão pra sem extensão, então listar a versão com extensão no
    sitemap mandaria o Google bater num redirect em vez da URL final. A
    home é o único caso especial: vira "{DOMINIO}/", não "{DOMINIO}/index"."""
    with open(os.path.join(PASTA_SAIDA, "sitemap.xml"), encoding="utf-8") as f:
        sitemap = f.read()
    urls_no_sitemap = set(re.findall(r"<loc>(.*?)</loc>", sitemap))
    dominio = "https://veiculos.datalabglobal.com"
    arquivos_esperados = {
        f"{dominio}/" if n == "index.html" else f"{dominio}/{n[:-len('.html')]}"
        for n in _arquivos_html() if n != "404.html"
    }
    faltando = arquivos_esperados - urls_no_sitemap
    assert not faltando, f"{len(faltando)} página(s) gerada(s) mas ausente(s) do sitemap: {list(faltando)[:10]}"


def test_pagina_404_tem_noindex():
    """Mesmo teste do projeto irmão: garante que 404.html nunca perde o
    meta robots=noindex — sem ele, o Google poderia tentar indexar a
    página de erro genérica como se fosse conteúdo de verdade."""
    with open(os.path.join(PASTA_SAIDA, "404.html"), encoding="utf-8") as f:
        conteudo = f.read()
    assert 'name="robots" content="noindex"' in conteudo, "404.html sem noindex — Google poderia tentar indexar a página de erro"
