"""Servidor local de paginas_seo/ para os testes de navegador: imita o Cloudflare Pages (URL sem .html abre o .html) e não imprime log."""
import http.server
import os
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "paginas_seo")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=PASTA, **k)

    def log_message(self, *a, **k):
        pass

    def translate_path(self, path):
        p = super().translate_path(path)
        if not os.path.exists(p) and os.path.exists(p + ".html"):
            return p + ".html"
        return p


def subir(porta=0):
    """Sobe o servidor numa porta livre (porta=0): portas fixas colidiam com os testes dos outros simuladores, que rodam na mesma máquina."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", porta), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
