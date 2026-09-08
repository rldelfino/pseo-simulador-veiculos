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

import json
import math
import os
from datetime import date, datetime

from bancos_veiculos import (
    BANCOS_VEICULOS,
    bancos_para_categoria,
    entrada_minima,
    normalizar_chave,
    obter_regra,
)
from icones import icone, tooltip

DOMINIO = 'https://veiculos.datalabglobal.com'

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
    lo, hi = 0.0, 0.08
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
    let lo = 0, hi = 0.08;
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

        const tabela = gerarTabelaAmortizacao(financiado, prazo, dados.taxaAm);
        const tbodyVisivel = document.getElementById('tabela_visivel');
        const tbodyResto = document.getElementById('tabela_resto');
        const blocoResto = document.getElementById('bloco_tabela_resto');
        const resumoResto = document.getElementById('resumo_tabela_resto');
        if (tbodyVisivel) tbodyVisivel.innerHTML = tabela.slice(0, 6).map(linhaTabelaHtml).join('');
        if (tbodyResto) tbodyResto.innerHTML = tabela.slice(6).map(linhaTabelaHtml).join('');
        if (blocoResto) blocoResto.hidden = tabela.length <= 6;
        if (resumoResto) resumoResto.innerText = 'Ver tabela completa (' + prazo + ' meses)';

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


def render_head(titulo, meta_description, url_canonica, json_ld_blocos):
    if len(meta_description) > 160:
        meta_description = meta_description[:157].rstrip() + "..."
    return f'''<meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{titulo}</title>
    <meta name="description" content="{meta_description}">
    <link rel="canonical" href="{url_canonica}" />
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="icon" href="favicon.ico" sizes="16x16 32x32 48x48">
    <link rel="apple-touch-icon" href="apple-touch-icon.png">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <meta property="og:type" content="website">
    <meta property="og:locale" content="pt_BR">
    <meta property="og:site_name" content="Datalab Global">
    <meta property="og:title" content="{titulo}">
    <meta property="og:description" content="{meta_description}">
    <meta property="og:url" content="{url_canonica}">
    <meta property="og:image" content="{DOMINIO}/logo.svg">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{titulo}">
    <meta name="twitter:description" content="{meta_description}">
    <link rel="stylesheet" href="styles.css?v={VERSAO_BUILD}">
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    {render_json_ld(*json_ld_blocos)}'''


def render_nav():
    return f'''<nav class="border-b border-white/5 sticky top-0 z-50 backdrop-blur-2xl bg-slate-950/50">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
            <a href="index.html" class="flex items-center"><img src="logo.svg" alt="Datalab Global" class="h-8 w-auto"></a>
            <div class="flex items-center gap-2">
                <a href="index.html" class="inline-flex items-center gap-1.5 -my-2.5 p-2.5 text-xs text-slate-400 hover:text-sky-400 transition-colors">{icone('home')} <span class="hidden sm:inline">Início</span></a>
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
    if mensagem is None:
        mensagem = (
            f"Nas condições simuladas, o CET no mercado costuma variar entre "
            f"<strong class='text-sky-400'>{cet_min_fmt}%</strong> e "
            f"<strong class='text-sky-400'>{cet_max_fmt}%</strong> — aqui no {banco_exib} está em "
            f"{cet_banco_fmt}%. Encontrar e negociar manualmente a melhor condição pode levar semanas de idas "
            f"e vindas ao banco."
        )
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
            <div class="flex justify-between text-[10px] text-slate-500 uppercase tracking-wide">
                <span id="faixa_min">{cet_min_fmt}% menor CET</span>
                <span id="faixa_max">{cet_max_fmt}% maior CET</span>
            </div>
        </div>
        <p class="text-slate-300 text-xs font-light leading-relaxed mt-4" id="faixa_texto">
            {mensagem}
            <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="text-sky-400 underline hover:text-sky-300 block mt-2 font-semibold">É esse trabalho que fazemos por você, sem custo →</a>
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
    return '''<footer class="border-t border-white/5 mt-16 py-8">
        <div class="max-w-5xl mx-auto px-4 sm:px-6 text-center text-xs text-slate-500 leading-relaxed">
            <p>Datalab Global — simulações educativas de financiamento de veículos, não são uma oferta de crédito nem substituem a proposta oficial do banco.</p>
            <p class="mt-1">Taxas com base em dados reais do Banco Central do Brasil (Relatório de Taxas de Juros por Instituição Financeira). CET estimado inclui IOF (alíquota de lei), tarifa de registro de contrato e seguro prestamista típicos de mercado — a taxa final de cada cliente varia com relacionamento bancário, histórico de crédito e seguradora escolhida.</p>
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
    return f'<nav class="text-xs text-slate-500 mb-6 flex flex-wrap items-center gap-1.5" aria-label="breadcrumb">{separador.join(partes)}</nav>'


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

    valor_curto = formatar_valor_curto(valor)
    total_pago = parcela * prazo
    total_juros = total_pago - financiado
    renda_sugerida = calcular_renda_sugerida(parcela)
    label_categoria = CATEGORIA_LABEL[categoria]
    url_canonica = f"{DOMINIO}/{p['slug']}.html"
    href_hub = f"{slug_hub(categoria, banco)}.html"
    href_comparador = f"{slug_comparador(categoria)}.html"

    titulo_pagina = f"Financiamento {label_categoria} {banco_exib}: {valor_curto} em {prazo}x | Simulador Datalab"
    meta_description = (
        f"Simule o financiamento de {CATEGORIA_ARTIGO[categoria]} de {formatar_reais(valor)} pelo {banco_exib} "
        f"em {prazo} meses: parcela de {formatar_reais(parcela)}, CET estimado {cet:.2f}% a.a., "
        f"com base na taxa média real do Banco Central."
    )

    faq_q1 = f"O que é o CET no financiamento {label_categoria.lower()} do {banco_exib}?"
    faq_a1 = (f"CET (Custo Efetivo Total) é o custo real do financiamento — inclui a taxa de juros, o IOF "
              f"(imposto sobre a operação de crédito) e tarifas, não só a taxa anunciada. Neste cenário, o CET "
              f"estimado é {cet:.2f}% ao ano, acima da taxa nominal de {taxa_aa:.2f}% ao ano.")
    faq_q2 = f"Por que a parcela do {banco_exib} é fixa do início ao fim?"
    faq_a2 = ("Financiamento de veículo no Brasil (CDC) usa a Tabela Price: a parcela é fixa do primeiro ao "
              "último mês, mudando só a proporção entre juros e amortização a cada mês. É diferente do SAC do "
              "financiamento imobiliário, onde a parcela começa mais alta e cai com o tempo.")
    faq_q3 = "A taxa exibida é exatamente o que eu vou pagar?"
    faq_a3 = (f"Não necessariamente — é a taxa média real praticada pelo {banco_exib} nessa modalidade, segundo "
              f"o Banco Central, não uma proposta. A taxa final de cada cliente varia com relacionamento "
              f"bancário, histórico de crédito, entrada e seguradora escolhida.")

    schema_faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": faq_q1, "acceptedAnswer": {"@type": "Answer", "text": faq_a1}},
            {"@type": "Question", "name": faq_q2, "acceptedAnswer": {"@type": "Answer", "text": faq_a2}},
            {"@type": "Question", "name": faq_q3, "acceptedAnswer": {"@type": "Answer", "text": faq_a3}},
        ],
    }
    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/index.html"},
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
        f'<a href="{q["slug"]}.html" class="px-3 py-2 rounded-lg border border-white/10 hover:border-sky-500/50 text-xs transition-all whitespace-nowrap">{q["prazo"]}x de {formatar_reais(q["parcela"])}</a>'
        for q in outros_prazos
    )

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

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_faq, schema_breadcrumb, schema_software])
    breadcrumb = render_breadcrumb([
        ("Datalab Global", "index.html"),
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
                <span class="text-[10px] text-slate-500 uppercase tracking-widest border-l border-white/10 pl-2">CDC {label_categoria}</span>
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
            <p class="text-slate-500 text-[11px] mb-8 pb-4 border-b border-white/10 relative z-10">Defina os parâmetros do seu financiamento {banco_exib.lower()}.</p>
            <div class="flex flex-col lg:flex-row lg:items-start gap-10 relative z-10">
                <div class="w-full lg:w-1/2 space-y-4">
                    <div class="bg-slate-800/60 p-5 rounded-2xl border border-white/10 shadow-md shadow-black/20 hover:border-sky-500/30 transition-colors">
                        <div class="flex justify-between items-end mb-2">
                            <label class="text-[10px] font-semibold text-slate-400 uppercase tracking-widest flex items-center">
                                {icone('car' if categoria != 'moto' else 'motorcycle', 'mr-1.5 text-slate-500')} Valor do Veículo
                                {tooltip('A partir dele calculamos a entrada mínima e o valor financiado, usando a regra de entrada da categoria (' + f'{int(entrada_minima(categoria)*100)}' + '%).')}
                            </label>
                            <input type="text" id="input_valor" class="currency-input w-40 text-right bg-transparent font-medium text-white text-2xl outline-none border-b border-transparent focus:border-sky-500 transition-colors" value="{formatar_reais(valor)[3:]}">
                        </div>
                        <input type="range" id="slider_valor" min="{valor_min_slider}" max="{valor_max_slider}" step="{passo_slider}" value="{valor}" class="w-full mt-2">
                    </div>
                    <div class="bg-slate-800/60 p-5 rounded-2xl border border-white/10 shadow-md shadow-black/20 hover:border-sky-500/30 transition-colors">
                        <div class="flex justify-between items-end mb-2">
                            <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center">
                                {icone('calendar', 'mr-1.5 text-slate-500')} Prazo
                                {tooltip(f'Quantidade de parcelas mensais. O {banco_exib} permite no máximo {p["prazo_max_banco"]} meses nessa modalidade.')}
                            </label>
                            <span id="label_prazo" class="font-medium text-white text-lg">{prazo} meses</span>
                        </div>
                        <input type="range" id="slider_prazo" min="12" max="{p['prazo_max_banco']}" step="1" value="{prazo}" class="w-full mt-2">
                    </div>
                    <p class="text-[10px] text-slate-500 pl-2">Entrada mínima da categoria: {int(entrada_minima(categoria)*100)}% do valor do veículo.</p>
                    <div class="bg-slate-800/60 p-5 rounded-2xl border border-white/10 shadow-md shadow-black/20 flex flex-wrap items-start justify-between gap-6">
                        <div>
                            <p class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center">
                                CET Real (a.a.)
                                {tooltip('Custo Efetivo Total: a taxa de juros somada ao IOF, à tarifa de registro de contrato e ao seguro prestamista típico de mercado. É o número mais honesto pra comparar o custo entre bancos diferentes.')}
                            </p>
                            <p class="text-white font-medium text-lg" id="res_cet">{cet:.2f}% a.a.</p>
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
                            <div><p class="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-1.5">Valor Financiado</p><p class="text-white font-medium text-lg currency-input" id="res_financiado">{formatar_reais(financiado)}</p></div>
                            <div><p class="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-1.5">Entrada</p><p class="text-white font-medium text-lg currency-input" id="res_entrada">{formatar_reais(entrada)}</p></div>
                            <div><p class="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-1.5">Total Pago</p><p class="text-white font-medium text-lg currency-input" id="res_total_pago">{formatar_reais(total_pago)}</p></div>
                            <div><p class="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-1.5">Total de Juros</p><p class="text-white font-medium text-lg currency-input" id="res_total_juros">{formatar_reais(total_juros)}</p></div>
                        </div>
                        <div class="pt-6 border-t border-white/5">
                            <p class="text-slate-500 text-[10px] font-bold uppercase tracking-widest mb-3">Composição do custo total</p>
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

        {"".join([f'''<div class="mt-8"><h2 class="font-serif text-lg font-semibold mb-3">Outros prazos no {banco_exib}</h2><div class="flex flex-wrap gap-2">{outros_prazos_html}</div></div>'''] ) if outros_prazos_html else ""}

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
                        <input type="text" id="input_amortizar" class="currency-input w-full bg-black/50 border border-sky-500/30 rounded-2xl pl-16 pr-4 py-5 focus:border-sky-400 font-medium text-sky-400 text-4xl outline-none transition-all shadow-[inset_0_2px_10px_rgba(0,0,0,0.5)]" value="{aporte_padrao_fmt}">
                    </div>
                    <input type="range" id="slider_amortizar" min="0" max="{slider_amortizar_max}" step="100" value="{aporte_padrao}" class="w-full mb-6">
                    <div class="bg-slate-800/60 p-4 rounded-2xl border border-white/10">
                        <label class="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2 flex items-center">
                            {icone('repeat', 'mr-1.5 text-slate-500')} A Cada Quantos Meses?
                        </label>
                        <div class="flex items-center gap-3">
                            <input type="range" id="slider_periodicidade" min="1" max="24" step="1" value="{periodicidade_padrao}" class="w-full">
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
            <a href="{href_comparador}" class="inline-flex items-center gap-1.5 mt-3 text-xs text-slate-500 hover:text-sky-400 transition-colors">Ver ranking completo de {label_categoria.lower()} {icone('arrow-right')}</a>
        </section>

        <!-- ZONA E: GLOSSÁRIO / HUB DE AJUDA -->
        <div class="mt-16">
            <div class="flex items-center gap-3 mb-2 justify-center">
                {icone('book-open', 'text-sky-500 text-xl')}
                <h3 class="text-2xl font-serif text-white text-center">Entenda os Termos Antes de Decidir</h3>
            </div>
            <p class="text-slate-500 text-sm text-center max-w-2xl mx-auto mb-8">
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
                    <p class="text-slate-300 text-sm font-light leading-relaxed">A taxa de {taxa_aa:.2f}% a.a. mostrada aqui é a taxa média efetivamente contratada pelo {banco_exib} nessa modalidade, apurada mensalmente pelo Banco Central (BACEN) — não é uma taxa promocional "a partir de". Sua taxa final depende do seu relacionamento com o banco e da análise de crédito.</p>
                </div>
                <div class="py-5 pb-0 md:pb-0 md:border-b md:border-white/10">
                    <p class="text-sky-400 font-bold text-xs uppercase tracking-widest mb-2 flex items-center">{icone('percent', 'mr-2')} Renda Mínima Necessária</p>
                    <p class="text-slate-300 text-sm font-light leading-relaxed">Os bancos não aprovam um financiamento cuja parcela ultrapasse 30% da sua renda familiar bruta mensal. Boa notícia: você pode somar a sua renda com a do cônjuge ou companheiro(a) para atingir esse limite.</p>
                </div>
            </div>
        </div>

        <!-- ZONA D: FAQ VISUAL -->
        <div class="mt-16 mb-8">
            <h3 class="text-2xl font-serif text-white mb-6 text-center">Perguntas Frequentes</h3>
            <div class="space-y-3 max-w-3xl mx-auto">
                <details class="group bg-white/5 border border-white/10 rounded-xl overflow-hidden open:border-sky-500/30 transition-colors">
                    <summary class="cursor-pointer list-none p-5 flex items-center justify-between gap-4">
                        <h4 class="text-sky-400 font-bold text-sm">{faq_q1}</h4>
                        <span class="faq-toggle-icon shrink-0 text-slate-500 group-open:rotate-45 transition-transform text-lg leading-none">+</span>
                    </summary>
                    <p class="text-slate-300 text-sm font-light leading-relaxed px-5 pb-5">{faq_a1}</p>
                </details>
                <details class="group bg-white/5 border border-white/10 rounded-xl overflow-hidden open:border-sky-500/30 transition-colors">
                    <summary class="cursor-pointer list-none p-5 flex items-center justify-between gap-4">
                        <h4 class="text-sky-400 font-bold text-sm">{faq_q2}</h4>
                        <span class="faq-toggle-icon shrink-0 text-slate-500 group-open:rotate-45 transition-transform text-lg leading-none">+</span>
                    </summary>
                    <p class="text-slate-300 text-sm font-light leading-relaxed px-5 pb-5">{faq_a2}</p>
                </details>
                <details class="group bg-white/5 border border-white/10 rounded-xl overflow-hidden open:border-sky-500/30 transition-colors">
                    <summary class="cursor-pointer list-none p-5 flex items-center justify-between gap-4">
                        <h4 class="text-sky-400 font-bold text-sm">{faq_q3}</h4>
                        <span class="faq-toggle-icon shrink-0 text-slate-500 group-open:rotate-45 transition-transform text-lg leading-none">+</span>
                    </summary>
                    <p class="text-slate-300 text-sm font-light leading-relaxed px-5 pb-5">{faq_a3}</p>
                </details>
            </div>
        </div>
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
    url_canonica = f"{DOMINIO}/{slug_pagina}.html"
    href_comparador = f"{slug_comparador(categoria)}.html"
    dados_banco = obter_regra(banco)

    titulo_pagina = f"Financiamento {label_categoria} {banco_exib}: todas as simulações | Datalab"
    meta_description = (
        f"Todas as simulações de financiamento {label_categoria.lower()} do {banco_exib}: taxa média real de "
        f"{dados_banco['taxa_am']:.2f}% a.m., prazo até {dados_banco['prazo_max']} meses, parcelas por valor e prazo."
    )

    paginas_por_valor = {}
    for p in sorted(paginas_banco, key=lambda p: (p["valor_veiculo"], p["prazo"])):
        paginas_por_valor.setdefault(p["valor_veiculo"], []).append(p)

    blocos_valor = []
    for valor, paginas in paginas_por_valor.items():
        links = "\n".join(
            f'<a href="{p["slug"]}.html" class="flex items-center justify-between p-3 rounded-lg border border-white/10 hover:border-sky-500/50 hover:bg-white/5 transition-all">'
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

    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/index.html"},
            {"@type": "ListItem", "position": 2, "name": label_categoria, "item": f"{DOMINIO}/{href_comparador}"},
            {"@type": "ListItem", "position": 3, "name": banco_exib, "item": url_canonica},
        ],
    }

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_breadcrumb])
    breadcrumb = render_breadcrumb([("Datalab Global", "index.html"), (label_categoria, href_comparador), (banco_exib, None)])

    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Financiamento {label_categoria} pelo {banco_exib}</h1>
        <p class="text-slate-400 text-sm mb-8">Taxa média real: {dados_banco['taxa_am']:.2f}% a.m. ({dados_banco['taxa_aa']:.2f}% a.a.) · Prazo máximo: {dados_banco['prazo_max']} meses. Escolha um valor e prazo para ver a simulação completa.</p>

        <div class="mb-8">{faixa_html}</div>

        <div class="grid sm:grid-cols-2 gap-4">{grade_html}</div>
        <a href="{href_comparador}" class="inline-flex items-center gap-1.5 mt-8 text-xs text-slate-500 hover:text-sky-400 transition-colors">Ver ranking completo de {label_categoria.lower()} {icone('arrow-right')}</a>
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

def gerar_comparador(categoria, lookup, data_atualizacao):
    label_categoria = CATEGORIA_LABEL[categoria]
    slug_pagina = slug_comparador(categoria)
    url_canonica = f"{DOMINIO}/{slug_pagina}.html"
    valor_referencia = VALORES_POR_CATEGORIA[categoria][len(VALORES_POR_CATEGORIA[categoria]) // 2]
    prazo_referencia = 48

    titulo_pagina = f"Comparador de Financiamento {label_categoria}: menor taxa entre os bancos | Datalab"
    meta_description = (
        f"Compare a taxa real de todos os bancos para financiamento {label_categoria.lower()} — cenário de "
        f"referência: {formatar_valor_curto(valor_referencia)} em {prazo_referencia} meses. Dados do Banco Central."
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
        marcadores.append(
            f'<div class="absolute top-1/2 z-10 rounded-full bg-slate-950 border-2 border-white shadow-[0_1px_4px_rgba(0,0,0,0.4)] p-0.5" '
            f'style="left:{pct}%; transform:translate(-50%,-50%)" title="{r["nome_exibicao"]}: {r["cet"]:.2f}% CET">'
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
    linhas_lista = "\n".join(
        f'''<a href="{slug_hub(categoria, r["banco"])}.html" class="grid grid-cols-[1fr_110px_150px] items-center gap-3 p-3 rounded-lg border border-white/10 hover:border-sky-500/50 hover:bg-white/5 transition-all">
            <span class="flex items-center gap-2 min-w-0">
                {favicon_com_fallback(f"https://www.google.com/s2/favicons?domain={r['dominio_favicon']}&sz=64", r["nome_exibicao"], "w-5 h-5")}
                <span class="text-sm font-medium truncate">{r["nome_exibicao"]}</span>
            </span>
            <span class="text-xs text-slate-400 text-center">{r["taxa_am"]:.2f}% a.m.</span>
            <span class="text-sm text-slate-300 text-right">CET {r["cet"]:.2f}% a.a.</span>
        </a>'''
        for r in ranking
    )

    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/index.html"},
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

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_breadcrumb, schema_item_list])
    breadcrumb = render_breadcrumb([("Datalab Global", "index.html"), (label_categoria, None)])

    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <div class="flex items-center gap-4 mb-2">
            <div class="w-14 h-14 sm:w-16 sm:h-16 shrink-0">{ilustracao_categoria(categoria, f'il-grad-cmp-{categoria}')}</div>
            <h1 class="font-serif text-2xl sm:text-3xl font-bold">Comparador de Financiamento {label_categoria}</h1>
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
            <div class="flex justify-between text-[10px] text-slate-500 uppercase tracking-wide mb-6">
                <span>{cet_min:.2f}% menor CET</span>
                <span>{cet_max:.2f}% maior CET</span>
            </div>
            <a href="{LINK_FINANCIA_TUDO}" target="_blank" rel="noopener sponsored" class="inline-flex items-center justify-center bg-sky-500 hover:bg-sky-400 text-slate-950 font-bold px-8 py-3.5 rounded-2xl transition-all text-sm w-full shadow-[0_0_15px_rgba(14,165,233,0.3)]">
                Peça uma análise gratuita com essas condições {icone('arrow-right', 'ml-2')}
            </a>
        </section>

        <div class="grid gap-2">{linhas_lista}</div>
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

def gerar_index(data_atualizacao):
    url_home = f"{DOMINIO}/index.html"
    titulo_pagina = "Simulador de Financiamento de Veículos: Carro Novo, Usado e Moto | Datalab"
    meta_description = (
        "Compare taxas reais de financiamento de carro novo, carro usado e moto entre os principais bancos "
        "do Brasil, com dados do Banco Central. Simule parcela, CET e tabela de amortização."
    )

    cards = []
    for categoria in CATEGORIAS:
        label = CATEGORIA_LABEL[categoria]
        n_bancos = len(bancos_para_categoria(categoria))
        cards.append(f'''<a href="{slug_comparador(categoria)}.html" class="glass-panel-sky rounded-2xl p-6 hover:border-sky-500/40 transition-all group">
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
    }
    schema_organization = {
        "@context": "https://schema.org", "@type": "Organization",
        "name": "Datalab Global", "url": url_home, "logo": f"{DOMINIO}/logo-schema.png",
    }

    head = render_head(titulo_pagina, meta_description, url_home, [schema_breadcrumb, schema_website, schema_organization])
    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-3xl font-bold mb-2">Simulador de Financiamento de Veículos</h1>
        <p class="text-slate-400 text-sm mb-8">Escolha a categoria do seu veículo para comparar taxas reais e simular parcelas.</p>
        <div class="grid sm:grid-cols-3 gap-4">{cards_html}</div>
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


# ---------------------------------------------------------------------------
# sitemap.xml / robots.txt / llms.txt / _headers
# ---------------------------------------------------------------------------

def gerar_sitemap(urls, data_atualizacao):
    partes = ['<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    partes.append(f"  <url>\n    <loc>{DOMINIO}/index.html</loc>\n    <lastmod>{data_atualizacao}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>1.0</priority>\n  </url>")
    for url in urls:
        partes.append(f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{data_atualizacao}</lastmod>\n    <changefreq>monthly</changefreq>\n    <priority>0.8</priority>\n  </url>")
    partes.append('</urlset>')
    return "\n".join(partes)


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
- [Home]({DOMINIO}/index.html)
- [Comparador Carro Novo]({DOMINIO}/{slug_comparador('novo')}.html)
- [Comparador Carro Usado]({DOMINIO}/{slug_comparador('usado')}.html)
- [Comparador Moto]({DOMINIO}/{slug_comparador('moto')}.html)
- [Sitemap completo]({DOMINIO}/sitemap.xml)

## Sobre os dados
Taxa de juros e prazo máximo são específicos de cada instituição e categoria de veículo. Prazo máximo e entrada mínima seguem convenção geral de mercado (ainda não confirmada banco a banco em fonte oficial — ver bancos_veiculos.py). Cada página de simulação (padrão de URL: /financiamento-{{categoria}}-{{banco}}-{{valor}}-mil-{{prazo}}-meses.html) traz parcela, CET e tabela de amortização completa para o cenário daquele banco/valor/prazo específico. As taxas são simulações representativas, não uma cotação — a taxa final de cada cliente depende de fatores fora do nosso controle (relacionamento bancário, histórico de crédito, seguradora escolhida).
"""


def gerar_headers():
    """_headers (formato Cloudflare Pages) — mesma política de segurança
    do projeto irmão, auditada contra o que esta página de fato carrega
    (fonts.googleapis.com/gstatic.com; nenhum outro domínio externo nesta
    v1, sem AdSense ainda)."""
    return (
        "/*\n"
        "  X-Frame-Options: DENY\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()\n"
        "  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com; font-src fonts.gstatic.com; "
        "img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'\n\n"
        "/styles.css\n"
        "  Cache-Control: public, max-age=3600, must-revalidate\n\n"
        "/logo.svg\n"
        "  Cache-Control: public, max-age=3600, must-revalidate\n\n"
        "/calculo.js\n"
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
            f.write(html)
        urls_sitemap.append(f"{DOMINIO}/{p['slug']}.html")

    hubs = {}
    for p in paginas:
        hubs.setdefault((p["categoria"], p["banco"]), []).append(p)
    for (categoria, banco), paginas_banco in hubs.items():
        banco_exib = paginas_banco[0]["nome_exibicao"]
        slug_pagina, html = gerar_hub(categoria, banco, banco_exib, paginas_banco, data_atualizacao)
        with open(os.path.join(pasta_saida, f"{slug_pagina}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        urls_sitemap.append(f"{DOMINIO}/{slug_pagina}.html")

    for categoria in CATEGORIAS:
        slug_pagina, html = gerar_comparador(categoria, lookup, data_atualizacao)
        with open(os.path.join(pasta_saida, f"{slug_pagina}.html"), "w", encoding="utf-8") as f:
            f.write(html)
        urls_sitemap.append(f"{DOMINIO}/{slug_pagina}.html")

    with open(os.path.join(pasta_saida, "index.html"), "w", encoding="utf-8") as f:
        f.write(gerar_index(data_atualizacao))

    with open(os.path.join(pasta_saida, "logo.svg"), "w", encoding="utf-8") as f:
        f.write(gerar_logo_svg())

    gerar_favicon_svg(pasta_saida)
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
