"""Gera o logo (SVG), os ícones (favicon, apple-touch-icon, logo-schema), o logo do cabeçalho e a imagem de compartilhamento (og-image.png).

O desenho é o de layout_home.py (frasco de laboratório com líquido e barras de dados, feito à mão em SVG). Precisa do Playwright e do Pillow;
roda na máquina do dono, fora do CI. Os arquivos gerados ficam em paginas_seo/ e são versionados. Uso: python gerar_icones.py
"""
import base64
import os

from PIL import Image
from playwright.sync_api import sync_playwright

import layout_home

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "paginas_seo")
AC = "#0ea5e9"


def _fonte(nome):
    with open(os.path.join(SAIDA, "fonts", nome), "rb") as f:
        return base64.b64encode(f.read()).decode()


def _svg(tamanho):
    return layout_home.LOGO_SVG.replace("@@W@@", str(tamanho))


def _icone_html(lado, cheio=False):
    """cheio=True: quadrado sem cantos arredondados nem borda (o iOS arredonda o apple-touch-icon sozinho; canto transparente vira preto)."""
    if cheio:
        return ("<html><body style='margin:0'><div style='width:%dpx;height:%dpx;display:grid;place-items:center;color:%s;background:linear-gradient(145deg,#0a2a3f,#06101c)'>%s</div></body></html>"
                % (lado, lado, AC, _svg(int(lado * 0.66))))
    return ("<html><body style='margin:0;background:transparent'><div style='width:%dpx;height:%dpx;border-radius:%dpx;display:grid;place-items:center;color:%s;"
            "background:linear-gradient(145deg,#0a2a3f,#06101c);border:%dpx solid rgba(14,165,233,.6);box-sizing:border-box'>%s</div></body></html>"
            % (lado, lado, lado * 0.26, AC, max(1, lado // 40), _svg(int(lado * 0.72))))


def _wordmark_html():
    return ("<html><head><style>@font-face{font-family:'Inter';font-weight:300 700;src:url('data:font/woff2;base64,%s') format('woff2')}"
            "body{margin:0;background:transparent;font-family:'Inter',sans-serif}"
            ".w{display:inline-flex;align-items:center;gap:22px;padding:8px}"
            ".t{width:116px;height:116px;border-radius:32px;display:grid;place-items:center;color:%s;background:linear-gradient(145deg,#0a2a3f,#06101c);border:3px solid rgba(14,165,233,.6);box-sizing:border-box}"
            ".m b{display:block;font-size:64px;font-weight:700;letter-spacing:-.02em;color:#f8fafc;line-height:1}"
            ".m i{display:block;font-style:normal;font-size:19px;letter-spacing:.46em;color:%s;margin-top:11px;font-weight:600}</style></head>"
            "<body><span class='w' id='w'><span class='t'>%s</span><span class='m'><b>Datalab</b><i>GLOBAL</i></span></span></body></html>"
            % (_fonte("inter-latin.woff2"), AC, AC, _svg(84)))


def _og_html():
    with open(os.path.join(AQUI, "src", "og-image.html"), encoding="utf-8") as f:
        h = f.read()
    return h.replace("@@LOGO@@", _svg(104)).replace("@@PLAYFAIR@@", _fonte("playfair-display-latin.woff2")).replace("@@INTER@@", _fonte("inter-latin.woff2"))


def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for nome, lado, omit in (("favicon-32.png", 32, True), ("favicon-192.png", 192, True), ("apple-touch-icon.png", 180, False),
                                 ("logo-schema.png", 512, True), ("_icone-256.png", 256, True)):
            pg = b.new_page(viewport={"width": lado, "height": lado})
            pg.set_content(_icone_html(lado, nome == "apple-touch-icon.png"))
            pg.wait_for_timeout(200)
            pg.screenshot(path=os.path.join(SAIDA, nome), omit_background=omit)
            pg.close()
        pg = b.new_page(viewport={"width": 900, "height": 300})
        pg.set_content(_wordmark_html())
        pg.wait_for_timeout(300)
        pg.locator("#w").screenshot(path=os.path.join(SAIDA, "_wm.png"), omit_background=True)
        pg.close()
        pg = b.new_page(viewport={"width": 1200, "height": 630})
        pg.set_content(_og_html())
        pg.wait_for_timeout(400)
        pg.screenshot(path=os.path.join(SAIDA, "og-image.png"))
        b.close()

    ico = Image.open(os.path.join(SAIDA, "_icone-256.png")).convert("RGBA")
    ico.save(os.path.join(SAIDA, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    os.remove(os.path.join(SAIDA, "_icone-256.png"))

    wm = Image.open(os.path.join(SAIDA, "_wm.png")).convert("RGBA")
    wm = wm.crop(wm.getbbox())
    os.remove(os.path.join(SAIDA, "_wm.png"))
    wm.resize((round(wm.width * 128 / wm.height), 128), Image.LANCZOS).save(os.path.join(SAIDA, "logo-header.webp"), "WEBP", quality=92, method=6)
    wm.resize((round(wm.width * 160 / wm.height), 160), Image.LANCZOS).save(os.path.join(SAIDA, "logo-full.png"))

    cru = _svg(48).replace('width="48" height="48"', 'width="100%" height="100%"').replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    with open(os.path.join(SAIDA, "logo.svg"), "w", encoding="utf-8") as f:
        f.write(cru.replace('stroke="currentColor"', 'stroke="%s" color="%s"' % (AC, AC), 1))
    interno = cru.replace('viewBox="0 0 48 48"', 'viewBox="0 0 48 48" x="6" y="6" width="48" height="48"', 1).replace('width="100%" height="100%"', "", 1)
    with open(os.path.join(SAIDA, "favicon.svg"), "w", encoding="utf-8") as f:
        f.write('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60" width="100%" height="100%"><rect width="60" height="60" rx="15" fill="#06101c" stroke="#0e75a8" stroke-width="1.5"/>'
                + interno.replace('stroke="currentColor"', 'stroke="%s" color="%s"' % (AC, AC), 1) + "</svg>")
    print("Ícones, logos e og-image gerados em", SAIDA)


if __name__ == "__main__":
    main()
