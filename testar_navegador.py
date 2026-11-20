"""Teste de ponta a ponta no navegador (Chromium e WebKit, computador e celular): abre a home gerada e usa o simulador como uma pessoa usaria.

Precisa do Playwright (fora do CI). Sobe um servidor local em paginas_seo/, bloqueia o Umami (não contaminar a medição) e confere os números
contra a conta de referência em Python (gerador_veiculos.calcular_pmt_price / calcular_cet_veiculo). Uso: python testar_navegador.py
"""
import os
import re
import sys

from playwright.sync_api import sync_playwright

import bancos_veiculos as bv
import gerador_veiculos as gv
import servidor_local

AQUI = os.path.dirname(os.path.abspath(__file__))
FALHAS = []
NAVEGADORES = ("chromium", "webkit")
LARGURAS = (1280, 390)


def confere(nome, cond, detalhe=""):
    print(("OK    " if cond else "FALHOU") + " " + nome + (" -> " + str(detalhe) if not cond or detalhe else ""))
    if not cond:
        FALHAS.append(nome)


def centavos(texto):
    """'R$ 2.083,97' -> 208397 ; 'R$ 100.031' -> 100031 (sem centavos no texto)."""
    t = re.sub(r"[^\d,]", "", texto.replace(".", ""))
    return round(float(t.replace(",", ".")) * 100)


def reais(texto):
    return int(re.sub(r"[^\d]", "", texto.split(",")[0]))


def pct(texto):
    return float(re.sub(r"[^\d,]", "", texto).replace(",", "."))


def taxa_media(cat):
    taxas = [v["taxa_am"] for v in bv.bancos_para_categoria(cat).values()]
    return sum(taxas) / len(taxas)


def esperado(valor, pct_entrada, prazo, taxa):
    fin = valor * (1 - pct_entrada)
    pmt = gv.calcular_pmt_price(fin, prazo, taxa)
    return {"fin": fin, "parcela": pmt, "total": pmt * prazo, "juros": pmt * prazo - fin, "cet": gv.calcular_cet_veiculo(fin, prazo, taxa)}


def rodar(nav, nome_nav, base, largura):
    ctx = nav.new_context(viewport={"width": largura, "height": 900}, accept_downloads=False)
    pg = ctx.new_page()
    erros = []
    pg.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: erros.append("PAGEERROR " + str(e)))
    pg.route("**/*umami*", lambda r: r.abort())
    pg.route("**/*cloudflareinsights*", lambda r: r.abort())
    pg.add_init_script("window.umami={track:function(n,d){window.__ev=(window.__ev||[]);window.__ev.push([n,d]);}}")
    tag = nome_nav + "/" + str(largura) + ": "

    pg.goto(base + "/")
    pg.wait_for_selector("#alts .alt")

    # cenário inicial: carro novo, R$ 80 mil, 20% de entrada, 48 meses, média dos bancos
    tx = taxa_media("novo")
    r = esperado(80_000, 0.20, 48, tx)
    confere(tag + "parcela inicial", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.inner_text("#r-parcela"))
    confere(tag + "total inicial", reais(pg.inner_text("#r-total")) == round(r["total"]), pg.inner_text("#r-total"))
    confere(tag + "CET inicial", abs(pct(pg.inner_text("#r-cet")) - r["cet"]) < 0.006, pg.inner_text("#r-cet"))
    confere(tag + "juros no resumo", str(round(r["juros"]))[:2] in re.sub(r"[^\d]", "", pg.inner_text("#r-resumo")), pg.inner_text("#r-resumo"))
    confere(tag + "10 bancos no comparativo", pg.locator("#cm-linhas .mrow").count() == 10)
    confere(tag + "cartões do Raio-X", pg.locator("#alts .alt").count() >= 3)
    sem_rolagem = pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    confere(tag + "sem rolagem lateral", sem_rolagem, pg.evaluate("document.documentElement.scrollWidth"))

    # valor e entrada digitados
    pg.fill("#campo-valor", "120.000"); pg.press("#campo-valor", "Enter")
    r = esperado(120_000, 0.20, 48, tx)
    confere(tag + "valor digitado", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.inner_text("#r-parcela"))
    confere(tag + "entrada acompanha o valor (20%)", reais(pg.input_value("#campo-entrada")) == 24_000, pg.input_value("#campo-entrada"))
    pg.fill("#campo-entrada", "48.000"); pg.press("#campo-entrada", "Enter")
    r = esperado(120_000, 0.40, 48, tx)
    confere(tag + "entrada maior", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.inner_text("#r-parcela"))
    pg.fill("#campo-entrada", "1.000"); pg.press("#campo-entrada", "Enter")
    confere(tag + "entrada abaixo do mínimo é ajustada com aviso", pg.is_visible("#msg-entrada") and reais(pg.input_value("#campo-entrada")) == 24_000, pg.input_value("#campo-entrada"))

    # prazo: lista suspensa e digitação
    confere(tag + "lista de prazos fechada", not pg.is_visible("#lista-prazo"))
    pg.click("#btn-prazo")
    confere(tag + "abre a lista de prazos", pg.is_visible("#lista-prazo") and pg.locator("#lista-prazo li").count() == 9)
    pg.click("#lista-prazo-op-4")  # 36 meses
    r = esperado(120_000, 0.20, 36, tx)
    confere(tag + "prazo pela lista", pg.input_value("#campo-prazo") == "36" and centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.input_value("#campo-prazo"))
    pg.fill("#campo-prazo", "60"); pg.press("#campo-prazo", "Enter")
    r = esperado(120_000, 0.20, 60, tx)
    confere(tag + "prazo digitado (60)", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100))
    pg.click("#btn-prazo"); pg.keyboard.press("Escape")
    confere(tag + "Esc fecha a lista", not pg.is_visible("#lista-prazo"))

    # banco pela lista: taxa do banco; CET do mesmo banco aparece igual no comparativo
    pg.click("#btn-banco")
    confere(tag + "lista de bancos", pg.locator("#lista-banco li").count() == 11)
    pg.click("#lista-banco-op-1")  # menor taxa (Caixa)
    caixa = bv.BANCOS_VEICULOS["Caixa"]["taxa_am"]
    r = esperado(120_000, 0.20, 60, caixa)
    confere(tag + "taxa da Caixa", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.inner_text("#r-parcela"))
    confere(tag + "linha selecionada no comparativo", pg.locator("#cm-linhas .mrow.us").count() == 1)
    linha = pg.inner_text("#cm-linhas .mrow.us")
    confere(tag + "CET da linha bate", f"{r['cet']:.2f}".replace(".", ",") in linha, linha.replace("\n", " "))

    # taxa da proposta própria
    pg.click("#det-taxa summary")
    pg.fill("#campo-taxa-prop", "1,5"); pg.press("#campo-taxa-prop", "Enter")
    r = esperado(120_000, 0.20, 60, 1.5)
    confere(tag + "taxa da proposta", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.inner_text("#r-parcela"))
    confere(tag + "CET com a taxa da proposta", abs(pct(pg.inner_text("#r-cet")) - r["cet"]) < 0.006, pg.inner_text("#r-cet"))
    pg.fill("#campo-taxa-prop", ""); pg.press("#campo-taxa-prop", "Enter")

    # moto: valor e entrada padrão da categoria; Honda limita o prazo a 48 meses
    pg.click("label[for=cat-moto]")
    confere(tag + "moto: valor padrão", reais(pg.input_value("#campo-valor")) == 18_000, pg.input_value("#campo-valor"))
    confere(tag + "moto: entrada 30%", reais(pg.input_value("#campo-entrada")) == 5_400, pg.input_value("#campo-entrada"))
    confere(tag + "moto: 12 bancos", pg.locator("#cm-linhas .mrow").count() == 12)
    pg.click("#btn-banco")
    achou = pg.locator("#lista-banco li", has_text="Banco Honda")
    achou.first.click()
    confere(tag + "Honda: prazo máximo 48 meses, com aviso", pg.input_value("#campo-prazo") == "48" and pg.is_visible("#msg-prazo"), pg.input_value("#campo-prazo"))
    r = esperado(18_000, 0.30, 48, bv.BANCOS_VEICULOS["Banco Honda"]["taxa_am"])
    confere(tag + "moto Honda: parcela", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.inner_text("#r-parcela"))
    pg.click("label[for=cat-usado]")
    confere(tag + "usado: banco volta para a média (Honda não existe aqui)", pg.input_value("#campo-banco") == "Média dos bancos", pg.input_value("#campo-banco"))
    # o prazo pedido (60) volta quando o banco que limitava a 48 sai da lista
    r = esperado(50_000, 0.30, 60, taxa_media("usado"))
    confere(tag + "usado: parcela (prazo pedido volta a 60)", centavos(pg.inner_text("#r-parcela")) == round(r["parcela"] * 100), pg.inner_text("#r-parcela"))

    # pagar a mais: mais dinheiro por mês poupa juros e encurta o prazo
    pg.click("#det-amsim summary")
    confere(tag + "cartões de amortização", pg.locator("#am-cartoes .amc").count() >= 2)
    confere(tag + "economia positiva", reais(pg.inner_text("#am-cartoes .amc .big")) > 0, pg.inner_text("#am-cartoes .amc .big"))

    # link compartilhável
    pg.click("label[for=cat-novo]")
    pg.fill("#campo-valor", "90.000"); pg.press("#campo-valor", "Enter")
    pg.wait_for_timeout(600)
    url = pg.url
    confere(tag + "endereço guarda a simulação", "valor=90000" in url and "tipo=novo" in url, url)
    pg2 = ctx.new_page()
    pg2.route("**/*umami*", lambda r_: r_.abort())
    pg2.goto(url)
    pg2.wait_for_selector("#alts .alt")
    confere(tag + "link reproduz a simulação", pg2.inner_text("#r-parcela") == pg.inner_text("#r-parcela"), pg2.inner_text("#r-parcela"))
    pg2.close()

    # botão do parceiro: abre a tela de confirmação, que leva ao link certo
    confere(tag + "diálogo começa fechado", not pg.is_visible("#dlg-confirma"))
    pg.click("#btn-cta")
    confere(tag + "abre a tela de confirmação", pg.is_visible("#dlg-confirma"))
    href = pg.get_attribute("#a-parceiro", "href")
    confere(tag + "link do parceiro", href == gv.LINK_FINANCIA_TUDO, href)
    confere(tag + "link do parceiro com nofollow/sponsored", "sponsored" in (pg.get_attribute("#a-parceiro", "rel") or "") and pg.get_attribute("#a-parceiro", "target") == "_blank")
    texto_dlg = pg.inner_text("#dlg-confirma").lower()
    confere(tag + "mensagem agnóstica (sem nome do parceiro)", "ftudo" not in texto_dlg and "financiatudo" not in texto_dlg and "parceiro de crédito" in texto_dlg)
    pg.click("#btn-voltar")
    confere(tag + "voltar fecha a tela", not pg.is_visible("#dlg-confirma"))
    ev = pg.evaluate("(window.__ev||[]).map(function(x){return x[0]})")
    confere(tag + "eventos de medição", "abriu-confirmacao" in ev, ev)

    confere(tag + "sem erro de console", not erros, erros[:3])
    ctx.close()


def main():
    try:
        gv.gerar_site  # noqa: B018 (garante que o gerador carregou)
    except AttributeError:
        sys.exit("gerador_veiculos não carregou")
    srv = servidor_local.subir()
    base = f"http://127.0.0.1:{srv.server_address[1]}"
    with sync_playwright() as pw:
        for nome in NAVEGADORES:
            nav = getattr(pw, nome).launch()
            for largura in LARGURAS:
                rodar(nav, nome, base, largura)
            nav.close()
    srv.shutdown()
    print("\n%d falha(s)." % len(FALHAS))
    for f in FALHAS:
        print(" -", f)
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
