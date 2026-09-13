"""
Ícones SVG inline (estilo Feather, licença MIT-compatível), substituindo o
carregamento da biblioteca inteira do Font Awesome via CDN só para ~10
ícones. Cada ícone é auto-contido, herda a cor do texto (currentColor) e
escala com o font-size do elemento pai (via width/height: 1em), então
qualquer classe Tailwind de tamanho de texto (text-sm, text-6xl, etc.)
que antes controlava o <i class="fa-..."> continua funcionando igual.

Arquivo copiado do projeto irmão (pseo_simulador/icones.py) — é genérico,
sem nada específico de imóvel. Únicos ícones novos aqui: "car" e
"motorcycle", específicos deste produto.
"""

_ICONES = {
    "arrow-right": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line><polyline points="12 5 19 12 12 19"></polyline></svg>',
    "bolt": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M13 2 3 14h7l-1 8 11-14h-7l0-6z"></path></svg>',
    "shield-check": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><polyline points="9 12 11 14 15 10"></polyline></svg>',
    "external-link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>',
    "download": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
    "link": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>',
    "file-excel": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="9" y1="13" x2="15" y2="19"></line><line x1="15" y1="13" x2="9" y2="19"></line></svg>',
    "whatsapp": '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15l-1.4 5 5.1-1.4A10 10 0 1 0 12 2zm5.6 14.2c-.2.6-1.3 1.2-1.8 1.2-.5.1-1 .1-1.7-.1-.4-.1-.9-.3-1.6-.6-2.8-1.2-4.6-4-4.7-4.2-.1-.2-1.1-1.5-1.1-2.9 0-1.4.7-2 1-2.3.2-.3.5-.3.7-.3h.5c.2 0 .4 0 .6.4.2.5.7 1.7.8 1.8.1.2.1.3 0 .5-.1.2-.1.3-.3.5l-.4.5c-.1.2-.3.3-.1.6.2.3.8 1.3 1.7 2.1 1.2 1 2.1 1.4 2.4 1.5.3.1.5.1.6-.1.2-.2.7-.8.9-1.1.2-.3.4-.2.6-.1.2.1 1.5.7 1.7.8.2.1.4.2.5.3.1.2.1.9-.1 1.5z"></path></svg>',
    "invoice": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 2h11l5 5v13a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"></path><path d="M14 2v5h5"></path><line x1="8" y1="13" x2="16" y2="13"></line><line x1="8" y1="17" x2="13" y2="17"></line></svg>',
    "home": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9.5 12 3l9 6.5"></path><path d="M5 9v11a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9"></path></svg>',
    "percent": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="5" x2="5" y2="19"></line><circle cx="6.5" cy="6.5" r="2.5"></circle><circle cx="17.5" cy="17.5" r="2.5"></circle></svg>',
    "calendar": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>',
    "trending-up": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 17 9 11 13 15 21 6"></polyline><polyline points="15 6 21 6 21 12"></polyline></svg>',
    "info": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="11"></line><circle cx="12" cy="7.5" r="0.9" fill="currentColor" stroke="none"></circle></svg>',
    "bank": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18"></path><path d="M5 21V10"></path><path d="M19 21V10"></path><path d="M9 21V10"></path><path d="M15 21V10"></path><path d="M3 10l9-6 9 6"></path></svg>',
    "book-open": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 5h7a3 3 0 0 1 3 3v12a2.5 2.5 0 0 0-2.5-2.5H2z"></path><path d="M22 5h-7a3 3 0 0 0-3 3v12a2.5 2.5 0 0 1 2.5-2.5H22z"></path></svg>',
    "lightbulb": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18h6"></path><path d="M10 22h4"></path><path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.2 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2z"></path></svg>',
    "repeat": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>',
    "car": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 17h14"></path><path d="M5 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0z" fill="currentColor"></path><path d="M23 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0z" fill="currentColor"></path><path d="M3 17V12l2-5h10l4 5h2v5"></path><path d="M5 12h14"></path></svg>',
    "motorcycle": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="5" cy="17" r="3"></circle><circle cx="19" cy="17" r="3"></circle><path d="M5 17h4l3-6h4"></path><path d="M12 11h3l3 6"></path><path d="M9 11 7 6h3"></path></svg>',
}


def icone(nome, classes_extra=""):
    """Achado real (13/set/2026, auditoria PageSpeed Insights mobile em
    veiculos.datalabglobal.com): "Os links não têm um nome compreensível" —
    ícones decorativos (sempre ao lado de texto visível, exceto onde há
    aria-label explícito no <a>) estavam expostos à árvore de acessibilidade
    sem nome nenhum, fazendo leitor de tela anunciar "imagem" vazio a cada
    ícone. aria-hidden remove o SVG do cômputo de nome acessível do link,
    deixando o texto adjacente (ou o aria-label do <a>, quando não há texto
    visível) ser a única fonte — correção na raiz porque cobre as ~200
    chamadas de icone() no site inteiro de uma vez, sem tocar cada call site."""
    svg = _ICONES.get(nome, "")
    if not svg:
        return ""
    classe = f'inline-block align-[-0.125em] {classes_extra}'.strip()
    return svg.replace("<svg ", f'<svg class="{classe}" style="width:1em;height:1em" aria-hidden="true" focusable="false" ', 1)


def tooltip(texto):
    """Ícone de 'i' com balão explicativo em CSS puro (sem JS, funciona em
    hover no desktop e em toque no mobile via :focus com tabindex). Usado
    para transformar termos técnicos (CET, Tabela Price, IOF...) em
    conteúdo educativo direto na página, sem poluir o layout principal.

    O balão (.tooltip-box) é centralizado no ícone via left-1/2 + margin,
    com largura FIXA (w-56 = 224px). max-w-[calc(100vw-2rem)] garante que
    ele nunca seja mais largo que a tela menos as margens — sem isso,
    ícones perto da borda empurram o balão pra fora do viewport e ele
    conta pro scrollWidth da página mesmo "invisível" (visibility:hidden
    ainda participa do layout; só display:none não participaria, mas
    quebraria a transição suave). Ver também a nota em src/input.css
    sobre por que --tt-shift usa margin-left e não transform.

    A área de toque do ícone (span.tooltip-wrap) seria só ~10x10px sem o
    padding abaixo — WCAG 2.5.5 recomenda pelo menos 44x44px. O p-2.5
    (10px de padding) mais a margem negativa compensatória (-my-2.5) dão
    uma área de toque real de ~30x30px sem aumentar o ícone visualmente
    nem abrir buraco no fluxo do texto ao redor."""
    icone_info = icone('info', 'text-slate-500 hover:text-sky-400 transition-colors')
    return f'''<span class="tooltip-wrap relative inline-flex items-center justify-center ml-0.5 -my-2.5 p-2.5 align-middle" tabindex="0">
        {icone_info}
        <span class="tooltip-box absolute z-20 bottom-full mb-1 w-56 max-w-[calc(100vw-2rem)] p-3 rounded-lg bg-slate-800 border border-white/10 text-[11px] leading-relaxed font-normal text-slate-300 shadow-2xl normal-case tracking-normal">{texto}</span>
    </span>'''
