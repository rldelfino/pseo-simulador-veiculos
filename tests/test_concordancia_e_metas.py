"""
Concordância de gênero dos bancos femininos ("a Caixa", "a BV Financeira",
"a Omni Financeira") e metas sem corte no meio da frase — achados da
auditoria de SEO de 29/out/2026 (ver bancos_veiculos.py e gerador_veiculos.py).

A parte que lê paginas_seo/ roda só se a pasta já foi gerada
(python gerador_veiculos.py); a função pura roda sempre.
"""
import html
import os
import re

import pytest

from bancos_veiculos import BANCOS_VEICULOS, BANCOS_FEMININOS, corrigir_concordancia

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_SAIDA = os.path.join(RAIZ, "paginas_seo")
gerada = os.path.isdir(PASTA_SAIDA)


@pytest.mark.parametrize("entrada, esperado", [
    ("pelo Caixa em 24x", "pela Caixa em 24x"),
    ("O Omni Financeira permite", "A Omni Financeira permite"),
    ("aqui no BV Financeira", "aqui na BV Financeira"),
    ("do Caixa e do Itaú", "da Caixa e do Itaú"),
    ("ao BV Financeira", "à BV Financeira"),
    ("pelo Banco Pan e o Banco do Brasil", "pelo Banco Pan e o Banco do Brasil"),
    ("/financiamento-carro-novo-caixa-60-mil-24-meses", "/financiamento-carro-novo-caixa-60-mil-24-meses"),
    ("Carro Novo Caixa", "Carro Novo Caixa"),
])
def test_corrigir_concordancia(entrada, esperado):
    assert corrigir_concordancia(entrada) == esperado


def test_bancos_femininos_existem_no_cadastro():
    nomes = {r["nome_exibicao"] for r in BANCOS_VEICULOS.values()}
    assert set(BANCOS_FEMININOS) <= nomes


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_paginas_sem_artigo_masculino_diante_de_banco_feminino():
    ruim = re.compile(r"\b(pelo|do|no|ao|o)\s+(" + "|".join(map(re.escape, BANCOS_FEMININOS)) + r")\b", re.IGNORECASE)
    erros = []
    for nome in os.listdir(PASTA_SAIDA):
        if nome.endswith(".html"):
            texto = open(os.path.join(PASTA_SAIDA, nome), encoding="utf-8").read()
            erros += [(nome, m.group(0)) for m in ruim.finditer(texto) if m.group(2) in BANCOS_FEMININOS]
    assert not erros, erros[:5]


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_descriptions_e_titles_cabem_sem_corte():
    longos = []
    for nome in os.listdir(PASTA_SAIDA):
        if not nome.endswith(".html") or nome == "404.html" or nome.startswith("yandex_"):
            continue
        texto = open(os.path.join(PASTA_SAIDA, nome), encoding="utf-8").read()
        d = re.search(r'name="description" content="([^"]*)"', texto)
        t = re.search(r"<title>([^<]*)</title>", texto)
        if d:
            desc = html.unescape(d.group(1))
            if len(desc) > 160 or desc.endswith(("...", "…")):
                longos.append((nome, "description", len(desc)))
        if t and len(html.unescape(t.group(1))) > 60:
            longos.append((nome, "title", len(t.group(1))))
    assert not longos, longos[:5]


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_rodape_mostra_identidade_da_empresa():
    # mesmo texto já publicado no hub (www.datalabglobal.com): site YMYL
    # precisa dizer quem está por trás.
    faltando = []
    for nome in os.listdir(PASTA_SAIDA):
        if not nome.endswith(".html") or nome == "404.html" or nome.startswith("yandex_"):
            continue
        texto = open(os.path.join(PASTA_SAIDA, nome), encoding="utf-8").read()
        if "<footer" in texto and "CNPJ 63.998.502/0001-73" not in texto:
            faltando.append(nome)
    assert not faltando, faltando[:5]


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_rodape_linka_privacidade_e_termos():
    # site de dinheiro (YMYL): política de privacidade e termos acessíveis em toda página de conteúdo
    faltando = []
    for nome in os.listdir(PASTA_SAIDA):
        if not nome.endswith(".html") or nome in ("404.html", "embed.html") or nome.startswith("yandex_"):
            continue
        texto = open(os.path.join(PASTA_SAIDA, nome), encoding="utf-8").read()
        if "datalabglobal.com/privacidade/" not in texto or "datalabglobal.com/termos/" not in texto:
            faltando.append(nome)
    assert not faltando, faltando[:5]


@pytest.mark.skipif(not gerada, reason="paginas_seo/ não gerada")
def test_rodape_linka_os_outros_simuladores_da_datalab():
    # links diretos (sem redirecionamento) para o empréstimo e para o simulador imobiliário, em toda página com rodapé
    import re
    sitemap = open(os.path.join(PASTA_SAIDA, "sitemap.xml"), encoding="utf-8").read()
    # só as páginas do sitemap: sobram arquivos antigos em paginas_seo/ que o gerador não escreve mais
    nomes = {(u.rstrip("/").rsplit("/", 1)[-1] + ".html") if u.rstrip("/").count("/") > 2 else "index.html"
             for u in re.findall(r"<loc>([^<]+)</loc>", sitemap)}
    faltando = []
    for nome in sorted(nomes):
        caminho = os.path.join(PASTA_SAIDA, nome)
        if not os.path.exists(caminho):
            continue
        texto = open(caminho, encoding="utf-8").read()
        if "<footer" not in texto:
            continue
        if 'href="https://emprestimo.datalabglobal.com/"' not in texto or 'href="https://simulador.datalabglobal.com/"' not in texto:
            faltando.append(nome)
    assert not faltando, faltando[:5]
