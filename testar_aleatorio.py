"""Sessões aleatórias no navegador (Chromium e WebKit): 8 sessões x 70 passos (digitar, controle deslizante, trocar tipo e banco, taxa da proposta, lixo).

A cada passo lê o que a tela mostra (valor, entrada, prazo, taxa) e confere parcela, total, CET, % de juros e as linhas do comparativo contra a conta
de referência em Python (gerador_veiculos). Semente fixa (muda com a variável SEMENTE). Precisa do Playwright, fora do CI. Uso: python testar_aleatorio.py
"""
import os
import random
import re
import sys

from playwright.sync_api import sync_playwright

import bancos_veiculos as bv
import gerador_veiculos as gv
import servidor_local

SESSOES = 8
PASSOS = 70
SEMENTE = int(os.environ.get("SEMENTE", "20261120"))
FALHAS = []
LIXO = ["abc", "", "0", "-5", "9999999999", "1e9", "  ", "R$ 12,5", "0,0001", "٣"]


def num(texto):
    t = re.sub(r"[^\d,]", "", texto.replace(".", ""))
    return float(t.replace(",", ".")) if t else 0.0


def passo_confere(pg, tag, modelo, i):
    cat = modelo["cat"]
    valor = num(pg.input_value("#campo-valor"))
    entrada = num(pg.input_value("#campo-entrada"))
    prazo = int(re.search(r"em (\d+) meses", pg.inner_text("#r-sub")).group(1))
    if modelo["taxa_prop"]:
        taxa = modelo["taxa_prop"]
    elif modelo["banco"] == "media":
        ts = [v["taxa_am"] for v in bv.bancos_para_categoria(cat).values()]
        taxa = sum(ts) / len(ts)
    else:
        taxa = bv.BANCOS_VEICULOS[modelo["banco"]]["taxa_am"]
    fin = valor - entrada
    pmt = gv.calcular_pmt_price(fin, prazo, taxa)
    cet = gv.calcular_cet_veiculo(fin, prazo, taxa)
    total = pmt * prazo
    erros = []
    if abs(num(pg.inner_text("#r-parcela")) - round(pmt, 2)) > 0.011:
        erros.append("parcela %s != %.2f" % (pg.inner_text("#r-parcela"), pmt))
    if abs(num(pg.inner_text("#r-total")) - round(total)) > 1.01:
        erros.append("total %s != %.0f" % (pg.inner_text("#r-total"), total))
    if abs(num(pg.inner_text("#r-cet")) - cet) > 0.006:
        erros.append("CET %s != %.2f" % (pg.inner_text("#r-cet"), cet))
    pj = round((total - fin) / total * 100)
    if int(num(pg.text_content("#rosca-pct"))) != pj:
        erros.append("rosca %s != %d%%" % (pg.text_content("#rosca-pct"), pj))
    n_bancos = len(bv.bancos_para_categoria(cat))
    if pg.locator("#cm-linhas .mrow").count() != n_bancos:
        erros.append("linhas do comparativo")
    pmin = bv.entrada_minima(cat)
    if entrada + 1 < valor * pmin - 1 or entrada > valor * 0.9 + 1:
        erros.append("entrada fora da faixa: %s de %s" % (entrada, valor))
    L = gv.VALORES_SIMULADOR[cat]
    if not (L["min"] <= valor <= L["max"]):
        erros.append("valor fora da faixa %s" % valor)
    if not pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"):
        erros.append("rolagem lateral")
    if re.search(r"NaN|undefined|Infinity", pg.inner_text("#resultado") + pg.inner_text("#alts") + pg.inner_text("#cm-linhas")):
        erros.append("NaN/undefined na tela")
    # a linha do comparativo do banco escolhido tem a mesma parcela do painel
    if modelo["banco"] != "media" and not modelo["taxa_prop"] and prazo <= bv.BANCOS_VEICULOS[modelo["banco"]]["prazo_max"]:
        linha = pg.inner_text("#cm-linhas .mrow.us")
        if ("%.2f" % pmt).replace(".", ",") not in linha.replace(".", "").replace(" ", " "):
            erros.append("linha do banco: %s" % linha.replace("\n", " "))
    for e in erros:
        FALHAS.append("%s passo %d: %s" % (tag, i, e))
        print("FALHOU", tag, "passo", i, e)


def sessao(nav, nome, base, largura, rnd, n):
    ctx = nav.new_context(viewport={"width": largura, "height": 900})
    pg = ctx.new_page()
    erros_console = []
    pg.on("console", lambda m: erros_console.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: erros_console.append("PAGEERROR " + str(e)))
    pg.route("**/*umami*", lambda r: r.abort())
    pg.goto(base + "/")
    pg.wait_for_selector("#alts .alt")
    tag = "%s/%d s%d" % (nome, largura, n)
    pg.click("#det-amsim summary")  # os campos de pagar a mais ficam num bloco recolhido
    modelo = {"cat": "novo", "banco": "media", "taxa_prop": 0.0}
    for i in range(1, PASSOS + 1):
        a = rnd.choice(["valor", "valor_slider", "entrada", "entrada_slider", "prazo", "prazo_slider", "cat", "banco", "taxa", "taxa_limpa", "lixo"])
        L = gv.VALORES_SIMULADOR[modelo["cat"]]
        if a == "valor":
            pg.fill("#campo-valor", str(rnd.randrange(L["min"] - 5000, L["max"] + 20000, 500))); pg.press("#campo-valor", "Enter")
        elif a == "valor_slider":
            pg.fill("#range-valor", str(rnd.randrange(L["min"], L["max"] + 1, L["passo"])))
        elif a == "entrada":
            v = num(pg.input_value("#campo-valor"))
            pg.fill("#campo-entrada", str(int(v * rnd.uniform(0.05, 1.0)))); pg.press("#campo-entrada", "Enter")
        elif a == "entrada_slider":
            lo, hi = int(pg.get_attribute("#range-entrada", "min")), int(pg.get_attribute("#range-entrada", "max"))
            pg.fill("#range-entrada", str(rnd.randrange(lo, hi + 1, 500)))
        elif a == "prazo":
            pg.fill("#campo-prazo", str(rnd.randrange(1, 80))); pg.press("#campo-prazo", "Enter")
        elif a == "prazo_slider":
            lo, hi = int(pg.get_attribute("#range-prazo", "min")), int(pg.get_attribute("#range-prazo", "max"))
            pg.fill("#range-prazo", str(rnd.randrange(lo, hi + 1)))
        elif a == "cat":
            modelo["cat"] = rnd.choice(gv.CATEGORIAS)
            pg.click("label[for=cat-%s]" % modelo["cat"])
            if modelo["banco"] != "media" and modelo["banco"] not in bv.bancos_para_categoria(modelo["cat"]):
                modelo["banco"] = "media"
        elif a == "banco":
            pg.click("#btn-banco")
            opcoes = pg.locator("#lista-banco li")
            k = rnd.randrange(0, opcoes.count())
            nome_op = opcoes.nth(k).inner_text().split("\n")[0].strip()
            opcoes.nth(k).click()
            if k == 0:
                modelo["banco"] = "media"
            else:
                modelo["banco"] = next(b for b, v in bv.bancos_para_categoria(modelo["cat"]).items() if (v["nome_exibicao"] or b) == nome_op)
        elif a == "taxa":
            t = round(rnd.uniform(0.3, 6.0), 2)
            if not pg.is_visible("#campo-taxa-prop"):
                pg.click("#det-taxa summary")
            pg.fill("#campo-taxa-prop", str(t).replace(".", ",")); pg.press("#campo-taxa-prop", "Enter")
            modelo["taxa_prop"] = t
        elif a == "taxa_limpa":
            if pg.is_visible("#campo-taxa-prop"):
                pg.fill("#campo-taxa-prop", ""); pg.press("#campo-taxa-prop", "Enter")
            modelo["taxa_prop"] = 0.0
        else:  # lixo em um campo qualquer
            campo = rnd.choice(["#campo-valor", "#campo-entrada", "#campo-prazo", "#campo-conforto", "#campo-extra", "#campo-unico"])
            pg.fill(campo, rnd.choice(LIXO)); pg.press(campo, "Enter")
            if campo == "#campo-prazo":
                pass
        passo_confere(pg, tag, modelo, i)
    if erros_console:
        FALHAS.append(tag + " console: " + str(erros_console[:2]))
        print("FALHOU", tag, "console", erros_console[:2])
    ctx.close()


def main():
    srv = servidor_local.subir()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    rnd = random.Random(SEMENTE)
    with sync_playwright() as pw:
        for nome in ("chromium", "webkit"):
            nav = getattr(pw, nome).launch()
            for largura in (1280, 390):
                for n in range(1, SESSOES // 2 + 1):
                    sessao(nav, nome, base, largura, rnd, n)
            nav.close()
    srv.shutdown()
    total = 2 * 2 * (SESSOES // 2) * PASSOS
    print("\n%d passos conferidos, %d falha(s)." % (total, len(FALHAS)))
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
