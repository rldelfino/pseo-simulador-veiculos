"""
Gerador das páginas pSEO de financiamento de veículos (veiculos.datalabglobal.com).

Segue a mesma arquitetura do projeto irmão (pseo_simulador/gerador.py):
motor de cálculo em Python (server-side, bom pra SEO/crawlers) gerando
HTML estático, MAIS um motor gêmeo em JavaScript (paginas_seo/calculo.js)
pro slider de valor/prazo recalcular ao vivo no navegador — mesmo padrão
de UX do irmão (arrastar e simular pra cada valor), pedido explicitamente
pelo usuário depois de ver a v1 (que era só server-side, decisão que foi
revertida).

Diferente do irmão (que embute a fórmula em JS repetida, colada à mão,
dentro de cada página gerada), aqui o JS vive em UM ÚNICO arquivo
estático (calculo.js) referenciado por <script src> em toda página — o
navegador baixa e cacheia uma vez só em vez de repetir a mesma centena
de linhas em cada um dos milhares de HTMLs, e havendo só uma cópia do
arquivo, um teste Node (tests/test_calculo_js.mjs) pode comparar a saída
do JS com a do Python pros mesmos cenários — trava automatizada que o
irmão não tem (lá a dessincronia entre as duas cópias já causou um bug
real, "Comparação com o Mercado" congelada no cenário padrão).

MODELO DE NEGÓCIO — por que a "comparação com outros bancos" nunca vira
um ranking numerado com medalha de "melhor banco": a monetização é por
indicação (lead quente pro correspondente bancário), não por qual banco
o cliente escolhe — ao contrário de um comparador de preços comum, aqui
não faz sentido nenhum "empurrar" o visitante pro banco mais barato como
se fosse o vencedor, porque isso não muda a receita (é indiferente qual
banco o cliente feche) e ainda dá a um banco específico um destaque
editorial que não temos como sustentar de forma imparcial. Por isso a
seção de comparação é uma barra neutra de POSIÇÃO no mercado (menor CET
... maior CET, com um marcador por banco), sem #1º/#2º nem "🏆 melhor
taxa" — mesmo padrão do "box de posição no mercado" do projeto irmão
(ver gerar_hub_bancos() em gerador.py de lá).

Achado real (07/set/2026, revisão pedida pelo usuário depois de testar
o site: "não tem simulador nenhum"): a v1 desta regra tinha ido longe
demais e cortado TAMBÉM o link do comparador pra página-hub de cada
banco — a "barra neutra" ficou tão neutra que virou um beco sem saída,
sem nenhum caminho de navegação normal (clicando) até as 876 páginas
de simulação, que só existiam pro Google via sitemap.xml. A distinção
que importa: link pra HUB é link pra conteúdo NOSSO (mesmo domínio,
mesmo CTA de afiliado no fim) — mantém o visitante dentro do funil, é o
oposto de "empurrar pra fora". O que continua proibido é: (a) qualquer
link pra fora do domínio que não seja o de afiliado, e (b) qualquer
hierarquia editorial de "melhor/pior banco" (número de posição, medalha,
badge). Comparador agora linka pra cada hub (favicon do banco + CET),
sem ranking numerado — ver gerar_comparador() e o teste
test_comparador_linka_para_hub_de_todos_os_bancos_da_categoria.

ÁRVORE DE PÁGINAS (decidida com o usuário antes de codar):
  categoria (novo | usado | moto)
    -> banco elegível naquela categoria (bancos_veiculos.aplica_a)
      -> valor do veículo (grade por categoria, VALORES_POR_CATEGORIA)
        -> prazo em meses (grade comum, limitada ao prazo_max do banco)
Cada folha da árvore = 1 página estática. Entrada/valor financiado não
são eixos livres: são derivados de ENTRADA_MINIMA_POR_CATEGORIA (mesmo
papel que o LTV cumpre no financiamento imobiliário).

Estrutura de conteúdo, do mais específico ao mais geral (evita
conteúdo quase-duplicado entre níveis — cada nível responde uma pergunta
de busca diferente):
  financiamento-{categoria}-{banco}-{valor}-mil-{prazo}-meses.html
      -> 1 cenário exato (banco+valor+prazo): parcela, CET, amortização.
  hub-{banco}-{categoria}.html
      -> todas as combinações de valor/prazo daquele banco nessa categoria.
  comparador-{categoria}.html
      -> ranking de TODOS os bancos elegíveis nessa categoria, um cenário
         de referência por vez — também serve de "hub da categoria"
         (decidiu-se não ter uma página extra só de índice por categoria:
         seria conteúdo quase-duplicado do comparador, um anti-padrão de
         SEO por canibalização).
  index.html -> linka os 3 comparadores de categoria.
"""

import html
import json
import math
import os
from datetime import date, datetime

from bancos_veiculos import (
    BANCOS_VEICULOS,
    bancos_para_categoria,
    corrigir_concordancia,
    entrada_minima,
    normalizar_chave,
    obter_regra,
)
from icones import icone, tooltip

DOMINIO = 'https://veiculos.datalabglobal.com'
# Identidade da empresa por trás do site — mesmo texto já publicado no rodapé
# e no schema Organization do hub (www.datalabglobal.com). Achado de auditoria
# (29/out/2026): os simuladores, que são tema YMYL (dinheiro), não mostravam
# razão social nem CNPJ; o hub mostrava. Texto copiado do hub, não inventado.
EMPRESA_RODAPE = "Satori Soluções Comerciais LTDA · CNPJ 63.998.502/0001-73"

# Cache-busting do styles.css (achado real, 07/set/2026: durante os testes
# desta sessão, o navegador serviu uma versão cacheada e desatualizada do
# CSS várias vezes seguidas — mesmo depois de "python gerador_veiculos.py"
# + "npm run build:css" já terem sido rodados de novo — porque o servidor
# local (python -m http.server) não manda nenhum header de cache, e o
# navegador cacheia de forma heurística sem nunca revalidar. Isso fazia o
# HTML novo carregar junto com classes Tailwind AUSENTES da folha antiga
# (ex: w-40 sumindo, o campo de valor "vazando" pra fora do card; w-24/h-24
# sumindo, o donut virando um círculo gigante sem proporção) — um bug de
# CACHE, não do HTML/CSS gerado, mas visualmente indistinguível de um bug
# real sem investigar. Same problema se aplicaria em produção (Cloudflare
# Pages já limita isso a 1h via _headers, mas ainda existe uma janela).
# Um timestamp gerado a cada rodagem, anexado como query string no link do
# stylesheet, garante que toda regeneração force o navegador a buscar o
# CSS de novo — elimina essa classe de confusão de vez.
VERSAO_BUILD = datetime.now().strftime('%Y%m%d%H%M%S')
ARQUIVO_ULTIMA_ATUALIZACAO = 'ultima_atualizacao_taxas.txt'

_URL_GOOGLE_FONTS = (
    "https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700"
    "&family=Inter:wght@300;400;500;600;700&display=swap"
)
# Achado real (13/set/2026, PageSpeed Insights mobile em veiculos.data-
# labglobal.com): o <link rel="stylesheet"> síncrono pro Google Fonts era
# o maior item de "solicitações que bloqueiam a renderização" (~1970ms de
# economia estimada) — o navegador para de renderizar a página até baixar
# o CSS da fonte de um domínio terceiro antes mesmo de saber quais glifos
# vai precisar. Troca pelo padrão "loadCSS" (preload + media=print que
# vira media=all no onload): o CSS da fonte carrega em paralelo sem
# bloquear o first paint, com <noscript> como rede de segurança pra quem
# desabilita JS. O onload inline funciona sob o CSP do site porque
# script-src já inclui 'unsafe-inline' (ver gerar_headers()).
GOOGLE_FONTS_LINK_ASSINCRONO = (
    f'<link rel="preload" as="style" href="{_URL_GOOGLE_FONTS}">\n'
    f'    <link rel="stylesheet" href="{_URL_GOOGLE_FONTS}" media="print" onload="this.media=\'all\'">\n'
    f'    <noscript><link rel="stylesheet" href="{_URL_GOOGLE_FONTS}"></noscript>'
)

# Link de afiliado (correspondente bancário) — passado pelo usuário
# verbatim. NÃO alterar o domínio/formato sem confirmar com ele: um erro
# aqui custa comissão real, não é um detalhe cosmético.
LINK_FINANCIA_TUDO = "https://ftudo.com/rodolfo-financiamento-de-automoveis/"

CATEGORIAS = ["novo", "usado", "moto"]
CATEGORIA_LABEL = {"novo": "Carro Novo", "usado": "Carro Usado", "moto": "Moto"}
CATEGORIA_SLUG = {"novo": "carro-novo", "usado": "carro-usado", "moto": "moto"}
CATEGORIA_ARTIGO = {"novo": "um carro novo", "usado": "um carro usado", "moto": "uma moto"}

# Grade de valores por categoria — faixas bem diferentes de ordem de
# grandeza (moto não pode usar a mesma grade de carro). Prazos são uma
# grade única, cortada pelo prazo_max de cada banco na hora de gerar.
VALORES_POR_CATEGORIA = {
    "novo": [60_000, 80_000, 100_000, 120_000, 150_000, 200_000],
    "usado": [20_000, 30_000, 40_000, 60_000, 80_000],
    "moto": [8_000, 12_000, 18_000, 25_000, 35_000],
}
PRAZOS_MESES = [12, 24, 36, 48, 60]


# ---------------------------------------------------------------------------
# Motor de cálculo
# ---------------------------------------------------------------------------

def calcular_pmt_price(valor_financiado, prazo_meses, taxa_am):
    """Parcela fixa pela Tabela Price. É praticamente o único sistema usado
    em CDC de veículo no Brasil — SAC é particularidade do financiamento
    imobiliário (SFH); nenhum banco do mercado oferece SAC pra carro/moto,
    por isso (diferente do projeto irmão) não há alternância de sistema
    aqui."""
    if valor_financiado <= 0 or prazo_meses <= 0:
        return 0.0
    i = taxa_am / 100
    if i == 0:
        return valor_financiado / prazo_meses
    fator = (1 + i) ** prazo_meses
    return valor_financiado * (i * fator) / (fator - 1)


def calcular_iof_veiculo(valor_financiado, prazo_meses):
    """IOF real sobre operação de crédito para pessoa física (Decreto
    6.306/2007, art. 7º): 0,38% fixo sobre o valor financiado + 0,0082% ao
    dia, limitado a 365 dias corridos (dias além disso não aumentam mais
    o IOF). Contamos os dias como prazo_meses * 30 (convenção padrão de
    mercado pra esse cálculo).

    Diferente das taxas de seguro usadas no CET do irmão (estimativas de
    mercado, não públicas de forma padronizada), esta é uma alíquota de
    lei — não carrega a mesma ressalva de "não é o valor exato do banco"."""
    if valor_financiado <= 0 or prazo_meses <= 0:
        return 0.0
    ALIQUOTA_FIXA = 0.0038
    ALIQUOTA_DIARIA = 0.000082
    dias = min(prazo_meses * 30, 365)
    return valor_financiado * (ALIQUOTA_FIXA + ALIQUOTA_DIARIA * dias)


# Estimativas conservadoras de mercado (não públicas de forma padronizada
# por banco) — mesma natureza das taxas de seguro MIP/DFI usadas no CET do
# financiamento imobiliário: o objetivo não é reproduzir o CET exato que o
# banco vai apresentar na proposta (impossível sem saber seguradora
# escolhida, relacionamento do cliente etc.), e sim dar um número bem mais
# realista que "taxa de juros anunciada" pura, pra efeito de comparação.
TARIFA_REGISTRO_CONTRATO = 120.00   # gravame eletrônico (DETRAN), valor típico
SEGURO_PRESTAMISTA_MENSAL = 0.00035  # ~0,035% do saldo devedor/mês


def calcular_cet_veiculo(valor_financiado, prazo_meses, taxa_am):
    """CET real via TIR (Taxa Interna de Retorno) do fluxo de caixa
    completo — mesma técnica do projeto irmão (bisseção sobre a TIR
    mensal), adaptada pra CDC de veículo: o cliente recebe efetivamente
    (valor_financiado - IOF - tarifa de registro) mas paga a parcela cheia
    calculada sobre valor_financiado. É essa diferença entre o que entra e
    o que sai que o CET capta e a taxa de juros nominal sozinha esconde."""
    if valor_financiado <= 0 or prazo_meses <= 0:
        return 0.0

    taxa_mensal = taxa_am / 100
    pmt = calcular_pmt_price(valor_financiado, prazo_meses, taxa_am)
    iof = calcular_iof_veiculo(valor_financiado, prazo_meses)

    saldo = valor_financiado
    fluxo = []
    for _ in range(prazo_meses):
        juros = saldo * taxa_mensal
        amortizacao = pmt - juros
        seguro = saldo * SEGURO_PRESTAMISTA_MENSAL
        fluxo.append(pmt + seguro)
        saldo -= amortizacao

    valor_liquido_recebido = valor_financiado - iof - TARIFA_REGISTRO_CONTRATO

    def vpl(r):
        total = -valor_liquido_recebido
        for i, cf in enumerate(fluxo, start=1):
            total += cf / ((1 + r) ** i)
        return total

    # Bisseção: mesmo com o banco mais caro do mercado (Omni, ~3,35% a.m.
    # nominal) mais custos, a TIR mensal real fica com folga bem abaixo de
    # 8% a.m. — teto generoso o suficiente pra não estourar a busca.
    #
    # Achado real (08/set/2026, auditoria pedida pelo usuário): esse "banco
    # mais caro" é uma garantia sobre taxa_am (fixa, vem do BACEN), mas
    # valor/prazo NÃO são fixos do lado do simulador ao vivo (calculo.js)
    # — o visitante pode arrastar o slider pra qualquer combinação dentro
    # do range permitido. A bisseção não valida sinal oposto em vpl(lo)/
    # vpl(hi) antes de buscar: se algum dia a TIR real passar de 8% a.m.,
    # a busca converge silenciosamente perto do teto e devolve um CET
    # errado (subestimado), sem nenhum sinal de falha. Teto dobrado pra
    # 15% como margem de segurança mais folgada (o pior caso hoje mapeado
    # — moto no valor mínimo do slider com o prazo mínimo — fica bem
    # abaixo até de 8%, então 15% não muda nenhum resultado real, só
    # afasta a borda). JS (calculo.js) espelha o mesmo teto.
    lo, hi = 0.0, 0.15
    for _ in range(60):
        mid = (lo + hi) / 2
        if vpl(mid) > 0:
            lo = mid
        else:
            hi = mid
    tir_mensal = (lo + hi) / 2
    return round(((1 + tir_mensal) ** 12 - 1) * 100, 2)


def gerar_tabela_amortizacao(valor_financiado, prazo_meses, taxa_am):
    """Tabela Price mês a mês (parcela, juros, amortização, saldo) — usada
    tanto pro conteúdo da página quanto pelos testes de regressão."""
    taxa_mensal = taxa_am / 100
    pmt = calcular_pmt_price(valor_financiado, prazo_meses, taxa_am)
    saldo = valor_financiado
    linhas = []
    for mes in range(1, prazo_meses + 1):
        juros = saldo * taxa_mensal
        amortizacao = pmt - juros
        saldo = max(0.0, saldo - amortizacao)
        linhas.append({"mes": mes, "parcela": pmt, "juros": juros, "amortizacao": amortizacao, "saldo": saldo})
    return linhas


def calcular_renda_sugerida(parcela):
    """Regra de comprometimento de renda de mercado: parcela não deve
    passar de 30% da renda."""
    return parcela / 0.30 if parcela > 0 else 0.0


def comparar_bancos_categoria(categoria, valor_veiculo, prazo, lookup_paginas=None):
    """Ranking (por CET, crescente) de todos os bancos elegíveis pra uma
    categoria de veículo, no mesmo cenário de valor/prazo. Bancos cujo
    prazo_max é menor que o prazo pedido entram com o prazo deles mesmo
    (capado), igual ao produto irmão faz com prazo_maximo."""
    lookup_paginas = lookup_paginas or {}
    entrada_pct = entrada_minima(categoria)
    resultados = []
    for banco, dados in bancos_para_categoria(categoria).items():
        prazo_banco = min(prazo, dados["prazo_max"])
        entrada = valor_veiculo * entrada_pct
        valor_financiado = valor_veiculo - entrada
        pmt = calcular_pmt_price(valor_financiado, prazo_banco, dados["taxa_am"])
        cet = calcular_cet_veiculo(valor_financiado, prazo_banco, dados["taxa_am"])
        slug = lookup_paginas.get((categoria, banco, valor_veiculo, prazo_banco))
        resultados.append({
            "banco": banco, "nome_exibicao": dados["nome_exibicao"],
            "taxa_am": dados["taxa_am"], "taxa_aa": dados["taxa_aa"],
            "cet": cet, "parcela": pmt, "prazo": prazo_banco,
            "slug": slug, "dominio_favicon": dados["dominio_favicon"],
        })
    resultados.sort(key=lambda r: r["cet"])
    return resultados


def formatar_reais(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_valor_curto(valor):
    """Ex: 80000 -> '80 mil'. Casa com a forma como as pessoas digitam a
    busca (mesma função do projeto irmão)."""
    milhares = int(round(valor / 1000))
    return f"{milhares} mil"


# ---------------------------------------------------------------------------
# Slugs e grade de páginas
# ---------------------------------------------------------------------------

def slugificar_banco(banco):
    return normalizar_chave(banco).lower().replace(' ', '-')


def gerar_slug_pagina(categoria, banco, valor, prazo):
    valor_k = int(round(valor / 1000))
    return f"financiamento-{CATEGORIA_SLUG[categoria]}-{slugificar_banco(banco)}-{valor_k}-mil-{prazo}-meses"


def slug_hub(categoria, banco):
    return f"hub-{slugificar_banco(banco)}-{CATEGORIA_SLUG[categoria]}"


def slug_comparador(categoria):
    return f"comparador-{CATEGORIA_SLUG[categoria]}"


def gerar_grade_paginas():
    """Monta a árvore inteira (categoria -> banco -> valor -> prazo) e
    devolve uma lista de dicts, um por página final a gerar. Prazos acima
    do prazo_max do banco simplesmente não geram página (mesmo
    comportamento do produto irmão com prazo_maximo)."""
    paginas = []
    for categoria in CATEGORIAS:
        entrada_pct = entrada_minima(categoria)
        for banco, dados in bancos_para_categoria(categoria).items():
            for valor in VALORES_POR_CATEGORIA[categoria]:
                entrada = valor * entrada_pct
                valor_financiado = valor - entrada
                for prazo in PRAZOS_MESES:
                    if prazo > dados["prazo_max"]:
                        continue
                    pmt = calcular_pmt_price(valor_financiado, prazo, dados["taxa_am"])
                    cet = calcular_cet_veiculo(valor_financiado, prazo, dados["taxa_am"])
                    paginas.append({
                        "categoria": categoria, "banco": banco,
                        "nome_exibicao": dados["nome_exibicao"],
                        "valor_veiculo": valor, "entrada": entrada,
                        "valor_financiado": valor_financiado, "prazo": prazo,
                        "taxa_am": dados["taxa_am"], "taxa_aa": dados["taxa_aa"],
                        "prazo_max_banco": dados["prazo_max"],
                        "parcela": pmt, "cet": cet,
                        "slug": gerar_slug_pagina(categoria, banco, valor, prazo),
                        "dominio_favicon": dados["dominio_favicon"],
                    })
    return paginas


def montar_lookup(paginas):
    return {(p["categoria"], p["banco"], p["valor_veiculo"], p["prazo"]): p["slug"] for p in paginas}


# ---------------------------------------------------------------------------
# HTML — partes compartilhadas
#
# JSON-LD é montado como dict Python + json.dumps (não como f-string com
# chaves escapadas manualmente, jeito que o projeto irmão usa) — evita uma
# classe inteira de bug (chave desbalanceada num schema.org por um {{ }}
# esquecido) e garante que o bloco sempre é JSON válido por construção.
# ---------------------------------------------------------------------------

def obter_data_ultima_atualizacao():
    """Mesma lógica do projeto irmão: usa a data REAL da última coleta de
    taxas (gravada manualmente após consultar o relatório do BACEN), não
    a data do deploy — 'lastmod sempre = hoje' é sinal de frescor falso
    pro Google."""
    try:
        with open(ARQUIVO_ULTIMA_ATUALIZACAO, encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return date.today().isoformat()


def gerar_logo_svg():
    """Mesmo logo do projeto irmão (identidade visual única da família de
    produtos Datalab Global) — genérico, sem texto específico de imóvel."""
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 200" width="100%" height="100%">
    <defs>
        <linearGradient id="emeraldGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#34d399" /><stop offset="100%" stop-color="#047857" /></linearGradient>
        <linearGradient id="emeraldDark" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#059669" /><stop offset="100%" stop-color="#022c22" /></linearGradient>
        <filter id="glowMedium" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.5" result="blur" /><feComposite in="SourceGraphic" in2="blur" operator="over" /></filter>
    </defs>
    <g transform="translate(60, 50)">
        <g opacity="0.8">
            <ellipse cx="40" cy="40" rx="78" ry="44" fill="none" stroke="#34d399" stroke-width="1" stroke-dasharray="8 8" opacity="0.3"/>
            <ellipse cx="40" cy="40" rx="64" ry="36" fill="none" stroke="#059669" stroke-width="1" opacity="0.4"/>
            <ellipse cx="40" cy="40" rx="78" ry="44" fill="none" stroke="#fef08a" stroke-width="1.8" stroke-dasharray="35 300" stroke-dashoffset="15" stroke-linecap="round" filter="url(#glowMedium)" opacity="0.8"/>
            <circle cx="118" cy="40" r="2.5" fill="#fef08a" filter="url(#glowMedium)"/><circle cx="118" cy="40" r="1" fill="#ffffff"/><circle cx="-38" cy="40" r="2.5" fill="#34d399" filter="url(#glowMedium)"/><circle cx="70" cy="-2" r="1.5" fill="#ffffff" opacity="0.6"/>
        </g>
        <path d="M 40 80 L 40 40 L 5 20 L 5 60 Z" fill="url(#emeraldDark)" opacity="0.85"/><path d="M 40 80 L 40 40 L 75 20 L 75 60 Z" fill="#064e3b" opacity="0.9"/><path d="M 40 40 L 75 20 L 40 0 L 5 20 Z" fill="url(#emeraldGrad)"/>
        <line x1="40" y1="40" x2="40" y2="80" stroke="#022c22" stroke-width="1.5" /><line x1="40" y1="40" x2="5" y2="20" stroke="#34d399" stroke-width="1" opacity="0.5" /><line x1="40" y1="40" x2="75" y2="20" stroke="#34d399" stroke-width="1" opacity="0.5" />
        <line x1="40" y1="0" x2="5" y2="20" stroke="#fef08a" stroke-width="2" filter="url(#glowMedium)"/><line x1="40" y1="0" x2="75" y2="20" stroke="#fef08a" stroke-width="2" filter="url(#glowMedium)"/><line x1="40" y1="0" x2="40" y2="40" stroke="#fef08a" stroke-width="2.5" filter="url(#glowMedium)"/><line x1="5" y1="20" x2="40" y2="40" stroke="#10b981" stroke-width="1.5" /><line x1="75" y1="20" x2="40" y2="40" stroke="#10b981" stroke-width="1.5" />
        <circle cx="40" cy="0" r="4.5" fill="#fef08a" filter="url(#glowMedium)"/><circle cx="40" cy="0" r="2" fill="#ffffff"/><circle cx="5" cy="20" r="3.5" fill="#34d399" filter="url(#glowMedium)"/><circle cx="75" cy="20" r="3.5" fill="#34d399" filter="url(#glowMedium)"/><circle cx="40" cy="40" r="4.5" fill="#fef08a" filter="url(#glowMedium)"/><circle cx="40" cy="40" r="2" fill="#ffffff"/><circle cx="40" cy="80" r="3" fill="#059669"/>
    </g>
    <text x="185" y="105" font-family="'Playfair Display', Georgia, serif" font-size="64" font-weight="700" fill="#ffffff">Datalab</text>
    <text x="190" y="145" font-family="'Inter', system-ui, sans-serif" font-size="20" font-weight="600" fill="#10b981" letter-spacing="14">GLOBAL</text>
    <circle cx="375" cy="139" r="2.5" fill="#fef08a" filter="url(#glowMedium)"/>
</svg>"""


def gerar_favicon_svg(pasta_saida):
    """Ícone quadrado (só o cubo, sem o texto "Datalab"+"GLOBAL" de
    logo.svg) pra usar como favicon — copiado do projeto irmão
    (pseo_simulador/gerador.py:gerar_favicon_svg) sem alteração: é o
    MESMO ícone de marca (cores emerald sólidas, sem gradiente/glow — ver
    docstring original sobre a limitação do svglib com fill="url(...)"),
    de propósito idêntico ao do imobiliário. Achado real (06/set/2026,
    aplicado primeiro no projeto irmão): sem favicon nenhum, o Google
    mostra o domínio cru com ícone genérico em vez do nome da marca; a
    correção foi replicada aqui pra manter os dois produtos "irmãos" no
    mesmo padrão de indexação, mesmo o veicular ainda não estando no ar.

    O favicon fica verde (cor do logo.svg deste mesmo projeto, que também
    é verde) por decisão explícita: o logo é identidade CORPORATIVA
    compartilhada entre os produtos Datalab Global, enquanto o azul é a
    cor de PRODUTO (só do veicular) — ver decisão documentada em
    ilustracao_categoria() sobre a mesma distinção."""
    svg_favicon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="-10 -10 100 100" width="100%" height="100%">
    <rect x="-10" y="-10" width="100" height="100" fill="#022c22"/>
    <path d="M 40 80 L 40 40 L 5 20 L 5 60 Z" fill="#065f46" opacity="0.85"/><path d="M 40 80 L 40 40 L 75 20 L 75 60 Z" fill="#064e3b" opacity="0.9"/><path d="M 40 40 L 75 20 L 40 0 L 5 20 Z" fill="#34d399"/>
    <line x1="40" y1="40" x2="40" y2="80" stroke="#022c22" stroke-width="1.5" /><line x1="40" y1="40" x2="5" y2="20" stroke="#34d399" stroke-width="1" opacity="0.5" /><line x1="40" y1="40" x2="75" y2="20" stroke="#34d399" stroke-width="1" opacity="0.5" />
    <line x1="40" y1="0" x2="5" y2="20" stroke="#fef08a" stroke-width="2"/><line x1="40" y1="0" x2="75" y2="20" stroke="#fef08a" stroke-width="2"/><line x1="40" y1="0" x2="40" y2="40" stroke="#fef08a" stroke-width="2.5"/><line x1="5" y1="20" x2="40" y2="40" stroke="#10b981" stroke-width="1.5" /><line x1="75" y1="20" x2="40" y2="40" stroke="#10b981" stroke-width="1.5" />
    <circle cx="40" cy="0" r="4.5" fill="#fef08a"/><circle cx="40" cy="0" r="2" fill="#ffffff"/><circle cx="5" cy="20" r="3.5" fill="#34d399"/><circle cx="75" cy="20" r="3.5" fill="#34d399"/><circle cx="40" cy="40" r="4.5" fill="#fef08a"/><circle cx="40" cy="40" r="2" fill="#ffffff"/><circle cx="40" cy="80" r="3" fill="#059669"/>
</svg>"""
    with open(os.path.join(pasta_saida, 'favicon.svg'), "w", encoding="utf-8") as f:
        f.write(svg_favicon)
    return svg_favicon


def rasterizar_favicon_png(pasta_saida):
    """Converte favicon.svg em PNG/ICO — fallback pra navegadores/crawlers
    antigos, mesma função do projeto irmão (ver gerador.py:
    rasterizar_favicon_png pro raciocínio completo de cada detalhe, ex.
    por que recarrega o SVG do zero por tamanho). Gera favicon.ico,
    apple-touch-icon.png (180x180) e logo-schema.png (512x512, usado como
    "logo" no schema.org Organization). Não roda automaticamente em
    gerar_site() pelo mesmo motivo do irmão: depende de svglib/reportlab,
    que não são dependência do site em si — rodar à mão só quando o
    desenho do ícone mudar, e comitar os 3 arquivos gerados como estático."""
    try:
        from svglib.svglib import svg2rlg
        from reportlab.graphics import renderPM
    except ImportError:
        print("⚠️  svglib/reportlab não instalados — pulando favicon.ico/apple-touch-icon.png. Rode: pip install svglib reportlab")
        return

    caminho_svg = os.path.join(pasta_saida, 'favicon.svg')

    def _renderizar_png(tamanho_px, caminho_saida):
        desenho = svg2rlg(caminho_svg)
        fator = tamanho_px / desenho.width
        desenho.width = desenho.height = tamanho_px
        desenho.scale(fator, fator)
        renderPM.drawToFile(desenho, caminho_saida, fmt="PNG", bg=0x022c22)

    caminho_180 = os.path.join(pasta_saida, 'apple-touch-icon.png')
    caminho_512 = os.path.join(pasta_saida, 'logo-schema.png')
    _renderizar_png(180, caminho_180)
    _renderizar_png(512, caminho_512)

    from PIL import Image
    tamanhos_ico = [16, 32, 48]
    caminhos_tmp = []
    for tamanho in tamanhos_ico:
        caminho_tmp = os.path.join(pasta_saida, f'_favicon_tmp_{tamanho}.png')
        _renderizar_png(tamanho, caminho_tmp)
        caminhos_tmp.append(caminho_tmp)
    imagens = []
    for c in caminhos_tmp:
        img = Image.open(c)
        img.load()
        imagens.append(img)
    imagens[0].save(
        os.path.join(pasta_saida, 'favicon.ico'),
        format='ICO',
        sizes=[(t, t) for t in tamanhos_ico],
        append_images=imagens[1:],
    )
    for c in caminhos_tmp:
        os.remove(c)
    print("✅ favicon.ico, apple-touch-icon.png e logo-schema.png gerados a partir de favicon.svg.")


def gerar_calculo_js():
    """Motor de cálculo em JavaScript — espelha EXATAMENTE calcular_pmt_price,
    calcular_iof_veiculo, calcular_cet_veiculo e gerar_tabela_amortizacao
    deste mesmo arquivo (Python). Ver tests/test_calculo_js.mjs: compara a
    saída deste arquivo com a do Python pros mesmos cenários — qualquer
    mudança de fórmula num lado sem atualizar o outro quebra esse teste,
    em vez de só divergir silenciosamente em produção (foi assim que o
    projeto irmão perdeu a sincronia uma vez).

    Fica em UM arquivo estático (não inline em cada página) de propósito:
    o navegador baixa e cacheia uma vez só, em vez de repetir a mesma
    fórmula em cada uma das 800+ páginas."""
    return '''// Gerado por gerador_veiculos.py (gerar_calculo_js) — não editar à mão
// sem também atualizar o lado Python e tests/test_calculo_js.mjs.
'use strict';

function unformatCurrency(val) { return typeof val === 'number' ? val : Number(String(val).replace(/\\D/g, '')) / 100; }
function formatCurrency(val) { return (val).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
function formatarReais(val) { return 'R$ ' + formatCurrency(val); }

function initMask(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    let rawVal = unformatCurrency(input.value);
    if (rawVal > 0) input.value = formatCurrency(rawVal);
    input.addEventListener('input', function (e) {
        let raw = unformatCurrency(e.target.value);
        e.target.value = formatCurrency(raw);
    });
}

// Só reinicia a animação de pulso quando o valor realmente muda — evita
// reiniciar em toda chamada de atualizarSimulacao(), inclusive quando
// nada mudou (lição do irmão: WCAG/prefers-reduced-motion já tratados no
// CSS via @media, isso aqui evita o pulso "nervoso" de re-disparar à toa).
function atualizarValor(id, texto) {
    const el = document.getElementById(id);
    if (!el || el.innerText === texto) return;
    el.innerText = texto;
    el.classList.remove('valor-pulse');
    void el.offsetWidth; // força reflow, senão o navegador não reinicia a animação
    el.classList.add('valor-pulse');
}

// --- Motor de cálculo (espelha gerador_veiculos.py) -------------------

function calcularPmtPrice(valorFinanciado, prazoMeses, taxaAm) {
    if (valorFinanciado <= 0 || prazoMeses <= 0) return 0;
    const i = taxaAm / 100;
    if (i === 0) return valorFinanciado / prazoMeses;
    const fator = Math.pow(1 + i, prazoMeses);
    return valorFinanciado * (i * fator) / (fator - 1);
}

function calcularIofVeiculo(valorFinanciado, prazoMeses) {
    if (valorFinanciado <= 0 || prazoMeses <= 0) return 0;
    const ALIQUOTA_FIXA = 0.0038, ALIQUOTA_DIARIA = 0.000082;
    const dias = Math.min(prazoMeses * 30, 365);
    return valorFinanciado * (ALIQUOTA_FIXA + ALIQUOTA_DIARIA * dias);
}

const TARIFA_REGISTRO_CONTRATO = 120.00;
const SEGURO_PRESTAMISTA_MENSAL = 0.00035;

function calcularCetVeiculo(valorFinanciado, prazoMeses, taxaAm) {
    if (valorFinanciado <= 0 || prazoMeses <= 0) return 0;
    const taxaMensal = taxaAm / 100;
    const pmt = calcularPmtPrice(valorFinanciado, prazoMeses, taxaAm);
    const iof = calcularIofVeiculo(valorFinanciado, prazoMeses);

    let saldo = valorFinanciado;
    const fluxo = [];
    for (let m = 0; m < prazoMeses; m++) {
        const juros = saldo * taxaMensal;
        const amortizacao = pmt - juros;
        const seguro = saldo * SEGURO_PRESTAMISTA_MENSAL;
        fluxo.push(pmt + seguro);
        saldo -= amortizacao;
    }
    const valorLiquidoRecebido = valorFinanciado - iof - TARIFA_REGISTRO_CONTRATO;
    const vpl = (r) => {
        let total = -valorLiquidoRecebido;
        for (let i = 0; i < fluxo.length; i++) total += fluxo[i] / Math.pow(1 + r, i + 1);
        return total;
    };
    let lo = 0, hi = 0.15; // teto com margem de segurança maior — ver comentário em calcular_cet_veiculo (Python)
    for (let i = 0; i < 60; i++) {
        const mid = (lo + hi) / 2;
        if (vpl(mid) > 0) lo = mid; else hi = mid;
    }
    const tirMensal = (lo + hi) / 2;
    return Math.round(((Math.pow(1 + tirMensal, 12) - 1) * 100) * 100) / 100;
}

function gerarTabelaAmortizacao(valorFinanciado, prazoMeses, taxaAm) {
    const taxaMensal = taxaAm / 100;
    const pmt = calcularPmtPrice(valorFinanciado, prazoMeses, taxaAm);
    let saldo = valorFinanciado;
    const linhas = [];
    for (let mes = 1; mes <= prazoMeses; mes++) {
        const juros = saldo * taxaMensal;
        const amortizacao = pmt - juros;
        saldo = Math.max(0, saldo - amortizacao);
        linhas.push({ mes, parcela: pmt, juros, amortizacao, saldo });
    }
    return linhas;
}

// Simula o mesmo financiamento (Tabela Price) com amortização extra
// recorrente: a cada `periodicidade` meses, abate `aporte` direto do
// saldo devedor (nunca deixando saldo negativo), mantendo a MESMA
// parcela fixa original (pmtFixo) — a folga vira prazo mais curto, não
// parcela menor. Espelha simularComAmortizacaoRecorrente do projeto
// irmão, mas sem o branch SAC/PRICE: financiamento de veículo (CDC) no
// Brasil só usa Tabela Price, não existe SAC nessa modalidade.
function simularComAmortizacaoRecorrente(valorFinanciado, prazoMeses, taxaAm, aporte, periodicidade, pmtFixo) {
    const taxaMensal = taxaAm / 100;
    let saldo = valorFinanciado, jurosTotal = 0, meses = 0;
    while (saldo > 0.005 && meses < prazoMeses) {
        meses++;
        const juros = saldo * taxaMensal;
        jurosTotal += juros;
        let amortizacaoBase = pmtFixo - juros;
        if (amortizacaoBase > saldo) amortizacaoBase = saldo;
        saldo -= amortizacaoBase;
        if (aporte > 0 && periodicidade > 0 && saldo > 0 && meses % periodicidade === 0) {
            const abate = Math.min(aporte, saldo);
            saldo -= abate;
        }
    }
    return { jurosTotal, meses };
}

function calcularRendaSugerida(parcela) {
    return parcela > 0 ? parcela / 0.30 : 0;
}

// Ranking só pra achar a posição do banco no mercado (posição neutra) —
// NUNCA usado pra montar uma lista de concorrentes com link. Cada banco
// usa a MESMA entradaPct (regra é por categoria, não por banco, nesta
// v1) e seu próprio prazoMax/taxaAm. cetAtual/bancoChaveAtual sobrescrevem
// a entrada do banco desta página no ranking, pra nunca mostrar dois CETs
// diferentes do mesmo banco na mesma tela (mesmo cuidado do Python).
//
// marcadorPct é interpolação linear do CET real contra o mínimo/máximo
// real da faixa (valor, não ranking) — espelha renderizar_faixa_mercado
// no Python; ver docstring de lá pro raciocínio completo (testado e
// revertido de "fração do ranking" no mesmo dia, a pedido do usuário:
// com todo marcador igualmente espaçado a barra perdia a noção de o
// quanto os bancos realmente se aproximam ou distanciam em taxa).
function calcularFaixaMercado(bancosCategoria, valorLive, prazoLive, entradaPct, cetAtual, bancoChaveAtual) {
    const ranking = bancosCategoria.map(b => {
        const prazoB = Math.min(prazoLive, b.prazoMax);
        const financiadoB = valorLive * (1 - entradaPct);
        const cet = (b.chave === bancoChaveAtual) ? cetAtual : calcularCetVeiculo(financiadoB, prazoB, b.taxaAm);
        return { chave: b.chave, cet };
    });
    ranking.sort((a, b) => a.cet - b.cet);
    const n = ranking.length;
    const cetMin = ranking[0].cet, cetMax = ranking[n - 1].cet;
    const spread = cetMax - cetMin;
    let marcadorPct = spread > 0 ? Math.round(((cetAtual - cetMin) / spread) * 100) : 50;
    marcadorPct = Math.max(2, Math.min(98, marcadorPct));
    return { cetMin, cetMax, marcadorPct };
}

function linhaTabelaHtml(l) {
    return '<tr class="border-b border-white/5"><td class="py-2 px-3">' + l.mes + '</td>' +
        '<td class="py-2 px-3 text-right">' + formatarReais(l.parcela) + '</td>' +
        '<td class="py-2 px-3 text-right text-amber-400">' + formatarReais(l.juros) + '</td>' +
        '<td class="py-2 px-3 text-right text-sky-400">' + formatarReais(l.amortizacao) + '</td>' +
        '<td class="py-2 px-3 text-right">' + formatarReais(l.saldo) + '</td></tr>';
}

// --- Orquestração da página individual (slider valor + prazo) ---------

function iniciarSimulador(dados) {
    const sliderValor = document.getElementById('slider_valor');
    const inputValor = document.getElementById('input_valor');
    const sliderPrazo = document.getElementById('slider_prazo');
    const labelPrazo = document.getElementById('label_prazo');
    const inputAmortizar = document.getElementById('input_amortizar');
    const sliderAmortizar = document.getElementById('slider_amortizar');
    const sliderPeriodicidade = document.getElementById('slider_periodicidade');
    const labelPeriodicidade = document.getElementById('label_periodicidade');
    if (!sliderValor || !sliderPrazo) return; // página sem simulador interativo

    initMask('input_valor');
    if (inputAmortizar) initMask('input_amortizar');

    function atualizar() {
        const valor = Math.max(dados.valorMin, Math.min(dados.valorMax, unformatCurrency(inputValor.value)));
        const prazo = Math.min(dados.prazoMaxBanco, Math.max(12, Number(sliderPrazo.value)));
        const entrada = valor * dados.entradaPct;
        const financiado = valor - entrada;
        const pmt = calcularPmtPrice(financiado, prazo, dados.taxaAm);
        const cet = calcularCetVeiculo(financiado, prazo, dados.taxaAm);
        const totalPago = pmt * prazo;
        const totalJuros = totalPago - financiado;
        const rendaSugerida = calcularRendaSugerida(pmt);

        atualizarValor('res_entrada', formatarReais(entrada));
        atualizarValor('res_financiado', formatarReais(financiado));
        atualizarValor('res_parcela', formatarReais(pmt));
        atualizarValor('res_cet', cet.toFixed(2).replace('.', ',') + '% a.a.');
        atualizarValor('res_total_pago', formatarReais(totalPago));
        atualizarValor('res_total_juros', formatarReais(totalJuros));
        atualizarValor('res_renda', formatarReais(rendaSugerida));
        labelPrazo.innerText = prazo + ' meses';

        // Achado real (08/set/2026, auditoria pedida pelo usuário): esta
        // função escrevia em #tabela_visivel/#tabela_resto/
        // #bloco_tabela_resto/#resumo_tabela_resto, mas a página não tem
        // NENHUM desses elementos desde que a tabela mês a mês foi
        // removida (pedido do usuário comparando com o projeto irmão,
        // "mantém a tabela de amortização... tudo errado") — os
        // guardas `if (elemento) ...` mascaravam isso silenciosamente
        // (nunca lançava erro, só não fazia nada). gerarTabelaAmortizacao
        // continua existindo e testada (tests/test_calculo_js.mjs,
        // paridade com gerar_tabela_amortizacao do Python) por ainda ser
        // uma função pura útil, só não é mais chamada daqui.

        // Amortização extra recorrente (Zona "Valor a Amortizar"): a cada N
        // meses, abate um valor fixo do saldo devedor, mantendo a MESMA
        // parcela — o ganho vira prazo mais curto e menos juros pagos, não
        // parcela menor. Espelha a Zona B do projeto irmão (financiamento
        // imobiliário), sem o toggle SAC/PRICE porque CDC de veículo só
        // usa Tabela Price.
        if (inputAmortizar && sliderAmortizar && sliderPeriodicidade) {
            let aporte = unformatCurrency(inputAmortizar.value);
            let amortizacaoMaxima = Math.max(0, financiado);
            if (aporte > amortizacaoMaxima) {
                aporte = amortizacaoMaxima;
                inputAmortizar.value = formatCurrency(aporte);
            }
            sliderAmortizar.max = amortizacaoMaxima;
            sliderAmortizar.value = aporte;

            const periodicidade = parseInt(sliderPeriodicidade.value, 10) || 1;
            if (labelPeriodicidade) labelPeriodicidade.innerText = 'a cada ' + periodicidade + (periodicidade === 1 ? ' mês' : ' meses');

            const resultadoNovo = simularComAmortizacaoRecorrente(financiado, prazo, dados.taxaAm, aporte, periodicidade, pmt);
            const economiaJuros = Math.max(0, totalJuros - resultadoNovo.jurosTotal);
            const mesesEliminados = Math.max(0, prazo - resultadoNovo.meses);

            atualizarValor('res_economia', formatarReais(economiaJuros));
            let anosRestantes = Math.floor(mesesEliminados / 12), mesesRestantes = mesesEliminados % 12, textoTempo = '';
            if (anosRestantes > 0) textoTempo += anosRestantes + (anosRestantes === 1 ? ' Ano' : ' Anos');
            if (anosRestantes > 0 && mesesRestantes > 0) textoTempo += ' e ';
            if (mesesRestantes > 0 || (anosRestantes === 0 && mesesRestantes === 0)) textoTempo += mesesRestantes + (mesesRestantes === 1 ? ' Mês' : ' Meses');
            atualizarValor('res_impacto', textoTempo);
            const barNovoPrazo = document.getElementById('bar_novo_prazo');
            if (barNovoPrazo) barNovoPrazo.style.width = ((resultadoNovo.meses / prazo) * 100) + '%';
        }

        if (dados.bancosCategoria && dados.bancosCategoria.length) {
            const { cetMin, cetMax, marcadorPct } = calcularFaixaMercado(dados.bancosCategoria, valor, prazo, dados.entradaPct, cet, dados.bancoChave);
            const marcador = document.getElementById('faixa_marcador');
            const rotuloMin = document.getElementById('faixa_min');
            const rotuloMax = document.getElementById('faixa_max');
            const texto = document.getElementById('faixa_texto');
            const cetFmt = cet.toFixed(2).replace('.', ',');
            const cetMinFmt = cetMin.toFixed(2).replace('.', ',');
            const cetMaxFmt = cetMax.toFixed(2).replace('.', ',');
            if (marcador) { marcador.style.left = marcadorPct + '%'; marcador.title = dados.bancoNome + ': ' + cetFmt + '%'; }
            if (rotuloMin) rotuloMin.innerText = cetMinFmt + '% menor CET';
            if (rotuloMax) rotuloMax.innerText = cetMaxFmt + '% maior CET';
            if (texto) {
                const cta = '<a href="' + dados.linkAfiliado + '" target="_blank" rel="noopener sponsored" class="text-sky-400 underline hover:text-sky-300 block mt-2 font-semibold">' +
                    (marcadorPct <= 15 ? 'Falar com um especialista →' : 'É esse trabalho que fazemos por você, sem custo →') + '</a>';
                texto.innerHTML = (marcadorPct <= 15
                    ? ('O ' + dados.bancoNome + ' está entre as condições <strong class="text-sky-400">mais competitivas</strong> que acompanhamos (' + cetFmt + '% de CET). Vale confirmar essa condição e agilizar a aprovação sem custo.')
                    : ('Nas condições simuladas, o CET no mercado costuma variar entre <strong class="text-sky-400">' + cetMinFmt + '%</strong> e <strong class="text-sky-400">' + cetMaxFmt + '%</strong> — aqui no ' + dados.bancoNome + ' está em ' + cetFmt + '%.')
                ) + cta;
            }
        }
    }

    sliderValor.addEventListener('input', function () { inputValor.value = formatCurrency(Number(this.value)); atualizar(); });
    inputValor.addEventListener('blur', function () { const val = unformatCurrency(this.value); sliderValor.value = val; atualizar(); });
    sliderPrazo.addEventListener('input', atualizar);
    if (sliderAmortizar) sliderAmortizar.addEventListener('input', function () { inputAmortizar.value = formatCurrency(Number(this.value)); atualizar(); });
    if (inputAmortizar) inputAmortizar.addEventListener('blur', function () { const val = unformatCurrency(this.value); sliderAmortizar.value = val; atualizar(); });
    if (sliderPeriodicidade) sliderPeriodicidade.addEventListener('input', atualizar);
    atualizar();
}
'''


def render_json_ld(*blocos):
    return "\n".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>' for b in blocos)


def render_faq_visual(perguntas):
    """Bloco de FAQ visível (accordion <details>, sem JS) + schema.org
    FAQPage correspondente — as duas coisas nascem sempre JUNTAS aqui de
    propósito: a diretriz do Google pra FAQPage exige que a marcação
    reflita conteúdo que o usuário de fato vê na página (senão é tratada
    como manipulativa e não gera o rich result, podendo até levar a ação
    manual). `perguntas` é uma lista de tuplas (pergunta, resposta), ambas
    com dado real da página (taxa, prazo, banco) — nunca genérico
    inventado.

    Achado real (13/set/2026, auditoria de SEO): a página individual de
    simulação já tinha esse exato padrão (schema_faq + <details> inline,
    ver gerar_pagina_individual) — só não existia nas páginas de hub
    (por banco), comparador (por categoria) e na home, que são páginas
    de MAIS valor de SEO (termos de cabeça, mais link equity) e ficaram
    de fora. Extraído aqui pra essas 3 não duplicarem o bloco 3x cada."""
    itens_html = "\n".join(f'''<details class="group bg-white/5 border border-white/10 rounded-xl overflow-hidden open:border-sky-500/30 transition-colors">
                    <summary class="cursor-pointer list-none p-5 flex items-center justify-between gap-4">
                        <h4 class="text-sky-400 font-bold text-sm">{q}</h4>
                        <span class="faq-toggle-icon shrink-0 text-slate-400 group-open:rotate-45 transition-transform text-lg leading-none">+</span>
                    </summary>
                    <p class="text-slate-300 text-sm font-light leading-relaxed px-5 pb-5">{a}</p>
                </details>''' for q, a in perguntas)
    html = f'''<div class="mt-16 mb-8">
            <h3 class="text-2xl font-serif text-white mb-6 text-center">Perguntas Frequentes</h3>
            <div class="space-y-3 max-w-3xl mx-auto">
                {itens_html}
            </div>
        </div>'''
    schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in perguntas
        ],
    }
    return html, schema


def render_head(titulo, meta_description, url_canonica, json_ld_blocos, robots=None):
    # Achado real (21/set/2026, auditoria de SEO): 593 das 884 páginas
    # saíam com <title> acima de 65 caracteres (o sufixo de marca "|
    # Simulador Datalab" empurrava pra 70-80) — o Google corta em ~60 e o
    # que é cortado é justamente o final. O que identifica a página
    # (categoria, banco, valor, prazo) fica no começo; a marca sai só
    # quando não cabe. Feito aqui, no chokepoint de todo <title>.
    if len(titulo) > 60:
        for sufixo in (" | Simulador Datalab", " | Datalab Global", " | Datalab"):
            if titulo.endswith(sufixo):
                titulo = titulo[: -len(sufixo)]
                break
    if len(meta_description) > 160:
        meta_description = meta_description[:157].rstrip() + "..."
    # Achado real (08/set/2026, auditoria de segurança pedida pelo
    # usuário): titulo/meta_description chegam aqui via f-string sem
    # nenhum escape — hoje inofensivo porque todo texto vem de
    # BANCOS_VEICULOS (dicionário 100% hardcoded à mão neste arquivo),
    # mas bancos_veiculos.py já documenta a intenção de um
    # etl_taxas_veiculos.py futuro que alimentaria nome_exibicao a partir
    # de texto raspado do relatório do BACEN — no dia em que isso
    # acontecer, uma razão social com aspas/`&`/`<` no meio quebraria o
    # atributo HTML (ou pior, injetaria HTML/JS) em toda página que cita
    # aquele banco. html.escape() aqui é a defesa mínima nesse chokepoint
    # (todo <title>/<meta> de toda página passa por render_head), sem
    # precisar escapar individualmente cada f-string do arquivo inteiro.
    titulo = html.escape(titulo)
    meta_description = html.escape(meta_description)
    _medicao_head = ''.join('\n    ' + t for t in tags_medicao())
    return f'''<meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo}</title>
    <meta name="description" content="{meta_description}">
    <link rel="canonical" href="{url_canonica}" />
    {f'<meta name="robots" content="{robots}">' if robots else ''}
    <link rel="icon" href="favicon.ico?v=20261012" sizes="any">
    <link rel="icon" href="favicon-32.png?v=20261012" type="image/png" sizes="32x32">
    <link rel="icon" href="favicon-192.png?v=20261012" type="image/png" sizes="192x192">
    <link rel="apple-touch-icon" href="apple-touch-icon.png?v=20261012">{_medicao_head}
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <meta property="og:type" content="website">
    <meta property="og:locale" content="pt_BR">
    <meta property="og:site_name" content="Datalab Global">
    <meta property="og:title" content="{titulo}">
    <meta property="og:description" content="{meta_description}">
    <meta property="og:url" content="{url_canonica}">
    <meta property="og:image" content="{DOMINIO}/og-image.png">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{titulo}">
    <meta name="twitter:description" content="{meta_description}">
    <link rel="stylesheet" href="styles.css?v={VERSAO_BUILD}">
    {GOOGLE_FONTS_LINK_ASSINCRONO}
    {render_json_ld(*json_ld_blocos)}'''


def render_nav():
    return f'''<nav class="border-b border-white/5 sticky top-0 z-50 backdrop-blur-2xl bg-slate-950/50">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
            <a href="/" class="flex items-center"><img src="logo-header.webp" alt="Datalab Global" width="168" height="54" class="w-auto" style="height:54px;max-width:45vw"></a>
            <div class="flex items-center gap-2">
                <a href="/" aria-label="Início" class="inline-flex items-center gap-1.5 -my-2.5 p-2.5 text-xs text-slate-400 hover:text-sky-400 transition-colors">{icone('home')} <span class="hidden sm:inline">Início</span></a>
                <a href="/aprenda" aria-label="Aprenda" class="inline-flex items-center gap-1.5 -my-2.5 p-2.5 text-xs text-slate-400 hover:text-sky-400 transition-colors">{icone('book-open')} <span class="hidden sm:inline">Aprenda</span></a>
                <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="bg-sky-500 hover:bg-sky-400 text-slate-950 px-4 py-2 rounded-full font-bold transition-all text-xs flex items-center whitespace-nowrap shadow-[0_0_15px_rgba(14,165,233,0.3)]">
                    Análise Grátis {icone('arrow-right', 'ml-1.5 text-xs')}
                </a>
            </div>
        </div>
    </nav>'''


def renderizar_faixa_mercado(banco, banco_exib, cet_banco, ranking_ordenado, mensagem=None):
    """Barra neutra de posição no mercado (menor CET ... maior CET, com um
    marcador de onde este banco está) — NUNCA uma lista de concorrentes
    com link. Ver nota de modelo de negócio no topo do arquivo: o único
    CTA aqui é o link de afiliado.

    Posição do marcador é interpolação linear do CET deste banco contra
    o mínimo/máximo real da faixa (valor, não ranking) — achado real
    (07/set/2026, pedido explícito do usuário depois de ver o marcador
    do card de comparação): uma versão anterior desta função usava
    fração do ranking (índice/(n-1)), que deixava todo marcador
    igualmente espaçado independente da distância real entre as taxas —
    "parece uma fila indiana", sem noção nenhuma de o quanto os bancos
    realmente se aproximam ou distanciam uns dos outros. Voltado pra
    escala de valor real: dois bancos com CET bem próximo aparecem
    próximos no marcador, um banco isolado longe dos outros aparece
    isolado — é a informação que "Posição no Mercado" deveria mostrar.

    ranking_ordenado: lista de {"banco": ..., "cet": ...} de TODOS os
    bancos da categoria (retorno de comparar_bancos_categoria) — a
    entrada do banco atual é sobrescrita com cet_banco antes de
    reordenar, pra nunca mostrar dois CETs diferentes do mesmo banco na
    mesma página (mesmo cuidado do projeto irmão).

    Os ids fixos dos elementos internos (faixa_marcador/faixa_min/
    faixa_max/faixa_texto) são os que calculo.js:iniciarSimulador()
    reescreve ao vivo na página individual quando o slider mexe; na
    página hub (sem slider) esses ids ficam presentes mas nunca são
    tocados por JS — a barra fica só com o valor estático calculado
    aqui."""
    ranking = [dict(r) for r in ranking_ordenado]  # cópia — não muta a lista do chamador
    for r in ranking:
        if r["banco"] == banco:
            r["cet"] = cet_banco
    ranking.sort(key=lambda r: r["cet"])
    cet_min, cet_max = ranking[0]["cet"], ranking[-1]["cet"]
    spread = cet_max - cet_min
    marcador_pct = round(((cet_banco - cet_min) / spread) * 100) if spread > 0 else 50
    marcador_pct = max(2, min(98, marcador_pct))
    cet_banco_fmt = f"{cet_banco:.2f}".replace('.', ',')
    cet_min_fmt = f"{cet_min:.2f}".replace('.', ',')
    cet_max_fmt = f"{cet_max:.2f}".replace('.', ',')
    # Achado real (08/set/2026, auditoria pedida pelo usuário): o JS
    # (calculo.js:atualizar(), bloco "faixa_texto") já troca esta mensagem
    # e o texto do CTA quando marcador_pct <= 15 (banco entre os mais
    # baratos do mercado) — mas essa função SSR sempre renderizava a
    # mensagem genérica "varia entre X e Y", nunca a variante "está entre
    # as mais competitivas". Resultado: todo crawler (Googlebot incluso,
    # liberado no robots.txt) e todo visitante sem JS via a mensagem
    # ERRADA pra ~1/6 dos bancos de cada categoria (os mais baratos,
    # justamente onde a mensagem mais forte importa mais) — só quem tinha
    # JS habilitado via a versão correta, depois de um "flash" de texto
    # trocando na tela. Corrigido calculando aqui o MESMO branch que o JS
    # usa, pra SSR e client-side sempre concordarem desde o primeiro
    # paint (parâmetro `mensagem` continua aceito pra quem quiser
    # sobrescrever explicitamente, mas nenhum chamador atual faz isso).
    if mensagem is None:
        if marcador_pct <= 15:
            mensagem = (
                f"O {banco_exib} está entre as condições <strong class='text-sky-400'>mais competitivas</strong> "
                f"que acompanhamos ({cet_banco_fmt}% de CET). Vale confirmar essa condição e agilizar a aprovação "
                f"sem custo."
            )
            texto_cta = "Falar com um especialista →"
        else:
            mensagem = (
                f"Nas condições simuladas, o CET no mercado costuma variar entre "
                f"<strong class='text-sky-400'>{cet_min_fmt}%</strong> e "
                f"<strong class='text-sky-400'>{cet_max_fmt}%</strong> — aqui no {banco_exib} está em "
                f"{cet_banco_fmt}%. Encontrar e negociar manualmente a melhor condição pode levar semanas de idas "
                f"e vindas ao banco."
            )
            texto_cta = "É esse trabalho que fazemos por você, sem custo →"
    else:
        texto_cta = "É esse trabalho que fazemos por você, sem custo →"
    return f'''<div class="bg-sky-500/10 border border-sky-500/30 rounded-2xl p-6">
        <div class="flex items-center gap-2 mb-4">
            <span class="text-amber-400">{icone('lightbulb')}</span>
            <span class="bg-sky-500 text-slate-950 text-[9px] font-black px-2 py-0.5 rounded-full uppercase tracking-widest">Dica</span>
            <span class="text-slate-300 text-[11px] font-bold uppercase tracking-widest">Posição do {banco_exib} no Mercado</span>
            {tooltip('Mostramos onde este banco fica entre o menor e o maior CET dos bancos que acompanhamos nessa categoria — não uma lista de concorrentes, porque nosso trabalho é te conectar com a melhor condição, não te mandar pra outro banco.')}
        </div>
        <div class="space-y-2">
            <div class="relative h-2 rounded-full bg-gradient-to-r from-sky-500 via-amber-400 to-rose-500">
                <div id="faixa_marcador" class="absolute top-1/2 h-4 w-4 rounded-full bg-white border-2 border-sky-950 shadow-[0_0_0_3px_rgba(14,165,233,0.35)]" style="left:{marcador_pct}%; transform:translate(-50%,-50%)" title="{banco_exib}: {cet_banco_fmt}%"></div>
            </div>
            <div class="flex justify-between text-[10px] text-slate-400 uppercase tracking-wide">
                <span id="faixa_min">{cet_min_fmt}% menor CET</span>
                <span id="faixa_max">{cet_max_fmt}% maior CET</span>
            </div>
        </div>
        <p class="text-slate-300 text-xs font-light leading-relaxed mt-4" id="faixa_texto">
            {mensagem}
            <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="text-sky-400 underline hover:text-sky-300 block mt-2 font-semibold">{texto_cta}</a>
        </p>
    </div>'''


# Reposiciona em runtime qualquer .tooltip-box que estouraria a tela —
# a v1 desta função tinha só a metade CSS (margin-left, ver input.css) e
# ficou sem esta metade em JS, reproduzindo ao vivo o exato bug do
# projeto irmão: confirmado via Playwright/browser real nesta sessão
# (scrollWidth 411 > clientWidth 375 numa página de 375px, causado pelo
# tooltip do CET). Diferente do irmão, chamamos ajustarTooltips() de
# imediato (não só dentro de document.fonts.ready) — depender só do
# fonts.ready deixa a posição errada até a fonte do Google Fonts
# resolver, e em ambiente sem rede (preview local, crawler bloqueado)
# essa promise pode nunca resolver, deixando o overflow permanente.
SCRIPT_AJUSTA_TOOLTIPS = '''
    <script>
        function ajustarTooltips() {
            const margem = 8;
            // clientWidth (não window.innerWidth) é a largura real
            // renderizada da página: nesta página o <body> tem
            // overflow-x:hidden, e nesse caso window.innerWidth pode
            // devolver um valor maior que a área visível de verdade
            // (confirmado ao vivo nesta sessão: innerWidth relatou 404px
            // numa tela de 375px). Usar innerWidth aqui faria a correção
            // clampar contra um limite errado maior que a tela real,
            // deixando o balão ainda estourando por fora.
            const larguraTela = document.documentElement.clientWidth;
            document.querySelectorAll('.tooltip-box').forEach(box => {
                const metade = box.offsetWidth / 2;
                box.style.setProperty('--tt-shift', (-metade) + 'px');
                const r = box.getBoundingClientRect();
                let shift = 0;
                if (r.right > larguraTela - margem) shift = (larguraTela - margem) - r.right;
                else if (r.left < margem) shift = margem - r.left;
                if (shift !== 0) box.style.setProperty('--tt-shift', (-metade + shift).toFixed(0) + 'px');
            });
        }
        ajustarTooltips();
        window.addEventListener('resize', ajustarTooltips);
        if (document.fonts && document.fonts.ready) {
            document.fonts.ready.then(ajustarTooltips).catch(() => {});
        }
    </script>'''.strip('\\n')


def render_footer():
    return f'''<footer class="border-t border-white/5 mt-16 py-8">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 text-center text-xs text-slate-400 leading-relaxed">
            <p>Datalab Global — simulações educativas de financiamento de veículos, não são uma oferta de crédito nem substituem a proposta oficial do banco.</p>
            <p class="mt-1">Taxas com base em dados reais do Banco Central do Brasil (Relatório de Taxas de Juros por Instituição Financeira). CET estimado inclui IOF (alíquota de lei), tarifa de registro de contrato e seguro prestamista típicos de mercado — a taxa final de cada cliente varia com relacionamento bancário, histórico de crédito e seguradora escolhida.</p>
            <p class="mt-1">Datalab Global é uma marca de {EMPRESA_RODAPE}. Contato: contato@datalabglobal.com · <a href="https://www.datalabglobal.com/privacidade/" class="underline hover:text-sky-400">Privacidade</a> · <a href="https://www.datalabglobal.com/termos/" class="underline hover:text-sky-400">Termos</a> · <a href="incorporar" class="underline hover:text-sky-400">Simulador para o seu site</a> · <a href="imprensa" class="underline hover:text-sky-400">Imprensa</a></p>
            <p class="mt-3 flex items-center justify-center gap-4">
                <a href="https://www.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Outros produtos Datalab</a>
                <a href="https://www.datalabglobal.com/pix-no-cartao/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Pix no cartão</a>
                <a href="https://dados.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Lente B2B: dados de empresas</a>
                <a href="/aprenda" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Aprenda</a>
                <a href="/sobre" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Sobre a Datalab Global</a>
                <a href="/metodologia" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Metodologia</a>
                <a href="/taxas-financiamento-veiculos" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Taxas mês a mês</a>
                <a href="/renda-para-financiar-veiculo" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Renda para financiar</a>
            </p>
        </div>
    </footer>'''


_ILUSTRACAO_CARRO_PATHS = '''<path d="M17.001,49.693c-4.12,0-7.46,3.338-7.46,7.459c0,0.319,0.026,0.631,0.066,0.938c0.462,3.677,3.593,6.521,7.394,6.521c3.906,0,7.105-3.002,7.429-6.823c0.019-0.211,0.032-0.422,0.032-0.638C24.463,53.031,21.123,49.693,17.001,49.693z M13.264,54.342l1.522,1.521c-0.119,0.203-0.211,0.423-0.271,0.656H12.37C12.483,55.706,12.794,54.967,13.264,54.342z M12.364,57.812h2.16c0.062,0.229,0.15,0.447,0.27,0.646l-1.524,1.524C12.798,59.361,12.479,58.62,12.364,57.812z M16.356,61.787c-0.809-0.111-1.543-0.429-2.164-0.896l1.517-1.518c0.199,0.116,0.418,0.201,0.647,0.262V61.787z M16.356,54.672c-0.235,0.062-0.455,0.153-0.66,0.274l-1.521-1.521c0.625-0.475,1.366-0.788,2.181-0.901V54.672z M17.647,52.524c0.813,0.113,1.555,0.428,2.18,0.902l-1.52,1.52c-0.205-0.121-0.426-0.214-0.66-0.274V52.524z M17.647,61.786v-2.151c0.229-0.061,0.447-0.146,0.646-0.264l1.519,1.52C19.191,61.357,18.456,61.675,17.647,61.786z M20.738,59.988l-1.53-1.531c0.118-0.199,0.217-0.414,0.278-0.646h2.144C21.516,58.62,21.21,59.367,20.738,59.988z M19.487,56.52c-0.061-0.233-0.152-0.453-0.271-0.656l1.522-1.521c0.471,0.625,0.782,1.364,0.894,2.179L19.487,56.52L19.487,56.52z"/>
<path d="M78.611,49.758c-4.103,0-7.428,3.324-7.428,7.428c0,0.317,0.025,0.627,0.064,0.934c0.46,3.66,3.578,6.494,7.363,6.494c3.889,0,7.074-2.989,7.396-6.794c0.019-0.21,0.032-0.42,0.032-0.634C86.04,53.082,82.715,49.758,78.611,49.758z M74.891,54.387l1.516,1.516c-0.118,0.202-0.21,0.421-0.27,0.653h-2.136C74.112,55.744,74.422,55.009,74.891,54.387z M73.994,57.842h2.15c0.062,0.229,0.15,0.444,0.269,0.644l-1.519,1.52C74.427,59.386,74.108,58.646,73.994,57.842z M77.969,61.801c-0.805-0.112-1.535-0.429-2.154-0.896l1.51-1.51c0.198,0.115,0.417,0.201,0.645,0.26V61.801z M77.969,54.715c-0.233,0.061-0.453,0.152-0.656,0.272l-1.514-1.514c0.622-0.471,1.36-0.784,2.17-0.897V54.715z M79.255,52.576c0.812,0.113,1.549,0.428,2.17,0.898l-1.513,1.513c-0.204-0.12-0.423-0.213-0.657-0.272V52.576z M79.255,61.8v-2.145c0.229-0.059,0.446-0.146,0.645-0.262l1.511,1.512C80.792,61.371,80.061,61.687,79.255,61.8z M82.332,60.009l-1.523-1.524c0.117-0.199,0.216-0.412,0.276-0.643h2.134C83.106,58.646,82.802,59.389,82.332,60.009z M81.087,56.555c-0.06-0.232-0.15-0.451-0.27-0.653l1.516-1.516c0.469,0.622,0.778,1.357,0.889,2.169H81.087z"/>
<path d="M99.352,52.001c-0.026-0.983-0.331-1.941-0.882-2.759l-0.402-0.6l-1.757-4.635c-0.331-0.875-1.139-1.484-2.07-1.562c-1.728-0.146-4.663-0.368-7.465-0.471c-9.794-5.201-27.904-10.43-43.262-4.731c-3.151,1.169-12.154,5.744-12.154,5.744s-14.62-0.37-25.047,3.349c-4.108,1.465-6.699,5.543-6.266,9.884c0.087,0.869,0.215,1.642,0.341,2.266c0.199,0.987,1.014,1.731,2.015,1.842l6.487,0.711c-0.408-0.852-0.695-1.773-0.818-2.755c-0.052-0.401-0.078-0.772-0.078-1.132c0-4.967,4.041-9.008,9.008-9.008c4.968,0,9.01,4.042,9.01,9.008c0,0.26-0.017,0.514-0.038,0.768c-0.095,1.115-0.399,2.172-0.868,3.135h45.045l0.365-0.021c-0.4-0.842-0.683-1.753-0.804-2.72c-0.052-0.403-0.077-0.773-0.077-1.127c0-4.95,4.026-8.978,8.977-8.978s8.978,4.026,8.978,8.978c0,0.259-0.017,0.511-0.038,0.764c-0.062,0.734-0.223,1.438-0.453,2.11L88.112,60l6.979-0.923c1.214-0.161,2.285-0.876,2.898-1.936l0.695-1.199c0.479-0.83,0.721-1.777,0.695-2.735L99.352,52.001z M74.63,43.068H40.469c0,0,0.203-0.809-0.69-1.786c0,0,8.733-5.633,22.22-4.226c3.711,0.388,8.246,0.651,14.42,3.86L74.63,43.068z"/>'''

_ILUSTRACAO_MOTO_PATH = '''<path d="M305.079,162.353c6.063-2.512,7.322-13.002-0.729-15.095c-6.137-1.595-12.396-2.092-18.601-1.631c13.381-12.339,19.688-22.022,9.859-24.171c-8.533-1.87-15.514-5.163-21.8-8.596c1.688-21.117,3.412-51.906-25.922-51.388c-10.242,0.181-10.263,16.088,0,15.907c12.936-0.228,12.34,15.213,10.998,27.195c-10.589-5.225-21.022-7.177-36.624,2.63c-30.935,19.449-88.375,17.678-134.331-3.531c-45.956-21.209-46.836-5.303-46.836-5.303s-49.552,70.221-15.907,43.305c12.27-9.812,30.463-8.569,50.341-1.683c-22.848-4.552-48.951,1.962-68.561,20.588c-4.973,4.718-1.6,11.263,3.395,13.018C3.834,183.091,0,194.576,0,206.967c0,32.576,26.411,58.989,58.989,58.989c32.371,0,58.629-26.082,58.958-58.383c4.357,0.559,8.992-1.942,8.647-7.57c-1.145-18.693-8.319-33.265-18.924-43.543c0.238-0.436,0.456-0.886,0.689-1.326c20.951,11.688,41.291,26.273,56.475,38.023c-0.259,0.336-0.507,0.673-0.704,1.062c-1.766,3.536-3.537,7.067-5.303,10.604c-1.941,3.879-1.066,8.586,2.854,10.879c3.552,2.087,8.945,1.025,10.879-2.853c1.618-3.231,3.236-6.468,4.853-9.704c8.119,6.628,13.027,10.993,13.027,10.993s5.013-3.138,12.873-8.243c-0.699,3.438-1.108,6.995-1.165,10.677c-0.119,7.793,9.016,9.647,13.489,5.603c4.723,27.849,28.899,49.078,58.093,49.078c32.576,0,58.989-26.413,58.989-58.988C332.726,191.215,321.665,172.792,305.079,162.353z M58.989,250.049c-23.755,0-43.082-19.33-43.082-43.082c0-23.757,19.327-43.082,43.082-43.082c7.933,0,15.351,2.196,21.74,5.95c-8.091,11.821-17.064,23.068-26.698,33.828c-6.825,7.612,4.391,18.9,11.247,11.247c9.852-10.998,19.12-22.493,27.514-34.574c5.789,7.337,9.279,16.575,9.279,26.626C102.071,230.719,82.744,250.049,58.989,250.049z M264.995,189.931c-4.329-4.971-8.922-9.729-13.546-14.467c3.832-2.331,8.047-4.081,12.547-5.127C264.281,176.873,264.581,183.402,264.995,189.931z M273.736,255.352c-23.758,0-43.082-19.33-43.082-43.082c0-9.906,3.396-19.015,9.035-26.295c11.098,11.304,21.873,22.815,29.169,37.268c4.417,8.756,15.721,2.076,14.54-6.126c-2.278-15.742-3.055-31.592-3.671-47.463c20.925,2.926,37.096,20.894,37.096,42.616C316.818,236.022,297.493,255.352,273.736,255.352z"/>'''

_ILUSTRACAO_CARRO_USADO_PATHS = '''<path d="M324.873,165.878c0,0-0.823-13.567-2.485-18.543c-1.657-4.971-1.652-4.971,0.828-8.119c2.48-3.144-7.291-0.994-8.953-0.663c-1.657,0.337-0.994,1.491-0.994,1.491c-19.222,0.829-63.303-23.86-98.26-27.34c-34.958-3.475-69.097-0.161-81.69,2.817c-12.593,2.982-54.018,25.352-58.652,26.512c-4.635,1.16-2.651-1.16-2.651-1.16c-23.855,0.989-64.783,21.375-64.783,21.375c-1.657,1.16-2.983,7.953-2.983,7.953l0.829,2.32c-6.794,6.302-4.806,19.558-4.806,19.558l3.325-1.165c1.175,2.154,1.481,6.959,1.481,6.959c-5.629,2.651-1.491,4.972-1.491,4.972s2.49-2.149,12.593,0.999c3.904,1.212,12.599,1.636,21.805,1.704c-1.294-3.268-2.03-6.814-2.03-10.538c0-15.84,12.883-28.723,28.723-28.723c15.834,0,28.723,12.883,28.723,28.723c0,3.438-0.642,6.727-1.755,9.792l147.467-0.248c-1.056-2.994-1.662-6.193-1.662-9.544c0-15.84,12.884-28.723,28.724-28.723c15.834,0,28.723,12.883,28.723,28.723c0,2.946-0.45,5.794-1.279,8.472c14.675-3.392,31.769-5.769,31.769-5.769l3.147-4.143c0,0,2.485-17.729,0-20.547C326.048,170.212,324.873,165.878,324.873,165.878z"/>
<path d="M64.672,218.42c9.419,0,17.487-5.598,21.205-13.618c1.382-2.988,2.211-6.286,2.211-9.803c0-12.935-10.486-23.42-23.42-23.42c-12.935,0-23.421,10.48-23.421,23.42c0,3.807,0.994,7.354,2.61,10.527C47.729,213.149,55.543,218.42,64.672,218.42z"/>
<path d="M266.163,218.42c9.311,0,17.284-5.479,21.055-13.349c1.471-3.056,2.361-6.452,2.361-10.072c0-12.935-10.486-23.42-23.421-23.42c-12.936,0-23.421,10.48-23.421,23.42c0,3.402,0.761,6.618,2.066,9.533C248.47,212.704,256.636,218.42,266.163,218.42z"/>'''


def ilustracao_categoria(categoria, id_gradiente):
    """Ilustração colorida por categoria — pensada pra usar só em lugares
    de alto nível (cards de categoria da home, cabeçalho dos comparadores),
    NUNCA nas 840 páginas individuais de simulação: com só 3-4 imagens
    repetindo centenas de vezes, ia parecer template genérico (achado
    real, 07/set/2026, decisão discutida com o usuário — mesmo risco que
    ele já tinha identificado com foto de banco de imagens).

    As silhuetas são referências prontas (não desenhadas à mão por
    tentativa): "novo" é a mesma referência que o usuário mandou
    (svgrepo.com, "coupe-car" — um esportivo/cupê); "usado" é outra
    referência do mesmo repositório, licença CC0, mas um carro diferente
    de propósito (svgrepo.com/svg/130586/personal-car-side-view-silhouette
    — um hatch/sedan mais "do dia a dia"), justamente pra não ficar
    idêntico ao de "novo" (achado real, 07/set/2026: o usuário notou que
    as duas eram rigorosamente a mesma silhueta só recolorida, e pediu
    silhuetas diferentes — cupê pra novo, sedã popular pra usado, o
    mesmo tipo de contraste visual que uma revenda usa). A moto é do
    mesmo repositório sob licença CC0
    (svgrepo.com/svg/113631/motorcycle-side-view-silhouette). Todas
    recoloridas no MESMO degradê azul vibrante + ponto de brilho
    amarelo da marca — a diferenciação agora vem da FORMA, não da cor
    (a tentativa anterior de diferenciar só pela cor, deixando "usado"
    acinzentado, foi revertida a pedido do usuário).

    id_gradiente: precisa ser único por <svg> na mesma página — dois
    cards de carro (novo + usado) na mesma home não podem compartilhar
    id de <linearGradient>, ou o segundo não resolve a referência."""
    gradiente = f'<linearGradient id="{id_gradiente}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#38bdf8"/><stop offset="100%" stop-color="#0369a1"/></linearGradient>'
    if categoria == 'moto':
        return f'''<svg viewBox="0 0 332.72 332.719" class="w-14 h-14" aria-hidden="true">
            <defs>{gradiente}</defs>
            <g fill="url(#{id_gradiente})">{_ILUSTRACAO_MOTO_PATH}</g>
            <circle cx="290" cy="120" r="9" fill="#fef08a"/>
        </svg>'''
    if categoria == 'usado':
        return f'''<svg viewBox="0 0 329.638 329.637" class="w-14 h-14" aria-hidden="true">
            <defs>{gradiente}</defs>
            <g fill="url(#{id_gradiente})">{_ILUSTRACAO_CARRO_USADO_PATHS}</g>
            <circle cx="315" cy="145" r="3.4" fill="#fef08a"/>
        </svg>'''
    return f'''<svg viewBox="0 0 99.382 99.382" class="w-14 h-14" aria-hidden="true">
        <defs>{gradiente}</defs>
        <g fill="url(#{id_gradiente})">{_ILUSTRACAO_CARRO_PATHS}</g>
        <circle cx="93" cy="50" r="3.4" fill="#fef08a"/>
    </svg>'''


def svg_donut_capital_juros(capital, juros):
    """Gráfico donut SVG puro (sem lib externa) mostrando a proporção
    Capital vs Juros do custo total — copiado do projeto irmão (mesma
    função, só com a cor de destaque trocada de emerald pra sky, pra
    combinar com a paleta deste produto). Estático (calculado uma vez no
    cenário padrão da página, não recalcula ao vivo no slider) — mesmo
    comportamento do irmão."""
    total = capital + juros
    if total <= 0:
        return ""
    pct_capital = capital / total
    r = 42
    circ = 2 * 3.14159265 * r
    dash_capital = pct_capital * circ
    dash_juros = circ - dash_capital
    pct_juros_label = round((1 - pct_capital) * 100)
    return f'''<div class="flex items-center gap-6">
        <svg viewBox="0 0 100 100" class="w-24 h-24 shrink-0" style="transform: rotate(-90deg)">
            <circle cx="50" cy="50" r="{r}" fill="none" stroke="#1e293b" stroke-width="12"></circle>
            <circle cx="50" cy="50" r="{r}" fill="none" stroke="#0ea5e9" stroke-width="12"
                    stroke-dasharray="{dash_capital:.2f} {circ:.2f}" stroke-linecap="round"></circle>
            <circle cx="50" cy="50" r="{r}" fill="none" stroke="#f59e0b" stroke-width="12"
                    stroke-dasharray="{dash_juros:.2f} {circ:.2f}" stroke-dashoffset="-{dash_capital:.2f}" stroke-linecap="round"></circle>
        </svg>
        <div class="space-y-2 text-xs">
            <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-sky-500 shrink-0"></span><span class="text-slate-400">Valor Financiado</span><span class="text-white font-medium ml-auto">{100 - pct_juros_label}%</span></div>
            <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full bg-amber-500 shrink-0"></span><span class="text-slate-400">Juros</span><span class="text-white font-medium ml-auto">{pct_juros_label}%</span></div>
        </div>
    </div>'''


def favicon_com_fallback(url_logo, banco_exib, classe_tamanho="w-6 h-6", lazy=True):
    """<img> do favicon do banco com fallback silencioso: se o serviço
    externo de favicons falhar pra algum domínio, o onerror esconde a
    imagem quebrada via classe CSS e revela um ícone de banco genérico
    ao lado (.favicon-img/.favicon-fallback já existiam em input.css,
    copiados do projeto irmão, mas nunca tinham sido de fato usados por
    nenhuma função Python aqui — achado real, 07/set/2026, revisão pedida
    pelo usuário depois de ver bolinhas brancas genéricas em vez de
    ícone de banco na barra "CET de Mercado" do comparador).

    lazy=False pros ícones da barra "CET de Mercado": eles ficam sempre
    ACIMA da dobra (topo da página, visíveis sem rolar), então
    loading="lazy" não tem nenhum benefício de performance ali — só
    risco de o navegador atrasar/pular o carregamento por engano (achado
    real, 07/set/2026: confirmado ao vivo que com lazy=True nenhuma
    requisição de favicon sequer disparava nesses marcadores, ficando só
    a bolinha vazia). Nas linhas de lista mais abaixo na página (fora da
    dobra em telas menores), lazy=True continua fazendo sentido."""
    lazy_attr = ' loading="lazy"' if lazy else ""
    banco_exib = html.escape(banco_exib)  # ver nota de segurança em render_head — mesmo chokepoint, texto de banco em atributo HTML
    return f'''<span class="relative inline-flex items-center justify-center {classe_tamanho} shrink-0">
        <img src="{url_logo}" alt="Logo {banco_exib}" width="24" height="24"{lazy_attr}
             class="favicon-img {classe_tamanho} rounded object-contain"
             onerror="this.classList.add('favicon-erro')">
        <span class="favicon-fallback {classe_tamanho} rounded bg-white/10 text-sky-400 items-center justify-center absolute inset-0">{icone('bank')}</span>
    </span>'''


def render_breadcrumb(itens):
    """itens: lista de (label, href|None) — href None marca o item atual
    (sem link, mesmo padrão de breadcrumb visual do projeto irmão)."""
    partes = []
    for label, href in itens:
        if href:
            partes.append(f'<a href="{href}" class="hover:text-sky-400 transition-colors">{label}</a>')
        else:
            partes.append(f'<span class="text-slate-300">{label}</span>')
    separador = ' <span class="text-slate-700">/</span> '
    return f'<nav class="text-xs text-slate-400 mb-6 flex flex-wrap items-center gap-1.5" aria-label="breadcrumb">{separador.join(partes)}</nav>'


def linha_tabela_amortizacao_html(l):
    return (f'<tr class="border-b border-white/5"><td class="py-2 px-3">{l["mes"]}</td>'
            f'<td class="py-2 px-3 text-right">{formatar_reais(l["parcela"])}</td>'
            f'<td class="py-2 px-3 text-right text-amber-400">{formatar_reais(l["juros"])}</td>'
            f'<td class="py-2 px-3 text-right text-sky-400">{formatar_reais(l["amortizacao"])}</td>'
            f'<td class="py-2 px-3 text-right">{formatar_reais(l["saldo"])}</td></tr>')


# ---------------------------------------------------------------------------
# Página individual: financiamento-{categoria}-{banco}-{valor}-mil-{prazo}-meses.html
# ---------------------------------------------------------------------------

def gerar_pagina_individual(p, todas_paginas, lookup, data_atualizacao):
    categoria, banco, banco_exib = p["categoria"], p["banco"], p["nome_exibicao"]
    valor, prazo = p["valor_veiculo"], p["prazo"]
    entrada, financiado = p["entrada"], p["valor_financiado"]
    taxa_am, taxa_aa, parcela, cet = p["taxa_am"], p["taxa_aa"], p["parcela"], p["cet"]
    # Achado real (08/set/2026, auditoria pedida pelo usuário): formatar
    # aqui, uma vez, e reusar — achado no mesmo levantamento que vários
    # pontos da página (meta description, resultado da simulação,
    # respostas do FAQ) usavam {cet:.2f}%/{taxa_aa:.2f}% direto, sem o
    # .replace('.', ',') que o padrão brasileiro (e o resto do arquivo,
    # ex. cet_banco_fmt em renderizar_faixa_mercado) usa — saía "12.83%"
    # com PONTO em vez de "12,83%", visível no card de resultado e no
    # snippet do Google.
    cet_fmt = f"{cet:.2f}".replace('.', ',')
    taxa_aa_fmt = f"{taxa_aa:.2f}".replace('.', ',')

    valor_curto = formatar_valor_curto(valor)
    total_pago = parcela * prazo
    total_juros = total_pago - financiado
    renda_sugerida = calcular_renda_sugerida(parcela)
    label_categoria = CATEGORIA_LABEL[categoria]
    # Achado real (10/set/2026, checagem final de SEO pedida pelo
    # usuário): canonical/hrefs internos apontavam pra URL COM ".html",
    # mas o Cloudflare Pages redireciona (308) automaticamente a versão
    # com ".html" pra sem extensão (confirmado ao vivo em produção) — ou
    # seja, o canonical apontava pra uma URL que a própria plataforma
    # redireciona, exatamente o padrão que o Google desaconselha. O
    # projeto irmão (imobiliário) já usa URL sem extensão em tudo (canonical,
    # sitemap, links internos) e não tem esse problema — replicado aqui.
    # O arquivo em disco continua se chamando "slug.html" (é como o
    # Cloudflare Pages localiza o arquivo estático); só as REFERÊNCIAS
    # (href, canonical, sitemap) deixam de citar a extensão.
    url_canonica = f"{DOMINIO}/{p['slug']}"
    href_hub = f"{slug_hub(categoria, banco)}"
    href_comparador = f"{slug_comparador(categoria)}"

    titulo_pagina = f"Financiamento {label_categoria} {banco_exib}: {valor_curto} em {prazo}x | Simulador Datalab"
    # Achado real (auditoria de SEO, 29/out/2026): 848 das 884 descriptions
    # passavam de 160 caracteres e o corte ("...com base na taxa média real
    # do Banc...") caía no meio da frase. Tenta a versão completa e, se não
    # couber, a curta — as duas terminam em frase inteira, sem reticências.
    meta_description_completa = (
        f"Simule o financiamento de {CATEGORIA_ARTIGO[categoria]} de {formatar_reais(valor)} pelo {banco_exib} "
        f"em {prazo}x: parcela de {formatar_reais(parcela)} e CET de {cet_fmt}% a.a., "
        f"com a taxa média real do Banco Central."
    )
    meta_description_curta = (
        f"Simule o financiamento de {CATEGORIA_ARTIGO[categoria]} de {formatar_reais(valor)} pelo {banco_exib} "
        f"em {prazo}x: parcela de {formatar_reais(parcela)} e CET de {cet_fmt}% a.a."
    )
    meta_description = (
        meta_description_completa if len(corrigir_concordancia(meta_description_completa)) <= 160
        else meta_description_curta
    )

    faq_q1 = f"O que é o CET no financiamento {label_categoria.lower()} do {banco_exib}?"
    faq_a1 = (f"CET (Custo Efetivo Total) é o custo real do financiamento — inclui a taxa de juros, o IOF "
              f"(imposto sobre a operação de crédito) e tarifas, não só a taxa anunciada. Neste cenário, o CET "
              f"estimado é {cet_fmt}% ao ano, acima da taxa nominal de {taxa_aa_fmt}% ao ano.")
    faq_q3 = "A taxa exibida é exatamente o que eu vou pagar?"
    faq_a3 = (f"Não necessariamente — é a taxa média real praticada pelo {banco_exib} nessa modalidade, segundo "
              f"o Banco Central, não uma proposta. A taxa final de cada cliente varia com relacionamento "
              f"bancário, histórico de crédito, entrada e seguradora escolhida.")

    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": label_categoria, "item": f"{DOMINIO}/{href_comparador}"},
            {"@type": "ListItem", "position": 3, "name": banco_exib, "item": f"{DOMINIO}/{href_hub}"},
            {"@type": "ListItem", "position": 4, "name": f"{valor_curto} em {prazo} meses", "item": url_canonica},
        ],
    }
    schema_software = {
        "@context": "https://schema.org", "@type": "SoftwareApplication",
        "name": f"Simulador de Financiamento {label_categoria} {banco_exib}",
        "applicationCategory": "FinanceApplication", "operatingSystem": "Web",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"},
        "url": url_canonica, "dateModified": data_atualizacao,
    }

    ranking = comparar_bancos_categoria(categoria, valor, prazo, lookup)
    faixa_html = renderizar_faixa_mercado(banco, banco_exib, cet, ranking)

    bancos_categoria_js = json.dumps([
        {"chave": b, "nome": d["nome_exibicao"], "taxaAm": d["taxa_am"], "prazoMax": d["prazo_max"]}
        for b, d in bancos_para_categoria(categoria).items()
    ], ensure_ascii=False)

    valores_categoria = VALORES_POR_CATEGORIA[categoria]
    valor_min_slider, valor_max_slider = valores_categoria[0], valores_categoria[-1] * 2
    passo_slider = {"novo": 5_000, "usado": 2_000, "moto": 500}[categoria]

    outros_prazos = sorted(
        (q for q in todas_paginas if q["categoria"] == categoria and q["banco"] == banco
         and q["valor_veiculo"] == valor and q["slug"] != p["slug"]),
        key=lambda q: q["prazo"],
    )
    outros_prazos_html = "\n".join(
        f'<a href="{q["slug"]}" class="px-3 py-2 rounded-lg border border-white/10 hover:border-sky-500/50 text-xs transition-all whitespace-nowrap">{q["prazo"]}x de {formatar_reais(q["parcela"])}</a>'
        for q in outros_prazos
    )
    # Achado real (12/set/2026, erro real do GitHub Actions em produção —
    # "SyntaxError: f-string: unmatched '['", Python 3.10): o bloco
    # "Outros prazos" era montado como uma f-string ANINHADA (delimitada
    # por ''', igual à f-string gigante da página inteira) dentro de uma
    # expressão condicional, dentro de uma lista de 1 item só passada pra
    # "".join([...]) — complexidade sem propósito (.join numa lista de 1
    # elemento só devolve o próprio elemento) que quebrava a análise de
    # colchetes/aspas do parser em versões antigas do Python. Calculado
    # aqui como variável simples, fora da f-string grande da página — a
    # referência lá embaixo vira só {bloco_outros_prazos}, uma
    # substituição de variável comum, sem nenhum aninhamento.
    link_comparacao_html = ""
    if pagina_comparacao_existe(p["categoria"], p["valor_veiculo"], p["prazo"]):
        link_comparacao_html = (
            f'<a href="{slug_comparacao(p["categoria"], p["valor_veiculo"], p["prazo"])}" class="inline-flex items-center gap-1.5 mt-3 mr-4 text-xs text-sky-400 hover:text-sky-300 underline transition-colors">'
            f'Comparar {formatar_valor_curto(p["valor_veiculo"])} em {p["prazo"]} meses em todos os bancos</a>'
        )
    bloco_outros_prazos = (
        f'<div class="mt-8"><h2 class="font-serif text-lg font-semibold mb-3">Outros prazos no {banco_exib}</h2>'
        f'<div class="flex flex-wrap gap-2">{outros_prazos_html}</div></div>'
    ) if outros_prazos_html else ""

    # Aporte padrão da Zona "Valor a Amortizar": 5% do valor financiado
    # desta página (piso de R$ 500, arredondado pra R$ 100 mais próximo —
    # escala menor que o financiamento imobiliário porque o valor típico
    # de um veículo é bem menor que o de um imóvel). Mesma lógica do
    # projeto irmão, só a escala de arredondamento ajustada.
    aporte_padrao = max(500, round((financiado * 0.05) / 100) * 100)
    aporte_padrao = min(aporte_padrao, int(financiado)) if financiado > 0 else 500
    aporte_padrao_fmt = formatar_reais(aporte_padrao)[3:]
    slider_amortizar_max = max(int(financiado), aporte_padrao)
    periodicidade_padrao = 6  # a cada 6 meses (13º/bônus), mesmo padrão do irmão

    dominio_favicon_atual = p["dominio_favicon"]
    url_logo_atual = f"https://www.google.com/s2/favicons?domain={dominio_favicon_atual}&sz=128"

    # Achado real (27/set/2026, Search Console + medicao de texto): duas paginas individuais quaisquer eram 96% identicas
    # (so os numeros do resultado mudavam) e parte delas ficava em "Rastreada, mas nao indexada" — o Google as tratava
    # como copias. Cada pagina ganha conteudo que so ela tem, calculado com os dados reais dela (nunca texto reescrito):
    # uma analise do cenario, o ranking dos bancos para o MESMO caso e perguntas frequentes com os numeros da pagina.
    prazo_max_banco = max(q["prazo"] for q in todas_paginas if q["banco"] == banco and q["categoria"] == categoria)
    prazo_alt = prazo + 12 if prazo + 12 <= prazo_max_banco else (prazo - 12 if prazo - 12 >= 12 else None)
    frase_prazo = ""
    if prazo_alt:
        parcela_alt = calcular_pmt_price(financiado, prazo_alt, taxa_am)
        juros_alt = parcela_alt * prazo_alt - financiado
        if prazo_alt > prazo:
            frase_prazo = (f"Esticar para {prazo_alt} meses baixa a parcela em {formatar_reais(parcela - parcela_alt)}, "
                           f"mas soma {formatar_reais(juros_alt - total_juros)} de juros ao contrato.")
        else:
            frase_prazo = (f"Encurtar para {prazo_alt} meses sobe a parcela em {formatar_reais(parcela_alt - parcela)} "
                           f"e economiza {formatar_reais(total_juros - juros_alt)} de juros.")
    entrada_pct_min = entrada / valor if valor else 0
    entrada_mais = valor * (entrada_pct_min + 0.10)
    financiado_mais = valor - entrada_mais
    parcela_mais = calcular_pmt_price(financiado_mais, prazo, taxa_am)
    juros_mais = parcela_mais * prazo - financiado_mais
    frase_entrada = (f"Com {round((entrada_pct_min + 0.10) * 100)}% de entrada ({formatar_reais(entrada_mais)}) em vez de "
                     f"{round(entrada_pct_min * 100)}%, a parcela cai para {formatar_reais(parcela_mais)} e você paga "
                     f"{formatar_reais(total_juros - juros_mais)} a menos de juros.")
    # 27/set/2026, decisão do usuário: nada de ranking nomeado nem de "o mais barato é X" — um ranking pode influenciar
    # o cliente a escolher um banco, e não é esse o papel do simulador (mesma decisão já registrada no imobiliário). A
    # comparação com o mercado fica só na faixa sem nomes (renderizar_faixa_mercado).
    analise_html = (
        '<section class="mt-8"><h2 class="font-serif text-lg font-semibold mb-3">Análise desta simulação</h2>'
        '<div class="glass-panel rounded-2xl p-6 md:p-8">'
        f'<p class="text-slate-300 text-sm leading-relaxed font-light">Financiando {formatar_reais(financiado)} de '
        f'{CATEGORIA_ARTIGO[categoria]} de {formatar_reais(valor)} em {prazo}x no {banco_exib}, você paga {prazo} parcelas de '
        f'<strong class="text-white font-medium">{formatar_reais(parcela)}</strong> e {formatar_reais(total_juros)} de juros no total. '
        f'{frase_prazo}</p>'
        f'<p class="text-slate-300 text-sm leading-relaxed font-light mt-3">{frase_entrada} Para essa parcela caber na regra de 30% '
        f'de comprometimento, a renda familiar precisa ser de pelo menos {formatar_reais(renda_sugerida)} por mês.</p>'
        + '</div></section>'
    )
    frase_posicao = posicao_no_mercado(ranking, cet)
    if frase_posicao:
        analise_html = analise_html[:-len('</div></section>')] + (
            f'<p class="text-slate-300 text-sm leading-relaxed font-light mt-3">{frase_posicao}</p></div></section>')
    extras_html = (html_projecao_price(financiado, prazo, taxa_am, banco_exib)
                   + html_serie_banco(historico_cache(), banco, banco_exib, taxa_am)
                   + html_vizinhas(p, todas_paginas))
    faq_html, schema_faq = render_faq_visual([
        (f"Qual a parcela de {valor_curto} em {prazo}x no {banco_exib}?",
         f"Com a entrada mínima de {round(entrada_pct_min * 100)}% ({formatar_reais(entrada)}), o valor financiado é "
         f"{formatar_reais(financiado)} e a parcela fica em {formatar_reais(parcela)} por mês, fixa pela Tabela Price, "
         f"com a taxa média de {taxa_aa_fmt}% ao ano do {banco_exib} apurada pelo Banco Central."),
        (f"Quanto pago de juros financiando {valor_curto} em {prazo} meses?",
         f"O total pago é {formatar_reais(total_pago)}, sendo {formatar_reais(total_juros)} de juros. Somando IOF, "
         f"tarifa de registro e seguro prestamista típico, o custo efetivo total estimado é {cet_fmt}% ao ano."),
        (f"Qual renda preciso para financiar {valor_curto} no {banco_exib}?",
         f"Os bancos costumam limitar a parcela a 30% da renda bruta: para {formatar_reais(parcela)} por mês, a renda "
         f"familiar precisa ser de pelo menos {formatar_reais(renda_sugerida)}. Dá para somar a renda do cônjuge ou companheiro(a)."),
        (faq_q1, faq_a1),
        (faq_q3, faq_a3),
    ])

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_faq, schema_breadcrumb, schema_software])
    breadcrumb = render_breadcrumb([
        ("Datalab Global", "/"),
        (label_categoria, href_comparador),
        (banco_exib, href_hub),
        (f"{valor_curto} em {prazo}x", None),
    ])

    corpo = f'''<main class="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pb-20 pt-8 flex-grow w-full">
        {breadcrumb}
        <header class="py-4 md:py-6 relative z-10 text-center">
            <a href="{href_hub}" class="inline-flex items-center gap-2.5 bg-white/5 border border-white/10 hover:border-sky-500/40 hover:bg-white/10 rounded-full pl-2 pr-4 py-1.5 mb-6 transition-colors group">
                {favicon_com_fallback(url_logo_atual, banco_exib, "w-6 h-6")}
                <span class="text-xs font-bold text-slate-200 group-hover:text-sky-400 tracking-wide transition-colors">{banco_exib}</span>
                <span class="text-[10px] text-slate-400 uppercase tracking-widest border-l border-white/10 pl-2">CDC {label_categoria}</span>
                <span class="text-[10px] text-sky-500/70 group-hover:text-sky-400 uppercase tracking-widest border-l border-white/10 pl-2 transition-colors">Ver taxas e condições →</span>
            </a>
            <h1 class="font-serif text-3xl md:text-4xl font-bold mb-3 leading-tight px-4">Financiamento {label_categoria} {banco_exib}: {formatar_reais(valor)} em {prazo}x</h1>
            <p class="text-slate-400 text-sm md:text-base font-light mb-2 max-w-3xl mx-auto px-4">Simulação com a taxa média real do {banco_exib} para {CATEGORIA_ARTIGO[categoria]}, apurada pelo Banco Central. Ajuste os valores abaixo pro seu caso.</p>
            <p class="text-slate-600 text-[10px] uppercase tracking-widest">Taxas atualizadas em {date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')} · Fonte: Banco Central do Brasil (BACEN)</p>
        </header>

        <!-- ZONA A: A SIMULAÇÃO -->
        <div class="glass-panel p-6 md:p-10 rounded-3xl border-t border-slate-700/50 relative overflow-hidden">
            <h2 class="text-xs font-bold text-slate-300 uppercase tracking-widest mb-1 flex items-center relative z-10">
                {icone('invoice', 'mr-3')} 1. Estratégia
            </h2>
            <p class="text-slate-400 text-[11px] mb-8 pb-4 border-b border-white/10 relative z-10">Defina os parâmetros do seu financiamento {banco_exib.lower()}.</p>
            <div class="flex flex-col lg:flex-row lg:items-start gap-10 relative z-10">
                <div class="w-full lg:w-1/2 space-y-4">
                    <div class="bg-slate-800/60 p-5 rounded-2xl border border-white/10 shadow-md shadow-black/20 hover:border-sky-500/30 transition-colors">
                        <div class="flex justify-between items-end mb-2">
                            <label class="text-[10px] font-semibold text-slate-400 uppercase tracking-widest flex items-center">
                                {icone('car' if categoria != 'moto' else 'motorcycle', 'mr-1.5 text-slate-400')} Valor do Veículo
                                {tooltip('A partir dele calculamos a entrada mínima e o valor financiado, usando a regra de entrada da categoria (' + f'{int(entrada_minima(categoria)*100)}' + '%).')}
                            </label>
                            <input type="text" id="input_valor" aria-label="Valor do veículo em reais" class="currency-input w-40 text-right bg-transparent font-medium text-white text-2xl outline-none border-b border-transparent focus:border-sky-500 transition-colors" value="{formatar_reais(valor)[3:]}">
                        </div>
                        <input type="range" id="slider_valor" aria-label="Valor do veículo" min="{valor_min_slider}" max="{valor_max_slider}" step="{passo_slider}" value="{valor}" class="w-full mt-2">
                    </div>
                    <div class="bg-slate-800/60 p-5 rounded-2xl border border-white/10 shadow-md shadow-black/20 hover:border-sky-500/30 transition-colors">
                        <div class="flex justify-between items-end mb-2">
                            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center">
                                {icone('calendar', 'mr-1.5 text-slate-400')} Prazo
                                {tooltip(f'Quantidade de parcelas mensais. O {banco_exib} permite no máximo {p["prazo_max_banco"]} meses nessa modalidade.')}
                            </label>
                            <span id="label_prazo" class="font-medium text-white text-lg">{prazo} meses</span>
                        </div>
                        <input type="range" id="slider_prazo" aria-label="Prazo em meses" min="12" max="{p['prazo_max_banco']}" step="1" value="{prazo}" class="w-full mt-2">
                    </div>
                    <p class="text-[10px] text-slate-400 pl-2">Entrada mínima da categoria: {int(entrada_minima(categoria)*100)}% do valor do veículo.</p>
                    <div class="bg-slate-800/60 p-5 rounded-2xl border border-white/10 shadow-md shadow-black/20 flex flex-wrap items-start justify-between gap-6">
                        <div>
                            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center">
                                CET Real (a.a.)
                                {tooltip('Custo Efetivo Total: a taxa de juros somada ao IOF, à tarifa de registro de contrato e ao seguro prestamista típico de mercado. É o número mais honesto pra comparar o custo entre bancos diferentes.')}
                            </p>
                            <p class="text-white font-medium text-lg" id="res_cet">{cet_fmt}% a.a.</p>
                        </div>
                        <div>
                            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center">
                                Renda Sugerida
                                {tooltip('Os bancos costumam exigir que a parcela não ultrapasse 30% da renda bruta mensal. Você pode somar a sua renda com a do cônjuge ou companheiro(a) para compor esse valor.')}
                            </p>
                            <p class="text-white font-medium text-lg currency-input" id="res_renda">{formatar_reais(renda_sugerida)}</p>
                        </div>
                    </div>
                </div>
                <div class="w-full lg:w-1/2 bg-slate-950 rounded-2xl border border-sky-500/20 shadow-inner flex flex-col relative overflow-hidden">
                    <div class="absolute top-0 right-0 w-32 h-32 bg-sky-500 rounded-full blur-[60px] opacity-10"></div>
                    <div class="px-8 pt-6 pb-4 border-b border-white/5 relative z-10 flex items-center gap-2">
                        <span class="w-2 h-2 rounded-full bg-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.8)]"></span>
                        <p class="text-sky-400 text-[10px] font-bold uppercase tracking-widest">Resultado da Simulação</p>
                    </div>
                    <div class="p-8 flex-1 flex flex-col justify-center space-y-6 relative z-10">
                        <div>
                            <p class="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-2">Parcela Mensal (Tabela Price){tooltip('Sistema de amortização usado em financiamento de veículo no Brasil: a parcela é fixa do primeiro ao último mês.')}</p>
                            <p class="text-white text-3xl font-light tracking-tight currency-input break-words" id="res_parcela">{formatar_reais(parcela)}</p>
                        </div>
                        <div class="pt-6 border-t border-white/5 grid grid-cols-2 gap-6">
                            <div><p class="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1.5">Valor Financiado</p><p class="text-white font-medium text-lg currency-input" id="res_financiado">{formatar_reais(financiado)}</p></div>
                            <div><p class="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1.5">Entrada</p><p class="text-white font-medium text-lg currency-input" id="res_entrada">{formatar_reais(entrada)}</p></div>
                            <div><p class="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1.5">Total Pago</p><p class="text-white font-medium text-lg currency-input" id="res_total_pago">{formatar_reais(total_pago)}</p></div>
                            <div><p class="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1.5">Total de Juros</p><p class="text-white font-medium text-lg currency-input" id="res_total_juros">{formatar_reais(total_juros)}</p></div>
                        </div>
                        <div class="pt-6 border-t border-white/5">
                            <p class="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-3">Composição do custo total</p>
                            {svg_donut_capital_juros(financiado, total_juros)}
                        </div>
                    </div>
                </div>
            </div>
            <div class="mt-8 relative z-10 text-center">
                <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="inline-flex items-center justify-center bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold px-8 py-3.5 rounded-2xl transition-all text-sm w-full sm:w-auto shadow-[0_0_15px_rgba(14,165,233,0.3)]">
                    Peça uma análise gratuita com essa simulação {icone('arrow-right', 'ml-2')}
                </a>
            </div>
        </div>

        {bloco_outros_prazos}

        <!-- ZONA B: A AMORTIZAÇÃO -->
        <div class="mt-8 glass-panel-sky rounded-3xl p-6 md:p-10 relative overflow-hidden shadow-[0_10px_40px_rgba(14,165,233,0.1)] border-t border-sky-500/30" id="card_amortizacao">
            <h2 class="text-xs font-bold text-sky-400 uppercase tracking-widest mb-8 border-b border-sky-500/20 pb-4 relative z-10 flex items-center">
                {icone('bolt', 'mr-3')} 2. Valor a Amortizar (A Solução)
            </h2>
            <div class="flex flex-col lg:flex-row gap-10 relative z-10">
                <div class="w-full lg:w-1/2 flex flex-col justify-center">
                    <label class="text-[10px] font-bold text-slate-300 uppercase tracking-widest block mb-4 flex items-center">
                        Amortização Extra (Recorrente)
                        {tooltip('A maioria das pessoas não faz um único pagamento extra: faz vários, ao longo do tempo (ex: com o 13º ou bônus). Aqui você simula esse padrão — quanto, e a cada quantos meses.')}
                    </label>
                    <div class="relative mb-6">
                        <span class="absolute left-4 top-1/2 -translate-y-1/2 font-light text-sky-500/50 text-3xl">R$</span>
                        <input type="text" id="input_amortizar" aria-label="Valor da amortização extra em reais" class="currency-input w-full bg-black/50 border border-sky-500/30 rounded-2xl pl-16 pr-4 py-5 focus:border-sky-400 font-medium text-sky-400 text-4xl outline-none transition-all shadow-[inset_0_2px_10px_rgba(0,0,0,0.5)]" value="{aporte_padrao_fmt}">
                    </div>
                    <input type="range" id="slider_amortizar" aria-label="Valor da amortização extra" min="0" max="{slider_amortizar_max}" step="100" value="{aporte_padrao}" class="w-full mb-6">
                    <div class="bg-slate-800/60 p-4 rounded-2xl border border-white/10">
                        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center">
                            {icone('repeat', 'mr-1.5 text-slate-400')} A Cada Quantos Meses?
                        </label>
                        <div class="flex items-center gap-3">
                            <input type="range" id="slider_periodicidade" aria-label="A cada quantos meses" min="1" max="24" step="1" value="{periodicidade_padrao}" class="w-full">
                            <span class="text-white font-medium text-sm whitespace-nowrap w-24 text-right" id="label_periodicidade">a cada {periodicidade_padrao} meses</span>
                        </div>
                    </div>
                </div>
                <div class="w-full lg:w-1/2 bg-black/40 border border-sky-500/30 rounded-2xl p-8 backdrop-blur-sm text-center flex flex-col justify-center shadow-inner">
                    <div class="mb-8">
                        <p class="text-sky-500/80 text-[10px] font-bold uppercase tracking-widest mb-3">Economia Total de Juros</p>
                        <p class="text-5xl md:text-6xl font-serif text-sky-400 currency-input break-words" id="res_economia">R$ 0,00</p>
                    </div>
                    <div>
                        <p class="text-sky-500 text-[10px] font-bold uppercase tracking-widest mb-2">Tempo Reduzido Em</p>
                        <p class="text-3xl md:text-4xl font-light text-white tracking-tight" id="res_impacto">0 Meses</p>
                        <div class="mt-5 w-full h-2 bg-slate-800 rounded-full relative overflow-hidden">
                            <div class="absolute left-0 top-0 h-full bg-slate-600 w-full"></div>
                            <div id="bar_novo_prazo" class="absolute left-0 top-0 h-full bg-sky-500 transition-all duration-700" style="width: 100%;"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- BANNER DE CONVERSÃO FINANCIA TUDO -->
        <div class="mt-16 bg-gradient-to-r from-sky-600 to-sky-900 rounded-3xl p-8 md:p-12 relative overflow-hidden shadow-[0_20px_50px_rgba(14,165,233,0.3)] border border-sky-400/50">
            <div class="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-[80px]"></div>
            <div class="flex flex-col md:flex-row items-center justify-between gap-8 relative z-10">
                <div class="md:w-2/3 text-left">
                    <div class="flex items-center gap-3 mb-4">
                        <span class="bg-yellow-400 text-yellow-950 text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest">Parceria Oficial</span>
                        <span class="flex items-center text-sky-200 text-xs font-medium">{icone('shield-check', 'mr-1')} 100% Seguro</span>
                    </div>
                    <h3 class="text-3xl font-serif text-white mb-3">Aprove o seu crédito no {banco_exib} sem sair de casa.</h3>
                    <p class="text-sky-100 text-sm md:text-base font-light leading-relaxed">
                        Como parceiros credenciados, conectamos você diretamente à mesa de crédito para buscar as <strong>melhores taxas e condições de aprovação</strong>. Análise gratuita, rápida e sem compromisso.
                    </p>
                </div>
                <div class="md:w-1/3 w-full flex justify-center md:justify-end">
                    <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="group relative inline-flex items-center justify-center bg-white text-sky-900 hover:bg-slate-100 font-black px-8 py-5 rounded-2xl transition-all shadow-2xl text-sm tracking-widest uppercase w-full text-center overflow-hidden">
                        <span class="relative z-10 flex items-center">Fazer Análise Grátis {icone('external-link', 'ml-3 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform')}</span>
                    </a>
                </div>
            </div>
        </div>

        <section class="mt-8">
            <h2 class="font-serif text-lg font-semibold mb-3">Compare com o mercado</h2>
            {faixa_html}
            {link_comparacao_html}
            <a href="{href_comparador}" class="inline-flex items-center gap-1.5 mt-3 text-xs text-slate-400 hover:text-sky-400 transition-colors">Ver ranking completo de {label_categoria.lower()} {icone('arrow-right')}</a>
        </section>

        {analise_html}
        {extras_html}

        <!-- ZONA E: GLOSSÁRIO / HUB DE AJUDA -->
        <div class="mt-16">
            <div class="flex items-center gap-3 mb-2 justify-center">
                {icone('book-open', 'text-sky-500 text-xl')}
                <h3 class="text-2xl font-serif text-white text-center">Entenda os Termos Antes de Decidir</h3>
            </div>
            <p class="text-slate-400 text-sm text-center max-w-2xl mx-auto mb-8">
                Mais do que uma calculadora: reunimos aqui o que cada termo do seu financiamento {banco_exib.lower()} significa na prática.
            </p>
            <div class="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 md:gap-x-12 divide-y divide-white/10 md:divide-y-0">
                <div class="py-5 md:pt-0 md:border-b md:border-white/10">
                    <p class="text-sky-400 font-bold text-xs uppercase tracking-widest mb-2 flex items-center">{icone('invoice', 'mr-2')} CET (Custo Efetivo Total)</p>
                    <p class="text-slate-300 text-sm font-light leading-relaxed">É o custo real do financiamento por ano, incluindo a taxa de juros, o IOF, a tarifa de registro de contrato e o seguro prestamista típico de mercado — sempre maior que a taxa de juros anunciada. É o número certo pra comparar propostas de bancos diferentes.</p>
                </div>
                <div class="py-5 md:pt-0 md:border-b md:border-white/10">
                    <p class="text-sky-400 font-bold text-xs uppercase tracking-widest mb-2 flex items-center">{icone('percent', 'mr-2')} IOF</p>
                    <p class="text-slate-300 text-sm font-light leading-relaxed">Imposto sobre Operações Financeiras: incide sobre todo financiamento (0,38% fixo + uma taxa diária, limitada a 365 dias). É cobrado uma única vez, descontado do valor liberado — já está embutido no CET calculado aqui.</p>
                </div>
                <div class="py-5 md:border-b md:border-white/10">
                    <p class="text-sky-400 font-bold text-xs uppercase tracking-widest mb-2 flex items-center">{icone('calendar', 'mr-2')} Tabela Price</p>
                    <p class="text-slate-300 text-sm font-light leading-relaxed">Sistema de amortização usado em CDC de veículo: a parcela é fixa do primeiro ao último mês, mudando só a proporção entre juros e amortização a cada mês — diferente do SAC do financiamento imobiliário, onde a parcela começa mais alta e cai com o tempo.</p>
                </div>
                <div class="py-5 md:border-b md:border-white/10">
                    <p class="text-sky-400 font-bold text-xs uppercase tracking-widest mb-2 flex items-center">{icone('bolt', 'mr-2')} Amortização Extra</p>
                    <p class="text-slate-300 text-sm font-light leading-relaxed">Pagamento fora do cronograma que abate diretamente o saldo devedor (não é uma parcela adiantada). Reduz os juros futuros e encurta o prazo, mantendo a parcela mensal do jeito que já estava combinada.</p>
                </div>
                <div class="py-5 md:border-b md:border-white/10">
                    <p class="text-sky-400 font-bold text-xs uppercase tracking-widest mb-2 flex items-center">{icone('home', 'mr-2')} De Onde Vem essa Taxa</p>
                    <p class="text-slate-300 text-sm font-light leading-relaxed">A taxa de {taxa_aa_fmt}% a.a. mostrada aqui é a taxa média efetivamente contratada pelo {banco_exib} nessa modalidade, apurada mensalmente pelo Banco Central (BACEN) — não é uma taxa promocional "a partir de". Sua taxa final depende do seu relacionamento com o banco e da análise de crédito.</p>
                </div>
                <div class="py-5 pb-0 md:pb-0 md:border-b md:border-white/10">
                    <p class="text-sky-400 font-bold text-xs uppercase tracking-widest mb-2 flex items-center">{icone('percent', 'mr-2')} Renda Mínima Necessária</p>
                    <p class="text-slate-300 text-sm font-light leading-relaxed">Os bancos não aprovam um financiamento cuja parcela ultrapasse 30% da sua renda familiar bruta mensal. Boa notícia: você pode somar a sua renda com a do cônjuge ou companheiro(a) para atingir esse limite.</p>
                </div>
            </div>
        </div>

        {faq_html}
    </main>'''

    dados_pagina_js = json.dumps({
        "bancoChave": banco, "bancoNome": banco_exib, "taxaAm": taxa_am,
        "prazoMaxBanco": p["prazo_max_banco"], "entradaPct": entrada_minima(categoria),
        "valorMin": valor_min_slider, "valorMax": valor_max_slider,
        "bancosCategoria": json.loads(bancos_categoria_js),
        "linkAfiliado": LINK_FINANCIA_TUDO,
    }, ensure_ascii=False)

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
    <script src="calculo.js"></script>
    <script>iniciarSimulador({dados_pagina_js});</script>
    {SCRIPT_AJUSTA_TOOLTIPS}
</body>
</html>'''
    return html


# ---------------------------------------------------------------------------
# Hub por banco+categoria: hub-{banco}-{categoria}.html
# ---------------------------------------------------------------------------

def gerar_hub(categoria, banco, banco_exib, paginas_banco, data_atualizacao):
    label_categoria = CATEGORIA_LABEL[categoria]
    slug_pagina = slug_hub(categoria, banco)
    url_canonica = f"{DOMINIO}/{slug_pagina}"
    href_comparador = f"{slug_comparador(categoria)}"
    dados_banco = obter_regra(banco)
    # Ver nota de padrão brasileiro (vírgula decimal) em
    # gerar_pagina_individual — mesmo achado de auditoria, mesmo fix.
    taxa_am_fmt = f"{dados_banco['taxa_am']:.2f}".replace('.', ',')
    taxa_aa_fmt = f"{dados_banco['taxa_aa']:.2f}".replace('.', ',')

    titulo_pagina = f"Financiamento {label_categoria} {banco_exib}: simulações | Datalab"
    meta_description = (
        f"Taxa do {banco_exib} hoje para {label_categoria.lower()}: {taxa_am_fmt}% ao mês ({taxa_aa_fmt}% ao ano). "
        f"Simulações por valor e prazo, até {dados_banco['prazo_max']} meses."
    )

    paginas_por_valor = {}
    for p in sorted(paginas_banco, key=lambda p: (p["valor_veiculo"], p["prazo"])):
        paginas_por_valor.setdefault(p["valor_veiculo"], []).append(p)

    blocos_valor = []
    for valor, paginas in paginas_por_valor.items():
        links = "\n".join(
            f'<a href="{p["slug"]}" class="flex items-center justify-between p-3 rounded-lg border border-white/10 hover:border-sky-500/50 hover:bg-white/5 transition-all">'
            f'<span class="text-sm">{p["prazo"]} meses</span><span class="text-sm font-semibold text-sky-400">{formatar_reais(p["parcela"])}/mês</span></a>'
            for p in paginas
        )
        blocos_valor.append(f'''<div class="glass-panel rounded-2xl p-5">
            <h3 class="font-serif text-base font-semibold mb-3">{formatar_valor_curto(valor)}</h3>
            <div class="grid gap-2">{links}</div>
        </div>''')
    grade_html = "\n".join(blocos_valor)

    # Mesmo cenário de referência do comparador da categoria (valor
    # mediano da grade, 48 meses) — precisa ser o MESMO em toda página
    # dessa categoria pra faixa de CET ser comparável entre elas (mesma
    # lógica do "VALOR_REF/PRAZO_REF" do hub do projeto irmão).
    valor_referencia = VALORES_POR_CATEGORIA[categoria][len(VALORES_POR_CATEGORIA[categoria]) // 2]
    prazo_referencia = 48
    ranking_ref = comparar_bancos_categoria(categoria, valor_referencia, prazo_referencia)
    cet_banco_ref = next(r["cet"] for r in ranking_ref if r["banco"] == banco)
    faixa_html = renderizar_faixa_mercado(banco, banco_exib, cet_banco_ref, ranking_ref)
    cets_ref_ordenados = sorted(r["cet"] for r in ranking_ref)
    cet_min_ref_fmt = f"{cets_ref_ordenados[0]:.2f}".replace('.', ',')
    cet_max_ref_fmt = f"{cets_ref_ordenados[-1]:.2f}".replace('.', ',')

    faq_html, schema_faq = render_faq_visual([
        (
            f"Qual a taxa de financiamento de {label_categoria.lower()} no {banco_exib}?",
            f"A taxa média real do {banco_exib} para financiamento de {CATEGORIA_ARTIGO[categoria]} é {taxa_am_fmt}% "
            f"ao mês ({taxa_aa_fmt}% ao ano), segundo dados do Banco Central. O CET (Custo Efetivo Total, que já "
            f"inclui IOF e tarifas) varia conforme o valor e o prazo escolhidos — veja as simulações abaixo.",
        ),
        (
            f"Qual o prazo máximo pra financiar {label_categoria.lower()} no {banco_exib}?",
            f"O {banco_exib} financia {CATEGORIA_ARTIGO[categoria]} em até {dados_banco['prazo_max']} meses nesta "
            f"modalidade. Quanto maior o prazo, menor a parcela mensal, mas maior o total de juros pago no fim — "
            f"compare as opções na grade abaixo.",
        ),
        (
            f"O CET do {banco_exib} está competitivo em relação a outros bancos?",
            f"Na faixa de mercado atual para {label_categoria.lower()}, os CETs variam entre {cet_min_ref_fmt}% e "
            f"{cet_max_ref_fmt}% ao ano — a barra acima mostra onde o {banco_exib} está nessa faixa. A Datalab não "
            f"indica um banco \"vencedor\": a taxa final de cada cliente depende de relacionamento bancário, "
            f"histórico de crédito e entrada, então vale simular mais de uma opção antes de decidir.",
        ),
    ])

    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": label_categoria, "item": f"{DOMINIO}/{href_comparador}"},
            {"@type": "ListItem", "position": 3, "name": banco_exib, "item": url_canonica},
        ],
    }

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_breadcrumb, schema_faq])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), (label_categoria, href_comparador), (banco_exib, None)])

    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Financiamento {label_categoria} pelo {banco_exib}</h1>
        <p class="text-white text-lg font-medium mb-3">Taxa do {banco_exib} hoje para {label_categoria.lower()}: {taxa_am_fmt}% ao mês ({taxa_aa_fmt}% ao ano).</p>
        <p class="text-slate-400 text-sm mb-8">Taxa média real: {taxa_am_fmt}% a.m. ({taxa_aa_fmt}% a.a.) · Prazo máximo: {dados_banco['prazo_max']} meses. Escolha um valor e prazo para ver a simulação completa.</p>

        <div class="mb-8">{faixa_html}</div>
        {html_serie_banco(historico_cache(), banco, banco_exib, dados_banco['taxa_am'])}

        <div class="grid sm:grid-cols-2 gap-4">{grade_html}</div>
        <a href="{href_comparador}" class="inline-flex items-center gap-1.5 mt-8 text-xs text-slate-400 hover:text-sky-400 transition-colors">Ver ranking completo de {label_categoria.lower()} {icone('arrow-right')}</a>
        {faq_html}
    </main>'''

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
    {SCRIPT_AJUSTA_TOOLTIPS}
</body>
</html>'''
    return slug_pagina, html


# ---------------------------------------------------------------------------
# Comparador por categoria: comparador-{categoria}.html (também funciona
# como "hub da categoria" — decisão de arquitetura documentada no topo do
# arquivo, pra não duplicar conteúdo com uma página de índice separada).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Histórico de taxas (BACEN) e dados abertos
#
# A série vem de historico_taxas.csv (ver historico_taxas_veiculos.py): para
# cada mês fechado, a última janela de 5 dias úteis divulgada pelo BACEN
# (modalidade 401101, uma só para carro novo, usado e moto).
# ---------------------------------------------------------------------------

MESES_PT = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
            "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
MESES_PT_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
FONTE_BACEN_URL = "https://www.bcb.gov.br/estatisticas/reporttxjuros?codigoSegmento=1&codigoModalidade=401101"
LICENCA_DADOS = "CC BY 4.0"
LICENCA_DADOS_URL = "https://creativecommons.org/licenses/by/4.0/deed.pt-br"
MESES_NA_TABELA_EVOLUCAO = 6
NOTA_MODALIDADE = ("O Banco Central publica uma única modalidade para aquisição de veículos (pessoa física, pré-fixada), "
                   "sem separar carro novo, carro usado e moto: a taxa de cada banco é a mesma série para as três categorias.")


def carregar_historico():
    from historico_taxas_veiculos import ler_historico
    return ler_historico()


def _rotulo_mes(mes_referencia):
    return f"{MESES_PT_ABREV[int(mes_referencia[5:7]) - 1]}/{mes_referencia[2:4]}"


def _pct2(v):
    return f"{v:.2f}".replace(".", ",")


def _sinal_pp(v):
    return ("+" if v > 0 else "−" if v < 0 else "") + f"{abs(v):.2f}".replace(".", ",")


def resumo_historico(historico, categoria=None):
    """Estrutura pronta pra renderizar (taxa ao mês): meses, linhas por banco
    (só os da categoria, se informada) e maior alta/queda. None se < 2 meses."""
    permitidos = set(bancos_para_categoria(categoria)) if categoria else None
    meses = sorted({r["mes_referencia"] for r in historico})[-MESES_NA_TABELA_EVOLUCAO:]
    if len(meses) < 2:
        return None
    por_banco = {}
    for r in historico:
        if r["mes_referencia"] in meses and (permitidos is None or r["banco"] in permitidos):
            por_banco.setdefault(r["banco"], {})[r["mes_referencia"]] = r["taxa_am"]
    linhas = []
    for banco, serie in por_banco.items():
        if meses[0] in serie and meses[-1] in serie:
            linhas.append({"banco": banco, "banco_exib": BANCOS_VEICULOS[banco]["nome_exibicao"], "serie": serie,
                           "variacao": serie[meses[-1]] - serie[meses[0]], "atual": serie[meses[-1]]})
    if not linhas:
        return None
    linhas.sort(key=lambda x: x["atual"])
    return {"meses": meses, "linhas": linhas,
            "maior_queda": min(linhas, key=lambda x: x["variacao"]),
            "maior_alta": max(linhas, key=lambda x: x["variacao"])}


def html_evolucao_taxas(resumo):
    if not resumo:
        return ""
    cab = "".join(f'<th scope="col" class="px-2 py-2 text-right font-medium whitespace-nowrap">{_rotulo_mes(m)}</th>' for m in resumo["meses"])
    corpo = ""
    for x in resumo["linhas"]:
        celulas = ""
        for m in resumo["meses"]:
            valor = _pct2(x["serie"][m]) if m in x["serie"] else "–"
            celulas += f'<td class="px-2 py-2 text-right whitespace-nowrap">{valor}</td>'
        cor = "text-emerald-400" if x["variacao"] < 0 else "text-rose-400" if x["variacao"] > 0 else "text-slate-400"
        corpo += (f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">{x["banco_exib"]}</th>'
                  f'{celulas}<td class="px-2 py-2 text-right font-bold whitespace-nowrap {cor}">{_sinal_pp(x["variacao"])} p.p.</td></tr>')
    return f'''<section class="mt-12">
            <h2 class="font-serif text-xl font-bold mb-2">Como as taxas evoluíram nos últimos {len(resumo["meses"])} meses</h2>
            <p class="text-slate-400 text-xs font-light leading-relaxed mb-4">Taxa média de juros ao mês efetivamente contratada no financiamento de veículos, por banco, no fim de cada mês, segundo o Banco Central. É a taxa praticada, não uma oferta: a sua proposta pode ser diferente.</p>
            <div class="overflow-x-auto rounded-xl border border-white/10">
                <table class="w-full text-xs text-slate-300">
                    <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Banco (% a.m.)</th>{cab}<th scope="col" class="px-2 py-2 text-right font-medium whitespace-nowrap">Variação</th></tr></thead>
                    <tbody>{corpo}</tbody>
                </table>
            </div>
            <p class="text-slate-500 text-[11px] mt-3">{NOTA_MODALIDADE} Fonte: <a href="{FONTE_BACEN_URL}" rel="noopener" class="underline">Banco Central do Brasil</a>.</p>
        </section>'''


def texto_variacao(resumo):
    if not resumo:
        return None
    m0, m1 = resumo["meses"][0], resumo["meses"][-1]
    q, a = resumo["maior_queda"], resumo["maior_alta"]
    frase = (f"Entre {_rotulo_mes(m0)} e {_rotulo_mes(m1)}, a maior queda na taxa média contratada foi a de {q['banco_exib']} "
             f"({_sinal_pp(q['variacao'])} p.p. ao mês, de {_pct2(q['serie'][m0])}% para {_pct2(q['serie'][m1])}% a.m.)")
    if a["variacao"] > 0:
        frase += (f" e a maior alta, a de {a['banco_exib']} ({_sinal_pp(a['variacao'])} p.p., "
                  f"de {_pct2(a['serie'][m0])}% para {_pct2(a['serie'][m1])}% a.m.)")
    return frase + ". São médias do Banco Central, não ofertas."


# ---------------------------------------------------------------------------
# Motor v3 (31/out/2026): conteúdo próprio por página, links entre vizinhas,
# páginas mensais de taxas e metodologia. Tudo calculado dos dados reais.
# Nenhuma página existente sai do índice: veículos já indexa bem.
# ---------------------------------------------------------------------------
MESES_NA_SERIE_BANCO = 12
SLUG_INDICE_MENSAL = "taxas-financiamento-veiculos"
MESES_INDEXAVEIS_MENSAL = 12  # meses mais antigos continuam no ar, mas noindex
_SEM_ACENTO = str.maketrans("ç", "c")


_HISTORICO_CACHE = []


def historico_cache():
    """Lê historico_taxas.csv uma única vez por execução."""
    if not _HISTORICO_CACHE:
        _HISTORICO_CACHE.extend(carregar_historico())
    return _HISTORICO_CACHE


def slug_mes(mes_referencia):
    """'2026-09' -> 'taxas-financiamento-veiculos-setembro-2026'."""
    return f"{SLUG_INDICE_MENSAL}-{MESES_PT[int(mes_referencia[5:7]) - 1].translate(_SEM_ACENTO)}-{mes_referencia[:4]}"


def nome_mes(mes_referencia):
    """'2026-09' -> 'setembro de 2026'."""
    return f"{MESES_PT[int(mes_referencia[5:7]) - 1]} de {mes_referencia[:4]}"


def projecao_price(financiado, prazo, taxa_am):
    """Marcos do contrato (a cada 6 meses até 24x; a cada 12 depois, sempre
    incluindo o último mês): saldo devedor, juros acumulados e parcelas pagas.
    Números próprios de cada página (valor x prazo x taxa)."""
    passo = 6 if prazo <= 24 else 12
    marcos = sorted({m for m in range(passo, prazo + 1, passo)} | {prazo})
    tabela = gerar_tabela_amortizacao(financiado, prazo, taxa_am)
    juros_acum = 0.0
    linhas = []
    for l in tabela:
        juros_acum += l["juros"]
        if l["mes"] in marcos:
            linhas.append({"mes": l["mes"], "parcelas_pagas": l["parcela"] * l["mes"], "saldo": l["saldo"], "juros": juros_acum})
    return linhas


def html_projecao_price(financiado, prazo, taxa_am, banco_exib):
    linhas = projecao_price(financiado, prazo, taxa_am)
    if not linhas:
        return ""
    corpo = "".join(
        f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">Mês {x["mes"]}</th>'
        f'<td class="px-2 py-2 text-right whitespace-nowrap">{formatar_reais(x["parcelas_pagas"])}</td>'
        f'<td class="px-2 py-2 text-right whitespace-nowrap">{formatar_reais(x["saldo"])}</td>'
        f'<td class="px-2 py-2 text-right whitespace-nowrap">{formatar_reais(x["juros"])}</td></tr>' for x in linhas)
    meio = min(linhas, key=lambda x: abs(x["mes"] - prazo / 2))
    pct_quitado = 100 * (1 - meio["saldo"] / financiado)
    pct_prazo = 100 * meio["mes"] / prazo
    frase = (f"No mês {meio['mes']} ({pct_prazo:.0f}% do prazo), você já pagou {formatar_reais(meio['parcelas_pagas'])} em parcelas, "
             f"mas só {pct_quitado:.0f}% do valor financiado foi quitado: na Tabela Price os juros pesam mais no início, "
             f"então a dívida cai devagar nas primeiras parcelas. Se quiser quitar antes, vale simular uma amortização extra no simulador acima.")
    return f'''<section class="mt-8"><h2 class="font-serif text-lg font-semibold mb-3">Como a dívida evolui ao longo do contrato</h2>
        <div class="glass-panel rounded-2xl p-6 md:p-8">
            <p class="text-slate-400 text-xs mb-4">Financiando {formatar_reais(financiado)} em {prazo}x no {banco_exib}, a {_pct2(taxa_am)}% ao mês, sem amortizações extras.</p>
            <div class="overflow-x-auto rounded-xl border border-white/10">
                <table class="w-full text-xs text-slate-300">
                    <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr>
                        <th scope="col" class="px-2 py-2 text-left font-medium">Mês</th>
                        <th scope="col" class="px-2 py-2 text-right font-medium">Parcelas pagas</th>
                        <th scope="col" class="px-2 py-2 text-right font-medium">Saldo devedor</th>
                        <th scope="col" class="px-2 py-2 text-right font-medium">Juros acumulados</th>
                    </tr></thead>
                    <tbody>{corpo}</tbody>
                </table>
            </div>
            <p class="text-slate-300 text-sm font-light leading-relaxed mt-4">{frase}</p>
            <p class="text-slate-500 text-[11px] mt-2">Sem IOF, tarifa de registro e seguro (o CET, que os inclui, está no simulador). Parcela fixa: {formatar_reais(calcular_pmt_price(financiado, prazo, taxa_am))}.</p>
        </div></section>'''


def posicao_no_mercado(ranking, cet_atual):
    """Posição do CET desta página entre os bancos simulados no mesmo cenário,
    sem nomear concorrente (decisão do usuário: o simulador não indica banco)."""
    cets = sorted(r["cet"] for r in ranking)
    n = len(cets)
    if n < 3:
        return ""
    mediana = cets[n // 2] if n % 2 else (cets[n // 2 - 1] + cets[n // 2]) / 2
    posicao = sum(1 for c in cets if c < cet_atual - 1e-9) + 1
    dif = cet_atual - mediana
    if abs(dif) < 0.005:
        rel = "praticamente igual à mediana"
    else:
        rel = f"{_pct2(abs(dif))} p.p. {'acima' if dif > 0 else 'abaixo'} da mediana"
    return (f"Nas mesmas condições (mesmo valor e prazo, cada banco com a sua entrada mínima), o CET desta simulação, "
            f"{_pct2(cet_atual)}% ao ano, fica na {posicao}ª posição entre {n} bancos (do menor para o maior CET), "
            f"{rel} do mercado ({_pct2(mediana)}%).")


def serie_do_banco(historico, banco):
    """Últimos MESES_NA_SERIE_BANCO meses da taxa média (a.m.) do banco, do
    mais antigo ao mais recente."""
    pontos = sorted((r["mes_referencia"], r["taxa_am"]) for r in historico if r["banco"] == banco)
    return pontos[-MESES_NA_SERIE_BANCO:]


def html_serie_banco(historico, banco, banco_exib, taxa_simulada):
    pontos = serie_do_banco(historico, banco)
    if len(pontos) < 3:
        return ""
    (m0, t0), (m1, t1) = pontos[0], pontos[-1]
    maior = max(pontos, key=lambda p: p[1])
    menor = min(pontos, key=lambda p: p[1])
    celulas = "".join(
        f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-1.5 text-left font-medium text-white whitespace-nowrap">'
        f'<a href="{slug_mes(m)}" class="hover:text-sky-400">{_rotulo_mes(m)}</a></th>'
        f'<td class="px-2 py-1.5 text-right">{_pct2(t)}%</td></tr>' for m, t in reversed(pontos))
    sentido = "caiu" if t1 < t0 else "subiu" if t1 > t0 else "ficou estável"
    frase = (f"Segundo o Banco Central, a taxa média contratada no {banco_exib} {sentido} de {_pct2(t0)}% ao mês em {_rotulo_mes(m0)} "
             f"para {_pct2(t1)}% em {_rotulo_mes(m1)} ({_sinal_pp(t1 - t0)} p.p.). Nos últimos {len(pontos)} meses, a máxima foi de "
             f"{_pct2(maior[1])}% ({_rotulo_mes(maior[0])}) e a mínima, de {_pct2(menor[1])}% ({_rotulo_mes(menor[0])}). "
             f"A simulação desta página usa {_pct2(taxa_simulada)}% ao mês.")
    return f'''<section class="mt-8"><h2 class="font-serif text-lg font-semibold mb-3">Taxa do {banco_exib} nos últimos meses</h2>
        <div class="glass-panel rounded-2xl p-6 md:p-8">
            <p class="text-slate-400 text-xs mb-4">Taxa média efetivamente contratada, por mês (% ao mês). Não é uma oferta: a sua proposta pode ser diferente.</p>
            <p class="text-slate-300 text-sm font-light leading-relaxed mb-4">{frase}</p>
            <div class="overflow-x-auto rounded-xl border border-white/10 max-w-xs">
                <table class="w-full text-xs text-slate-300"><thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Mês</th><th scope="col" class="px-2 py-2 text-right font-medium">Taxa a.m.</th></tr></thead><tbody>{celulas}</tbody></table>
            </div>
            <p class="text-slate-500 text-[11px] mt-3">Fonte: <a href="{FONTE_BACEN_URL}" rel="noopener" class="underline">Banco Central do Brasil</a>. O BACEN publica uma só modalidade para veículos (carro novo, usado e moto juntos). Série completa em <a href="dados-abertos" class="underline">dados abertos</a>.</p>
        </div></section>'''


def html_vizinhas(p, todas_paginas):
    """Links para o valor anterior e o seguinte (mesmo banco, categoria e prazo) e
    para os índices de taxas e a metodologia. Os outros prazos do mesmo valor já
    têm bloco próprio na página."""
    mesmo = sorted((q for q in todas_paginas if q["categoria"] == p["categoria"] and q["banco"] == p["banco"]
                    and q["prazo"] == p["prazo"]), key=lambda q: q["valor_veiculo"])
    idx = next((k for k, q in enumerate(mesmo) if q["slug"] == p["slug"]), None)
    itens = []
    if idx is not None:
        if idx > 0:
            itens.append(mesmo[idx - 1])
        if idx + 1 < len(mesmo):
            itens.append(mesmo[idx + 1])
    links = "".join(
        f'<a href="{q["slug"]}" class="block p-3 rounded-lg border border-white/10 hover:border-sky-500/50 text-sm text-slate-300 transition-all">'
        f'{p["nome_exibicao"]}: {formatar_valor_curto(q["valor_veiculo"])} em {q["prazo"]}x, parcela de {formatar_reais(q["parcela"])}</a>' for q in itens)
    bloco = (f'<h2 class="font-serif text-lg font-semibold mb-3">Valores vizinhos no {p["nome_exibicao"]}</h2>'
             f'<div class="grid sm:grid-cols-2 gap-3">{links}</div>') if links else ""
    return (f'<section class="mt-8">{bloco}<p class="text-slate-500 text-xs mt-3">'
            f'<a href="{SLUG_INDICE_MENSAL}" class="underline hover:text-sky-400">Taxas de financiamento de veículos mês a mês</a> · '
            f'<a href="financiamento-veiculos" class="underline hover:text-sky-400">Parcela por valor e prazo</a> · '
            f'<a href="{slug_renda(p["categoria"], p["valor_veiculo"]) if p["valor_veiculo"] in VALORES_POR_CATEGORIA[p["categoria"]] else SLUG_INDICE_RENDA}" class="underline hover:text-sky-400">Renda necessária para financiar</a> · '
            f'<a href="metodologia" class="underline hover:text-sky-400">Como calculamos</a></p></section>')


def _mediana(valores):
    v = sorted(valores)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def _hub_do_banco(banco):
    for categoria in CATEGORIAS:
        if banco in bancos_para_categoria(categoria):
            return slug_hub(categoria, banco)
    return None


def gerar_paginas_mensais(pasta_saida, data_atualizacao, historico):
    """Uma página por mês da série do BACEN + o arquivo (/taxas-financiamento-
    veiculos). Só os MESES_INDEXAVEIS_MENSAL mais recentes são indexáveis.
    Retorna as URLs indexáveis (para o sitemap)."""
    meses = sorted({r["mes_referencia"] for r in historico})
    if len(meses) < 2:
        return []
    por_mes = {}
    for r in historico:
        por_mes.setdefault(r["mes_referencia"], {})[r["banco"]] = r["taxa_am"]
    recentes = set(meses[-MESES_INDEXAVEIS_MENSAL:])
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    urls = []
    for k, mes in enumerate(meses):
        taxas = por_mes[mes]
        anterior = por_mes[meses[k - 1]] if k > 0 else {}
        ano_antes = f"{int(mes[:4]) - 1}{mes[4:]}"
        mes_ano = nome_mes(mes)
        ordenado = sorted(taxas.items(), key=lambda kv: kv[1])
        menor_b, menor_t = ordenado[0]
        maior_b, maior_t = ordenado[-1]
        media = sum(taxas.values()) / len(taxas)
        mediana = _mediana(list(taxas.values()))
        comuns = [b for b in taxas if b in anterior]
        var_media = (sum(taxas[b] for b in comuns) / len(comuns) - sum(anterior[b] for b in comuns) / len(comuns)) if comuns else None
        var_ano = None
        if ano_antes in por_mes:
            cb = [b for b in taxas if b in por_mes[ano_antes]]
            if cb:
                var_ano = sum(taxas[b] for b in cb) / len(cb) - sum(por_mes[ano_antes][b] for b in cb) / len(cb)
        linhas = ""
        for b, t in ordenado:
            parcela = calcular_pmt_price(50_000, 48, t)
            v = f'{_sinal_pp(t - anterior[b])} p.p.' if b in anterior else "–"
            nome = BANCOS_VEICULOS[b]["nome_exibicao"]
            hub = _hub_do_banco(b)
            rotulo = f'<a href="{hub}" class="hover:text-sky-400">{nome}</a>' if hub else nome
            linhas += (f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">{rotulo}</th>'
                       f'<td class="px-2 py-2 text-right whitespace-nowrap">{_pct2(t)}%</td>'
                       f'<td class="px-2 py-2 text-right whitespace-nowrap">{_pct2(((1 + t / 100) ** 12 - 1) * 100)}%</td>'
                       f'<td class="px-2 py-2 text-right whitespace-nowrap">{v}</td>'
                       f'<td class="px-2 py-2 text-right whitespace-nowrap">{formatar_reais(parcela)}</td></tr>')
        n_menor, n_maior = BANCOS_VEICULOS[menor_b]["nome_exibicao"], BANCOS_VEICULOS[maior_b]["nome_exibicao"]
        resumo = (f"Em {mes_ano}, a taxa média contratada no financiamento de veículos variou de {_pct2(menor_t)}% ao mês "
                  f"({n_menor}) a {_pct2(maior_t)}% ({n_maior}), com média de {_pct2(media)}% e mediana de "
                  f"{_pct2(mediana)}% entre os {len(taxas)} bancos que o Banco Central acompanha.")
        if var_media is not None:
            resumo += (f" Em relação ao mês anterior, a média dos mesmos bancos {'caiu' if var_media < 0 else 'subiu' if var_media > 0 else 'ficou estável'}"
                       f" ({_sinal_pp(var_media)} p.p.).")
        if var_ano is not None:
            resumo += f" Contra {nome_mes(ano_antes)}, a variação é de {_sinal_pp(var_ano)} p.p."
        faq_html, schema_faq = render_faq_visual([
            (f"Qual a menor taxa de financiamento de veículos em {mes_ano}?",
             f"Entre os bancos acompanhados pelo Banco Central, {n_menor} teve a menor taxa média contratada em {mes_ano}: {_pct2(menor_t)}% ao mês."),
            (f"Qual a taxa média do financiamento de veículos em {mes_ano}?",
             f"A média simples dos {len(taxas)} bancos foi de {_pct2(media)}% ao mês, e a mediana, de {_pct2(mediana)}%. São taxas efetivamente contratadas, não ofertas."),
        ])
        slug = slug_mes(mes)
        url = f"{DOMINIO}/{slug}"
        indexavel = mes in recentes
        titulo = _escolher_que_cabe(60, f"Taxa de financiamento de veículos em {mes_ano} | Datalab Global",
                                    f"Taxa de financiamento de veículos em {mes_ano}")
        desc = _escolher_que_cabe(
            160, f"Taxa do financiamento de veículos em {mes_ano}: de {_pct2(menor_t)}% a {_pct2(maior_t)}% ao mês, média de {_pct2(media)}%. Veja a taxa de cada banco.",
            f"Taxa do financiamento de veículos em {mes_ano}: de {_pct2(menor_t)}% a {_pct2(maior_t)}% ao mês, média de {_pct2(media)}%.")
        schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": "Taxas mês a mês", "item": f"{DOMINIO}/{SLUG_INDICE_MENSAL}"},
            {"@type": "ListItem", "position": 3, "name": mes_ano, "item": url}]}
        vizinhos = ""
        if k > 0:
            vizinhos += f'<a href="{slug_mes(meses[k - 1])}" class="underline hover:text-sky-400">← {nome_mes(meses[k - 1])}</a>'
        if k + 1 < len(meses):
            vizinhos += f' &nbsp;·&nbsp; <a href="{slug_mes(meses[k + 1])}" class="underline hover:text-sky-400">{nome_mes(meses[k + 1])} →</a>'
        cobertura = [(r["inicio_periodo"], r["fim_periodo"]) for r in historico if r["mes_referencia"] == mes]
        schema_dados = {
            "@context": "https://schema.org", "@type": "Dataset", "name": f"Taxas do financiamento de veículos por banco em {mes_ano}",
            "description": f"Taxa média de juros contratada (% ao mês) por banco em {mes_ano}, segundo o Banco Central do Brasil.",
            "url": url, "inLanguage": "pt-BR", "license": LICENCA_DADOS_URL, "isAccessibleForFree": True,
            "creator": {"@type": "Organization", "name": "Datalab Global", "url": f"{DOMINIO}/"},
            "isBasedOn": FONTE_BACEN_URL, "temporalCoverage": f"{min(c[0] for c in cobertura)}/{max(c[1] for c in cobertura)}",
            "variableMeasured": ["Taxa média de juros contratada (% ao mês)"],
            "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{DOMINIO}/dados/taxas-financiamento-veiculos.csv"}],
        }
        head = render_head(titulo, desc, url, [schema_bc, schema_faq, schema_dados], robots=(None if indexavel else "noindex,follow"))
        html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    <main class="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-2xl sm:text-4xl font-bold mb-4">Taxa de financiamento de veículos em {mes_ano}</h1>
        <p class="text-slate-300 text-base font-light leading-relaxed mb-8">{resumo}</p>
        <div class="overflow-x-auto rounded-xl border border-white/10">
            <table class="w-full text-xs text-slate-300">
                <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr>
                    <th scope="col" class="px-2 py-2 text-left font-medium">Banco</th>
                    <th scope="col" class="px-2 py-2 text-right font-medium">Taxa a.m.</th>
                    <th scope="col" class="px-2 py-2 text-right font-medium">Taxa a.a.</th>
                    <th scope="col" class="px-2 py-2 text-right font-medium">Vs. mês anterior</th>
                    <th scope="col" class="px-2 py-2 text-right font-medium">Parcela de R$ 50 mil em 48x*</th>
                </tr></thead>
                <tbody>{linhas}</tbody>
            </table>
        </div>
        <p class="text-slate-500 text-[11px] mt-3">* Financiando R$ 50.000 em 48 meses pela Tabela Price, sem IOF, tarifas e seguro, na taxa do mês. Taxa a.a. = taxa mensal composta por 12 meses. Fonte: média contratada, <a href="{FONTE_BACEN_URL}" rel="noopener" class="underline">Banco Central do Brasil</a>; o BACEN publica uma só modalidade para veículos (carro novo, usado e moto). Veja <a href="metodologia" class="underline">como calculamos</a>.</p>
        <p class="text-slate-400 text-sm mt-6">{vizinhos}</p>
        {faq_html}
        <p class="text-slate-400 text-sm mt-10">Simule o seu caso: <a href="{slug_comparador('novo')}" class="text-sky-400 underline">carro novo</a> · <a href="{slug_comparador('usado')}" class="text-sky-400 underline">carro usado</a> · <a href="{slug_comparador('moto')}" class="text-sky-400 underline">moto</a> · <a href="{SLUG_INDICE_MENSAL}" class="text-sky-400 underline">todos os meses</a></p>
        {_cta_comparacao("Quer a menor taxa para o seu caso?")}
    </main>
    {render_footer()}
</body>
</html>'''
        with open(os.path.join(pasta_saida, f"{slug}.html"), "w", encoding="utf-8") as f:
            f.write(corrigir_concordancia(html))
        if indexavel:
            urls.append(url)

    itens = "".join(
        f'<li><a href="{slug_mes(m)}" class="text-sky-400 underline hover:text-sky-300">Taxa de financiamento de veículos em {nome_mes(m)}</a>'
        f' <span class="text-slate-500 text-xs">(média {_pct2(sum(por_mes[m].values()) / len(por_mes[m]))}% a.m.)</span></li>'
        for m in reversed(meses))
    url_ind = f"{DOMINIO}/{SLUG_INDICE_MENSAL}"
    titulo_ind = "Taxas de financiamento de veículos mês a mês | Datalab Global"
    desc_ind = (f"Histórico mensal das taxas do financiamento de veículos por banco, de {nome_mes(meses[0])} a {nome_mes(meses[-1])}, "
                f"com dados do Banco Central.")[:160]
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Taxas mês a mês", "item": url_ind}]}
    head = render_head(titulo_ind, desc_ind, url_ind, [schema_bc])
    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    <main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-2xl sm:text-4xl font-bold mb-4">Taxas de financiamento de veículos mês a mês</h1>
        <p class="text-slate-300 text-base font-light leading-relaxed mb-8">A taxa média efetivamente contratada de cada banco, todo mês, desde {nome_mes(meses[0])}, segundo o Banco Central. Atualizado em {data_br}. Para baixar a série completa, veja os <a href="dados-abertos" class="text-sky-400 underline">dados abertos</a>.</p>
        <ul class="space-y-3 text-sm">{itens}</ul>
        <p class="text-slate-400 text-sm mt-10"><a href="metodologia" class="text-sky-400 underline">Metodologia</a> · <a href="financiamento-veiculos" class="text-sky-400 underline">Parcela por valor e prazo</a></p>
    </main>
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, f"{SLUG_INDICE_MENSAL}.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html))
    urls.append(url_ind)
    return urls


def gerar_pagina_metodologia(pasta_saida, data_atualizacao):
    """/metodologia: de onde vêm os números, como são calculados e o que não
    são. Descreve só o que o código faz (ver calcular_cet_veiculo)."""
    url = f"{DOMINIO}/metodologia"
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    titulo = "Metodologia: de onde vêm as taxas e os cálculos | Datalab Global"
    desc = ("Como a Datalab Global obtém as taxas do Banco Central e calcula parcela, IOF e CET do financiamento de veículos. "
            "O que os números são e o que não são.")
    schema = {"@context": "https://schema.org", "@type": "WebPage", "url": url, "name": titulo, "dateModified": data_atualizacao,
              "isPartOf": {"@type": "WebSite", "url": f"{DOMINIO}/", "name": "Simulador de financiamento de veículos | Datalab Global"},
              "publisher": {"@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global"}}
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Metodologia", "item": url}]}
    head = render_head(titulo, desc, url, [schema, schema_bc])
    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    <main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-2xl sm:text-4xl font-bold mb-8">Metodologia</h1>
        <div class="glass-panel rounded-2xl p-6 md:p-10 space-y-6 text-slate-300 leading-relaxed">
            <h2 class="text-xl font-serif text-white">De onde vêm as taxas</h2>
            <p>As taxas vêm do relatório de taxas de juros por instituição financeira do Banco Central do Brasil, modalidade "Pessoa Física, aquisição de veículos, prefixado" (código 401101). É a taxa <strong>média das operações efetivamente contratadas</strong>, não uma oferta. O Banco Central publica uma única modalidade para veículos: não existe taxa oficial separada para carro novo, usado e moto, então o mesmo número serve às três categorias. O histórico mensal usa, para cada mês fechado, a última janela de 5 dias úteis divulgada. Última atualização: {data_br}. A série está em <a href="dados-abertos" class="text-sky-400 underline">dados abertos</a> (licença CC BY 4.0).</p>
            <h2 class="text-xl font-serif text-white">Entrada e prazo</h2>
            <p>O Banco Central não publica entrada mínima nem prazo máximo por banco. Usamos a convenção geral de mercado (entrada mínima de 20% para carro novo e de 30% para usado e moto; prazos de 12 a 60 meses), que ainda não foi confirmada banco a banco. Trate esses dois campos como estimativa e confirme com a instituição.</p>
            <h2 class="text-xl font-serif text-white">Como calculamos</h2>
            <p><strong>Parcela:</strong> Tabela Price, parcela fixa pela fórmula PMT com a taxa mensal do banco. É o sistema usado no crédito de veículo; não simulamos SAC porque os bancos não o oferecem para carro e moto.</p>
            <p><strong>CET:</strong> calculado por TIR (taxa interna de retorno). Você recebe o valor financiado menos o IOF e a tarifa de registro do contrato, e paga a parcela mais o seguro prestamista. O IOF segue a lei (0,38% sobre o valor financiado mais 0,0082% ao dia, por até 365 dias, contando 30 dias por mês). Os outros dois itens são estimativas de mercado: tarifa de registro de R$ 120 e seguro prestamista de 0,035% do saldo devedor por mês. Eles variam por banco e seguradora, então o CET aqui serve para comparar; o seu depende da sua análise de crédito.</p>
            <p><strong>Renda sugerida:</strong> a parcela dividida por 30%, a regra de comprometimento de renda usada pelos bancos.</p>
            <h2 class="text-xl font-serif text-white">O que os números não são</h2>
            <p>Não são oferta, proposta nem aprovação de crédito. A taxa que o banco oferece a você pode ser maior ou menor que a média. Use os resultados para comparar e entender a ordem de grandeza; confirme as condições direto com a instituição.</p>
            <h2 class="text-xl font-serif text-white">Quem mantém</h2>
            <p>A Datalab Global é uma marca de {EMPRESA_RODAPE}, criada por Rodolfo Delfino. <a href="sobre" class="text-sky-400 underline">Saiba mais</a>. Encontrou um número errado? Escreva para <a href="mailto:contato@datalabglobal.com" class="text-sky-400 underline">contato@datalabglobal.com</a>.</p>
            <p>Divulgação: o simulador pode indicar a Financia Tudo, parceira com a qual podemos receber comissão, sem custo adicional para você. As taxas e os rankings não são influenciados por essa parceria.</p>
        </div>
    </main>
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, "metodologia.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html))
    return [url]



# ---------------------------------------------------------------------------
# Motor v3b (31/out/2026): renda necessária por valor, llms-full.txt e medição
# de cliques (Umami, só liga com o ID do site).
# ---------------------------------------------------------------------------
SLUG_INDICE_RENDA = "renda-para-financiar-veiculo"
ENTRADAS_RENDA = (0.20, 0.30, 0.50)
PERC_RENDA_COMPROMETIDA = 0.30

# Medição de cliques: vazio = não carrega nada. Preencha com o "Website ID" do
# Umami Cloud (plano gratuito, sem cookies) para ligar.
UMAMI_WEBSITE_ID = ""
UMAMI_SCRIPT = "https://cloud.umami.is/script.js"
# Link do parceiro (ftudo.com) e, por garantia, o domínio institucional dele.
SELETOR_CTA_PARCEIRO = 'a[href*="ftudo.com"], a[href*="financiatudo"]'


def slug_renda(categoria, valor):
    return f"renda-para-financiar-{CATEGORIA_SLUG[categoria]}-{int(round(valor / 1000))}-mil"


def _entradas_da_categoria(categoria):
    return [e for e in ENTRADAS_RENDA if e >= entrada_minima(categoria) - 1e-9]


def renda_minima(categoria, valor, entrada_perc, prazo):
    """Renda familiar mínima (parcela Price / 30%) na taxa mediana dos bancos da
    categoria que oferecem o prazo. None se há menos de MIN_BANCOS_COMPARACAO."""
    bancos = bancos_com_prazo(categoria, prazo)
    if len(bancos) < MIN_BANCOS_COMPARACAO:
        return None
    taxa = _mediana([d["taxa_am"] for d in bancos.values()])
    parcela = calcular_pmt_price(valor * (1 - entrada_perc), prazo, taxa)
    return {"taxa_am": taxa, "parcela": parcela, "renda": math.ceil((parcela / PERC_RENDA_COMPROMETIDA) / 50) * 50}


def gerar_paginas_renda(pasta_saida, data_atualizacao):
    """/renda-para-financiar-{carro-novo|carro-usado|moto}-{valor}-mil: quanto de
    renda os bancos costumam exigir, por prazo e entrada. Números próprios por
    categoria e valor. Retorna as URLs (sitemap)."""
    urls = []
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    prazos = list(PRAZOS_MESES)
    for categoria in CATEGORIAS:
        valores = VALORES_POR_CATEGORIA[categoria]
        entradas = _entradas_da_categoria(categoria)
        nome_cat = CATEGORIA_ARTIGO[categoria].split(" ", 1)[1]  # "carro novo", "carro usado", "moto"
        for k, valor in enumerate(valores):
            vc, vf = formatar_valor_curto(valor), formatar_reais(valor)
            tab = {(p, e): renda_minima(categoria, valor, e, p) for p in prazos for e in entradas}
            validos = [(p, e) for (p, e), v in tab.items() if v]
            if not validos:
                continue
            e_base = entradas[0]
            p_base = 48 if tab.get((48, e_base)) else max(p for p, e in validos if e == e_base)
            base = tab[(p_base, e_base)]
            e_alta = entradas[-1]
            p_longo = max(p for p, e in validos if e == e_base)
            alta = tab.get((p_base, e_alta)) or base
            longo = tab[(p_longo, e_base)]

            cab = "".join(f'<th scope="col" class="px-2 py-2 text-right font-medium">{round(e * 100)}% de entrada<br>'
                          f'<span class="normal-case text-slate-500">({formatar_reais(valor * e)})</span></th>' for e in entradas)
            linhas_tab = ""
            for p in prazos:
                cels = ""
                for e in entradas:
                    v = tab[(p, e)]
                    cels += (f'<td class="px-2 py-2 text-right whitespace-nowrap"><strong class="text-white">{formatar_reais(v["renda"])}</strong>'
                             f'<br><span class="text-slate-500">parcela {formatar_reais(v["parcela"])}</span></td>') if v \
                        else '<td class="px-2 py-2 text-right text-slate-500">–</td>'
                linhas_tab += f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">{p} meses</th>{cels}</tr>'
            tabela = (f'<div class="overflow-x-auto rounded-xl border border-white/10"><table class="w-full text-xs text-slate-300">'
                      f'<thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Prazo</th>{cab}</tr></thead>'
                      f'<tbody>{linhas_tab}</tbody></table></div>')

            resumo = (f"Para financiar {nome_cat} de {vf} com {round(e_base * 100)}% de entrada ({formatar_reais(valor * e_base)}) em {p_base} meses, "
                      f"na taxa mediana dos bancos ({_pct2(base['taxa_am'])}% ao mês), a parcela pela Tabela Price é de {formatar_reais(base['parcela'])} "
                      f"e a renda familiar mínima, considerando o limite de 30% da renda, é de {formatar_reais(base['renda'])} por mês.")
            dica = ""
            if e_alta != e_base and tab.get((p_base, e_alta)):
                dica += (f"Com {round(e_alta * 100)}% de entrada ({formatar_reais(valor * e_alta)}), a renda mínima cai para "
                         f"{formatar_reais(alta['renda'])} em {p_base} meses. ")
            if p_longo != p_base:
                dica += (f"Esticar para {p_longo} meses baixa a renda mínima ({round(e_base * 100)}% de entrada) para "
                         f"{formatar_reais(longo['renda'])}, mas aumenta o total de juros.")
            perguntas = [
                (f"Qual a renda mínima para financiar {nome_cat} de {vc}?",
                 f"Com {round(e_base * 100)}% de entrada, em {p_base} meses e na taxa mediana dos bancos ({_pct2(base['taxa_am'])}% ao mês), "
                 f"a renda familiar mínima é de cerca de {formatar_reais(base['renda'])} por mês."),
                (f"Como diminuir a renda exigida para financiar {nome_cat} de {vc}?",
                 "Aumentar a entrada e alongar o prazo reduzem a parcela e, com ela, a renda exigida."
                 + (f" Com {round(e_alta * 100)}% de entrada, a renda mínima cai para {formatar_reais(alta['renda'])} em {p_base} meses."
                    if e_alta != e_base and tab.get((p_base, e_alta)) else "")),
                ("Por que a renda mínima é calculada com 30%?",
                 "Os bancos costumam limitar a parcela a 30% da renda bruta. É uma regra de mercado, não uma lei: cada banco faz a própria análise de crédito."),
            ]
            faq_html, schema_faq = render_faq_visual(perguntas)
            slug = slug_renda(categoria, valor)
            url = f"{DOMINIO}/{slug}"
            titulo = _escolher_que_cabe(60, f"Renda para financiar {nome_cat} de {vc}: quanto precisa ganhar | Datalab Global",
                                        f"Renda para financiar {nome_cat} de {vc}: quanto precisa ganhar", f"Renda para financiar {nome_cat} de {vc}")
            desc = _escolher_que_cabe(
                160, f"Renda mínima para financiar {nome_cat} de {vc}: {formatar_reais(base['renda'])} por mês com {round(e_base * 100)}% de entrada em {p_base} meses. Veja por prazo e entrada.",
                f"Renda mínima para financiar {nome_cat} de {vc}: {formatar_reais(base['renda'])} por mês com {round(e_base * 100)}% de entrada em {p_base} meses.")
            schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
                {"@type": "ListItem", "position": 2, "name": "Renda para financiar", "item": f"{DOMINIO}/{SLUG_INDICE_RENDA}"},
                {"@type": "ListItem", "position": 3, "name": f"{CATEGORIA_LABEL[categoria]} {vc}", "item": url}]}
            viz = []
            if k > 0:
                viz.append(f'<a href="{slug_renda(categoria, valores[k - 1])}" class="underline hover:text-sky-400">← Renda para {formatar_valor_curto(valores[k - 1])}</a>')
            if k + 1 < len(valores):
                viz.append(f'<a href="{slug_renda(categoria, valores[k + 1])}" class="underline hover:text-sky-400">Renda para {formatar_valor_curto(valores[k + 1])} →</a>')
            comp = ""
            if pagina_comparacao_existe(categoria, valor, p_base):
                comp = f'<a href="{slug_comparacao(categoria, valor, p_base)}" class="text-sky-400 underline">Compare {vc} em {p_base} meses em todos os bancos</a> · '
            head = render_head(titulo, desc, url, [schema_bc, schema_faq])
            html_pag = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    <main class="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-10 w-full">
        {render_breadcrumb([("Datalab Global", "/"), ("Renda para financiar", SLUG_INDICE_RENDA), (f"{CATEGORIA_LABEL[categoria]} {vc}", None)])}
        <h1 class="font-serif text-2xl sm:text-4xl font-bold mb-4">Renda necessária para financiar {nome_cat} de {vc}</h1>
        <p class="text-slate-300 text-base font-light leading-relaxed mb-4">{resumo}</p>
        <p class="text-slate-300 text-sm font-light leading-relaxed mb-8">{dica}</p>
        <h2 class="font-serif text-xl font-bold mb-3">Renda mínima por prazo e entrada</h2>
        {tabela}
        <p class="text-slate-500 text-[11px] mt-3">Cálculo: parcela pela Tabela Price dividida por 30%, na taxa mediana dos bancos da categoria que oferecem o prazo (taxas médias contratadas, Banco Central, atualizadas em {data_br}), sem IOF, tarifas e seguro. A entrada mínima desta categoria é {round(entrada_minima(categoria) * 100)}%. A sua análise de crédito pode exigir mais ou menos. Veja a <a href="metodologia" class="underline">metodologia</a>.</p>
        <p class="text-slate-400 text-sm mt-6">{" &nbsp;·&nbsp; ".join(viz)}</p>
        {faq_html}
        <p class="text-slate-400 text-sm mt-10">{comp}<a href="{SLUG_INDICE_RENDA}" class="text-sky-400 underline">Renda por valor do veículo</a> · <a href="{slug_comparador(categoria)}" class="text-sky-400 underline">Comparador de bancos</a></p>
        {_cta_comparacao("Quer saber se a sua renda aprova?")}
    </main>
    {render_footer()}
</body>
</html>'''
            with open(os.path.join(pasta_saida, f"{slug}.html"), "w", encoding="utf-8") as f:
                f.write(corrigir_concordancia(html_pag))
            urls.append(url)

    secoes = ""
    for categoria in CATEGORIAS:
        itens = "".join(
            f'<li><a href="{slug_renda(categoria, v)}" class="text-sky-400 underline hover:text-sky-300">Renda para financiar {formatar_valor_curto(v)}</a></li>'
            for v in VALORES_POR_CATEGORIA[categoria])
        secoes += (f'<h2 class="font-serif text-xl font-bold mt-8 mb-3">{CATEGORIA_LABEL[categoria]}</h2><ul class="space-y-2 text-sm">{itens}</ul>')
    url_ind = f"{DOMINIO}/{SLUG_INDICE_RENDA}"
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Renda para financiar", "item": url_ind}]}
    head = render_head("Renda para financiar veículo: quanto precisa ganhar | Datalab Global",
                       "Renda mínima para financiar carro novo, carro usado e moto, por valor, prazo e entrada, com a taxa mediana dos bancos.",
                       url_ind, [schema_bc])
    html_ind = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    <main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-2xl sm:text-4xl font-bold mb-4">Renda para financiar um veículo</h1>
        <p class="text-slate-300 text-base font-light leading-relaxed mb-4">Escolha a categoria e o valor do veículo e veja a renda familiar mínima por prazo e entrada, calculada com o limite de 30% da renda e a taxa mediana do mercado.</p>
        {secoes}
        <p class="text-slate-400 text-sm mt-10"><a href="financiamento-veiculos" class="text-sky-400 underline">Parcela por valor e prazo</a> · <a href="metodologia" class="text-sky-400 underline">Metodologia</a></p>
    </main>
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, f"{SLUG_INDICE_RENDA}.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html_ind))
    urls.append(url_ind)
    return urls


def gerar_llms_full_txt(pasta_saida, data_atualizacao, historico):
    """llms-full.txt: versão longa do llms.txt, com as taxas de hoje em frases
    curtas e datadas, fáceis de citar por buscadores de IA."""
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    linhas = []
    for banco, d in sorted(BANCOS_VEICULOS.items(), key=lambda kv: kv[1]["taxa_am"]):
        cats = ", ".join(CATEGORIA_LABEL[c].lower() for c in CATEGORIAS if c in d["aplica_a"])
        linhas.append(f"- {d['nome_exibicao']}: taxa de {_pct2(d['taxa_am'])}% ao mês ({_pct2(d['taxa_aa'])}% ao ano), prazo de até {d['prazo_max']} meses ({cats}).")
    serie = ""
    meses = sorted({r["mes_referencia"] for r in historico})
    if meses:
        ult = meses[-1]
        atual = {r["banco"]: r["taxa_am"] for r in historico if r["mes_referencia"] == ult}
        if atual:
            menor, maior = min(atual, key=atual.get), max(atual, key=atual.get)
            serie = (f"\n## Taxa média contratada em {nome_mes(ult)} (Banco Central)\n"
                     f"- Menor: {BANCOS_VEICULOS[menor]['nome_exibicao']}, {_pct2(atual[menor])}% ao mês.\n"
                     f"- Maior: {BANCOS_VEICULOS[maior]['nome_exibicao']}, {_pct2(atual[maior])}% ao mês.\n"
                     f"- Média simples de {len(atual)} bancos: {_pct2(sum(atual.values()) / len(atual))}% ao mês.\n"
                     f"- Série mensal desde {nome_mes(meses[0])}: {DOMINIO}/{SLUG_INDICE_MENSAL}\n")
    entradas = "; ".join(f"{CATEGORIA_LABEL[c].lower()}: {round(entrada_minima(c) * 100)}%" for c in CATEGORIAS)
    conteudo = f"""# Datalab Global: simulador de financiamento de veículos (versão completa)

> Simulador e dados abertos de financiamento de carro novo, carro usado e moto no Brasil. Última atualização das taxas: {data_br}. Os números abaixo podem ser citados com link para {DOMINIO}/ (dados sob licença CC BY 4.0).

## O que é e o que não é
Calcula parcela (Tabela Price), CET estimado e economia de juros com amortização extra. Não é oferta de crédito: as taxas são médias efetivamente contratadas, divulgadas pelo Banco Central (modalidade 401101), e a proposta de cada pessoa depende da análise do banco.

## Taxas usadas nas simulações hoje ({data_br})
{chr(10).join(linhas)}
{serie}
## Como os números são calculados
- Fonte das taxas: API pública do Banco Central, modalidade 401101 (aquisição de veículos, pessoa física, pré-fixada), taxa média do mês por banco. O Banco Central publica uma única modalidade para veículos, sem divisão por categoria.
- Parcela fixa pela Tabela Price. A renda mínima usa 30% de comprometimento da renda bruta.
- Entrada mínima usada por categoria (convenção de mercado, ainda não confirmada banco a banco): {entradas}.
- CET: TIR do fluxo com IOF, tarifa de registro e seguro prestamista estimados. Detalhes: {DOMINIO}/metodologia

## Páginas principais
- Comparador carro novo: {DOMINIO}/{slug_comparador('novo')}
- Comparador carro usado: {DOMINIO}/{slug_comparador('usado')}
- Comparador moto: {DOMINIO}/{slug_comparador('moto')}
- Parcela por valor e prazo: {DOMINIO}/financiamento-veiculos
- Renda necessária por valor do veículo: {DOMINIO}/{SLUG_INDICE_RENDA}
- Taxas mês a mês: {DOMINIO}/{SLUG_INDICE_MENSAL}
- Dados abertos (CSV, JSON): {DOMINIO}/dados-abertos
- Metodologia: {DOMINIO}/metodologia
- Guias: {DOMINIO}/aprenda

## Como citar
Datalab Global ({DOMINIO}/), taxas do Banco Central compiladas em {data_br}.

## Responsável
Marca de {EMPRESA_RODAPE}. Contato: contato@datalabglobal.com
"""
    with open(os.path.join(pasta_saida, "llms-full.txt"), "w", encoding="utf-8") as f:
        f.write(conteudo)


def gerar_medicao_js(pasta_saida):
    """medicao.js: cliques no CTA do parceiro e primeira interação com o
    simulador. Só é gerado/carregado com UMAMI_WEBSITE_ID."""
    caminho = os.path.join(pasta_saida, "medicao.js")
    if not UMAMI_WEBSITE_ID:
        if os.path.exists(caminho):
            os.remove(caminho)
        return
    js = """(function () {
  function bloco(a) {
    if (a.closest('nav')) return 'topo';
    if (a.closest('footer')) return 'rodape';
    var s = a.closest('[id]');
    return s ? s.id : 'corpo';
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('__SELETOR__');
    if (a && window.umami) umami.track('cta-financiatudo', { pagina: location.pathname, bloco: bloco(a) });
  }, true);
  var usou = false;
  document.addEventListener('input', function (e) {
    if (usou || !window.umami || !e.target.matches('input')) return;
    usou = true;
    umami.track('usou-simulador', { pagina: location.pathname });
  }, true);
})();
""".replace("__SELETOR__", SELETOR_CTA_PARCEIRO)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(js)


def tags_medicao():
    """<script> do Umami + medicao.js para o <head> (lista vazia sem UMAMI_WEBSITE_ID)."""
    if not UMAMI_WEBSITE_ID:
        return []
    host = DOMINIO.replace("https://", "")
    return [f'<script defer src="{UMAMI_SCRIPT}" data-website-id="{UMAMI_WEBSITE_ID}" data-domains="{host}" data-do-not-track="true"></script>',
            '<script defer src="/medicao.js"></script>']


def gerar_dados_abertos(pasta_saida, data_atualizacao):
    """Publica a série como dados abertos em /dados/ (CSV, JSON,
    datapackage.json, README.md) e a página /dados-abertos. Retorna as URLs
    de página (pro sitemap)."""
    historico = carregar_historico()
    if not historico:
        return []
    pasta_dados = os.path.join(pasta_saida, "dados")
    os.makedirs(pasta_dados, exist_ok=True)
    meses = sorted({r["mes_referencia"] for r in historico})
    campos = ["mes_referencia", "periodo_inicio", "periodo_fim", "instituicao", "taxa_juros_am_pct", "taxa_juros_aa_pct"]
    linhas = [{"mes_referencia": r["mes_referencia"], "periodo_inicio": r["inicio_periodo"], "periodo_fim": r["fim_periodo"],
               "instituicao": BANCOS_VEICULOS[r["banco"]]["nome_exibicao"],
               "taxa_juros_am_pct": round(r["taxa_am"], 2), "taxa_juros_aa_pct": round(r["taxa_aa"], 2)} for r in historico]
    import csv as _csv
    with open(os.path.join(pasta_dados, "taxas-financiamento-veiculos.csv"), "w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)
    with open(os.path.join(pasta_dados, "taxas-financiamento-veiculos.json"), "w", encoding="utf-8") as f:
        json.dump({"titulo": "Taxas médias de juros do financiamento de veículos por banco (BACEN)", "fonte": FONTE_BACEN_URL,
                   "licenca": LICENCA_DADOS, "atualizado_em": data_atualizacao, "organizacao": "Datalab Global", "dados": linhas},
                  f, ensure_ascii=False, indent=1)

    url_pagina = f"{DOMINIO}/dados-abertos"
    n_bancos = len({r["banco"] for r in historico})
    descricao = ("Taxa média de juros efetivamente contratada no financiamento de veículos (aquisição de veículos, pessoa física, "
                 "pré-fixada), por banco, ao mês e ao ano, segundo o Banco Central do Brasil. Para cada mês fechado, a última janela de "
                 f"5 dias úteis divulgada. Cobre {len(meses)} meses ({_rotulo_mes(meses[0])} a {_rotulo_mes(meses[-1])}) e {n_bancos} instituições. {NOTA_MODALIDADE}")
    citacao = f"Datalab Global. Taxas médias de juros do financiamento de veículos por banco (dados do BACEN). {url_pagina}, acesso em {{data}}."
    ini, fim = min(r["inicio_periodo"] for r in historico), max(r["fim_periodo"] for r in historico)
    with open(os.path.join(pasta_dados, "datapackage.json"), "w", encoding="utf-8") as f:
        json.dump({
            "name": "taxas-financiamento-veiculos", "title": "Taxas médias de juros do financiamento de veículos por banco (BACEN)",
            "description": descricao, "licenses": [{"name": "CC-BY-4.0", "path": LICENCA_DADOS_URL, "title": LICENCA_DADOS}],
            "sources": [{"title": "Banco Central do Brasil — Taxas de juros por instituição financeira", "path": FONTE_BACEN_URL}],
            "contributors": [{"title": "Datalab Global", "role": "publisher", "path": f"{DOMINIO}/"}],
            "resources": [{"name": "taxas", "path": "taxas-financiamento-veiculos.csv", "format": "csv", "mediatype": "text/csv", "encoding": "utf-8",
                           "schema": {"fields": [
                               {"name": "mes_referencia", "type": "string", "description": "Mês de referência (AAAA-MM)"},
                               {"name": "periodo_inicio", "type": "date", "description": "Início da janela de 5 dias úteis usada"},
                               {"name": "periodo_fim", "type": "date", "description": "Fim da janela de 5 dias úteis usada"},
                               {"name": "instituicao", "type": "string", "description": "Banco (nome comercial)"},
                               {"name": "taxa_juros_am_pct", "type": "number", "description": "Taxa média contratada, % ao mês"},
                               {"name": "taxa_juros_aa_pct", "type": "number", "description": "Taxa média contratada, % ao ano"}]}}],
        }, f, ensure_ascii=False, indent=1)
    with open(os.path.join(pasta_dados, "README.md"), "w", encoding="utf-8") as f:
        f.write(f"""# Taxas médias de juros do financiamento de veículos por banco

{descricao}

- **Fonte original:** [Banco Central do Brasil]({FONTE_BACEN_URL}), modalidade 401101.
- **Licença:** {LICENCA_DADOS} ({LICENCA_DADOS_URL}). Pode usar, copiar e adaptar, citando a fonte.
- **Atualização:** a cada mês fechado. Última atualização: {data_atualizacao}.
- **Arquivos:** `taxas-financiamento-veiculos.csv`, `taxas-financiamento-veiculos.json`, `datapackage.json`.
- **Colunas:** `mes_referencia`, `periodo_inicio`, `periodo_fim`, `instituicao`, `taxa_juros_am_pct`, `taxa_juros_aa_pct`.
- **Limites:** são médias do que foi efetivamente contratado, não ofertas; a modalidade não separa carro novo, usado e moto.

## Como citar

{citacao.format(data="AAAA-MM-DD")}

Publicado por Datalab Global ({DOMINIO}/), marca de {EMPRESA_RODAPE}.
""")

    schema_dataset = {
        "@context": "https://schema.org", "@type": "Dataset",
        "name": "Taxas médias de juros do financiamento de veículos por banco (BACEN)",
        "description": descricao, "url": url_pagina, "inLanguage": "pt-BR",
        "license": LICENCA_DADOS_URL, "isAccessibleForFree": True,
        "creator": {"@type": "Organization", "name": "Datalab Global", "url": f"{DOMINIO}/"},
        "isBasedOn": FONTE_BACEN_URL, "dateModified": data_atualizacao,
        "temporalCoverage": f"{ini}/{fim}", "spatialCoverage": {"@type": "Country", "name": "Brasil"},
        "variableMeasured": ["Taxa média de juros contratada (% ao mês)", "Taxa média de juros contratada (% ao ano)"],
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{DOMINIO}/dados/taxas-financiamento-veiculos.csv"},
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{DOMINIO}/dados/taxas-financiamento-veiculos.json"},
        ],
    }
    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": "Dados abertos", "item": url_pagina},
        ],
    }
    titulo = "Dados abertos: taxas de financiamento de veículos por banco | Datalab"
    meta = f"Baixe grátis a série de {len(meses)} meses de taxas de juros do financiamento de veículos por banco, do Banco Central, em CSV e JSON ({LICENCA_DADOS})."
    head = render_head(titulo, meta, url_pagina, [schema_breadcrumb, schema_dataset])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Dados abertos", None)])
    resumo = resumo_historico(historico)
    corpo = f'''<main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Dados abertos: taxas de financiamento de veículos</h1>
        <p class="text-slate-400 text-sm mb-8">Série mensal de {len(meses)} meses, por banco, com dados do Banco Central. Livre para usar, com citação da fonte ({LICENCA_DADOS}).</p>

        <section>
            <h2 class="font-serif text-xl font-bold mb-3">Baixar</h2>
            <ul class="space-y-2 text-sm">
                <li><a href="dados/taxas-financiamento-veiculos.csv" download class="text-sky-400 underline">taxas-financiamento-veiculos.csv</a> <span class="text-slate-400">· planilha (UTF-8, vírgula)</span></li>
                <li><a href="dados/taxas-financiamento-veiculos.json" download class="text-sky-400 underline">taxas-financiamento-veiculos.json</a> <span class="text-slate-400">· para programação</span></li>
                <li><a href="dados/datapackage.json" download class="text-sky-400 underline">datapackage.json</a> <span class="text-slate-400">· metadados (Frictionless Data)</span></li>
                <li><a href="dados/README.md" class="text-sky-400 underline">README.md</a> <span class="text-slate-400">· descrição e como citar</span></li>
            </ul>
        </section>

        <section class="mt-10">
            <h2 class="font-serif text-xl font-bold mb-3">O que há nos dados</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed">{descricao}</p>
            <table class="w-full text-xs text-slate-300 mt-4 rounded-xl border border-white/10">
                <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-3 py-2 text-left font-medium">Coluna</th><th scope="col" class="px-3 py-2 text-left font-medium">Descrição</th></tr></thead>
                <tbody>
                    <tr class="border-t border-white/5"><th scope="row" class="px-3 py-2 text-left font-mono font-normal">mes_referencia</th><td class="px-3 py-2">Mês de referência (AAAA-MM)</td></tr>
                    <tr class="border-t border-white/5"><th scope="row" class="px-3 py-2 text-left font-mono font-normal">periodo_inicio / periodo_fim</th><td class="px-3 py-2">Janela de 5 dias úteis usada para o mês</td></tr>
                    <tr class="border-t border-white/5"><th scope="row" class="px-3 py-2 text-left font-mono font-normal">instituicao</th><td class="px-3 py-2">Banco (nome comercial)</td></tr>
                    <tr class="border-t border-white/5"><th scope="row" class="px-3 py-2 text-left font-mono font-normal">taxa_juros_am_pct</th><td class="px-3 py-2">Taxa média contratada, em % ao mês</td></tr>
                    <tr class="border-t border-white/5"><th scope="row" class="px-3 py-2 text-left font-mono font-normal">taxa_juros_aa_pct</th><td class="px-3 py-2">Taxa média contratada, em % ao ano</td></tr>
                </tbody>
            </table>
            <p class="text-slate-400 text-xs font-light leading-relaxed mt-3">São médias do que foi efetivamente contratado, não ofertas: a sua proposta pode ser diferente.</p>
        </section>

        <section class="mt-10">
            <h2 class="font-serif text-xl font-bold mb-3">Como citar</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed bg-white/5 border border-white/10 rounded-xl p-4">{citacao.format(data="AAAA-MM-DD")}</p>
            <p class="text-slate-400 text-xs font-light mt-3">Licença <a href="{LICENCA_DADOS_URL}" rel="noopener" class="underline">{LICENCA_DADOS}</a>. Fonte original: <a href="{FONTE_BACEN_URL}" rel="noopener" class="underline">Banco Central do Brasil</a>. Atualizado em {date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')}.</p>
        </section>

        <section class="mt-10">
            <h2 class="font-serif text-xl font-bold mb-3">Exemplo em Python</h2>
            <pre class="bg-slate-900/60 border border-white/10 rounded-xl p-4 text-xs text-slate-300 overflow-x-auto"><code>import pandas as pd
df = pd.read_csv("{DOMINIO}/dados/taxas-financiamento-veiculos.csv")
df.pivot(index="mes_referencia", columns="instituicao", values="taxa_juros_am_pct").tail(6)</code></pre>
        </section>

        {html_evolucao_taxas(resumo)}

        <p class="mt-10 text-center text-xs text-slate-400"><a href="/" class="text-sky-400 underline">Voltar ao simulador de financiamento de veículos →</a></p>
    </main>'''
    html_pagina = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, "dados-abertos.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html_pagina))
    return [url_pagina]



def gerar_comparador(categoria, lookup, data_atualizacao):
    label_categoria = CATEGORIA_LABEL[categoria]
    nome_cat = label_categoria.lower()
    d_atual = date.fromisoformat(data_atualizacao)
    mes_ano = f"{MESES_PT[d_atual.month - 1]} de {d_atual.year}"
    mes_curto = f"{MESES_PT_ABREV[d_atual.month - 1]}/{d_atual.year}"
    resumo_hist = resumo_historico(carregar_historico(), categoria)
    slug_pagina = slug_comparador(categoria)
    url_canonica = f"{DOMINIO}/{slug_pagina}"
    valor_referencia = VALORES_POR_CATEGORIA[categoria][len(VALORES_POR_CATEGORIA[categoria]) // 2]
    prazo_referencia = 48

    # Mês no título e no H1: a busca real é "taxa de financiamento de carro
    # {mês} {ano}". Abreviado no <title> pra caber em 60 caracteres.
    titulo_pagina = f"Taxas de financiamento de {nome_cat} por banco: {mes_curto} | Datalab"
    meta_description = _escolher_que_cabe(
        160,
        f"Compare a taxa real de todos os bancos para financiar {nome_cat} em {mes_ano}: cenário de "
        f"{formatar_valor_curto(valor_referencia)} em {prazo_referencia} meses e evolução das taxas. Dados do Banco Central.",
        f"Taxa real de todos os bancos para financiar {nome_cat} em {mes_ano}: cenário de "
        f"{formatar_valor_curto(valor_referencia)} em {prazo_referencia} meses e evolução. Dados do Banco Central.",
    )

    ranking = comparar_bancos_categoria(categoria, valor_referencia, prazo_referencia, lookup)
    cet_min, cet_max = ranking[0]["cet"], ranking[-1]["cet"]

    # Barra neutra ÚNICA com um marcador por banco (não mais uma lista
    # ranqueada #1º/#2º com link pra página de cada banco) — mesma regra
    # de negócio da barra individual: aqui é a página cuja função É
    # comparar todos de uma vez, então em vez de "esconder" o comparativo
    # (isso tiraria a utilidade da página), tiramos a hierarquia visual
    # de "melhor/pior" (sem medalha, sem #1º/#2º) e mantemos só a
    # posição relativa de cada um.
    #
    # Achado real (07/set/2026, revisão pedida pelo usuário depois de
    # testar o site): os marcadores eram bolinhas brancas idênticas —
    # dava pra ver QUE havia dispersão, mas não QUEM era quem sem passar
    # o mouse em cada uma. Trocado pelo favicon de cada banco (mesmo
    # padrão visual do projeto irmão), pra reconhecer os bancos de
    # relance.
    #
    # Posição do marcador é interpolação linear de VALOR (CET real
    # contra o mínimo/máximo real), não fração de ranking — testei
    # fração de ranking antes (índice/(n-1)) e revertido a pedido do
    # usuário no mesmo dia: com todo marcador igualmente espaçado, a
    # barra "parece uma fila indiana" e perde a informação de o quanto
    # os bancos realmente se aproximam ou distanciam uns dos outros em
    # taxa — ver docstring de renderizar_faixa_mercado pro raciocínio
    # completo (mesma correção nas duas funções).
    spread_mercado = cet_max - cet_min
    marcadores = []
    for r in ranking:
        pct = round(((r["cet"] - cet_min) / spread_mercado) * 100) if spread_mercado > 0 else 50
        pct = max(2, min(98, pct))
        url_logo = f"https://www.google.com/s2/favicons?domain={r['dominio_favicon']}&sz=64"
        r_cet_fmt = f"{r['cet']:.2f}".replace('.', ',')  # padrão brasileiro — ver nota em gerar_pagina_individual
        marcadores.append(
            f'<div class="absolute top-1/2 z-10 rounded-full bg-slate-950 border-2 border-white shadow-[0_1px_4px_rgba(0,0,0,0.4)] p-0.5" '
            f'style="left:{pct}%; transform:translate(-50%,-50%)" title="{r["nome_exibicao"]}: {r_cet_fmt}% CET">'
            f'{favicon_com_fallback(url_logo, r["nome_exibicao"], "w-5 h-5", lazy=False)}'
            f'</div>'
        )
    marcadores_html = "\n".join(marcadores)

    # Linha da lista agora é um LINK pra página-hub do banco (achado real,
    # 07/set/2026: antes disso não existia NENHUM caminho de navegação
    # normal — clicando pela home/comparador — até uma página de
    # simulação individual; as 876 páginas geradas só eram alcançáveis
    # pelo sitemap.xml, órfãs de verdade pro visitante humano e com sinal
    # de importância interna praticamente zero pro Google). Isso NÃO
    # contradiz a decisão de não ter ranking numerado/medalha acima: um
    # link pra NOSSA PRÓPRIA página-hub (que tem o CTA da Financia Tudo)
    # mantém o visitante dentro do funil — é bem diferente de um link
    # pra fora, que era o motivo original de remover o ranking nomeado.
    # Grid com colunas de largura FIXA (não mais flex+justify-between):
    # achado real (07/set/2026, print do usuário — "parece uma cobra
    # entortada"): com justify-between e só 3 filhos, a posição da coluna
    # do meio (taxa a.m.) depende da largura do NOME do banco (filho 1),
    # que varia de "Caixa" a "Banco do Brasil" — cada linha desalinhava
    # em um X diferente. Grid de colunas fixas garante que toda coluna
    # cai exatamente na mesma posição horizontal em toda linha,
    # independente do tamanho do nome — mesmo princípio que a página do
    # projeto irmão já usa na tabela de comparação de bancos.
    #
    # Achado real (08/set/2026, auditoria mobile pedida pelo usuário):
    # 110px + 150px fixos era mais largura do que sobrava numa tela de
    # 375px depois do padding/gap do card — a coluna de nome (1fr) ficava
    # com ~5px reais, truncando "Bradesco"/"Santander" pra 1 letra só
    # (confirmado via scrollWidth > offsetWidth no DOM). Trocado pra
    # colunas 'auto' (largura = conteúdo real, não um pixel fixo
    # arbitrário) — como cada linha é seu PRÓPRIO grid independente (não
    # uma grid-table compartilhada entre as linhas), 'auto' não herda o
    # bug antigo do flex: taxa_am e CET são sempre formatados com o MESMO
    # número de dígitos ("X.XX% a.m.", "CET XX.XX% a.a."), então a
    # largura de cada coluna já não varia de forma perceptível de uma
    # linha pra outra — o alinhamento reto do fix original é preservado
    # sem precisar reservar espaço fixo maior que o conteúdo, que é
    # exatamente o que quebrava no mobile. Mesma técnica que o projeto
    # irmão já usa (colunas 'auto' pra conteúdo numérico de largura
    # quase-constante, só o nome variável vira '1fr').
    # Achado real (12/set/2026, workflow do GitHub Actions falhando com
    # exit code 1 — CI usa Python 3.10, aqui em dev usávamos 3.14): esta
    # função tinha uma f-string ANINHADA dentro da f-string grande de
    # cada linha (delimitada por '''): ex. {f"{r['taxa_am']:.2f}".
    # replace('.', ',')}. Confirmado contra o texto oficial do PEP 701
    # (peps.python.org/pep-0701): antes do Python 3.12, reusar o MESMO
    # CARACTERE de aspas usado pela f-string externa dentro da expressão
    # — mesmo se a externa usa aspas triplas e a interna usa aspas
    # simples — é SyntaxError; aspas triplas não são exceção a essa
    # regra. Corrigido calculando os valores formatados ANTES da
    # f-string grande, num loop explícito (não dá pra usar variável
    # intermediária dentro de uma expressão geradora) — mesmo padrão já
    # usado em r_cet_fmt (comparar_bancos_categoria) acima.
    linhas_lista_partes = []
    for r in ranking:
        taxa_am_fmt = f"{r['taxa_am']:.2f}".replace('.', ',')
        cet_fmt = f"{r['cet']:.2f}".replace('.', ',')
        linhas_lista_partes.append(f'''<a href="{slug_hub(categoria, r["banco"])}" class="grid grid-cols-[1fr_auto_auto] items-center gap-3 p-3 rounded-lg border border-white/10 hover:border-sky-500/50 hover:bg-white/5 transition-all">
            <span class="flex items-center gap-2 min-w-0">
                {favicon_com_fallback(f"https://www.google.com/s2/favicons?domain={r['dominio_favicon']}&sz=64", r["nome_exibicao"], "w-5 h-5")}
                <span class="text-sm font-medium truncate">{r["nome_exibicao"]}</span>
            </span>
            <span class="text-xs text-slate-400 text-right whitespace-nowrap">{taxa_am_fmt}% a.m.</span>
            <span class="text-sm text-slate-300 text-right whitespace-nowrap">CET {cet_fmt}% a.a.</span>
        </a>''')
    linhas_lista = "\n".join(linhas_lista_partes)

    cet_min_fmt = f"{cet_min:.2f}".replace('.', ',')
    cet_max_fmt = f"{cet_max:.2f}".replace('.', ',')

    texto_var = texto_variacao(resumo_hist)
    perguntas_faq = [
        (
            f"Qual banco tem a menor taxa pra financiar {label_categoria.lower()}?",
            f"No cenário de referência de {formatar_valor_curto(valor_referencia)} em {prazo_referencia} meses, o "
            f"CET varia entre {cet_min_fmt}% e {cet_max_fmt}% ao ano entre os bancos que acompanhamos — veja a "
            f"posição de cada um na barra acima. A Datalab não indica um banco \"vencedor\": a taxa final de cada "
            f"cliente depende de relacionamento bancário, histórico de crédito e entrada, então vale simular mais "
            f"de uma opção antes de decidir.",
        ),
        (
            "O que é CET e por que ele é melhor que só olhar a taxa de juros?",
            "CET (Custo Efetivo Total) é o custo real do financiamento por ano — inclui a taxa de juros, o IOF, a "
            "tarifa de registro de contrato e o seguro prestamista típico de mercado, sempre maior que a taxa "
            "anunciada isoladamente. É o número certo pra comparar propostas de bancos diferentes de forma justa.",
        ),
        (
            f"Como simulo o financiamento {label_categoria.lower()} num banco específico?",
            "Clique no banco desejado na lista abaixo pra ver todas as simulações de valor e prazo disponíveis "
            "dele, com parcela e CET calculados a partir da taxa média real apurada pelo Banco Central.",
        ),
    ]
    if texto_var:
        perguntas_faq.append(("Como as taxas de financiamento de veículos variaram nos últimos meses?", texto_var))
    faq_html, schema_faq = render_faq_visual(perguntas_faq)

    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": label_categoria, "item": url_canonica},
        ],
    }
    # ItemList sem "url": ainda é útil pra engines de IA/busca entenderem
    # que a página cobre N instituições nomeadas, mas sem oferecer aos
    # crawlers um atalho pra "página de outro banco" que também não
    # queremos oferecer aos visitantes humanos.
    schema_item_list = {
        "@context": "https://schema.org", "@type": "ItemList",
        "itemListElement": [
            {"@type": "ListItem", "position": i, "name": r["nome_exibicao"]}
            for i, r in enumerate(sorted(ranking, key=lambda r: r["cet"]), start=1)
        ],
    }

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_breadcrumb, schema_item_list, schema_faq])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), (label_categoria, None)])

    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <div class="flex items-center gap-4 mb-2">
            <div class="w-14 h-14 sm:w-16 sm:h-16 shrink-0">{ilustracao_categoria(categoria, f'il-grad-cmp-{categoria}')}</div>
            <h1 class="font-serif text-2xl sm:text-3xl font-bold">Taxas de financiamento de {nome_cat} por banco em {mes_ano}</h1>
        </div>
        <p class="text-slate-400 text-sm mb-8">Posição de cada banco pelo CET, cenário de referência de {formatar_valor_curto(valor_referencia)} em {prazo_referencia} meses.</p>

        <section class="bg-sky-500/10 border border-sky-500/30 rounded-2xl p-6 mb-6">
            <div class="flex items-center gap-2 mb-4">
                <span class="text-amber-400">{icone('lightbulb')}</span>
                <span class="text-slate-300 text-[11px] font-bold uppercase tracking-widest">CET de mercado — {label_categoria}</span>
                {tooltip('Cada ícone é um banco, posicionado pelo CET real dele entre o menor e o maior que acompanhamos nessa categoria. Não é uma lista "do melhor pro pior" — clique num banco pra ver todas as simulações dele.')}
            </div>
            <div class="relative h-2 rounded-full bg-gradient-to-r from-sky-500 via-amber-400 to-rose-500 mb-2">
                {marcadores_html}
            </div>
            <div class="flex justify-between text-[10px] text-slate-400 uppercase tracking-wide mb-6">
                <span>{f"{cet_min:.2f}".replace('.', ',')}% menor CET</span>
                <span>{f"{cet_max:.2f}".replace('.', ',')}% maior CET</span>
            </div>
            <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="inline-flex items-center justify-center bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold px-8 py-3.5 rounded-2xl transition-all text-sm w-full shadow-[0_0_15px_rgba(14,165,233,0.3)]">
                Peça uma análise gratuita com essas condições {icone('arrow-right', 'ml-2')}
            </a>
        </section>

        <div class="grid gap-2">{linhas_lista}</div>
        <p class="mt-6 text-sm text-slate-300">Quer ver outro valor ou prazo? Consulte a <a href="financiamento-veiculos" class="text-sky-400 underline">tabela de financiamento de veículo por valor e prazo</a>.</p>

        {html_evolucao_taxas(resumo_hist)}

        <section class="mt-10">
            <h2 class="font-serif text-xl font-bold mb-2">Como calculamos e de onde vêm os dados</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed">As taxas vêm do relatório de taxas de juros por instituição financeira do Banco Central (modalidade "aquisição de veículos, pessoa física, pré-fixada"): são médias do que cada banco efetivamente contratou, não ofertas. O CET é calculado por nós a partir dessa taxa, com IOF, tarifa de registro e seguro prestamista estimados, para o mesmo valor, prazo e entrada mínima de cada banco. {NOTA_MODALIDADE} A série histórica está em <a href="dados-abertos" class="text-sky-400 underline">dados abertos</a> (CSV e JSON).</p>
        </section>
        {faq_html}
    </main>'''

    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
    {SCRIPT_AJUSTA_TOOLTIPS}
</body>
</html>'''
    return slug_pagina, html


# ---------------------------------------------------------------------------
# index.html
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Páginas de comparação SEM marca de banco: "financiamento carro novo de 60
# mil em 48 meses" — todos os bancos da categoria lado a lado, mesma condição.
#
# Por que existem (auditoria de SEO, 29/out/2026): no imobiliário, 76% das
# buscas que o Google mostrou citavam nome de banco e o CTR era zero. A busca
# sem marca ("financiar carro de 60 mil em 48 meses") é onde um site neutro
# tem o que oferecer. Cada página traz números próprios (parcela, total pago e
# CET por banco para aquele cenário), não troca de variável em texto.
# Mantém a regra de neutralidade do site: ordena por CET mas não numera nem
# coroa "melhor banco" (ver gerar_comparador).
# ---------------------------------------------------------------------------

MIN_BANCOS_COMPARACAO = 3  # não gera a página se menos bancos oferecem aquele prazo
_CACHE_LINHAS_COMPARACAO = {}


def slug_comparacao(categoria, valor, prazo):
    return f"financiamento-{CATEGORIA_SLUG[categoria]}-{int(round(valor / 1000))}-mil-{prazo}-meses"


def bancos_com_prazo(categoria, prazo):
    return {b: d for b, d in bancos_para_categoria(categoria).items() if d["prazo_max"] >= prazo}


def pagina_comparacao_existe(categoria, valor, prazo):
    return (
        valor in VALORES_POR_CATEGORIA[categoria]
        and prazo in PRAZOS_MESES
        and len(bancos_com_prazo(categoria, prazo)) >= MIN_BANCOS_COMPARACAO
    )


def _reais_inteiros(valor):
    return f"R$ {valor:,.0f}".replace(",", ".")


def _pct(valor):
    return f"{valor:.2f}".replace(".", ",")


def linhas_comparacao(categoria, valor, prazo):
    """Uma linha por banco que oferece o prazo, ordenada por CET. Entrada
    mínima da categoria, taxa média real do BACEN de cada banco."""
    chave = (categoria, valor, prazo)
    if chave in _CACHE_LINHAS_COMPARACAO:
        return _CACHE_LINHAS_COMPARACAO[chave]
    entrada = valor * entrada_minima(categoria)
    financiado = valor - entrada
    linhas = []
    for banco, dados in bancos_com_prazo(categoria, prazo).items():
        pmt = calcular_pmt_price(financiado, prazo, dados["taxa_am"])
        linhas.append({
            "banco": banco, "nome_exibicao": dados["nome_exibicao"], "taxa_am": dados["taxa_am"],
            "taxa_aa": dados["taxa_aa"], "parcela": pmt, "total": pmt * prazo, "financiado": financiado,
            "entrada": entrada, "cet": calcular_cet_veiculo(financiado, prazo, dados["taxa_am"]),
            "dominio_favicon": dados["dominio_favicon"],
        })
    linhas.sort(key=lambda x: x["cet"])
    _CACHE_LINHAS_COMPARACAO[chave] = linhas
    return linhas


GUIAS_RELACIONADOS = ("aprenda-o-que-e-cet", "aprenda-tabela-price", "aprenda-o-que-e-cdc",
                      "aprenda-iof-financiamento-veiculo", "aprenda-amortizacao-extra-veiculo",
                      "aprenda-financiamento-x-consorcio-veiculo", "aprenda-quitacao-antecipada-financiamento-veiculo",
                      "aprenda-portabilidade-financiamento-veiculo", "aprenda-score-e-taxa-financiamento-veiculo",
                      "aprenda-entrada-ideal-financiamento-veiculo")


def _guias_html():
    """Bloco "Entenda melhor" com links contextuais para os guias de /aprenda.
    Achado da auditoria de links internos (29/out/2026): cada guia recebia só 1
    link (do índice /aprenda), o que o deixa fraco para o Google."""
    por_slug = {a["slug"]: a for a in ARTIGOS_APRENDA}
    itens = "".join(
        f'<li><a href="{sl}" class="text-sky-400 underline hover:text-sky-300">{por_slug[sl]["titulo_h1"]}</a></li>'
        for sl in GUIAS_RELACIONADOS if sl in por_slug)
    return f'''<section class="mt-10"><h2 class="font-serif text-xl font-bold mb-2">Entenda melhor</h2>
            <ul class="text-sm space-y-2 list-disc list-inside text-slate-300">{itens}</ul></section>'''


def _escolher_que_cabe(limite, *opcoes):
    for o in opcoes:
        if len(o) <= limite:
            return o
    return opcoes[-1][:limite].rsplit(" ", 1)[0]


def _cta_comparacao(titulo):
    return f'''<section class="bg-sky-500/10 border border-sky-500/30 rounded-2xl p-6 mt-10">
            <h2 class="font-serif text-xl font-bold mb-2">{titulo}</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed mb-4">A Datalab não indica um banco: a taxa final de cada cliente depende de relacionamento, histórico de crédito e entrada. Se quiser ajuda para comparar propostas, nosso parceiro faz a análise sem custo. Podemos receber uma comissão do parceiro, sem custo extra pra você.</p>
            <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="inline-flex items-center justify-center bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold px-8 py-3.5 rounded-2xl transition-all">
                Peça uma análise gratuita {icone('arrow-right', 'ml-2')}
            </a>
        </section>'''


def gerar_paginas_comparacao(pasta_saida, data_atualizacao, lookup):
    """Gera as páginas categoria x valor x prazo sem marca + o índice
    (financiamento-veiculos.html). Retorna as URLs (pro sitemap)."""
    urls = []
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    url_indice = f"{DOMINIO}/financiamento-veiculos"

    for categoria in CATEGORIAS:
        label = CATEGORIA_LABEL[categoria]
        nome_cat = label.lower()
        valores = VALORES_POR_CATEGORIA[categoria]
        for valor in valores:
            for prazo in PRAZOS_MESES:
                if not pagina_comparacao_existe(categoria, valor, prazo):
                    continue
                linhas = linhas_comparacao(categoria, valor, prazo)
                n = len(linhas)
                vc = formatar_valor_curto(valor)
                vf = formatar_reais(valor)
                slug = slug_comparacao(categoria, valor, prazo)
                url_canonica = f"{DOMINIO}/{slug}"
                menor_cet, maior_cet = linhas[0], linhas[-1]
                por_parcela = sorted(linhas, key=lambda x: x["parcela"])
                menor_p, maior_p = por_parcela[0], por_parcela[-1]
                entrada_pct = round(entrada_minima(categoria) * 100)

                titulo = f"Financiar {nome_cat} de {vc} em {prazo}x: parcela nos bancos | Datalab"
                meta = _escolher_que_cabe(
                    160,
                    f"Financiamento de {nome_cat} de {vc} em {prazo}x: parcela de {_reais_inteiros(menor_p['parcela'])} a {_reais_inteiros(maior_p['parcela'])} e CET de {_pct(menor_cet['cet'])}% a {_pct(maior_cet['cet'])}% a.a. em {n} bancos.",
                    f"Financiamento de {nome_cat} de {vc} em {prazo}x: parcela de {_reais_inteiros(menor_p['parcela'])} a {_reais_inteiros(maior_p['parcela'])} em {n} bancos.",
                )

                linhas_html = []
                for x in linhas:
                    slug_b = lookup.get((categoria, x["banco"], valor, prazo))
                    favicon = favicon_com_fallback(f"https://www.google.com/s2/favicons?domain={x['dominio_favicon']}&sz=64", x["nome_exibicao"], "w-5 h-5")
                    linhas_html.append(f'''<a href="{slug_b}" class="grid grid-cols-[1fr_auto_auto] md:grid-cols-[1.4fr_1fr_1fr_1fr_1fr] items-center gap-3 p-3 rounded-lg border border-white/10 hover:border-sky-500/50 hover:bg-white/5 transition-all">
            <span class="flex items-center gap-2 min-w-0">{favicon}<span class="text-sm font-medium truncate">{x["nome_exibicao"]}</span></span>
            <span class="hidden md:block text-xs text-slate-400 text-center">{_pct(x["taxa_am"])}% a.m.</span>
            <span class="text-xs text-slate-300 text-right md:text-center whitespace-nowrap">{formatar_reais(x["parcela"])}</span>
            <span class="hidden md:block text-xs text-slate-400 text-center whitespace-nowrap">{_reais_inteiros(x["total"])}</span>
            <span class="text-sm text-sky-400 font-bold text-right whitespace-nowrap">CET {_pct(x["cet"])}%</span>
        </a>''')
                linhas_blocos = "\n".join(linhas_html)

                outros_prazos = []
                for p2 in PRAZOS_MESES:
                    if p2 != prazo and pagina_comparacao_existe(categoria, valor, p2):
                        l2 = linhas_comparacao(categoria, valor, p2)
                        outros_prazos.append(f'<a href="{slug_comparacao(categoria, valor, p2)}" class="flex items-center justify-between gap-3 p-3 rounded-lg border border-white/10 hover:border-sky-500/50 text-sm text-slate-300"><span>{vc} em {p2} meses</span><span class="text-xs text-slate-400">parcela a partir de {_reais_inteiros(min(y["parcela"] for y in l2))}</span></a>')
                vizinhos = []
                idx = valores.index(valor)
                for j in (idx - 1, idx + 1):
                    if 0 <= j < len(valores) and pagina_comparacao_existe(categoria, valores[j], prazo):
                        v2 = valores[j]
                        l2 = linhas_comparacao(categoria, v2, prazo)
                        vizinhos.append(f'<a href="{slug_comparacao(categoria, v2, prazo)}" class="flex items-center justify-between gap-3 p-3 rounded-lg border border-white/10 hover:border-sky-500/50 text-sm text-slate-300"><span>{formatar_valor_curto(v2)} em {prazo} meses</span><span class="text-xs text-slate-400">parcela a partir de {_reais_inteiros(min(y["parcela"] for y in l2))}</span></a>')

                perguntas = [
                    (f"Qual a parcela de um financiamento de {nome_cat} de {vc} em {prazo} meses?",
                     f"Com entrada mínima de {entrada_pct}% ({formatar_reais(menor_p['entrada'])}), o valor financiado é {formatar_reais(menor_p['financiado'])}. A parcela mensal vai de {formatar_reais(menor_p['parcela'])} ({menor_p['nome_exibicao']}) a {formatar_reais(maior_p['parcela'])} ({maior_p['nome_exibicao']}), na tabela Price (parcela fixa). A diferença vem da taxa média de cada banco."),
                    (f"Qual banco tem o menor CET para financiar {nome_cat} de {vc} em {prazo} meses?",
                     f"Na nossa simulação, o CET vai de {_pct(menor_cet['cet'])}% a.a. ({menor_cet['nome_exibicao']}) a {_pct(maior_cet['cet'])}% a.a. ({maior_cet['nome_exibicao']}). O CET inclui juros, IOF, tarifa de registro e seguro prestamista estimados. A taxa final de cada cliente depende de relacionamento, histórico de crédito e entrada."),
                    (f"Quanto vou pagar ao todo para financiar {vc} em {prazo} meses?",
                     f"Somando as {prazo} parcelas, o total pago vai de {formatar_reais(min(x['total'] for x in linhas))} a {formatar_reais(max(x['total'] for x in linhas))}, para {formatar_reais(menor_p['financiado'])} financiados. A diferença é o custo do crédito (juros) em cada banco; não inclui IOF, tarifas nem seguros."),
                ]
                faq_html, schema_faq = render_faq_visual(perguntas)
                schema_breadcrumb = {
                    "@context": "https://schema.org", "@type": "BreadcrumbList",
                    "itemListElement": [
                        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
                        {"@type": "ListItem", "position": 2, "name": "Financiamento de veículos por valor e prazo", "item": url_indice},
                        {"@type": "ListItem", "position": 3, "name": f"{label} {vc} em {prazo} meses", "item": url_canonica},
                    ],
                }
                schema_lista = {
                    "@context": "https://schema.org", "@type": "ItemList",
                    "name": f"Bancos para financiar {nome_cat} de {vc} em {prazo} meses, do menor ao maior CET",
                    "numberOfItems": len(linhas),
                    "itemListElement": [{"@type": "ListItem", "position": pos, "name": x["nome_exibicao"]}
                                        for pos, x in enumerate(linhas, start=1)],
                }
                head = render_head(titulo, meta, url_canonica, [schema_breadcrumb, schema_faq, schema_lista])
                breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Financiamento de veículos", "financiamento-veiculos"), (f"{label} {vc} em {prazo} meses", None)])

                corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Financiamento de {nome_cat} de {vc} em {prazo} meses</h1>
        <p class="text-slate-400 text-sm mb-2">Parcela e CET para financiar {vf} em {prazo} meses, com entrada mínima de {entrada_pct}%, nos {n} bancos que acompanhamos (ordenado por CET, do menor para o maior).</p>
        <p class="text-slate-600 text-[10px] uppercase tracking-widest mb-6">Taxas atualizadas em {data_br} · Fonte: Banco Central do Brasil (BACEN)</p>

        <div class="hidden md:grid grid-cols-[1.4fr_1fr_1fr_1fr_1fr] gap-3 px-3 mb-2 text-[11px] text-slate-400 uppercase tracking-widest"><span>Banco</span><span class="text-center">Taxa</span><span class="text-center">Parcela (Price)</span><span class="text-center">Total das parcelas</span><span class="text-right">CET</span></div>
        <div class="grid gap-2">{linhas_blocos}</div>
        <p class="text-slate-400 text-xs font-light leading-relaxed mt-4">Cada linha leva à simulação completa do banco, onde você ajusta valor, entrada e prazo. Valores de referência com a taxa média real apurada pelo Banco Central; a proposta final depende da análise de crédito.</p>

        <section class="mt-10">
            <h2 class="font-serif text-xl font-bold mb-2">Resumo para {vc} em {prazo} meses</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed">Financiando {vf} em {prazo} meses, a parcela vai de <strong class="text-white">{formatar_reais(menor_p["parcela"])}</strong> ({menor_p["nome_exibicao"]}) a <strong class="text-white">{formatar_reais(maior_p["parcela"])}</strong> ({maior_p["nome_exibicao"]}). O CET varia de {_pct(menor_cet["cet"])}% a {_pct(maior_cet["cet"])}% ao ano. Com {entrada_pct}% de entrada, você financia {formatar_reais(menor_p["financiado"])}.</p>
        </section>

        <section class="mt-8 grid md:grid-cols-2 gap-6">
            <div><h2 class="font-serif text-lg font-semibold mb-3">Mesmo valor, outros prazos</h2><div class="grid gap-2">{"".join(outros_prazos)}</div></div>
            <div><h2 class="font-serif text-lg font-semibold mb-3">Mesmo prazo, valores próximos</h2><div class="grid gap-2">{"".join(vizinhos)}</div></div>
        </section>

        {_guias_html()}
        {_cta_comparacao("Quer comparar propostas?")}
        {faq_html}
        <p class="text-center text-xs text-slate-400 mt-6"><a href="{slug_comparador(categoria)}" class="text-sky-400 underline">Ver o comparador de {nome_cat} →</a></p>
    </main>'''
                html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''
                with open(os.path.join(pasta_saida, f"{slug}.html"), "w", encoding="utf-8") as f:
                    f.write(corrigir_concordancia(html))
                urls.append(url_canonica)

    urls.append(gerar_indice_comparacao(pasta_saida, data_atualizacao))
    return urls


def gerar_indice_comparacao(pasta_saida, data_atualizacao):
    """Índice (financiamento-veiculos.html): uma tabela valor x prazo por
    categoria, com a menor parcela entre os bancos em cada cenário; cada
    célula leva à página de comparação."""
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    url_canonica = f"{DOMINIO}/financiamento-veiculos"
    titulo = "Financiamento de veículo: parcela por valor e prazo | Datalab"
    meta = "Tabela de financiamento de carro novo, carro usado e moto: parcela e CET por valor e prazo, comparados entre os bancos, com dados do Banco Central."
    prazos_validos = {c: [p for p in PRAZOS_MESES if len(bancos_com_prazo(c, p)) >= MIN_BANCOS_COMPARACAO] for c in CATEGORIAS}
    secoes = []
    for categoria in CATEGORIAS:
        cab = "".join(f'<th scope="col" class="px-3 py-2 text-right font-medium">{p}x</th>' for p in prazos_validos[categoria])
        corpo_tab = ""
        for valor in VALORES_POR_CATEGORIA[categoria]:
            celulas = ""
            for p in prazos_validos[categoria]:
                l = linhas_comparacao(categoria, valor, p)
                celulas += f'<td class="px-3 py-2 text-right"><a href="{slug_comparacao(categoria, valor, p)}" class="text-sky-400 hover:underline">{_reais_inteiros(min(x["parcela"] for x in l))}</a></td>'
            corpo_tab += f'<tr class="border-t border-white/5"><th scope="row" class="px-3 py-2 text-left font-medium text-white">{formatar_valor_curto(valor)}</th>{celulas}</tr>'
        secoes.append(f'''<section class="mt-10">
            <h2 class="font-serif text-xl font-bold mb-3">{CATEGORIA_LABEL[categoria]}: menor parcela por valor e prazo</h2>
            <div class="overflow-x-auto rounded-xl border border-white/10"><table class="w-full text-sm text-slate-300">
                <thead class="text-[11px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-3 py-2 text-left font-medium">Valor do veículo</th>{cab}</tr></thead>
                <tbody>{corpo_tab}</tbody>
            </table></div>
        </section>''')
    perguntas = [
        ("Como ler estas tabelas?",
         "Cada célula mostra a menor parcela mensal (tabela Price) entre os bancos para aquele valor de veículo e prazo, com a entrada mínima da categoria. Clique para ver todos os bancos lado a lado, com CET e total pago."),
        ("De onde vêm as taxas?",
         "Da taxa média real praticada por cada banco em cada modalidade, apurada pelo Banco Central do Brasil. A taxa final de cada cliente varia com relacionamento, histórico de crédito e entrada."),
    ]
    faq_html, schema_faq = render_faq_visual(perguntas)
    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": "Financiamento de veículos por valor e prazo", "item": url_canonica},
        ],
    }
    head = render_head(titulo, meta, url_canonica, [schema_breadcrumb, schema_faq])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Financiamento de veículos", None)])
    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Financiamento de veículo: parcela por valor e prazo</h1>
        <p class="text-slate-400 text-sm mb-2">Menor parcela entre os bancos para cada valor e prazo, em carro novo, carro usado e moto. Escolha um cenário para comparar todos os bancos.</p>
        <p class="text-slate-600 text-[10px] uppercase tracking-widest">Taxas atualizadas em {data_br} · Fonte: Banco Central do Brasil (BACEN)</p>
        {"".join(secoes)}
        {_guias_html()}
        {_cta_comparacao("Quer ajuda para escolher?")}
        {faq_html}
    </main>'''
    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, "financiamento-veiculos.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html))
    return url_canonica



# ---------------------------------------------------------------------------
# Simulador incorporável (/embed), página "como incorporar" (/incorporar) e
# página de imprensa (/imprensa). Mesma motivação do projeto irmão (ver
# gerador.py): ganhar links sem contato com ninguém.
# ---------------------------------------------------------------------------

_JS_CALCULO_EMBED = """// <calc>
function calcularFinanciamento(valorFinanciado, meses, taxaAmPct) {
  var i = taxaAmPct / 100;
  var price = i > 0 ? valorFinanciado * (i * Math.pow(1 + i, meses)) / (Math.pow(1 + i, meses) - 1) : valorFinanciado / meses;
  return {parcela: price, total: price * meses, juros: price * meses - valorFinanciado};
}
// </calc>"""

_TEMPLATE_EMBED = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Simulador de financiamento de veículos | Datalab Global</title>
<meta name="description" content="Simulador de financiamento de veículos incorporável: parcela com a taxa média de cada banco.">
<meta name="robots" content="noindex,follow">
<link rel="canonical" href="__DOMINIO__/incorporar">
<link rel="icon" href="/favicon.ico?v=20261012" sizes="any">
<link rel="icon" href="/favicon-32.png?v=20261012" type="image/png" sizes="32x32">
<style>
*{box-sizing:border-box}body{margin:0;padding:14px;font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:#0b1220;color:#e2e8f0}
h1{font-size:16px;margin:0 0 10px;font-weight:700}label{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;margin:10px 0 4px}
select,input{width:100%;padding:9px 10px;border-radius:8px;border:1px solid #334155;background:#111b2e;color:#f8fafc;font-size:14px}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.res{margin-top:14px;padding:12px;border-radius:10px;background:#0c2433;border:1px solid #0ea5e9}
.res b{display:block;font-size:20px;color:#7dd3fc}.res small{color:#94a3b8}.k{display:flex;justify-content:space-between;gap:8px;padding:4px 0;border-top:1px solid #16394f}
.nota{margin-top:10px;font-size:11px;color:#94a3b8}.nota a{color:#7dd3fc}
</style>
</head>
<body>
<h1>Simule seu financiamento de veículo</h1>
<div class="row"><div><label for="cat">Veículo</label><select id="cat"><option value="novo">Carro novo</option><option value="usado">Carro usado</option><option value="moto">Moto</option></select></div>
<div><label for="banco">Banco</label><select id="banco"></select></div></div>
<div class="row"><div><label for="valor">Valor do veículo (R$)</label><input id="valor" type="number" min="3000" step="1000" inputmode="numeric"></div>
<div><label for="prazo">Prazo</label><select id="prazo"></select></div></div>
<label for="entrada">Entrada (R$) <span id="minimo" style="text-transform:none;letter-spacing:0"></span></label><input id="entrada" type="number" min="0" step="500" inputmode="numeric">
<div class="res" aria-live="polite">
<small>Parcela mensal (Price, fixa)</small><b id="parcela">–</b>
<div class="k"><span>Total das parcelas</span><span id="total">–</span></div>
<div class="k"><span>Juros totais</span><span id="juros">–</span></div>
<div class="k"><span>Valor financiado</span><span id="fin">–</span></div></div>
<p class="nota" id="nota"></p>
<p class="nota">Simulação educativa, sem IOF, tarifas e seguros; não é oferta de crédito. Simulador por <a href="__DOMINIO__/" target="_blank" rel="noopener">Datalab Global</a>.</p>
<script>
__JS_CALCULO__
var BANCOS = __BANCOS_JSON__, ENTRADA = __ENTRADA_JSON__, VALOR_PADRAO = {novo: 80000, usado: 40000, moto: 18000};
var fmt = new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL', maximumFractionDigits: 0});
var el = function (id) { return document.getElementById(id); };
function bancosDaCategoria() { return BANCOS.filter(function (b) { return b.cats.indexOf(el('cat').value) >= 0; }); }
function preencherBancos() {
  var lista = bancosDaCategoria(); el('banco').innerHTML = '';
  lista.forEach(function (b, i) { var o = document.createElement('option'); o.value = i; o.textContent = b.nome + ' (' + b.taxaAm.toFixed(2).replace('.', ',') + '% a.m.)'; el('banco').appendChild(o); });
}
function preencherPrazos() {
  var b = bancosDaCategoria()[el('banco').value], atual = el('prazo').value; el('prazo').innerHTML = '';
  [12, 24, 36, 48, 60].forEach(function (m) { if (m <= b.prazoMax) { var o = document.createElement('option'); o.value = m; o.textContent = m + ' meses'; el('prazo').appendChild(o); } });
  el('prazo').value = Array.prototype.some.call(el('prazo').options, function (o) { return o.value === atual; }) ? atual : String(Math.min(48, b.prazoMax));
}
function calcular(ajustarEntrada) {
  var b = bancosDaCategoria()[el('banco').value], cat = el('cat').value, valor = Math.max(0, parseFloat(el('valor').value) || 0);
  var min = valor * ENTRADA[cat];
  el('minimo').textContent = '(mín. ' + fmt.format(min) + ')';
  if (ajustarEntrada || !el('entrada').value) el('entrada').value = Math.round(min);
  var entrada = Math.min(valor, Math.max(min, parseFloat(el('entrada').value) || 0)), fin = valor - entrada, meses = parseInt(el('prazo').value, 10);
  if (fin <= 0 || !meses) { ['parcela','total','juros','fin'].forEach(function (id) { el(id).textContent = '–'; }); return; }
  var r = calcularFinanciamento(fin, meses, b.taxaAm);
  el('parcela').textContent = fmt.format(r.parcela); el('total').textContent = fmt.format(r.total); el('juros').textContent = fmt.format(r.juros); el('fin').textContent = fmt.format(fin);
  el('nota').textContent = 'Taxa média: ' + b.nome + ', ' + b.taxaAm.toFixed(2).replace('.', ',') + '% a.m. (Banco Central, __DATA_BR__).';
}
el('cat').addEventListener('change', function () { el('valor').value = VALOR_PADRAO[el('cat').value]; preencherBancos(); preencherPrazos(); calcular(true); });
el('banco').addEventListener('change', function () { preencherPrazos(); calcular(false); });
el('prazo').addEventListener('change', function () { calcular(false); });
el('valor').addEventListener('input', function () { calcular(true); });
el('entrada').addEventListener('input', function () { calcular(false); });
el('valor').value = VALOR_PADRAO.novo; preencherBancos(); preencherPrazos(); calcular(true);
</script>
</body>
</html>"""


def gerar_embed(pasta_saida, data_atualizacao):
    """/embed: simulador mínimo, sem dependências, pra ser usado em <iframe>."""
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    bancos = [{"chave": b, "nome": d["nome_exibicao"], "taxaAm": d["taxa_am"], "taxaAa": d["taxa_aa"],
               "prazoMax": d["prazo_max"], "cats": list(d["aplica_a"])} for b, d in BANCOS_VEICULOS.items()]
    entrada = {c: entrada_minima(c) for c in CATEGORIAS}
    html_embed = (_TEMPLATE_EMBED
                  .replace("__JS_CALCULO__", _JS_CALCULO_EMBED)
                  .replace("__BANCOS_JSON__", json.dumps(bancos, ensure_ascii=False))
                  .replace("__ENTRADA_JSON__", json.dumps(entrada))
                  .replace("__DOMINIO__", DOMINIO).replace("__DATA_BR__", data_br))
    with open(os.path.join(pasta_saida, "embed.html"), "w", encoding="utf-8") as f:
        f.write(html_embed)


def gerar_pagina_incorporar(pasta_saida, data_atualizacao):
    url = f"{DOMINIO}/incorporar"
    codigo = (f'<iframe src="{DOMINIO}/embed" title="Simulador de financiamento de veículos" '
              f'width="100%" height="600" style="border:0;max-width:520px" loading="lazy"></iframe>\n'
              f'<p style="font-size:12px">Simulador por <a href="{DOMINIO}/">Datalab Global</a></p>')
    codigo_html = codigo.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    perguntas = [
        ("O simulador para incorporar é gratuito?",
         "Sim. Basta copiar o código e colar no HTML da sua página. Pedimos apenas que mantenha o link de crédito para a Datalab Global."),
        ("Preciso me cadastrar ou usar alguma biblioteca?",
         "Não. É um iframe: sem cadastro, sem chave de API, sem JavaScript no seu site e sem cookies."),
        ("Quais veículos e bancos o simulador cobre?",
         "Carro novo, carro usado e moto, com os bancos que acompanhamos em cada categoria, usando a taxa média mensal de cada um segundo o Banco Central. É atualizado por nós toda semana."),
        ("O que o simulador calcula?",
         "A parcela fixa (tabela Price), o total das parcelas, os juros totais e o valor financiado, respeitando a entrada mínima da categoria e o prazo máximo de cada banco. Não inclui IOF, tarifas nem seguros."),
    ]
    faq_html, schema_faq = render_faq_visual(perguntas)
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Simulador para incorporar", "item": url}]}
    titulo = "Simulador de financiamento de veículos para site (grátis) | Datalab"
    meta = "Incorpore grátis um simulador de financiamento de carro e moto no seu site, com taxas atualizadas dos bancos. Copie o código e cole: sem cadastro."
    head = render_head(titulo, meta, url, [schema_bc, schema_faq])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Simulador para incorporar", None)])
    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Simulador de financiamento de veículos para o seu site</h1>
        <p class="text-slate-400 text-sm mb-8">Copie o código, cole na sua página e pronto: um simulador de parcela de carro e moto com a taxa média atualizada de cada banco, grátis e sem cadastro.</p>
        <section class="grid md:grid-cols-2 gap-8 items-start">
            <div><h2 class="font-serif text-xl font-bold mb-3">Veja como fica</h2>
                <iframe src="embed" title="Simulador de financiamento de veículos" width="100%" height="600" style="border:0;max-width:520px;border-radius:12px" loading="lazy"></iframe></div>
            <div><h2 class="font-serif text-xl font-bold mb-3">Copie o código</h2>
                <textarea readonly rows="7" onclick="this.select()" class="w-full bg-slate-900/60 border border-white/10 rounded-xl p-3 text-xs text-slate-300 font-mono" aria-label="Código para incorporar o simulador">{codigo_html}</textarea>
                <ol class="mt-4 space-y-2 text-sm text-slate-300 list-decimal list-inside"><li>Clique no código e copie (Ctrl+C).</li><li>Cole no HTML da página onde o simulador deve aparecer.</li><li>Mantenha o link "Simulador por Datalab Global" logo abaixo.</li></ol>
                <p class="mt-4 text-xs text-slate-400">Taxas médias do Banco Central. Simulação educativa: não é oferta de crédito. Os <a href="dados-abertos" class="text-sky-400 underline">dados abertos</a> por trás do simulador estão em CSV e JSON.</p></div>
        </section>
        {faq_html}
        <p class="mt-8 text-center text-xs text-slate-400"><a href="financiamento-veiculos" class="text-sky-400 underline">Tabela de financiamento por valor e prazo</a></p>
    </main>'''
    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, "incorporar.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html))
    return [url]


def gerar_pagina_imprensa(pasta_saida, data_atualizacao):
    """/imprensa: fatos citáveis calculados dos dados reais, metodologia, logos,
    como citar e contato."""
    url = f"{DOMINIO}/imprensa"
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    historico = carregar_historico()
    fatos = []
    if historico:
        meses = sorted({r["mes_referencia"] for r in historico})
        ult = meses[-1]
        do_mes = sorted((r for r in historico if r["mes_referencia"] == ult), key=lambda r: r["taxa_am"])
        if do_mes:
            lo, hi = do_mes[0], do_mes[-1]
            n_lo, n_hi = BANCOS_VEICULOS[lo["banco"]]["nome_exibicao"], BANCOS_VEICULOS[hi["banco"]]["nome_exibicao"]
            fatos.append(f"Em {MESES_PT[int(ult[5:7]) - 1]} de {ult[:4]}, a taxa média contratada no financiamento de veículos foi de {_pct2(lo['taxa_am'])}% ao mês em {n_lo}, a menor entre os {len(do_mes)} bancos com dado do Banco Central, e de {_pct2(hi['taxa_am'])}% ao mês em {n_hi}, a maior.")
        resumo = resumo_historico(historico)
        if resumo:
            q, a = resumo["maior_queda"], resumo["maior_alta"]
            m0, m1 = resumo["meses"][0], resumo["meses"][-1]
            fatos.append(f"Entre {_rotulo_mes(m0)} e {_rotulo_mes(m1)}, a maior queda foi a de {q['banco_exib']} ({_sinal_pp(q['variacao'])} ponto percentual ao mês) e a maior alta, a de {a['banco_exib']} ({_sinal_pp(a['variacao'])} ponto percentual).")
        fatos.append(f"A série histórica cobre {len(meses)} meses ({_rotulo_mes(meses[0])} a {_rotulo_mes(meses[-1])}) e está disponível em dados abertos, sob licença {LICENCA_DADOS}.")
    ln = linhas_comparacao("novo", 60_000, 48)
    p_lo, p_hi = min(ln, key=lambda x: x["parcela"]), max(ln, key=lambda x: x["parcela"])
    fatos.append(f"Para financiar um carro novo de R$ 60 mil em 48 meses, com entrada de 20%, a parcela mensal vai de {formatar_reais(p_lo['parcela'])} ({p_lo['nome_exibicao']}) a {formatar_reais(p_hi['parcela'])} ({p_hi['nome_exibicao']}), e o CET estimado, de {_pct(min(x['cet'] for x in ln))}% a {_pct(max(x['cet'] for x in ln))}% ao ano.")
    fatos_html = "".join(f'<li class="mb-3">{f}</li>' for f in fatos)
    citacao = f"Datalab Global. Taxas de financiamento de veículos por banco (dados do Banco Central). {url}, acesso em AAAA-MM-DD."
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Imprensa", "item": url}]}
    schema_page = {"@context": "https://schema.org", "@type": "WebPage", "url": url, "name": "Imprensa e dados para citação",
                   "dateModified": data_atualizacao, "about": {"@type": "Organization", "name": "Datalab Global", "url": "https://www.datalabglobal.com/"}}
    titulo = "Imprensa: dados de financiamento de veículos para citar | Datalab"
    meta = "Números atualizados de taxas e parcelas de financiamento de veículos, metodologia, logos e como citar a Datalab Global. Dados abertos (CC BY 4.0)."
    head = render_head(titulo, meta, url, [schema_bc, schema_page])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Imprensa", None)])
    corpo = f'''<main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Imprensa e dados para citação</h1>
        <p class="text-slate-400 text-sm mb-8">Números prontos, metodologia aberta e a forma de citar. Atualizado em {data_br}.</p>
        <section><h2 class="font-serif text-xl font-bold mb-3">Números para citar</h2>
            <ul class="text-slate-300 text-sm font-light leading-relaxed list-disc list-inside">{fatos_html}</ul>
            <p class="text-slate-400 text-xs mt-2">Calculados automaticamente a partir dos dados do Banco Central; mudam a cada atualização. As taxas são médias do que foi efetivamente contratado, não ofertas.</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Metodologia</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed">As taxas vêm do relatório de taxas de juros por instituição financeira do Banco Central (modalidade 401101, aquisição de veículos, pessoa física, pré-fixada), que não separa carro novo, carro usado e moto. O CET é calculado por nós (IOF, tarifa de registro e seguro prestamista estimados) para o mesmo valor, prazo e a entrada mínima da categoria. Série completa em <a href="dados-abertos" class="text-sky-400 underline">dados abertos</a>.</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Sobre a Datalab Global</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed">A Datalab Global é uma marca de {EMPRESA_RODAPE}. Cria ferramentas gratuitas de dados e de simulação de crédito. As simulações são educativas e não constituem oferta de crédito. Conheça a <a href="sobre" class="text-sky-400 underline">página Sobre</a>.</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Logos e imagens</h2>
            <ul class="text-sm space-y-2"><li><a href="logo-full.png" download class="text-sky-400 underline">Logo completo (PNG)</a></li><li><a href="logo-schema.png" download class="text-sky-400 underline">Ícone (PNG, 512 px)</a></li><li><a href="og-image.png" download class="text-sky-400 underline">Imagem de compartilhamento (PNG)</a></li></ul></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Como citar</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed bg-white/5 border border-white/10 rounded-xl p-4">{citacao}</p>
            <p class="text-slate-400 text-xs mt-3">Dados sob licença <a href="{LICENCA_DADOS_URL}" rel="noopener" class="underline">{LICENCA_DADOS}</a>: pode usar e adaptar, citando a fonte com link.</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Contato</h2>
            <p class="text-slate-300 text-sm font-light">E-mail: <a href="mailto:contato@datalabglobal.com" class="text-sky-400 underline">contato@datalabglobal.com</a></p></section>
        <p class="mt-10 text-center text-xs text-slate-400"><a href="financiamento-veiculos" class="text-sky-400 underline">Parcela por valor e prazo</a> · <a href="incorporar" class="text-sky-400 underline">Simulador para o seu site</a></p>
    </main>'''
    html = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, "imprensa.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html))
    return [url]



def gerar_index(data_atualizacao):
    url_home = f"{DOMINIO}/"
    titulo_pagina = "Simulador de Financiamento de Veículos: Carro e Moto | Datalab"
    meta_description = (
        "Compare taxas reais de financiamento de carro novo, usado e moto entre os principais bancos "
        "do Brasil, com dados do Banco Central. Simule parcela e CET."
    )

    cards = []
    for categoria in CATEGORIAS:
        label = CATEGORIA_LABEL[categoria]
        n_bancos = len(bancos_para_categoria(categoria))
        cards.append(f'''<a href="{slug_comparador(categoria)}" class="glass-panel-sky rounded-2xl p-6 hover:border-sky-500/40 transition-all group">
            <div class="mb-3 flex justify-center">{ilustracao_categoria(categoria, f'il-grad-{categoria}')}</div>
            <h2 class="font-serif text-xl font-bold mb-1">{label}</h2>
            <p class="text-sm text-slate-400 mb-4">Compare {n_bancos} bancos e simule sua parcela.</p>
            <span class="inline-flex items-center gap-1.5 text-xs text-sky-400 group-hover:gap-2.5 transition-all">Ver comparador {icone('arrow-right')}</span>
        </a>''')
    cards_html = "\n".join(cards)

    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": url_home}],
    }

    # Schema WebSite + Organization — só na home, mesmo padrão do projeto
    # irmão (ver gerador.py). "logo" aponta pro logo-schema.png (raster
    # 512x512, gerado por rasterizar_favicon_png), não pro favicon.svg:
    # o Google recomenda uma imagem raster real de pelo menos 112x112px
    # pra aparecer no card de marca da busca (developers.google.com/
    # search/docs/appearance/structured-data/logo). Achado real
    # (06/set/2026, aplicado primeiro no imobiliário): sem isso o Google
    # mostra o domínio cru + ícone genérico em vez do nome "Datalab
    # Global" — replicado aqui pra manter os dois produtos irmãos no
    # mesmo padrão de indexação desde já, mesmo o veicular ainda não
    # estando no ar (não custa nada ter pronto pro dia do deploy).
    schema_website = {
        "@context": "https://schema.org", "@type": "WebSite",
        "name": "Datalab Global", "url": url_home, "dateModified": data_atualizacao,
        "publisher": {"@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global", "url": "https://www.datalabglobal.com/"},
    }
    # Achado real (12/set/2026, pesquisa sobre E-E-A-T/YMYL pedida pelo
    # usuário — conteúdo financeiro é avaliado pelo Google com padrão mais
    # alto de confiança do que conteúdo comum): "founder"/"contactPoint"
    # são sinais legíveis por máquina de que existe gente real, com
    # contato real, por trás do site. Mesmo dado aplicado no imobiliário
    # (ver gerador.py) — Rodolfo Delfino é o fundador real, e-mail é o
    # contato real do domínio (Google Workspace).
    schema_organization = {
        "@context": "https://schema.org", "@type": "Organization", "@id": "https://www.datalabglobal.com/#organization",
        "name": "Datalab Global", "url": "https://www.datalabglobal.com/", "logo": f"{DOMINIO}/logo-schema.png",
        "founder": {"@type": "Person", "name": "Rodolfo Delfino"},
        "contactPoint": {"@type": "ContactPoint", "email": "contato@datalabglobal.com", "contactType": "customer service"},
    }

    faq_html, schema_faq = render_faq_visual([
        (
            "Como funciona o simulador de financiamento de veículos da Datalab?",
            "Você escolhe a categoria do veículo (carro novo, carro usado ou moto), compara a taxa real de cada "
            "banco e simula a parcela pro valor e prazo que quiser. Os dados de taxa vêm direto do Banco Central "
            "e são atualizados semanalmente.",
        ),
        (
            "As taxas mostradas são reais ou só uma estimativa de marketing?",
            "São a taxa média efetivamente contratada por cada banco nessa modalidade, apurada mensalmente pelo "
            "Banco Central (BACEN) — não é uma taxa promocional \"a partir de\". Sua taxa final depende do seu "
            "relacionamento com o banco e da análise de crédito.",
        ),
        (
            "O simulador cobra alguma coisa pra usar?",
            "Não, simular é 100% gratuito. A Datalab é remunerada pelo correspondente bancário quando você pede "
            "uma análise por aqui — isso não muda o valor da sua parcela nem qual banco você escolhe.",
        ),
    ])

    head = render_head(titulo_pagina, meta_description, url_home, [schema_breadcrumb, schema_website, schema_organization, schema_faq])
    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-3xl font-bold mb-2">Simulador de Financiamento de Veículos</h1>
        <p class="text-slate-400 text-sm mb-8">Escolha a categoria do seu veículo para comparar taxas reais e simular parcelas.</p>
        <div class="grid sm:grid-cols-3 gap-4">{cards_html}</div>
        <p class="mt-6 text-sm text-slate-300">Prefere ver direto a parcela do seu valor e prazo? Consulte a <a href="financiamento-veiculos" class="text-sky-400 underline">tabela de financiamento de veículo por valor e prazo</a>.</p>
        {faq_html}
    </main>'''

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
    {SCRIPT_AJUSTA_TOOLTIPS}
</body>
</html>'''


def gerar_pagina_aprenda(art, data_atualizacao):
    """Página de conteúdo evergreen (educativo, sem calculadora) —
    segunda camada de profundidade de conteúdo, complementar às páginas
    de cálculo. Achado real (13/set/2026, pedido explícito do usuário
    depois da auditoria de SEO): o site inteiro só tinha página de
    CÁLCULO — nenhuma prova, legível por humano OU pelo Google, de que
    existe conhecimento real por trás da calculadora. Isso pesa duplo:
    no Helpful Content (avaliado no domínio inteiro, não por página) e
    na experiência de quem busca "o que é CET" sem estar pronto pra
    simular ainda. `art` é um dict do ARTIGOS_APRENDA (slug, títulos,
    corpo, CTA) — sempre com Article schema (headline = a própria
    pergunta/tema, não inventado) e um link de volta pro simulador
    relevante no fim, sem forçar (mantém o visitante no funil sem virar
    uma calculadora disfarçada de artigo)."""
    url_canonica = f"{DOMINIO}/{art['slug']}"
    schema_article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": art["titulo_h1"], "url": url_canonica,
        "author": {"@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global", "url": f"{DOMINIO}/sobre"},
        "publisher": {
            "@type": "Organization", "name": "Datalab Global",
            "logo": {"@type": "ImageObject", "url": f"{DOMINIO}/logo-schema.png"},
        },
        "dateModified": data_atualizacao, "mainEntityOfPage": url_canonica,
    }
    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": "Aprenda", "item": f"{DOMINIO}/aprenda"},
            {"@type": "ListItem", "position": 3, "name": art["titulo_h1"], "item": url_canonica},
        ],
    }
    head = render_head(art["titulo_pagina"], art["meta_description"], url_canonica, [schema_article, schema_breadcrumb])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Aprenda", "aprenda"), (art["titulo_h1"], None)])
    corpo = f'''<main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-3xl font-bold mb-8">{art["titulo_h1"]}</h1>
        <div class="glass-panel-sky rounded-2xl p-6 md:p-10 space-y-6 text-slate-300 leading-relaxed">
            {art["corpo_html"]}
        </div>
        <div class="flex flex-wrap gap-3 mt-8">
            <a href="{art['cta_href']}" class="bg-sky-500 hover:bg-sky-400 text-slate-950 px-6 py-3 rounded-full font-bold text-sm transition-all">{art['cta_texto']}</a>
            <a href="aprenda" class="border border-white/10 hover:border-sky-500/50 px-6 py-3 rounded-full font-bold text-sm transition-all">Ver todos os artigos</a>
        </div>
    </main>'''
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''


def gerar_hub_aprenda(artigos, data_atualizacao):
    """Índice /aprenda listando os artigos evergreen — o único caminho de
    navegação normal (clicando) até eles além do link no rodapé de toda
    página, mesmo cuidado que já tomamos com as páginas de simulação
    (achado real de 07/set/2026: conteúdo só alcançável via sitemap.xml
    é órfão de verdade pro visitante humano)."""
    url_canonica = f"{DOMINIO}/aprenda"
    cards_html = "\n".join(
        f'''<a href="{a['slug']}" class="glass-panel-sky rounded-2xl p-6 hover:border-sky-500/40 transition-all group">
            <h2 class="font-serif text-lg font-bold mb-2 group-hover:text-sky-400 transition-colors">{a['titulo_h1']}</h2>
            <p class="text-sm text-slate-400">{a['resumo_card']}</p>
        </a>'''
        for a in artigos
    )
    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
            {"@type": "ListItem", "position": 2, "name": "Aprenda", "item": url_canonica},
        ],
    }
    head = render_head(
        "Aprenda: guias sobre financiamento de veículos | Datalab Global",
        "Guias sobre financiamento de veículos: CDC, Price, IOF, CET, amortização, consórcio, "
        "quitação antecipada, portabilidade, score e entrada, sem juridiquês.",
        url_canonica, [schema_breadcrumb],
    )
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Aprenda", None)])
    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Aprenda sobre financiamento de veículos</h1>
        <p class="text-slate-400 text-sm mb-8">Guias educativos, sem juridiquês, pra você entender o que está simulando antes de decidir.</p>
        <div class="grid sm:grid-cols-2 gap-4">{cards_html}</div>
    </main>'''
    return "aprenda", f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''


# Conteúdo evergreen (educativo) — 2ª camada de profundidade além das
# páginas de cálculo, ver docstring de gerar_pagina_aprenda(). Baseado em
# definição técnica real e estabelecida (BACEN, legislação do IOF,
# mesma terminologia já usada no glossário "Entenda os Termos" de cada
# página individual) — nunca inventado. Aprovado pelo usuário
# (13/set/2026) como a lista de 6 temas antes de escrever.
ARTIGOS_APRENDA = [
    {
        "slug": "aprenda-o-que-e-cdc",
        "titulo_h1": "O que é CDC (Crédito Direto ao Consumidor)?",
        "titulo_pagina": "O que é CDC? Como funciona o financiamento de veículo | Datalab Global",
        "meta_description": "CDC é a modalidade usada para financiar carro e moto: veja como funciona a alienação fiduciária, quem fica com o documento e por que a parcela é fixa.",
        "resumo_card": "A modalidade por trás de todo financiamento de veículo no Brasil — e por que o banco fica com o documento até o fim.",
        "corpo_html": '''<p>CDC — Crédito Direto ao Consumidor — é a modalidade de crédito usada em praticamente todo financiamento de veículo no Brasil. Na prática, o banco empresta o dinheiro direto pra você comprar o carro, a moto ou o veículo usado à vista da loja ou do vendedor, e você devolve esse valor ao banco em parcelas fixas, com juros.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Por que o veículo fica "preso" ao financiamento</h2>
            <p>A garantia do CDC de veículo é a <strong class="text-white">alienação fiduciária</strong>: o veículo passa a ser, juridicamente, propriedade do banco até a última parcela ser paga — você usa o carro normalmente, mas o documento (CRLV) fica com uma restrição financeira registrada. Só depois de quitado o financiamento é que a propriedade plena passa pra você. É por isso que o banco consegue oferecer uma taxa de juros menor que a de um empréstimo sem garantia: se as parcelas param de ser pagas, o veículo pode ser retomado.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">CDC não é a única opção</h2>
            <p>Existe também o consórcio (sem juros, mas sem previsão certa de quando você recebe o veículo) e, em alguns casos, o leasing (mais comum pra empresas). Pra a maioria das pessoas físicas comprando um veículo pra uso próprio, o CDC é o caminho mais direto — é o que este simulador calcula.</p>
        </div>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Simular financiamento de carro novo",
    },
    {
        "slug": "aprenda-tabela-price",
        "titulo_h1": "Tabela Price: por que a parcela do financiamento de veículo é sempre fixa",
        "titulo_pagina": "Tabela Price no financiamento de veículo: como funciona | Datalab Global",
        "meta_description": "Tabela Price, o sistema de amortização do CDC de veículo: por que a parcela nunca muda e como juros e amortização se alternam mês a mês.",
        "resumo_card": "O sistema por trás da parcela fixa — e por que, no fim do contrato, você paga mais amortização e menos juros.",
        "corpo_html": '''<p>Todo financiamento de veículo (CDC) no Brasil usa a <strong class="text-white">Tabela Price</strong> — também chamada de sistema francês de amortização. A característica mais visível dela é simples: a parcela é <strong class="text-white">idêntica do primeiro ao último mês</strong>, do início ao fim do contrato.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">O que muda, se a parcela não muda</h2>
            <p>O valor fixo esconde uma composição que muda todo mês: no começo do financiamento, a maior parte da parcela é <strong class="text-white">juros</strong> (porque o saldo devedor ainda é alto); perto do fim, a maior parte já é <strong class="text-white">amortização</strong> (abatimento do saldo devedor em si), porque o saldo já diminuiu bastante. A soma das duas partes é sempre a mesma parcela — só a proporção interna muda.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Diferente do financiamento imobiliário</h2>
            <p>Vale notar que financiamento de imóvel no Brasil pode usar Tabela Price OU o sistema SAC (parcela decrescente, maior no início) — o cliente escolhe. No financiamento de veículo, a Tabela Price é praticamente universal: é o formato que todo banco usa, então não é uma escolha que você faz na hora de simular.</p>
        </div>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Ver simulação com parcela fixa",
    },
    {
        "slug": "aprenda-iof-financiamento-veiculo",
        "titulo_h1": "IOF no financiamento de veículo: como é calculado",
        "titulo_pagina": "IOF no financiamento de veículo: como é calculado | Datalab Global",
        "meta_description": "O IOF incide sobre todo financiamento de veículo: alíquota fixa e diária, cobrança única e por que ele já está embutido no CET do simulador.",
        "resumo_card": "O imposto que incide sobre todo financiamento — cobrado uma vez só, e já embutido no CET que você vê aqui.",
        "corpo_html": '''<p>IOF — Imposto sobre Operações Financeiras — incide sobre praticamente todo crédito concedido no Brasil, incluindo o financiamento de veículo. Ele é cobrado <strong class="text-white">uma única vez</strong>, descontado do valor liberado na operação (não é uma cobrança mensal recorrente).</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Como a conta é feita</h2>
            <p>A alíquota tem duas partes: uma taxa <strong class="text-white">fixa de 0,38%</strong> sobre o valor financiado, mais uma taxa <strong class="text-white">diária</strong> que se acumula conforme o prazo do contrato, limitada a 365 dias (financiamentos mais longos que um ano não pagam IOF diário adicional além desse teto). Na prática, quanto maior o prazo escolhido, maior a fatia do IOF no custo total — mais um motivo pra olhar o CET (que já inclui o IOF) em vez de só a taxa de juros isolada ao comparar prazos diferentes.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Você não precisa calcular isso à parte</h2>
            <p>Todo valor de CET mostrado neste simulador já inclui o IOF da operação — você não precisa somar nada por fora. É exatamente por isso que o CET, e não a taxa de juros nominal, é o número certo pra comparar duas propostas de bancos diferentes.</p>
        </div>''',
        "cta_href": "aprenda-o-que-e-cet",
        "cta_texto": "Entender o CET completo",
    },
    {
        "slug": "aprenda-o-que-e-cet",
        "titulo_h1": "O que é CET (Custo Efetivo Total) e por que ele importa mais que a taxa de juros",
        "titulo_pagina": "O que é CET no financiamento de veículo? | Datalab Global",
        "meta_description": "CET é o custo real do financiamento de veículo por ano: juros, IOF, tarifas e seguro. É o número certo para comparar bancos diferentes.",
        "resumo_card": "O número que soma tudo — juros, IOF, tarifas e seguro — e por isso é o único jeito justo de comparar dois bancos.",
        "corpo_html": '''<p>CET — Custo Efetivo Total — é o custo real e completo de um financiamento, expresso em percentual ao ano. Diferente da taxa de juros anunciada isoladamente, o CET soma <strong class="text-white">tudo</strong> que você efetivamente paga pra ter o crédito: a taxa de juros em si, o IOF, a tarifa de registro de contrato e o seguro prestamista típico de mercado.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Por que dois bancos com a "mesma taxa" podem custar diferente</h2>
            <p>É comum dois bancos anunciarem taxas de juros parecidas, mas cobrarem tarifas e seguros diferentes — o CET é o único número que captura essa diferença de uma vez, porque já soma todos esses componentes num percentual único e comparável. Comparar só a taxa de juros nominal esconde justamente a parte que mais varia de banco pra banco.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">O CET não é uma promessa</h2>
            <p>O CET mostrado neste simulador é calculado com a taxa média real apurada pelo Banco Central pra cada banco — não é uma taxa promocional de campanha. Sua taxa final aprovada ainda depende do seu relacionamento com o banco, do seu histórico de crédito e da entrada que você der; o CET daqui é a referência mais honesta que existe pra você comparar antes de negociar.</p>
        </div>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Comparar CET entre bancos",
    },
    {
        "slug": "aprenda-amortizacao-extra-veiculo",
        "titulo_h1": "Amortização extra no financiamento de veículo: como funciona",
        "titulo_pagina": "Amortização extra no financiamento de veículo | Datalab Global",
        "meta_description": "Como um pagamento extra reduz o saldo devedor do financiamento de veículo, encurta o prazo ou diminui a parcela e economiza juros.",
        "resumo_card": "Um pagamento fora do cronograma que ataca o saldo devedor direto — e pode economizar meses inteiros de juros.",
        "corpo_html": '''<p>Amortização extra é um pagamento feito <strong class="text-white">fora</strong> do cronograma normal de parcelas, com o objetivo específico de abater o saldo devedor do financiamento — não é uma parcela adiantada nem uma antecipação do próximo mês, é um valor que reduz diretamente quanto você ainda deve ao banco.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Por que isso economiza mais do que parece</h2>
            <p>Como o financiamento usa Tabela Price (parcela fixa, mas juros calculados sobre o saldo devedor a cada mês), reduzir esse saldo mais cedo significa pagar juros sobre um valor menor em todos os meses seguintes. Na prática, R$ 1.000 amortizados hoje "economizam" mais do que R$ 1.000 pagos normalmente ao longo do contrato, porque cortam os juros que incidiriam sobre esse valor pelo tempo que faltava.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Reduzir prazo ou reduzir parcela?</h2>
            <p>Ao amortizar, o banco costuma oferecer duas opções: manter a parcela do mesmo jeito e encurtar o número de meses restantes, ou manter o prazo original e diminuir o valor da parcela. Reduzir o prazo geralmente economiza mais juros no total — mas reduzir a parcela alivia mais o orçamento mês a mês. A escolha certa depende do seu momento financeiro, não existe resposta universal.</p>
        </div>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Simular meu financiamento",
    },
    {
        "slug": "aprenda-financiamento-x-consorcio-veiculo",
        "titulo_h1": "Financiamento x Consórcio de veículo: qual a diferença",
        "titulo_pagina": "Financiamento x Consórcio de veículo: diferenças | Datalab Global",
        "meta_description": "Compare financiamento (CDC) e consórcio de veículo: quem leva o carro pra casa primeiro, quem paga juros, e em que situação cada modalidade faz mais sentido.",
        "resumo_card": "Um te dá o carro agora com juros; o outro é mais barato, mas sem data certa. Veja qual combina com seu momento.",
        "corpo_html": '''<p>Financiamento (CDC) e consórcio resolvem o mesmo problema — comprar um veículo sem pagar tudo à vista — de formas bem diferentes, e a escolha certa depende principalmente de uma coisa: você precisa do veículo <strong class="text-white">agora</strong>, ou pode esperar?</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Financiamento: veículo já, com juros</h2>
            <p>No CDC, o banco libera o valor na hora, você sai com o veículo no mesmo dia, e paga de volta em parcelas fixas com juros — é o que este simulador calcula. A certeza de ter o veículo imediatamente tem um custo: o CET (juros + IOF + tarifas) que você vê em cada simulação.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Consórcio: sem juros, mas sem data certa</h2>
            <p>No consórcio, você entra num grupo de pessoas que pagam mensalidades numa espécie de poupança coletiva, sem juros — só correção monetária e uma taxa de administração. Você só recebe o veículo quando é sorteado ou dá um lance vencedor num dos encontros mensais do grupo, o que pode acontecer logo no início ou só perto do fim do prazo contratado. O custo total costuma ser menor que o do financiamento, mas em troca de não saber exatamente quando o veículo chega.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Qual escolher</h2>
            <p>Se você precisa do veículo pra trabalhar ou por uma necessidade imediata, o financiamento resolve isso — o custo do CET é, na prática, o preço de não esperar. Se você tem flexibilidade de tempo e quer pagar menos no total, o consórcio tende a sair mais barato.</p>
        </div>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Simular financiamento de carro novo",
    },
]


# ---------------------------------------------------------------------------
# Guias de 31/out/2026 (motor v3b). Os fatos legais foram conferidos em fonte
# oficial antes de escritos (CDC art. 52 §2º; Resolução CMN 4.292/2013; Lei
# 12.414/2011 e o Cadastro Positivo, segundo gov.br e Banco Central). Os
# números dos exemplos são contas feitas com o mesmo cálculo do simulador, com
# taxas ilustrativas (não são oferta). Onde não conseguimos confirmar uma
# regra em fonte oficial, o texto descreve a situação sem afirmá-la.
# ---------------------------------------------------------------------------
def _saldo_apos(valor, prazo, taxa_am, pagas):
    """Saldo devedor (Tabela Price) depois de `pagas` parcelas."""
    i = taxa_am / 100
    pmt = calcular_pmt_price(valor, prazo, taxa_am)
    restantes = prazo - pagas
    return pmt * (1 - (1 + i) ** -restantes) / i if i else pmt * restantes


_PMT_Q = calcular_pmt_price(40_000, 48, 2.0)
_SALDO_Q = _saldo_apos(40_000, 48, 2.0, 24)
_RESTANTE_Q = _PMT_Q * 24

_PMT_P1 = calcular_pmt_price(30_000, 36, 2.2)
_PMT_P2 = calcular_pmt_price(30_000, 36, 1.8)

_PMT_S1 = calcular_pmt_price(50_000, 48, 1.8)
_PMT_S2 = calcular_pmt_price(50_000, 48, 2.3)

_LINHAS_ENTRADA = "".join(
    f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white">{round(e * 100)}% ({formatar_reais(80_000 * e)})</th>'
    f'<td class="px-2 py-2 text-right">{formatar_reais(80_000 * (1 - e))}</td>'
    f'<td class="px-2 py-2 text-right">{formatar_reais(calcular_pmt_price(80_000 * (1 - e), 48, 2.0))}</td>'
    f'<td class="px-2 py-2 text-right">{formatar_reais(calcular_pmt_price(80_000 * (1 - e), 48, 2.0) * 48 - 80_000 * (1 - e))}</td></tr>'
    for e in (0.20, 0.30, 0.50))

ARTIGOS_APRENDA += [
    {
        "slug": "aprenda-quitacao-antecipada-financiamento-veiculo",
        "titulo_h1": "Quitar o financiamento do veículo antes do prazo: você tem desconto nos juros",
        "titulo_pagina": "Quitação antecipada do financiamento de veículo | Datalab Global",
        "meta_description": "Pagar o financiamento do carro ou da moto antes do fim dá direito a abatimento proporcional dos juros. Veja a conta, como pedir e onde reclamar.",
        "resumo_card": "O Código de Defesa do Consumidor garante a redução proporcional dos juros ao quitar antes. Veja a conta com números.",
        "corpo_html": f'''<p>Quem quita um financiamento antes do fim do contrato não precisa pagar os juros das parcelas que ainda não venceram. O <strong class="text-white">Código de Defesa do Consumidor (Lei 8.078/1990, art. 52, § 2º)</strong> assegura a liquidação antecipada do débito, total ou parcial, com redução proporcional dos juros e demais acréscimos. É o que órgãos de defesa do consumidor, como o <a href="https://proconresponde.sc.gov.br/faq/quero-efetuar-o-pagamento-das-parcelas-de-um-financiamento-antecipadamente-tenho-desconto/" rel="noopener" class="text-sky-400 underline">Procon de Santa Catarina</a>, orientam.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">A conta, com um exemplo</h2>
            <p>Um financiamento de R$ 40.000 em 48 parcelas, a 2,00% ao mês (taxa ilustrativa), tem parcela de {formatar_reais(_PMT_Q)} pela Tabela Price. Depois de pagar 24 parcelas, faltam 24. Somando-as, seriam {formatar_reais(_RESTANTE_Q)}. Mas o saldo devedor, o valor que o banco realmente emprestou e ainda não recebeu de volta, é de {formatar_reais(_SALDO_Q)}. A diferença, <strong class="text-white">{formatar_reais(_RESTANTE_Q - _SALDO_Q)}</strong>, são juros que só existiriam se você continuasse pagando até o fim.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Como pedir</h2>
            <p>Peça ao banco, por escrito ou pelo aplicativo, o <strong class="text-white">saldo devedor para quitação</strong> e a memória de cálculo. Compare com a soma das parcelas que faltam: o valor para quitar deve ser menor. Pergunte se há qualquer cobrança adicional e peça que conste no documento. Depois de pagar, guarde o comprovante de quitação e confirme a baixa da alienação fiduciária no documento do veículo.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">E se o banco não der o desconto?</h2>
            <p>Registre uma reclamação no Procon da sua cidade ou estado e no Banco Central. Guarde as propostas e os comprovantes. Se quiser pagar só uma parte, veja também como funciona a <a href="aprenda-amortizacao-extra-veiculo" class="text-sky-400 underline">amortização extra</a>.</p>
        </div>
        <p class="text-xs text-slate-500">Os números são um exemplo calculado como no simulador, sem IOF, tarifas e seguro, e não são oferta de crédito. Fonte legal: Lei 8.078/1990 (Código de Defesa do Consumidor), art. 52, § 2º.</p>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Simular um financiamento",
    },
    {
        "slug": "aprenda-portabilidade-financiamento-veiculo",
        "titulo_h1": "Portabilidade do financiamento de veículo: dá para trocar de banco?",
        "titulo_pagina": "Portabilidade de financiamento de veículo: como funciona | Datalab Global",
        "meta_description": "Como levar o financiamento do carro ou da moto para outro banco com taxa menor: o que diz a regra do Banco Central, quando vale a pena e como fazer a conta.",
        "resumo_card": "Trocar o financiamento de banco é permitido, mas não é automático. Veja quando compensa, com a conta.",
        "corpo_html": f'''<p>A portabilidade permite transferir uma dívida de um banco para outro que ofereça condições melhores. A <a href="https://www.bcb.gov.br/pre/normativos/res/2013/pdf/res_4292_v1_O.pdf" rel="noopener" class="text-sky-400 underline">Resolução CMN 4.292/2013</a>, do Banco Central, trata da portabilidade de operações de crédito de pessoas físicas, e o Banco Central aponta o financiamento de veículos entre as modalidades que mais aparecem nas operações portadas, segundo o <a href="https://www.bcb.gov.br/content/publicacoes/Documents/reb/boxesreb2020/boxe_2_evolucao_portabilidade_credito_brasil.pdf" rel="noopener" class="text-sky-400 underline">Relatório de Economia Bancária de 2020</a>.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Como funciona</h2>
            <p>O banco novo quita o saldo devedor no banco de origem e passa a ser o seu credor, com a taxa e o prazo que propuser. Ele faz a própria análise de crédito, então a aprovação não é garantida. O veículo continua como garantia do financiamento.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Quando vale a pena: a conta</h2>
            <p>Imagine que faltam 36 parcelas e o saldo devedor é de R$ 30.000. Com taxa de 2,20% ao mês, a parcela é de {formatar_reais(_PMT_P1)}. Se outro banco oferecer 1,80% ao mês no mesmo prazo, a parcela cai para {formatar_reais(_PMT_P2)}, uma economia de <strong class="text-white">{formatar_reais((_PMT_P1 - _PMT_P2) * 36)}</strong> ao longo dos 36 meses (exemplo ilustrativo). Quanto menos parcelas faltam, menor tende a ser a economia, porque o saldo já é pequeno.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Passo a passo</h2>
            <p>1) Peça ao banco atual o saldo devedor e o CET do contrato. 2) Compare com propostas de outros bancos pelo <a href="aprenda-o-que-e-cet" class="text-sky-400 underline">CET</a>, não só pela taxa. 3) Use o <a href="comparador-carro-novo" class="text-sky-400 underline">comparador</a> e a página de <a href="taxas-financiamento-veiculos" class="text-sky-400 underline">taxas mês a mês</a> para ter referência. 4) Se o banco de origem criar dificuldades, registre reclamação no Banco Central e no Procon.</p>
        </div>
        <p class="text-xs text-slate-500">Exemplo calculado como no simulador, sem IOF, tarifas e seguro; não é oferta de crédito. Fonte: Resolução CMN 4.292/2013 (Banco Central do Brasil).</p>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Ver taxas dos bancos",
    },
    {
        "slug": "aprenda-score-e-taxa-financiamento-veiculo",
        "titulo_h1": "Score de crédito e a taxa do financiamento de veículo",
        "titulo_pagina": "Score de crédito e taxa do financiamento de veículo | Datalab Global",
        "meta_description": "Como o score e o Cadastro Positivo entram na taxa do financiamento de carro ou moto, o que você controla e quanto meio ponto de taxa muda a parcela.",
        "resumo_card": "Duas pessoas, o mesmo banco, taxas diferentes: veja o que é o score e quanto a taxa pesa no bolso.",
        "corpo_html": f'''<p>As taxas que mostramos aqui são <strong class="text-white">médias</strong> contratadas por cada banco, divulgadas pelo Banco Central. A taxa da sua proposta pode ser maior ou menor, porque o banco avalia o risco de cada cliente. Uma das informações usadas é o histórico de crédito, que os birôs resumem em uma nota, o score.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">O que é o Cadastro Positivo</h2>
            <p>O Cadastro Positivo foi criado pela Lei 12.414/2011 e reúne o histórico de pagamentos dos consumidores. Segundo o <a href="https://www.gov.br/pt-br/noticias/financas-impostos-e-gestao-publica/2020/01/cadastro-positivo-ja-esta-no-ar" rel="noopener" class="text-sky-400 underline">Portal Gov.br</a>, a inclusão é automática, e quem não quiser participar pode pedir a exclusão. Segundo o <a href="https://www.bcb.gov.br/content/publicacoes/Documents/outras_pub_alfa/analise_dos_efeitos_do_cadastro_positivo.pdf" rel="noopener" class="text-sky-400 underline">Banco Central</a>, os gestores de bancos de dados podem informar a nota de crédito, mas o histórico detalhado só pode ser disponibilizado com autorização prévia do consumidor. Sair do cadastro pode deixar os birôs sem dados para calcular a sua nota.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Quanto a taxa pesa no bolso</h2>
            <p>Num financiamento de R$ 50.000 em 48 meses, a 1,80% ao mês a parcela é de {formatar_reais(_PMT_S1)}; a 2,30% ao mês, de {formatar_reais(_PMT_S2)}. Em 48 meses, são <strong class="text-white">{formatar_reais((_PMT_S2 - _PMT_S1) * 48)}</strong> a mais por apenas 0,5 ponto percentual de taxa por mês (exemplo ilustrativo).</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">O que você controla</h2>
            <p>Pagar as contas em dia, regularizar dívidas em atraso e conferir se os seus dados nos birôs estão corretos. Os birôs não divulgam a fórmula do score, então desconfie de promessas de aumentar a nota rápido. Antes de assinar, peça propostas em mais de um banco e compare pelo <a href="aprenda-o-que-e-cet" class="text-sky-400 underline">CET</a>. Veja também a <a href="metodologia" class="text-sky-400 underline">metodologia</a> das nossas taxas.</p>
        </div>
        <p class="text-xs text-slate-500">Exemplo calculado como no simulador, sem IOF, tarifas e seguro; não é oferta de crédito. Fontes: Lei 12.414/2011; Portal Gov.br; Banco Central do Brasil.</p>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Comparar bancos",
    },
    {
        "slug": "aprenda-entrada-ideal-financiamento-veiculo",
        "titulo_h1": "Qual a entrada ideal no financiamento de veículo?",
        "titulo_pagina": "Entrada ideal no financiamento de veículo: a conta | Datalab Global",
        "meta_description": "Quanto dar de entrada no financiamento do carro ou da moto: veja como 20%, 30% e 50% mudam a parcela e o total de juros, com números.",
        "resumo_card": "Não existe um percentual ideal para todos. Veja o que a conta mostra para 20%, 30% e 50% de entrada.",
        "corpo_html": f'''<p>Não existe uma entrada ideal que sirva para todo mundo: o que existe é um equilíbrio entre pagar menos juros e manter dinheiro disponível. Cada banco define o mínimo que exige. Nas nossas simulações, usamos 20% para carro novo e 30% para carro usado e moto, uma convenção de mercado que ainda não confirmamos banco a banco, como explicamos na <a href="metodologia" class="text-sky-400 underline">metodologia</a>.</p>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">O que a conta mostra</h2>
            <p class="mb-4">Veículo de R$ 80.000, 48 meses, taxa de 2,00% ao mês (ilustrativa), Tabela Price:</p>
            <div class="overflow-x-auto rounded-xl border border-white/10"><table class="w-full text-xs text-slate-300">
                <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Entrada</th><th scope="col" class="px-2 py-2 text-right font-medium">Financiado</th><th scope="col" class="px-2 py-2 text-right font-medium">Parcela</th><th scope="col" class="px-2 py-2 text-right font-medium">Juros no total</th></tr></thead>
                <tbody>{_LINHAS_ENTRADA}</tbody></table></div>
            <p class="mt-4">Cada real a mais de entrada deixa de render juros por 48 meses. Mas a entrada é dinheiro que sai da sua reserva.</p>
        </div>
        <div class="border-t border-white/10 pt-6">
            <h2 class="font-serif text-xl text-white mb-3">Como decidir</h2>
            <p>Primeiro, a parcela precisa caber no orçamento: veja quanto de <a href="renda-para-financiar-veiculo" class="text-sky-400 underline">renda os bancos costumam exigir</a> para o valor que você quer. Depois, evite zerar a reserva de emergência para aumentar a entrada: um imprevisto sem reserva pode custar mais caro que os juros economizados. Por fim, simule os cenários no <a href="comparador-carro-novo" class="text-sky-400 underline">comparador</a> e compare o <a href="aprenda-o-que-e-cet" class="text-sky-400 underline">CET</a>, que inclui IOF, tarifas e seguro.</p>
        </div>
        <p class="text-xs text-slate-500">Exemplo calculado como no simulador, sem IOF, tarifas e seguro; não é oferta de crédito.</p>''',
        "cta_href": "comparador-carro-novo",
        "cta_texto": "Simular com a minha entrada",
    },
]


def gerar_pagina_sobre():
    """Página institucional "Sobre" — mesmo achado do projeto irmão (ver
    gerador.py:gerar_pagina_sobre): conteúdo financeiro (YMYL) é avaliado
    pelo Google com padrão de confiança mais alto que conteúdo comum, e
    sinais de quem está por trás do site (fundador, contato) pesam nisso.
    Conteúdo real fornecido pelo usuário (12/set/2026) — não inventado."""
    url_home = f"{DOMINIO}/"
    url_canonica = f"{DOMINIO}/sobre"
    titulo_pagina = "Sobre a Datalab Global | Simulador de Veículos"
    meta_description = (
        "Conheça a Datalab Global, criada por Rodolfo Delfino para resolver problemas reais com dados e IA, "
        "incluindo este simulador de financiamento de veículos."
    )
    schema_sobre = {
        "@context": "https://schema.org", "@type": "AboutPage", "url": url_canonica,
        "mainEntity": {
            "@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global", "url": "https://www.datalabglobal.com/",
            "founder": {"@type": "Person", "name": "Rodolfo Delfino"},
            "contactPoint": {"@type": "ContactPoint", "email": "contato@datalabglobal.com", "contactType": "customer service"},
        },
    }
    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_sobre])
    corpo = f'''<main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-3xl font-bold mb-8">Sobre a Datalab Global</h1>

        <div class="glass-panel-sky rounded-2xl p-6 md:p-10 space-y-6 text-slate-300 leading-relaxed">
            <p>A Datalab Global foi criada por <strong class="text-white">Rodolfo Delfino</strong> com um objetivo direto: usar dados e as melhores técnicas de inteligência artificial disponíveis hoje para facilitar a vida das pessoas. Isso já tomou forma de produtos bem diferentes entre si — de SaaS a jogos, de relatórios a sistemas de ERP — mas todos guiados pela mesma pergunta: <strong class="text-sky-400">qual dor podemos resolver hoje?</strong></p>

            <p>Este simulador de financiamento de veículos nasceu dessa mesma lógica. Em vez de taxa promocional de material de marketing, usamos a taxa média <strong class="text-white">real</strong> apurada pelo Banco Central do Brasil — atualizada semanalmente, a mesma fonte que qualquer analista de crédito consultaria. O objetivo é simples: você saber, antes de entrar num banco, quanto um financiamento realmente custa.</p>

            <div class="border-t border-white/10 pt-6">
                <h2 class="font-serif text-xl text-white mb-3">Como funciona a Datalab Global</h2>
                <p>Este site é mantido por indicação: quando você pede uma análise gratuita através dos nossos parceiros credenciados, podemos receber uma comissão — sem nenhum custo extra pra você. Não somos um banco nem instituição financeira, e nenhuma simulação aqui é uma oferta de crédito; é uma estimativa educativa baseada em dados reais de mercado.</p>
            </div>

            <div class="border-t border-white/10 pt-6">
                <h2 class="font-serif text-xl text-white mb-3">Contato</h2>
                <p>E-mail: <a href="mailto:contato@datalabglobal.com" class="text-sky-400 hover:text-sky-300 underline">contato@datalabglobal.com</a></p>
            </div>
        </div>

        <div class="flex flex-wrap gap-3 mt-8">
            <a href="/" class="bg-sky-500 hover:bg-sky-400 text-slate-950 px-6 py-3 rounded-full font-bold text-sm transition-all">Ir pro simulador</a>
        </div>
    </main>'''
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    {corpo}
    {render_footer()}
</body>
</html>'''


# ---------------------------------------------------------------------------
# sitemap.xml / robots.txt / llms.txt / _headers
# ---------------------------------------------------------------------------

def gerar_sitemap(urls, data_atualizacao):
    partes = ['<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    partes.append(f"  <url>\n    <loc>{DOMINIO}/</loc>\n    <lastmod>{data_atualizacao}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>")
    for url in urls:
        partes.append(f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{data_atualizacao}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>")
    partes.append('</urlset>')
    return "\n".join(partes)


def gerar_404():
    """Achado real (10/set/2026, checagem final pedida pelo usuário depois
    do primeiro deploy em produção): sem esse arquivo, o Cloudflare Pages
    cai no comportamento padrão de app single-page — qualquer URL sem
    arquivo correspondente (link quebrado, erro de digitação, `ads.txt`
    que nem existe de propósito) devolve a home inteira com status 200 em
    vez de um 404 de verdade. Confirmado ao vivo: `curl` numa URL
    inventada respondia 200 com o HTML da home. Isso é ruim pra SEO (o
    Google trata como "soft 404", sinal de conteúdo duplicado/qualidade
    baixa) e esconde link quebrado de verdade, que passaria a mostrar
    "200 OK" mesmo estando errado. Basta esse arquivo existir na raiz
    pro Cloudflare Pages servir ele com status 404 de verdade pra
    qualquer caminho sem match — mesmo mecanismo do projeto irmão
    (ver 404.html em pseo_simulador), adaptado pra identidade visual e
    copy do produto de veículo."""
    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Página não encontrada | Datalab Global</title>
    <meta name="description" content="Essa página não existe mais ou nunca existiu. Veja os comparadores de financiamento de veículo ou volte pra home do simulador.">
    <meta name="robots" content="noindex">
    <link rel="icon" href="favicon.ico?v=20261012" sizes="any">
    <link rel="icon" href="favicon-32.png?v=20261012" type="image/png" sizes="32x32">
    <link rel="icon" href="favicon-192.png?v=20261012" type="image/png" sizes="192x192">
    <link rel="apple-touch-icon" href="apple-touch-icon.png?v=20261012">
    <link rel="stylesheet" href="styles.css">
    {GOOGLE_FONTS_LINK_ASSINCRONO}
</head>
<body class="antialiased flex flex-col min-h-screen items-center justify-center text-center px-6">
    <a href="/" class="mb-10"><img src="logo-header.webp" alt="Datalab Global" width="168" height="54" class="w-auto mx-auto" style="height:54px;max-width:70vw"></a>
    <h1 class="font-serif text-3xl md:text-4xl font-bold mb-4">Página não encontrada</h1>
    <p class="text-slate-400 max-w-md mx-auto mb-8">Essa simulação não existe (ou não existe mais). Talvez o valor, prazo ou banco que você buscou não esteja na nossa grade — ou a página tenha sido removida.</p>
    <div class="flex flex-wrap gap-3 justify-center">
        <a href="/" class="bg-sky-500 hover:bg-sky-400 text-slate-950 px-6 py-3 rounded-full font-bold text-sm transition-all">Ir pra home</a>
        <a href="/comparador-carro-novo" class="border border-white/10 hover:border-sky-500/50 px-6 py-3 rounded-full font-bold text-sm transition-all">Ver comparador de carro novo</a>
    </div>
</body>
</html>'''


def gerar_robots_txt():
    return (
        "User-agent: *\nAllow: /\n\n"
        "User-agent: GPTBot\nAllow: /\n\n"
        "User-agent: ClaudeBot\nAllow: /\n\n"
        "User-agent: PerplexityBot\nAllow: /\n\n"
        "User-agent: Google-Extended\nAllow: /\n\n"
        f"Sitemap: {DOMINIO}/sitemap.xml\n"
    )


def gerar_llms_txt(total_paginas, data_atualizacao):
    return f"""# Datalab Global — Financiamento de Veículos

> Simulador de financiamento de veículos (carro novo, carro usado e moto) para os principais bancos do Brasil (Caixa, Banco do Brasil, Bradesco, Santander, Itaú, Banco Inter, C6 Bank, BV Financeira, Banco Pan, Omni Financeira, Banco Honda, Banco Yamaha). Taxas com base no Relatório de Taxas de Juros por Instituição Financeira do Banco Central. Calcula parcela (Tabela Price), CET estimado (incluindo IOF) e tabela de amortização.

Dados atualizados em: {data_atualizacao}
Total de páginas de simulação: {total_paginas}

## Páginas
- [Home]({DOMINIO}/)
- [Comparador Carro Novo]({DOMINIO}/{slug_comparador('novo')})
- [Comparador Carro Usado]({DOMINIO}/{slug_comparador('usado')})
- [Comparador Moto]({DOMINIO}/{slug_comparador('moto')})
- [Financiamento de veículo: parcela por valor e prazo]({DOMINIO}/financiamento-veiculos)
- [Dados abertos: taxas de financiamento por banco, série mensal em CSV e JSON]({DOMINIO}/dados-abertos)
- [Simulador de financiamento de veículos para incorporar no seu site (grátis)]({DOMINIO}/incorporar)
- [Imprensa: números atualizados para citar]({DOMINIO}/imprensa)
- [Taxas de financiamento de veículos mês a mês, desde 2024]({DOMINIO}/taxas-financiamento-veiculos)
- [Metodologia: fonte das taxas e fórmulas]({DOMINIO}/metodologia)
- [Renda necessária para financiar um veículo, por valor]({DOMINIO}/renda-para-financiar-veiculo)
- [Versão completa com os números atuais]({DOMINIO}/llms-full.txt)
- [Sitemap completo]({DOMINIO}/sitemap.xml)

## Sobre os dados
Taxa de juros e prazo máximo são específicos de cada instituição e categoria de veículo. Prazo máximo e entrada mínima seguem convenção geral de mercado (ainda não confirmada banco a banco em fonte oficial — ver bancos_veiculos.py). Cada página de simulação (padrão de URL: /financiamento-{{categoria}}-{{banco}}-{{valor}}-mil-{{prazo}}-meses) traz parcela, CET e tabela de amortização completa para o cenário daquele banco/valor/prazo específico. As taxas são simulações representativas, não uma cotação — a taxa final de cada cliente depende de fatores fora do nosso controle (relacionamento bancário, histórico de crédito, seguradora escolhida).
"""


def gerar_headers():
    """_headers (formato Cloudflare Pages) — mesma política de segurança
    do projeto irmão, auditada contra o que esta página de fato carrega
    (fonts.googleapis.com/gstatic.com; nenhum outro domínio externo nesta
    v1, sem AdSense ainda) + o beacon do Cloudflare Web Analytics (static.cloudflareinsights.com / cloudflareinsights.com),
    que o Pages injeta sozinho e o CSP antigo bloqueava (achado real 21/set/2026, console do navegador)."""
    return (
        "/*\n"
        "  X-Frame-Options: DENY\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()\n"
        "  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com https://cloud.umami.is; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src fonts.gstatic.com; "
        "img-src 'self' data: https:; connect-src 'self' https://cloudflareinsights.com https://cloud.umami.is https://api-gateway.umami.dev; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'\n\n"
        "/styles.css\n"
        "  Cache-Control: public, max-age=31536000, immutable\n\n"
        "/logo-header.webp\n"
        "  Cache-Control: public, max-age=86400, must-revalidate\n\n"
        "/logo-full.png\n"
        "  Cache-Control: public, max-age=86400, must-revalidate\n\n"
        "/og-image.png\n"
        "  Cache-Control: public, max-age=86400, must-revalidate\n\n"
        "/calculo.js\n"
        "  Cache-Control: public, max-age=3600, must-revalidate\n\n"
        "# /embed é feito para ficar dentro de <iframe> em outros sites: libera o enquadramento só\n"
        "# nesta rota (o resto do site segue com X-Frame-Options DENY e frame-ancestors 'none').\n"
        "# O '!' remove o cabeçalho herdado da regra /* antes de definir o específico.\n"
        "/embed\n"
        "  ! X-Frame-Options\n"
        "  ! Content-Security-Policy\n"
        "  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; connect-src 'none'; frame-ancestors *; base-uri 'self'; form-action 'none'\n"
        "  Cache-Control: public, max-age=3600, must-revalidate\n"
    )


# ---------------------------------------------------------------------------
# Orquestração
# ---------------------------------------------------------------------------

def gerar_site(pasta_saida='paginas_seo'):
    os.makedirs(pasta_saida, exist_ok=True)
    data_atualizacao = obter_data_ultima_atualizacao()

    paginas = gerar_grade_paginas()
    lookup = montar_lookup(paginas)

    urls_sitemap = []

    for p in paginas:
        html = gerar_pagina_individual(p, paginas, lookup, data_atualizacao)
        with open(os.path.join(pasta_saida, f"{p['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(corrigir_concordancia(html))
        urls_sitemap.append(f"{DOMINIO}/{p['slug']}")

    hubs = {}
    for p in paginas:
        hubs.setdefault((p["categoria"], p["banco"]), []).append(p)
    for (categoria, banco), paginas_banco in hubs.items():
        banco_exib = paginas_banco[0]["nome_exibicao"]
        slug_pagina, html = gerar_hub(categoria, banco, banco_exib, paginas_banco, data_atualizacao)
        with open(os.path.join(pasta_saida, f"{slug_pagina}.html"), "w", encoding="utf-8") as f:
            f.write(corrigir_concordancia(html))
        urls_sitemap.append(f"{DOMINIO}/{slug_pagina}")

    for categoria in CATEGORIAS:
        slug_pagina, html = gerar_comparador(categoria, lookup, data_atualizacao)
        with open(os.path.join(pasta_saida, f"{slug_pagina}.html"), "w", encoding="utf-8") as f:
            f.write(corrigir_concordancia(html))
        urls_sitemap.append(f"{DOMINIO}/{slug_pagina}")

    urls_comparacao = gerar_paginas_comparacao(pasta_saida, data_atualizacao, lookup)
    urls_sitemap.extend(urls_comparacao)
    urls_sitemap.extend(gerar_dados_abertos(pasta_saida, data_atualizacao))
    gerar_embed(pasta_saida, data_atualizacao)
    urls_sitemap.extend(gerar_pagina_incorporar(pasta_saida, data_atualizacao))
    urls_sitemap.extend(gerar_pagina_imprensa(pasta_saida, data_atualizacao))
    urls_sitemap.extend(gerar_paginas_mensais(pasta_saida, data_atualizacao, historico_cache()))
    urls_sitemap.extend(gerar_pagina_metodologia(pasta_saida, data_atualizacao))
    urls_sitemap.extend(gerar_paginas_renda(pasta_saida, data_atualizacao))
    gerar_llms_full_txt(pasta_saida, data_atualizacao, historico_cache())
    gerar_medicao_js(pasta_saida)

    with open(os.path.join(pasta_saida, "index.html"), "w", encoding="utf-8") as f:
        f.write(gerar_index(data_atualizacao))

    with open(os.path.join(pasta_saida, "sobre.html"), "w", encoding="utf-8") as f:
        f.write(gerar_pagina_sobre())
    urls_sitemap.append(f"{DOMINIO}/sobre")

    for art in ARTIGOS_APRENDA:
        with open(os.path.join(pasta_saida, f"{art['slug']}.html"), "w", encoding="utf-8") as f:
            f.write(gerar_pagina_aprenda(art, data_atualizacao))
        urls_sitemap.append(f"{DOMINIO}/{art['slug']}")

    slug_aprenda, html_aprenda = gerar_hub_aprenda(ARTIGOS_APRENDA, data_atualizacao)
    with open(os.path.join(pasta_saida, f"{slug_aprenda}.html"), "w", encoding="utf-8") as f:
        f.write(html_aprenda)
    urls_sitemap.append(f"{DOMINIO}/{slug_aprenda}")

    # Logo oficial (21/set/2026): logo-full.png, favicon*.png/.ico, apple-touch-icon.png, logo-schema.png e og-image.png sao
    # arquivos ESTATICOS comitados em paginas_seo/ (ver projeto datalab-global-hub/make_logo_assets.py); logo.svg/favicon.svg aposentados.
    # rasterizar_favicon_png() NÃO roda aqui: mesmo motivo do projeto
    # irmão (ver comentário em gerador.py) — favicon.ico/apple-touch-
    # icon.png/logo-schema.png dependem de svglib/reportlab (não é
    # dependência do site em si) e não mudam a cada build, só quando o
    # desenho do ícone muda. Rodar rasterizar_favicon_png(pasta_saida) à
    # mão e comitar os 3 arquivos como estático, igual ao irmão.

    with open(os.path.join(pasta_saida, "calculo.js"), "w", encoding="utf-8") as f:
        f.write(gerar_calculo_js())

    with open(os.path.join(pasta_saida, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(gerar_sitemap(urls_sitemap, data_atualizacao))

    with open(os.path.join(pasta_saida, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(gerar_robots_txt())

    with open(os.path.join(pasta_saida, "404.html"), "w", encoding="utf-8") as f:
        f.write(gerar_404())

    with open(os.path.join(pasta_saida, "llms.txt"), "w", encoding="utf-8") as f:
        f.write(gerar_llms_txt(len(paginas), data_atualizacao))

    with open(os.path.join(pasta_saida, "_headers"), "w", encoding="utf-8") as f:
        f.write(gerar_headers())

    total_arquivos = len(paginas) + len(hubs) + len(CATEGORIAS) + 1
    print(f"Gerado: {len(paginas)} páginas individuais, {len(hubs)} hubs, {len(CATEGORIAS)} comparadores, "
          f"1 index — {total_arquivos} páginas HTML no total, em '{pasta_saida}/'.")
    return paginas


if __name__ == "__main__":
    gerar_site()
