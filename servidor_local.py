"""Servidor local de paginas_seo/ para os testes de navegador: imita o Cloudflare Pages (URL sem .html abre o .html) e não imprime log."""
import http.server
import os
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
PASTA = os.path.join(AQUI, "paginas_seo")


def _regras_de_cabecalho():
    """Lê paginas_seo/_headers (formato Cloudflare Pages) e devolve {caminho: {cabecalho: valor}}; '! Nome' remove o herdado de /*."""
    regras, atual = {}, None
    try:
        with open(os.path.join(PASTA, "_headers"), encoding="utf-8") as f:
            for linha in f:
                if not linha.strip() or linha.lstrip().startswith("#"):
                    continue
                if not linha.startswith(" "):
                    atual = linha.strip()
                    regras[atual] = {}
                elif ":" in linha and not linha.strip().startswith("!"):
                    nome, valor = linha.strip().split(":", 1)
                    regras[atual][nome.strip()] = valor.strip()
    except OSError:
        pass
    return regras


class Handler(http.server.SimpleHTTPRequestHandler):
    """Também aplica os cabeçalhos de paginas_seo/_headers (inclusive a CSP própria da home), para o teste pegar violação de CSP."""
    REGRAS = _regras_de_cabecalho()

    def end_headers(self):
        caminho = self.path.split("?")[0]
        aplicar = dict(self.REGRAS.get("/*", {}))
        if caminho in ("/", "/index.html") and "/" in self.REGRAS:
            aplicar.update(self.REGRAS["/"])
        for nome, valor in aplicar.items():
            self.send_header(nome, valor)
        super().end_headers()

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
