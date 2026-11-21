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
import urllib.parse
import bancos_veiculos as _bancos_veiculos
import math
import os
import re
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
import lastmod

DOMINIO = 'https://veiculos.datalabglobal.com'

# Datas reais de modificação (ver lastmod.py): preenchido no início de gerar_site().
_MANIFESTO_LASTMOD = {}

# Fontes oficiais dos guias que só tinham o link do parceiro (13/nov/2026). Só entram links que foram abertos e
# lidos (ou cujo título a busca confirmou). O Google pergunta se o conteúdo mostra "clear sourcing" e trata
# finanças como YMYL; o Bing perde elegibilidade de páginas finas.
URL_CDC_PROCON = "https://www.procon.sp.gov.br/wp-content/uploads/2026/01/CDC-2026-site.pdf"
URL_RES_3517 = "https://www.bcb.gov.br/pre/normativos/res/2007/pdf/res_3517_v1_o.pdf"
FONTES_GUIAS = {
    "aprenda-amortizacao-extra-veiculo": [
        (URL_CDC_PROCON, "Código de Defesa do Consumidor (Lei 8.078/1990), art. 52, § 2º: liquidação antecipada do débito com redução proporcional dos juros (texto publicado pelo Procon-SP)"),
    ],
    "aprenda-quitacao-antecipada-financiamento-veiculo": [
        (URL_CDC_PROCON, "Código de Defesa do Consumidor (Lei 8.078/1990), art. 52, § 2º (texto publicado pelo Procon-SP)"),
    ],
    "aprenda-entrada-ideal-financiamento-veiculo": [
        ("https://www.bcb.gov.br/content/cidadaniafinanceira/documentos_cidadania/Cuidando_do_seu_dinheiro_Gestao_de_Financas_Pessoais/v4_modulo_3_caderno_educacao_financeira_430206_2026.pdf", "Banco Central, Caderno de Educação Financeira, módulo 3 (uso do crédito): exemplo de carro financiado com entrada e o peso dos juros"),
        ("https://idec.org.br/em-acao/em-foco/vai-comprar-um-carro-confira-as-dicas-para-fugir-do-endividamento", "Idec: Vai comprar um carro? Dicas para fugir do endividamento (entrada maior e prazo menor)"),
    ],
    "aprenda-financiamento-x-consorcio-veiculo": [
        ("https://aprendervalor.bcb.gov.br/content/estabilidadefinanceira/panoramaconsorcio/panorama_de_consorcios_2024.pdf", "Banco Central: Panorama do Sistema de Consórcios (dados de dezembro/2024)"),
    ],
    "aprenda-iof-financiamento-veiculo": [
        ("https://www.gov.br/pgfn/pt-br/cidadania-tributaria/por-assunto/outros-tributos-em-especie-1/iof-2/iof-e-contratos-de-emprestimo", "Procuradoria-Geral da Fazenda Nacional: IOF e contratos de empréstimo"),
    ],
    "aprenda-o-que-e-cdc": [
        ("https://www.procon.sp.gov.br/wp-content/uploads/files/CreditoDicaseOrientacoes.pdf", "Procon-SP: Alternativas de crédito, dicas e orientações (inclui o Crédito Direto ao Consumidor)"),
    ],
    "aprenda-o-que-e-cet": [
        (URL_RES_3517, "Banco Central, Resolução CMN nº 3.517/2007: informação e divulgação do Custo Efetivo Total (CET)"),
        ("https://www.bcb.gov.br/content/cidadaniafinanceira/documentos_cidadania/guia_de_excelencia/guia_de_excelencia_oferta_de_produtos_servi%C3%A7os_financeiros.pdf", "Banco Central, Cidadania Financeira: Guia de Excelência em oferta de produtos e serviços financeiros (o CET como \"preço\" do crédito)"),
    ],
    "aprenda-tabela-price": [
        ("https://caixanoticias.caixa.gov.br/Paginas/Not%C3%ADcias/2026/02-FEVEREIRO/SAC-ou-Price-entenda-as-diferen%C3%A7as-entre-os-sistemas-de-amortiza%C3%A7%C3%A3o-e-fa%C3%A7a-a-melhor-escolha.aspx", "CAIXA Notícias (fev/2026): SAC ou Price, entenda as diferenças entre os sistemas de amortização (a Price é a tabela de parcela fixa)"),
    ],
}


def html_fontes_guia(slug, fontes=None):
    fontes = fontes if fontes is not None else FONTES_GUIAS.get(slug)
    if not fontes:
        return ""
    lis = "".join(f'<li><a href="{u}" target="_blank" rel="noopener" class="text-sky-400 underline">{t}</a></li>' for u, t in fontes)
    return (f'<div class="border-t border-white/10 pt-6"><h2 class="font-serif text-xl text-white mb-3">Fontes e referências</h2>'
            f'<ul class="list-disc pl-6 space-y-1 text-sm">{lis}</ul></div>')
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
# O mesmo carimbo vai em calculo.js e medicao.js (a borda do Cloudflare também os segura por horas).
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

# As páginas "banco x valor x prazo" (840) e a comparação sem marca (80) saíram em 21/11/2026 (ver AVALIACAO-SUBPAGINAS.md): em 13/11 só 7 de
# 1.004 URLs do sitemap estavam indexadas e as consultas reais caem nos hubs de banco e nos comparadores. A grade abaixo só alimenta os hubs
# (parcelas por valor e prazo, com link para o simulador da home) e o mapa de redirecionamentos (o slug antigo de cada página removida).

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


# Enxugamento (21/11/2026): o Banco Central não separa carro novo de usado, então o hub de carro usado era o do carro novo com outro nome.
# Há um hub por banco para "carro novo e usado" (hub-<banco>-carro-novo) e outro para moto; o endereço antigo de carro usado redireciona.
HUB_ROTULO = {"novo": "Carro Novo e Usado", "usado": "Carro Novo e Usado", "moto": "Moto"}


def categoria_do_hub(categoria):
    return "novo" if categoria == "usado" else categoria


def slug_hub(categoria, banco):
    return f"hub-{slugificar_banco(banco)}-{CATEGORIA_SLUG[categoria_do_hub(categoria)]}"


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
    // Desempenho (02/nov/2026): fator de desconto incremental em vez de Math.pow por parcela e 36 iterações de
    // bisseção (precisão de ~2e-12 ao mês, além das 2 casas exibidas).
    const vpl = (r) => {
        const f = 1 / (1 + r);
        let d = 1, total = -valorLiquidoRecebido;
        for (let i = 0; i < fluxo.length; i++) { d *= f; total += fluxo[i] * d; }
        return total;
    };
    let lo = 0, hi = 0.15; // teto com margem de segurança maior — ver comentário em calcular_cet_veiculo (Python)
    for (let i = 0; i < 36; i++) {
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
    <link rel="icon" href="favicon.ico?v=20261120" sizes="any">
    <link rel="icon" href="favicon-32.png?v=20261120" type="image/png" sizes="32x32">
    <link rel="icon" href="favicon-192.png?v=20261120" type="image/png" sizes="192x192">
    <link rel="apple-touch-icon" href="apple-touch-icon.png?v=20261120">{_medicao_head}
    <link rel="alternate" type="application/atom+xml" title="Taxas de financiamento de veículos" href="/feed.xml">
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
                <a href="https://emprestimo.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Empréstimo com crédito do cartão</a>
                <a href="https://simulador.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Financiamento imobiliário</a>
                <a href="https://homeequity.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Home Equity</a>
                <a href="https://autoequity.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Auto Equity</a>
                <a href="https://condominio.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Empréstimo para Condomínios</a>
                <a href="https://dados.datalabglobal.com/" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Lente B2B: dados de empresas</a>
                <a href="/aprenda" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Aprenda</a>
                <a href="/sobre" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Sobre a Datalab Global</a>
                <a href="/metodologia" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Metodologia</a>
                <a href="/taxas-financiamento-veiculos" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Taxas mês a mês</a>
                <a href="/renda-para-financiar-veiculo" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">Renda para financiar</a>
                <a href="/atualizacoes" class="hover:text-sky-400 transition-colors uppercase tracking-widest text-[10px]">O que mudou esta semana</a>
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


# ---------------------------------------------------------------------------
# Página individual: financiamento-{categoria}-{banco}-{valor}-mil-{prazo}-meses.html
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Hub por banco+categoria: hub-{banco}-{categoria}.html
# ---------------------------------------------------------------------------

def schema_webpage(url, nome, descricao, data_atualizacao):
    """JSON-LD WebPage (04/11/2026): url, nome, data de modificação, site e publicador, para hubs, comparadores
    e home (as páginas que o Copilot mais cita, segundo o Bing > AI Performance)."""
    return {
        "@context": "https://schema.org", "@type": "WebPage", "url": url, "name": nome, "description": descricao,
        "inLanguage": "pt-BR", "dateModified": data_atualizacao,
        "isPartOf": {"@type": "WebSite", "url": f"{DOMINIO}/", "name": "Datalab Global"},
        "publisher": {"@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global"},
    }


def html_mais_sobre_banco(categoria, banco_exib):
    """Bloco 'Mais sobre {banco}' dos hubs: taxas mês a mês, renda necessária, comparador da categoria,
    metodologia e dois guias. Só links para páginas que existem."""
    label = CATEGORIA_LABEL[categoria].lower()
    meses = sorted({r["mes_referencia"] for r in historico_cache()})
    itens = []
    if meses:
        itens.append((slug_mes(meses[-1]), f"Taxas de financiamento de veículos em {nome_mes(meses[-1])}"))
    itens.append((SLUG_INDICE_MENSAL, "Taxas de financiamento de veículos mês a mês"))
    itens.append((SLUG_ATUALIZACOES, "O que mudou nas taxas esta semana"))
    itens.append((SLUG_INDICE_RENDA, "Renda para financiar veículo, por valor"))
    itens.append((slug_comparador(categoria), f"Comparar bancos para financiar {label}"))
    itens.append(("aprenda-o-que-e-cet", "O que é CET e por que olhar além da taxa"))
    itens.append(("aprenda-score-e-taxa-financiamento-veiculo", "Como o score afeta a taxa do financiamento"))
    itens.append(("metodologia", "Como calculamos e de onde vêm os dados"))
    links = "".join(f'<li><a href="{h}" class="text-sky-400 underline hover:text-sky-300">{t}</a></li>' for h, t in itens)
    return (f'<section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Mais sobre {banco_exib}</h2>'
            f'<ul class="space-y-2 text-sm">{links}</ul></section>')


def html_requisitos_aprovacao(categoria, banco_exib=None):
    """Bloco "Antes de pedir a proposta" (13/nov/2026). Achado real: no painel do parceiro, a maioria
    dos pedidos encerrados foi "cadastro recusado na análise" (17 de 30) ou fora das regras do produto.
    Só fatos gerais e conferíveis (Registrato do Banco Central, parcela até ~30% da renda, entrada,
    documentos); nada sobre regras internas do parceiro, e avisa que não há garantia de aprovação."""
    veiculo = {"novo": "carro novo", "usado": "carro usado", "moto": "moto"}[categoria]
    quem, verbo = (f"O {banco_exib}", "costuma") if banco_exib else ("Os bancos", "costumam")
    itens = [
        ("Histórico de crédito", 'Nome sem restrições ativas e dívidas em dia pesam mais na análise do que a taxa. Você pode consultar de graça o seu extrato de dívidas e financiamentos no <a href="https://www.bcb.gov.br/meubc/registrato" target="_blank" rel="noopener" class="text-sky-400 underline">Registrato, do Banco Central</a>.'),
        ("Parcela que cabe na renda", f"{quem} {verbo} limitar a parcela a cerca de 30% da renda bruta. Se a parcela passar disso, o pedido tende a ser recusado ou a exigir mais entrada ou menos parcelas. Dá para somar a renda do cônjuge ou companheiro(a)."),
        ("Entrada", "Quanto maior a entrada, menor o valor financiado e a parcela, o que costuma facilitar a análise."),
        ("Regras do veículo", f"Ano de fabricação, valor e tipo de {veiculo} aceitos variam por instituição. Se o pedido não se enquadrar nas regras do produto, a análise pode recusar mesmo com renda suficiente."),
        ("Documentos", "Costumam ser exigidos documento com foto, CPF, comprovante de renda e de residência. Confirme a lista com a instituição."),
    ]
    lis = "".join(f'<li><strong class="text-white">{t}.</strong> {d}</li>' for t, d in itens)
    return (f'<section id="antes-de-pedir" class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Antes de pedir a proposta: o que costuma pesar na aprovação</h2>'
            f'<ul class="space-y-2 text-sm text-slate-300 font-light leading-relaxed list-disc pl-5">{lis}</ul>'
            f'<p class="mt-3 text-xs text-slate-400">O pedido de proposta é analisado por um correspondente bancário parceiro e a aprovação depende da análise de crédito de cada instituição. Nenhuma simulação garante aprovação.</p></section>')


def periodo_taxa_bacen(banco=None):
    """Janela de 5 dias úteis do Banco Central de onde vem a taxa (ex.: '23/10 a 29/10/2026'), lida do cache do ETL.
    Sem banco, devolve o período mais comum do cache. Devolve None se não houver (o texto então só diz 'média do Banco Central').
    Por que existe (15/nov/2026): as páginas diziam 'taxa hoje', mas o dado é a última média semanal divulgada,
    com mais de uma semana de atraso; dizer 'hoje' num tema de dinheiro é afirmar o que não dá para sustentar."""
    try:
        with open(_bancos_veiculos._ARQUIVO_CACHE_TAXAS, encoding="utf-8") as f:
            cache = json.load(f)
    except (FileNotFoundError, ValueError):
        return None
    if banco is not None:
        bruto = cache.get(banco, {}).get("periodo")
    else:
        periodos = [v.get("periodo") for v in cache.values() if v.get("periodo")]
        bruto = max(set(periodos), key=periodos.count) if periodos else None
    if not bruto or " a " not in bruto:
        return None
    ini, fim = bruto.split(" a ", 1)
    if ini[-4:] == fim[-4:]:
        ini = ini[:-5]
    return f"{ini} a {fim}"


def link_simulador(categoria, valor, entrada, prazo, banco=None):
    """Endereço da home com a simulação preenchida (tipo, valor, entrada, prazo e banco), lido por src/home.js."""
    params = f"tipo={categoria}&amp;valor={int(round(valor))}&amp;entrada={int(round(entrada))}&amp;prazo={prazo}"
    if banco:
        params += "&amp;banco=" + urllib.parse.quote(banco)
    return f"/?{params}#simulador"


def gerar_hub(categoria, banco, banco_exib, paginas_banco, data_atualizacao):
    label_categoria = HUB_ROTULO[categoria]
    slug_pagina = slug_hub(categoria, banco)
    url_canonica = f"{DOMINIO}/{slug_pagina}"
    href_comparador = f"{slug_comparador(categoria)}"
    dados_banco = obter_regra(banco)
    # Ver nota de padrão brasileiro (vírgula decimal) em
    # gerar_pagina_individual — mesmo achado de auditoria, mesmo fix.
    taxa_am_fmt = f"{dados_banco['taxa_am']:.2f}".replace('.', ',')
    taxa_aa_fmt = f"{dados_banco['taxa_aa']:.2f}".replace('.', ',')

    # Achado real (04/11/2026, Bing Webmaster > AI Performance): o Copilot cita o site para "taxa financiamento carro
    # novo", "taxas de financiamento de veículos" e "comparar taxas financiamento carro". O título passa a trazer
    # "taxa" e o ano, sem passar de 60 caracteres (a marca sai primeiro, depois a palavra "simulador").
    ano_hub = date.fromisoformat(data_atualizacao).year if isinstance(data_atualizacao, str) else date.today().year
    candidatos_titulo = (
        f"Taxa de financiamento {label_categoria} {banco_exib} {ano_hub} | Datalab",
        f"Taxa de financiamento {label_categoria} {banco_exib}: simulador {ano_hub}",
        f"Taxa de financiamento {label_categoria} {banco_exib} {ano_hub}",
        f"Taxa financiamento {label_categoria} {banco_exib} {ano_hub}",
        f"Financiamento {label_categoria} {banco_exib}: simulações | Datalab",
        f"Financiamento {label_categoria} {banco_exib}",
    )
    titulo_pagina = next((t for t in candidatos_titulo if len(t) <= 60), candidatos_titulo[-1])
    periodo_txt = periodo_taxa_bacen(banco)
    ref_curta = f"média de {periodo_txt} (Banco Central)" if periodo_txt else "média do Banco Central"
    ref_longa = f"média contratada de {periodo_txt}, segundo o Banco Central" if periodo_txt else "média contratada, segundo o Banco Central"
    meta_description = (
        f"Taxa do {banco_exib} para {label_categoria.lower()}: {taxa_am_fmt}% ao mês ({taxa_aa_fmt}% ao ano), {ref_curta}. "
        f"Simulações até {dados_banco['prazo_max']} meses."
    )

    paginas_por_valor = {}
    for p in sorted(paginas_banco, key=lambda p: (p["valor_veiculo"], p["prazo"])):
        paginas_por_valor.setdefault(p["valor_veiculo"], []).append(p)

    blocos_valor = []
    for valor, paginas in paginas_por_valor.items():
        links = "\n".join(
            f'<a href="{link_simulador(categoria, p["valor_veiculo"], p["entrada"], p["prazo"], banco)}" class="flex items-center justify-between p-3 rounded-lg border border-white/10 hover:border-sky-500/50 hover:bg-white/5 transition-all">'
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

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_breadcrumb, schema_faq,
                                                                       schema_webpage(url_canonica, titulo_pagina, meta_description, data_atualizacao)])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), (label_categoria, href_comparador), (banco_exib, None)])

    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Financiamento {label_categoria} pelo {banco_exib}</h1>
        <p class="text-white text-lg font-medium mb-3">Taxa do {banco_exib} para {label_categoria.lower()}: {taxa_am_fmt}% ao mês ({taxa_aa_fmt}% ao ano), {ref_longa}.</p>
        <p class="text-slate-400 text-sm mb-8">Taxa média real: {taxa_am_fmt}% a.m. ({taxa_aa_fmt}% a.a.) · Prazo máximo: {dados_banco['prazo_max']} meses. Escolha um valor e prazo para ver a simulação completa.</p>

        <div class="mb-8">{faixa_html}</div>
        {html_serie_banco(historico_cache(), banco, banco_exib, dados_banco['taxa_am'])}
        {html_comparacao_mercado(categoria, banco, banco_exib, dados_banco, historico_cache())}

        <div class="grid sm:grid-cols-2 gap-4">{grade_html}</div>
        <a href="{href_comparador}" class="inline-flex items-center gap-1.5 mt-8 text-xs text-slate-400 hover:text-sky-400 transition-colors">Ver ranking completo de {label_categoria.lower()} {icone('arrow-right')}</a>
        {html_requisitos_aprovacao(categoria, banco_exib)}
        {html_mais_sobre_banco(categoria, banco_exib)}
        {html_como_citar(categoria, banco_exib, url_canonica, data_atualizacao)}
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
# Cópia do conjunto de dados no Kaggle (publicada em 04/11/2026).
URL_KAGGLE = "https://www.kaggle.com/datasets/rodolfodelfino/taxas-financiamento-de-veculos-por-banco-bacen"
URL_ZENODO_DOI = "https://doi.org/10.5281/zenodo.24295614"  # DOI do conceito: resolve sempre para a versão mais recente do dataset
URL_HUGGINGFACE = "https://huggingface.co/datasets/datalabglobal/taxas-financiamento-veiculos"
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
MESES_INDEXAVEIS_MENSAL = 2  # só os 2 meses mais recentes têm página; os mais antigos redirecionam (301) para o índice, que lista todos
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
    recentes = {r["mes_referencia"] for r in historico}
    recentes = set(sorted(recentes)[-MESES_INDEXAVEIS_MENSAL:])  # só os meses mais recentes têm página (os outros redirecionam ao índice)
    celulas = "".join(
        f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-1.5 text-left font-medium text-white whitespace-nowrap">'
        + (f'<a href="{slug_mes(m)}" class="hover:text-sky-400">{_rotulo_mes(m)}</a>' if m in recentes else _rotulo_mes(m))
        + f'</th><td class="px-2 py-1.5 text-right">{_pct2(t)}%</td></tr>' for m, t in reversed(pontos))
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


VALOR_ANALISE_HUB = 60_000
PRAZO_ANALISE_HUB = 48
KEYWORDS_DATASET = ["financiamento de veículos", "taxa de juros", "Banco Central", "CET", "carro novo", "carro usado", "moto", "Brasil", "dados abertos"]


def html_comparacao_mercado(categoria, banco, banco_exib, dados_banco, historico):
    """Análise própria do hub (15/nov/2026): taxa do banco frente à média simples dos bancos da categoria, quantos dos últimos meses
    ficou acima ou abaixo dela e o efeito em reais da diferença, com o mesmo cálculo do simulador (Tabela Price). Texto neutro:
    não ordena nem recomenda banco; os números mudam de banco para banco, o que também reduz o texto repetido entre hubs."""
    bancos = list(bancos_para_categoria(categoria))
    if len(bancos) < 3:
        return ""
    taxas = {b: obter_regra(b)["taxa_am"] for b in bancos}
    media = sum(taxas.values()) / len(taxas)
    taxa_banco = dados_banco["taxa_am"]
    dif = taxa_banco - media
    posicao = "igual à" if abs(dif) < 0.005 else (f"{_pct2(abs(dif))} p.p. acima da" if dif > 0 else f"{_pct2(abs(dif))} p.p. abaixo da")
    por_mes = {}
    for b in bancos:
        for m, t in serie_do_banco(historico, b):
            por_mes.setdefault(m, {})[b] = t
    acima = abaixo = 0
    for d in por_mes.values():
        if banco in d and len(d) >= 3:
            m_ = sum(d.values()) / len(d)
            acima += d[banco] > m_
            abaixo += d[banco] < m_
    hist = (f" Nos últimos {acima + abaixo} meses de dados do Banco Central, ficou acima dessa média em {acima} e abaixo em {abaixo}."
            if acima + abaixo >= 3 else "")
    prazo = min(PRAZO_ANALISE_HUB, dados_banco["prazo_max"])
    p_a = calcular_pmt_price(VALOR_ANALISE_HUB, prazo, taxa_banco)
    p_m = calcular_pmt_price(VALOR_ANALISE_HUB, prazo, media)
    j_a, j_m = p_a * prazo - VALOR_ANALISE_HUB, p_m * prazo - VALOR_ANALISE_HUB
    return f'''<section class="mt-8"><h2 class="font-serif text-lg font-semibold mb-3">O {banco_exib} frente à média dos bancos</h2>
        <div class="glass-panel rounded-2xl p-6 md:p-8">
            <p class="text-slate-400 text-xs mb-4">Análise própria com dados do Banco Central. Não é recomendação de banco.</p>
            <p class="text-slate-300 text-sm font-light leading-relaxed mb-4">Na média simples dos {len(bancos)} bancos desta categoria, a taxa média é de {_pct2(media)}% ao mês. A do {banco_exib} ({_pct2(taxa_banco)}%) está {posicao} média.{hist}</p>
            <p class="text-slate-300 text-sm font-light leading-relaxed"><strong class="text-white">Exemplo calculado</strong>, como no simulador ({formatar_reais(VALOR_ANALISE_HUB)} em {prazo} meses, Tabela Price, sem IOF, tarifas e seguro): com a taxa do {banco_exib}, a parcela é de {formatar_reais(p_a)} e os juros somam {formatar_reais(j_a)}; com a taxa média dos bancos, {formatar_reais(p_m)} e {formatar_reais(j_m)}. A diferença é de {formatar_reais(abs(p_a - p_m))} por mês e {formatar_reais(abs(j_a - j_m))} nos juros do contrato. A sua taxa depende da análise do banco.</p>
        </div></section>'''


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
        if mes not in recentes:
            continue
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
        if k > 0 and meses[k - 1] in recentes:
            vizinhos += f'<a href="{slug_mes(meses[k - 1])}" class="underline hover:text-sky-400">← {nome_mes(meses[k - 1])}</a>'
        if k + 1 < len(meses) and meses[k + 1] in recentes:
            vizinhos += f' &nbsp;·&nbsp; <a href="{slug_mes(meses[k + 1])}" class="underline hover:text-sky-400">{nome_mes(meses[k + 1])} →</a>'
        cobertura = [(r["inicio_periodo"], r["fim_periodo"]) for r in historico if r["mes_referencia"] == mes]
        schema_dados = {
            "@context": "https://schema.org", "@type": "Dataset", "keywords": KEYWORDS_DATASET, "name": f"Taxas do financiamento de veículos por banco em {mes_ano}",
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
        (f'<li><a href="{slug_mes(m)}" class="text-sky-400 underline hover:text-sky-300">Taxa de financiamento de veículos em {nome_mes(m)}</a>' if m in recentes
         else f'<li><span class="text-slate-200">Taxa de financiamento de veículos em {nome_mes(m)}</span>')
        + f' <span class="text-slate-500 text-xs">(média {_pct2(sum(por_mes[m].values()) / len(por_mes[m]))}% a.m.)</span></li>'
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
UMAMI_WEBSITE_ID = "ba3c0b88-59e8-47dd-866d-0b05e5e7dae9"  # mesmo site do Umami do simulador. (plano Hobby tem 1 site; o hostname separa)
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
    """/renda-para-financiar-veiculo: quanto de renda os bancos costumam exigir, por valor, entrada e prazo, para carro novo, usado e moto.
    Enxugamento (21/11/2026): as 17 páginas por valor foram para 301 para esta, que agora traz as tabelas delas. Retorna as URLs (sitemap)."""
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    url_ind = f"{DOMINIO}/{SLUG_INDICE_RENDA}"
    secoes = ""
    for categoria in CATEGORIAS:
        nome_cat = CATEGORIA_ARTIGO[categoria].split(" ", 1)[1]
        entradas = _entradas_da_categoria(categoria)
        valores = VALORES_POR_CATEGORIA[categoria]
        e_min = entradas[0]
        cab_e = "".join(f'<th scope="col" class="px-2 py-2 text-right font-medium">{round(e * 100)}% de entrada</th>' for e in entradas)
        cab_p = "".join(f'<th scope="col" class="px-2 py-2 text-right font-medium">{p} meses</th>' for p in PRAZOS_MESES)
        linhas_e, linhas_p = "", ""
        for valor in valores:
            cels = ""
            for e in entradas:
                v = renda_minima(categoria, valor, e, 48)
                cels += (f'<td class="px-2 py-2 text-right whitespace-nowrap"><strong class="text-white">{formatar_reais(v["renda"])}</strong>'
                         f'<br><span class="text-slate-500">parcela {formatar_reais(v["parcela"])}</span></td>') if v else '<td class="px-2 py-2 text-right text-slate-500">–</td>'
            linhas_e += (f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">{formatar_valor_curto(valor)}</th>{cels}</tr>')
            cels = ""
            for p in PRAZOS_MESES:
                v = renda_minima(categoria, valor, e_min, p)
                cels += f'<td class="px-2 py-2 text-right whitespace-nowrap">{formatar_reais(v["renda"])}</td>' if v else '<td class="px-2 py-2 text-right text-slate-500">–</td>'
            linhas_p += (f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">{formatar_valor_curto(valor)}</th>{cels}</tr>')
        meio = valores[len(valores) // 2]
        base = renda_minima(categoria, meio, e_min, 48)
        secoes += f'''<section class="mt-10">
            <h2 class="font-serif text-xl font-bold mb-2">Renda para financiar {nome_cat}</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed mb-4">Para financiar {nome_cat} de {formatar_valor_curto(meio)} com {round(e_min * 100)}% de entrada em 48 meses, na taxa mediana dos bancos
            ({_pct2(base["taxa_am"])}% ao mês), a parcela pela Tabela Price é de {formatar_reais(base["parcela"])} e a renda familiar mínima, com o limite de 30%, é de {formatar_reais(base["renda"])} por mês.
            <a href="{link_simulador(categoria, meio, meio * e_min, 48)}" class="text-sky-400 underline">Simular este valor</a>.</p>
            <h3 class="font-serif text-base font-semibold mb-2">Renda mínima por valor e entrada (48 meses)</h3>
            <div class="overflow-x-auto rounded-xl border border-white/10"><table class="w-full text-xs text-slate-300">
                <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Valor do veículo</th>{cab_e}</tr></thead>
                <tbody>{linhas_e}</tbody></table></div>
            <h3 class="font-serif text-base font-semibold mt-6 mb-2">Renda mínima por valor e prazo ({round(e_min * 100)}% de entrada)</h3>
            <div class="overflow-x-auto rounded-xl border border-white/10"><table class="w-full text-xs text-slate-300">
                <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Valor do veículo</th>{cab_p}</tr></thead>
                <tbody>{linhas_p}</tbody></table></div>
        </section>'''
    perguntas = [
        ("Qual a renda mínima para financiar um carro?",
         "Depende do valor, da entrada e do prazo. Em geral, os bancos limitam a parcela a cerca de 30% da renda mensal. Divida a parcela por 0,30 para estimar a renda necessária: as tabelas acima já fazem essa conta."),
        ("Como diminuir a renda exigida para financiar?",
         "Aumentar a entrada e alongar o prazo reduzem a parcela e, com ela, a renda exigida. Alongar o prazo, porém, aumenta o total de juros pago."),
        ("Por que a renda mínima é calculada com 30%?",
         "Os bancos costumam limitar a parcela a 30% da renda bruta. É uma regra de mercado, não uma lei: cada banco faz a própria análise de crédito."),
    ]
    faq_html, schema_faq = render_faq_visual(perguntas)
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Renda para financiar", "item": url_ind}]}
    head = render_head("Renda para financiar veículo: quanto precisa ganhar",
                       "Renda mínima para financiar carro novo, carro usado e moto, por valor, prazo e entrada, com a taxa mediana dos bancos e o limite de 30% da renda.",
                       url_ind, [schema_bc, schema_faq, schema_webpage(url_ind, "Renda para financiar veículo", "Renda mínima para financiar carro novo, carro usado e moto.", data_atualizacao)])
    html_ind = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    <main class="flex-1 max-w-4xl mx-auto px-4 sm:px-6 py-10 w-full">
        {render_breadcrumb([("Datalab Global", "/"), ("Renda para financiar", None)])}
        <h1 class="font-serif text-2xl sm:text-4xl font-bold mb-4">Renda para financiar um veículo</h1>
        <p class="text-slate-300 text-base font-light leading-relaxed mb-4">Veja a renda familiar mínima para financiar carro novo, carro usado ou moto, por valor do veículo, entrada e prazo, calculada com o limite de 30% da renda e a taxa mediana dos bancos que acompanhamos.</p>
        <p class="text-slate-500 text-[11px]">Cálculo: parcela pela Tabela Price dividida por 30%, na taxa mediana dos bancos da categoria que oferecem o prazo (taxas médias contratadas, Banco Central, atualizadas em {data_br}). É uma conta nossa, não é análise de crédito.</p>
        {secoes}
        {faq_html}
        <p class="text-slate-400 text-sm mt-10"><a href="financiamento-veiculos" class="text-sky-400 underline">Parcela por valor e prazo</a> · <a href="metodologia" class="text-sky-400 underline">Metodologia</a></p>
        {_cta_comparacao("Quer saber se a sua renda aprova?")}
    </main>
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, f"{SLUG_INDICE_RENDA}.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html_ind))
    return [url_ind]


# ---------------------------------------------------------------------------
# Feed Atom, "O que mudou esta semana" e bloco "Como citar" (05/11/2026).
# ---------------------------------------------------------------------------
ARQUIVO_HISTORICO_SEMANAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "historico_semanal.csv")
SEMANAS_NO_HISTORICO = 26
SEMANAS_NA_TABELA = 6
SLUG_ATUALIZACOES = "atualizacoes"
URL_FEED = f"{DOMINIO}/feed.xml"
TITULO_FEED = "Taxas de financiamento de veículos"
ENTRADAS_MENSAIS_NO_FEED = 12
ENTRADAS_SEMANAIS_NO_FEED = 12
_CAMPOS_SEMANAL = ("data_referencia", "banco", "taxa_am", "taxa_aa")


def ler_historico_semanal(caminho=None):
    """Linhas de historico_semanal.csv: [{data_referencia, banco, taxa_am, taxa_aa}], ordenadas por data e banco.
    Arquivo ausente -> lista vazia."""
    import csv
    try:
        with open(caminho or ARQUIVO_HISTORICO_SEMANAL, encoding="utf-8", newline="") as f:
            linhas = [{"data_referencia": r["data_referencia"], "banco": r["banco"],
                       "taxa_am": float(r["taxa_am"]), "taxa_aa": float(r["taxa_aa"])}
                      for r in csv.DictReader(f, delimiter=";")]
    except FileNotFoundError:
        return []
    return sorted(linhas, key=lambda r: (r["data_referencia"], r["banco"]))


def _escrever_historico_semanal(linhas, caminho=None):
    import csv
    with open(caminho or ARQUIVO_HISTORICO_SEMANAL, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(_CAMPOS_SEMANAL)
        for r in sorted(linhas, key=lambda r: (r["data_referencia"], r["banco"])):
            w.writerow([r["data_referencia"], r["banco"], f"{r['taxa_am']:.2f}", f"{r['taxa_aa']:.2f}"])


def registrar_snapshot_semanal(data_atualizacao, caminho=None, bancos=None):
    """Acrescenta ao CSV o snapshot de taxas por banco da atualização atual (idempotente: se a data já está no
    arquivo, não muda nada) e mantém só as últimas SEMANAS_NO_HISTORICO datas. Retorna as linhas do arquivo."""
    linhas = ler_historico_semanal(caminho)
    if any(r["data_referencia"] == data_atualizacao for r in linhas):
        return linhas
    bancos = BANCOS_VEICULOS if bancos is None else bancos
    for banco, d in bancos.items():
        linhas.append({"data_referencia": data_atualizacao, "banco": banco,
                       "taxa_am": float(d["taxa_am"]), "taxa_aa": float(d["taxa_aa"])})
    datas = sorted({r["data_referencia"] for r in linhas})[-SEMANAS_NO_HISTORICO:]
    linhas = [r for r in linhas if r["data_referencia"] in datas]
    _escrever_historico_semanal(linhas, caminho)
    return sorted(linhas, key=lambda r: (r["data_referencia"], r["banco"]))


def _snapshots(historico_sem):
    snaps = {}
    for r in historico_sem:
        snaps.setdefault(r["data_referencia"], {})[r["banco"]] = r
    return dict(sorted(snaps.items()))


def comparar_snapshots(atual, anterior):
    """Variações (p.p. na taxa ao mês) dos bancos presentes nos dois snapshots, mais a média e as pontas."""
    linhas = []
    for b, r in atual.items():
        if b in anterior:
            linhas.append({"banco": b, "nome": BANCOS_VEICULOS[b]["nome_exibicao"] if b in BANCOS_VEICULOS else b,
                           "antes": anterior[b]["taxa_am"], "depois": r["taxa_am"], "var": round(r["taxa_am"] - anterior[b]["taxa_am"], 2)})
    if not linhas:
        return None
    media_antes = sum(x["antes"] for x in linhas) / len(linhas)
    media_depois = sum(x["depois"] for x in linhas) / len(linhas)
    alta = max(linhas, key=lambda x: x["var"])
    queda = min(linhas, key=lambda x: x["var"])
    return {"linhas": linhas, "media_antes": media_antes, "media_depois": media_depois,
            "alta": alta if alta["var"] > 0 else None, "queda": queda if queda["var"] < 0 else None}


def _data_br(iso):
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _texto_pontas(cmp):
    partes = []
    if cmp["alta"]:
        a = cmp["alta"]
        partes.append(f"maior alta: {a['nome']} ({_sinal_pp(a['var'])} p.p., de {_pct2(a['antes'])}% para {_pct2(a['depois'])}% ao mês)")
    if cmp["queda"]:
        q = cmp["queda"]
        partes.append(f"maior queda: {q['nome']} ({_sinal_pp(q['var'])} p.p., de {_pct2(q['antes'])}% para {_pct2(q['depois'])}% ao mês)")
    return "; ".join(partes) if partes else "nenhum banco mudou de taxa"


def gerar_pagina_atualizacoes(pasta_saida, data_atualizacao, historico_sem):
    """/atualizacoes: o que mudou na taxa de cada banco frente à atualização anterior. Com menos de 2 snapshots
    sai com noindex,follow e fora do sitemap; a partir de 2, vira indexável. Retorna as URLs do sitemap."""
    url = f"{DOMINIO}/{SLUG_ATUALIZACOES}"
    snaps = _snapshots(historico_sem)
    datas = list(snaps)
    cmp = comparar_snapshots(snaps[datas[-1]], snaps[datas[-2]]) if len(datas) >= 2 else None
    indexavel = cmp is not None
    data_ref = datas[-1] if datas else data_atualizacao
    titulo = "Taxas de financiamento de veículos: o que mudou esta semana"
    if indexavel:
        var_media = cmp["media_depois"] - cmp["media_antes"]
        sentido = "subiu" if var_media > 0.004 else "caiu" if var_media < -0.004 else "ficou estável"
        lead = (f"Na atualização de {_data_br(data_ref)}, a taxa média ao mês dos {len(cmp['linhas'])} bancos que acompanhamos {sentido}"
                f"{'' if sentido == 'ficou estável' else ' ' + _pct2(abs(var_media)) + ' p.p.'} frente à de {_data_br(datas[-2])} "
                f"(de {_pct2(cmp['media_antes'])}% para {_pct2(cmp['media_depois'])}% ao mês). Destaques: {_texto_pontas(cmp)}.")
        curto = []
        if cmp["alta"]:
            curto.append(f"maior alta, {cmp['alta']['nome']} ({_sinal_pp(cmp['alta']['var'])} p.p.)")
        if cmp["queda"]:
            curto.append(f"maior queda, {cmp['queda']['nome']} ({_sinal_pp(cmp['queda']['var'])} p.p.)")
        desc = f"O que mudou nas taxas de financiamento de veículos em {_data_br(data_ref)}: " + (" e ".join(curto) if curto else "nenhum banco mudou de taxa") + "."
        if len(desc) > 155:
            desc = f"O que mudou nas taxas de financiamento de veículos em {_data_br(data_ref)}, banco a banco, frente à atualização anterior."
        linhas_cmp = "".join(
            f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">{x["nome"]}</th>'
            f'<td class="px-2 py-2 text-right whitespace-nowrap">{_pct2(x["antes"])}%</td>'
            f'<td class="px-2 py-2 text-right whitespace-nowrap">{_pct2(x["depois"])}%</td>'
            f'<td class="px-2 py-2 text-right whitespace-nowrap font-bold {"text-rose-400" if x["var"] > 0 else "text-emerald-400" if x["var"] < 0 else "text-slate-400"}">{_sinal_pp(x["var"])} p.p.</td></tr>'
            for x in sorted(cmp["linhas"], key=lambda x: x["depois"]))
        tabela_cmp = (f'<div class="overflow-x-auto rounded-xl border border-white/10 mt-6"><table class="w-full text-xs text-slate-300">'
                      f'<thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Banco</th>'
                      f'<th scope="col" class="px-2 py-2 text-right font-medium">{_data_br(datas[-2])}</th><th scope="col" class="px-2 py-2 text-right font-medium">{_data_br(datas[-1])}</th>'
                      f'<th scope="col" class="px-2 py-2 text-right font-medium">Variação</th></tr></thead><tbody>{linhas_cmp}</tbody></table></div>')
        ult = datas[-SEMANAS_NA_TABELA:]
        cab = "".join(f'<th scope="col" class="px-2 py-2 text-right font-medium whitespace-nowrap">{_data_br(d)[:5]}</th>' for d in ult)
        bancos = sorted(snaps[datas[-1]], key=lambda b: snaps[datas[-1]][b]["taxa_am"])
        corpo = "".join(
            f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">'
            f'{BANCOS_VEICULOS[b]["nome_exibicao"] if b in BANCOS_VEICULOS else b}</th>'
            + "".join(f'<td class="px-2 py-2 text-right whitespace-nowrap">{_pct2(snaps[d][b]["taxa_am"]) + "%" if b in snaps[d] else "–"}</td>' for d in ult) + '</tr>'
            for b in bancos)
        historico_html = (f'<h2 class="font-serif text-xl font-bold mt-10 mb-3">Taxa ao mês nas últimas {len(ult)} atualizações</h2>'
                          f'<div class="overflow-x-auto rounded-xl border border-white/10"><table class="w-full text-xs text-slate-300">'
                          f'<thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Banco</th>{cab}</tr></thead>'
                          f'<tbody>{corpo}</tbody></table></div>')
    else:
        lead = ("Primeira medição: guardamos hoje a taxa de cada banco e a comparação começa na próxima atualização. "
                "A partir daí, esta página mostra o que subiu e o que caiu.")
        desc = "Acompanhamento semanal das taxas de financiamento de veículos por banco: a comparação começa na próxima atualização."
        tabela_cmp = historico_html = ""
    schema = schema_webpage(url, titulo, desc, data_ref)
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "O que mudou esta semana", "item": url}]}
    head = render_head(titulo, desc, url, [schema, schema_bc], robots=None if indexavel else "noindex,follow")
    html_pagina = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
    {head}
</head>
<body class="antialiased flex flex-col min-h-screen">
    {render_nav()}
    <main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        <h1 class="font-serif text-2xl sm:text-4xl font-bold mb-4">O que mudou esta semana nas taxas de financiamento de veículos</h1>
        <p class="text-slate-300 text-base font-light leading-relaxed">{lead}</p>
        {tabela_cmp}
        {historico_html}
        <p class="text-slate-500 text-[11px] mt-4">Taxa média efetivamente contratada, por banco, na última janela de 5 dias úteis divulgada pelo Banco Central (modalidade 401101). Quando o Banco Central ainda não divulgou uma janela nova, a taxa de um banco pode ficar igual de uma atualização para a outra. Não é oferta de crédito. Veja a <a href="metodologia" class="underline">metodologia</a>.</p>
        <p class="mt-8 text-sm text-slate-300"><a href="{SLUG_INDICE_MENSAL}" class="text-sky-400 underline">Taxas mês a mês</a> · <a href="{slug_comparador('novo')}" class="text-sky-400 underline">Comparar carro novo</a> · <a href="feed.xml" class="text-sky-400 underline">Feed de atualizações (Atom)</a></p>
    </main>
    {render_footer()}
</body>
</html>'''
    with open(os.path.join(pasta_saida, f"{SLUG_ATUALIZACOES}.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html_pagina))
    return [url] if indexavel else []


def _rfc3339(iso_data):
    return f"{iso_data}T00:00:00Z"


def gerar_feed_atom(pasta_saida, data_atualizacao, historico_mensal, historico_sem):
    """feed.xml (Atom 1.0): uma entrada por mês da série do BACEN (últimos ENTRADAS_MENSAIS_NO_FEED) e uma por
    atualização semanal (últimas ENTRADAS_SEMANAIS_NO_FEED). Fora do sitemap, de propósito."""
    import xml.etree.ElementTree as ET
    ns = "http://www.w3.org/2005/Atom"
    ET.register_namespace("", ns)
    feed = ET.Element(f"{{{ns}}}feed", {"{http://www.w3.org/XML/1998/namespace}lang": "pt-BR"})

    def sub(pai, tag, texto=None, **attrs):
        el = ET.SubElement(pai, f"{{{ns}}}{tag}", attrs)
        if texto is not None:
            el.text = texto
        return el
    sub(feed, "id", URL_FEED)
    sub(feed, "title", TITULO_FEED)
    sub(feed, "subtitle", "Taxas médias de juros do financiamento de carro novo, carro usado e moto por banco, com dados do Banco Central.")
    sub(feed, "link", rel="self", type="application/atom+xml", href=URL_FEED)
    sub(feed, "link", rel="alternate", type="text/html", href=f"{DOMINIO}/")
    sub(feed, "updated", _rfc3339(data_atualizacao))
    autor = sub(feed, "author")
    sub(autor, "name", "Datalab Global")
    sub(autor, "uri", f"{DOMINIO}/sobre")
    entradas = []
    por_mes = {}
    fim_mes = {}
    for r in historico_mensal:
        por_mes.setdefault(r["mes_referencia"], {})[r["banco"]] = r["taxa_am"]
        fim_mes[r["mes_referencia"]] = r["fim_periodo"]
    for mes in sorted(por_mes)[-MESES_INDEXAVEIS_MENSAL:]:
        taxas = por_mes[mes]
        menor, maior = min(taxas, key=taxas.get), max(taxas, key=taxas.get)
        nome = lambda b: BANCOS_VEICULOS[b]["nome_exibicao"] if b in BANCOS_VEICULOS else b
        resumo = (f"Em {nome_mes(mes)}, a taxa média contratada no financiamento de veículos foi de {_pct2(taxas[menor])}% ao mês ({nome(menor)}) "
                  f"a {_pct2(taxas[maior])}% ({nome(maior)}), com média de {_pct2(sum(taxas.values()) / len(taxas))}% entre {len(taxas)} bancos.")
        entradas.append((fim_mes[mes], f"{DOMINIO}/{slug_mes(mes)}", f"Taxas de financiamento de veículos em {nome_mes(mes)}", resumo))
    snaps = _snapshots(historico_sem)
    datas = list(snaps)
    for i, d in enumerate(datas):
        if i == 0:
            continue
        cmp = comparar_snapshots(snaps[d], snaps[datas[i - 1]])
        if cmp is None:
            continue
        resumo = f"Atualização de {_data_br(d)} frente à de {_data_br(datas[i - 1])}: {_texto_pontas(cmp)}."
        entradas.append((d, f"{DOMINIO}/{SLUG_ATUALIZACOES}#{d}", f"Taxas de financiamento de veículos: atualização de {_data_br(d)}", resumo[0].upper() + resumo[1:]))
    semanais = sorted((e for e in entradas if "#" in e[1]), key=lambda e: e[0])[-ENTRADAS_SEMANAIS_NO_FEED:]
    mensais = [e for e in entradas if "#" not in e[1]]
    for data, link, titulo, resumo in sorted(mensais + semanais, key=lambda e: e[0], reverse=True):
        entrada = sub(feed, "entry")
        sub(entrada, "id", link)
        sub(entrada, "title", titulo)
        sub(entrada, "link", rel="alternate", type="text/html", href=link.split("#")[0])
        sub(entrada, "updated", _rfc3339(data))
        sub(entrada, "summary", resumo)
    ET.indent(feed)
    ET.ElementTree(feed).write(os.path.join(pasta_saida, "feed.xml"), encoding="utf-8", xml_declaration=True)


def html_link_e_compartilhar(titulo, url, classe_link="text-sky-400"):
    """Facilita criar um link para a página, como pedem as Diretrizes do Bing ("copy-and-paste code snippets" e
    compartilhamento social). Texto de âncora descritivo e de marca, sem palavra-chave empilhada; botões sem JavaScript
    e com rel nofollow (são só atalhos de compartilhar)."""
    import urllib.parse as _up
    codigo = f'<a href="{url}">{titulo} (Datalab Global)</a>'
    u, t = _up.quote(url, safe=""), _up.quote(f"{titulo} (Datalab Global)", safe="")
    botoes = [("WhatsApp", f"https://api.whatsapp.com/send?text={t}%20{u}"),
              ("LinkedIn", f"https://www.linkedin.com/sharing/share-offsite/?url={u}"),
              ("X", f"https://twitter.com/intent/tweet?url={u}&text={t}"),
              ("Facebook", f"https://www.facebook.com/sharer/sharer.php?u={u}")]
    links = " · ".join(f'<a href="{h}" target="_blank" rel="noopener nofollow" class="underline {classe_link}">{n}</a>' for n, h in botoes)
    return (f'<h3 class="text-xs font-bold text-slate-300 uppercase tracking-widest mt-5 mb-2">Link para esta página</h3>'
            f'<textarea readonly rows="2" onclick="this.select()" aria-label="Código HTML do link para esta página" '
            f'class="w-full bg-slate-900/60 border border-white/10 rounded-xl p-3 text-xs text-slate-200 font-mono">{html.escape(codigo, quote=True)}</textarea>'
            f'<p class="text-slate-400 text-xs mt-2">Compartilhar: {links}</p>')


def html_como_citar(categoria, banco_exib, url, data_atualizacao):
    """Caixa 'Como citar este dado' dos hubs de banco (sem JavaScript: o textarea seleciona o texto ao clicar)."""
    texto = (f'Datalab Global, "Taxa do {banco_exib} para {CATEGORIA_LABEL[categoria].lower()}", dados do Banco Central, '
             f'atualizado em {_data_br(data_atualizacao)}. {url}')
    return (f'<section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Como citar este dado</h2>'
            f'<textarea readonly rows="3" onclick="this.select()" aria-label="Texto para citar este dado" '
            f'class="w-full bg-slate-900/60 border border-white/10 rounded-xl p-3 text-sm text-slate-200">{html.escape(texto, quote=False)}</textarea>'
            f'<p class="text-slate-400 text-xs mt-2">Dados sob licença <a href="{LICENCA_DADOS_URL}" rel="noopener" class="underline">{LICENCA_DADOS}</a>: '
            f'pode usar e adaptar, citando a fonte com link.</p>'
            + html_link_e_compartilhar(f"Taxa do {banco_exib} para {CATEGORIA_LABEL[categoria].lower()}", url) + '</section>')


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

## Taxas usadas nas simulações (média do Banco Central de {periodo_taxa_bacen() or "última semana divulgada"}; página atualizada em {data_br})
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
- O que mudou esta semana: {DOMINIO}/atualizacoes
- Feed Atom das atualizações: {DOMINIO}/feed.xml
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
            f'<script defer src="/medicao.js?v={VERSAO_BUILD}"></script>']


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
- **DOI (Zenodo):** {URL_ZENODO_DOI} (aponta sempre para a versão mais recente).
- **Arquivos:** `taxas-financiamento-veiculos.csv`, `taxas-financiamento-veiculos.json`, `datapackage.json`.
- **Colunas:** `mes_referencia`, `periodo_inicio`, `periodo_fim`, `instituicao`, `taxa_juros_am_pct`, `taxa_juros_aa_pct`.
- **Limites:** são médias do que foi efetivamente contratado, não ofertas; a modalidade não separa carro novo, usado e moto.

## Como citar

{citacao.format(data="AAAA-MM-DD")}

Publicado por Datalab Global ({DOMINIO}/), marca de {EMPRESA_RODAPE}.
""")

    schema_dataset = {
        "@context": "https://schema.org", "@type": "Dataset", "keywords": KEYWORDS_DATASET,
        "name": "Taxas médias de juros do financiamento de veículos por banco (BACEN)",
        "description": descricao, "url": url_pagina, "inLanguage": "pt-BR",
        "license": LICENCA_DADOS_URL, "isAccessibleForFree": True,
        "creator": {"@type": "Organization", "name": "Datalab Global", "url": f"{DOMINIO}/"},
        "isBasedOn": FONTE_BACEN_URL, "dateModified": data_atualizacao, "sameAs": [URL_KAGGLE, URL_HUGGINGFACE, URL_ZENODO_DOI], "identifier": URL_ZENODO_DOI,
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
                <li><a href="{URL_KAGGLE}" rel="noopener" class="text-sky-400 underline">Kaggle</a> <span class="text-slate-400">· mesma série, com notebook de exemplo</span></li>
                <li><a href="{URL_HUGGINGFACE}" rel="noopener" class="text-sky-400 underline">Hugging Face</a> <span class="text-slate-400">· mesma série</span></li>
                <li><a href="{URL_ZENODO_DOI}" rel="noopener" class="text-sky-400 underline">Zenodo (DOI)</a> <span class="text-slate-400">· registro citável; o DOI aponta sempre para a versão mais recente</span></li>
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
            {_html_citar(url_pagina, citacao.format(data="AAAA-MM-DD"))}
            <p class="text-slate-400 text-xs font-light mt-3">DOI (sempre a versão mais recente): <a href="{URL_ZENODO_DOI}" rel="noopener" class="underline">{URL_ZENODO_DOI}</a></p>
            <p class="text-slate-400 text-xs font-light mt-3">Licença <a href="{LICENCA_DADOS_URL}" rel="noopener" class="underline">{LICENCA_DADOS}</a>. Fonte original: <a href="{FONTE_BACEN_URL}" rel="noopener" class="underline">Banco Central do Brasil</a>. Leia também a <a href="analise-do-mes" class="underline">análise do mês</a>. Atualizado em {date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')}.</p>
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

    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_breadcrumb, schema_item_list, schema_faq,
                                                                       schema_webpage(url_canonica, titulo_pagina, meta_description, data_atualizacao)])
    por_taxa = sorted(ranking, key=lambda r: (r["taxa_am"], r["nome_exibicao"]))
    pct_am = lambda v: f"{v:.2f}".replace('.', ',') + "%"
    periodo_cmp = periodo_taxa_bacen()
    quando_cmp = (f"Na semana de {periodo_cmp}, a última divulgada pelo Banco Central," if periodo_cmp
                  else f"Na atualização de {d_atual.strftime('%d/%m/%Y')},")
    frase_resposta = (f"{quando_cmp} a menor taxa de financiamento de {nome_cat} entre os {len(ranking)} bancos que acompanhamos "
                      f"é a do {por_taxa[0]['nome_exibicao']} ({pct_am(por_taxa[0]['taxa_am'])} ao mês) e a maior, a do {por_taxa[-1]['nome_exibicao']} "
                      f"({pct_am(por_taxa[-1]['taxa_am'])}).")
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), (label_categoria, None)])

    corpo = f'''<main class="flex-1 max-w-5xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <div class="flex items-center gap-4 mb-2">
            <div class="w-14 h-14 sm:w-16 sm:h-16 shrink-0">{ilustracao_categoria(categoria, f'il-grad-cmp-{categoria}')}</div>
            <h1 class="font-serif text-2xl sm:text-3xl font-bold">Taxas de financiamento de {nome_cat} por banco em {mes_ano}</h1>
        </div>
        <p class="text-white text-lg font-medium mb-3">{frase_resposta}</p>
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

        {html_requisitos_aprovacao(categoria)}

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


def gerar_paginas_comparacao(pasta_saida, data_atualizacao, lookup=None):
    """Enxugamento (21/11/2026): as 80 páginas de comparação sem marca (categoria x valor x prazo) foram para 301 (ver gerar_redirects);
    sobra o índice /financiamento-veiculos, cuja tabela leva ao simulador da home com o cenário preenchido. Retorna as URLs (sitemap)."""
    return [gerar_indice_comparacao(pasta_saida, data_atualizacao)]


def gerar_indice_comparacao(pasta_saida, data_atualizacao):
    """Índice (financiamento-veiculos.html): uma tabela valor x prazo por
    categoria, com a menor parcela entre os bancos em cada cenário; cada
    célula leva ao simulador da home com o cenário preenchido."""
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
                melhor = min(l, key=lambda x: x["parcela"])
                celulas += f'<td class="px-3 py-2 text-right"><a href="{link_simulador(categoria, valor, melhor["entrada"], p, melhor["banco"])}" class="text-sky-400 hover:underline">{_reais_inteiros(melhor["parcela"])}</a></td>'
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
         "Cada célula mostra a menor parcela mensal (tabela Price) entre os bancos para aquele valor de veículo e prazo, com a entrada mínima da categoria. Clique para simular esse cenário no simulador, com o banco de menor parcela já escolhido."),
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
        <p class="text-slate-400 text-sm mb-2">Menor parcela entre os bancos para cada valor e prazo, em carro novo, carro usado e moto. Escolha um cenário para abrir a simulação com CET e total pago.</p>
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
<link rel="icon" href="/favicon.ico?v=20261120" sizes="any">
<link rel="icon" href="/favicon-32.png?v=20261120" type="image/png" sizes="32x32">
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
            {_html_citar(url, citacao)}
            <p class="text-slate-400 text-xs mt-3">Dados sob licença <a href="{LICENCA_DADOS_URL}" rel="noopener" class="underline">{LICENCA_DADOS}</a>: pode usar e adaptar, citando a fonte com link.</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Contato</h2>
            <p class="text-slate-300 text-sm font-light">E-mail: <a href="mailto:contato@datalabglobal.com" class="text-sky-400 underline">contato@datalabglobal.com</a></p></section>
        <p class="mt-10 text-center text-xs text-slate-400"><a href="analise-do-mes" class="text-sky-400 underline">Análise do mês</a> · <a href="financiamento-veiculos" class="text-sky-400 underline">Parcela por valor e prazo</a> · <a href="incorporar" class="text-sky-400 underline">Simulador para o seu site</a> · <a href="atualizacoes" class="text-sky-400 underline">O que mudou esta semana</a> · <a href="feed.xml" class="text-sky-400 underline">Feed de atualizações (Atom)</a></p>
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



def _html_citar(url, texto_citacao):
    """Bloco "Como citar": o texto e dois botões (copiar a citação; copiar o link em HTML, que é o que vira
    backlink de verdade). Funciona sem biblioteca; se a cópia automática falhar, avisa e o texto segue selecionável."""
    import html as _h
    link_html = f'<a href="{url}">Datalab Global</a>'
    botao = 'class="px-3 py-2 rounded-lg border border-white/10 text-sky-400 text-xs"'
    return f"""<div data-citar>
            <p class="text-slate-300 text-sm font-light leading-relaxed bg-white/5 border border-white/10 rounded-xl p-4">{texto_citacao}</p>
            <div class="flex flex-wrap gap-3 mt-3">
                <button type="button" data-copiar="{_h.escape(texto_citacao, quote=True)}" {botao}>Copiar citação</button>
                <button type="button" data-copiar="{_h.escape(link_html, quote=True)}" {botao}>Copiar link em HTML</button>
            </div>
            <p class="text-slate-400 text-xs mt-2" role="status" data-citar-status></p>
            <script>document.addEventListener('click',function(e){{var b=e.target.closest('[data-copiar]');if(!b)return;var t=b.getAttribute('data-copiar'),s=b.closest('[data-citar]').querySelector('[data-citar-status]');function ok(){{s.textContent='Copiado.';}}function falha(){{s.textContent='Não foi possível copiar automaticamente: selecione o texto e copie.';}}if(navigator.clipboard&&window.isSecureContext){{navigator.clipboard.writeText(t).then(ok,falha);}}else{{var a=document.createElement('textarea');a.value=t;a.setAttribute('readonly','');a.style.position='fixed';a.style.opacity='0';document.body.appendChild(a);a.select();try{{document.execCommand('copy')?ok():falha();}}catch(x){{falha();}}document.body.removeChild(a);}}}});</script>
        </div>"""


def gerar_analise_do_mes(pasta_saida, data_atualizacao):
    """/analise-do-mes: o último mês do Banco Central frente ao mesmo mês do ano anterior, banco a banco (% ao mês).
    Tudo calculado da série (muda sozinho a cada atualização). Sem 12 meses de série, não gera a página."""
    historico = carregar_historico()
    if not historico:
        return []
    meses = sorted({r["mes_referencia"] for r in historico})
    ult = meses[-1]
    ant = f"{int(ult[:4]) - 1}{ult[4:]}"
    if ant not in meses:
        return []
    atual = {r["banco"]: r["taxa_am"] for r in historico if r["mes_referencia"] == ult}
    antes = {r["banco"]: r["taxa_am"] for r in historico if r["mes_referencia"] == ant}
    linhas = [{"banco": b, "exib": BANCOS_VEICULOS[b]["nome_exibicao"], "antes": antes[b], "atual": atual[b], "var": atual[b] - antes[b]}
              for b in atual if b in antes and b in BANCOS_VEICULOS]
    if len(linhas) < 3:
        return []
    linhas.sort(key=lambda x: x["atual"])
    n = len(linhas)
    quedas = [x for x in linhas if x["var"] < 0]
    altas = [x for x in linhas if x["var"] > 0]
    mes_nome, ano, ano_ant = MESES_PT[int(ult[5:7]) - 1], ult[:4], str(int(ult[:4]) - 1)
    lo, hi = linhas[0], linhas[-1]
    maior_queda = min(linhas, key=lambda x: x["var"])
    maior_alta = max(linhas, key=lambda x: x["var"])
    media_atual = sum(x["atual"] for x in linhas) / n
    media_antes = sum(x["antes"] for x in linhas) / n
    fatos = [
        f"Em {mes_nome} de {ano}, a taxa média contratada foi de {_pct2(lo['atual'])}% ao mês em {lo['exib']}, a menor entre os {n} bancos com dado do Banco Central, e de {_pct2(hi['atual'])}% em {hi['exib']}, a maior.",
        f"Frente a {mes_nome} de {ano_ant}, {len(quedas)} de {n} bancos tiveram taxa média menor e {len(altas)}, maior"
        + ((f"; {n - len(quedas) - len(altas)} ficou igual" if n - len(quedas) - len(altas) == 1 else f"; {n - len(quedas) - len(altas)} ficaram iguais") if n - len(quedas) - len(altas) else "") + ".",
    ]
    if maior_queda["var"] < 0:
        fatos.append(f"A maior queda foi a de {maior_queda['exib']}: de {_pct2(maior_queda['antes'])}% para {_pct2(maior_queda['atual'])}% ao mês ({_sinal_pp(maior_queda['var'])} ponto percentual).")
    if maior_alta["var"] > 0:
        fatos.append(f"A maior alta foi a de {maior_alta['exib']}: de {_pct2(maior_alta['antes'])}% para {_pct2(maior_alta['atual'])}% ao mês ({_sinal_pp(maior_alta['var'])} ponto percentual).")
    fatos.append(f"A média simples dos {n} bancos foi de {_pct2(media_antes)}% para {_pct2(media_atual)}% ao mês ({_sinal_pp(media_atual - media_antes)} ponto percentual).")
    fatos_html = "".join(f'<li class="mb-3">{f}</li>' for f in fatos)
    teto = max(x["atual"] for x in linhas) or 1
    corpo_tab = ""
    for x in linhas:
        cor = "text-emerald-400" if x["var"] < 0 else "text-rose-400" if x["var"] > 0 else "text-slate-400"
        larg = max(4, round(100 * x["atual"] / teto))
        corpo_tab += (f'<tr class="border-t border-white/5"><th scope="row" class="px-2 py-2 text-left font-medium text-white whitespace-nowrap">{x["exib"]}</th>'
                      f'<td class="px-2 py-2 text-right whitespace-nowrap">{_pct2(x["antes"])}</td>'
                      f'<td class="px-2 py-2 text-right whitespace-nowrap">{_pct2(x["atual"])}</td>'
                      f'<td class="px-2 py-2" style="width:25%"><div class="w-full h-2 rounded-full bg-white/5"><div class="h-2 rounded-full bg-sky-500" style="width:{larg}%"></div></div></td>'
                      f'<td class="px-2 py-2 text-right font-bold whitespace-nowrap {cor}">{_sinal_pp(x["var"])} p.p.</td></tr>')
    url = f"{DOMINIO}/analise-do-mes"
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    citacao = f"Datalab Global. Análise do mês: juros do financiamento de veículos por banco (dados do Banco Central). {url}, acesso em AAAA-MM-DD."
    titulo = "Análise do mês: juros do financiamento de veículos por banco | Datalab"
    meta = (f"Taxa média contratada no financiamento de veículos em {mes_nome} de {ano}: de {_pct2(lo['atual'])}% a {_pct2(hi['atual'])}% ao mês. "
            f"Variação banco a banco frente a {mes_nome} de {ano_ant}.")
    schema_bc = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Análise do mês", "item": url}]}
    schema_page = {"@context": "https://schema.org", "@type": "WebPage", "url": url, "name": "Análise do mês: juros do financiamento de veículos por banco",
                   "dateModified": data_atualizacao, "isBasedOn": FONTE_BACEN_URL,
                   "about": {"@type": "Organization", "name": "Datalab Global", "url": "https://www.datalabglobal.com/"}}
    head = render_head(titulo, meta, url, [schema_bc, schema_page])
    breadcrumb = render_breadcrumb([("Datalab Global", "/"), ("Análise do mês", None)])
    corpo = f"""<main class="flex-1 max-w-3xl mx-auto px-4 sm:px-6 py-10 w-full">
        {breadcrumb}
        <h1 class="font-serif text-2xl sm:text-3xl font-bold mb-2">Análise do mês: juros do financiamento de veículos por banco</h1>
        <p class="text-slate-400 text-sm mb-8">{mes_nome.capitalize()} de {ano} frente a {mes_nome} de {ano_ant}. Atualizado em {data_br}.</p>
        <section><h2 class="font-serif text-xl font-bold mb-3">O que mudou em 12 meses</h2>
            <ul class="text-slate-300 text-sm font-light leading-relaxed list-disc list-inside">{fatos_html}</ul>
            <p class="text-slate-400 text-xs mt-2">Calculado automaticamente da série do Banco Central; muda a cada atualização. São médias do que foi efetivamente contratado, não ofertas: a sua proposta pode ser diferente.</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Banco a banco</h2>
            <p class="text-slate-400 text-xs font-light leading-relaxed mb-4">Taxa média contratada, em % ao mês. A barra mostra a taxa de {mes_nome} de {ano} em relação à maior do mês.</p>
            <div class="overflow-x-auto rounded-xl border border-white/10">
                <table class="w-full text-xs text-slate-300" aria-label="Taxa média de juros do financiamento de veículos por banco, {mes_nome} de {ano_ant} e {mes_nome} de {ano}">
                    <thead class="text-[10px] uppercase tracking-widest text-slate-400"><tr><th scope="col" class="px-2 py-2 text-left font-medium">Banco</th><th scope="col" class="px-2 py-2 text-right font-medium whitespace-nowrap">{_rotulo_mes(ant)}</th><th scope="col" class="px-2 py-2 text-right font-medium whitespace-nowrap">{_rotulo_mes(ult)}</th><th scope="col" class="px-2 py-2 text-left font-medium">Comparação</th><th scope="col" class="px-2 py-2 text-right font-medium whitespace-nowrap">Variação</th></tr></thead>
                    <tbody>{corpo_tab}</tbody>
                </table>
            </div>
            <p class="text-slate-400 text-xs font-light mt-3">O Banco Central publica uma única modalidade para carro novo, carro usado e moto; por isso a taxa é a mesma para os três.</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Fonte e método</h2>
            <p class="text-slate-300 text-sm font-light leading-relaxed">Os dados vêm do relatório de taxas de juros por instituição financeira do <a href="{FONTE_BACEN_URL}" rel="noopener" class="text-sky-400 underline">Banco Central do Brasil</a> (modalidade 401101: aquisição de veículos, pessoa física, pré-fixada). A série completa está em <a href="dados-abertos" class="text-sky-400 underline">dados abertos</a> (CSV e JSON, licença {LICENCA_DADOS}).</p></section>
        <section class="mt-10"><h2 class="font-serif text-xl font-bold mb-3">Como citar</h2>
            {_html_citar(url, citacao)}
            <p class="text-slate-400 text-xs mt-3">Dados sob licença <a href="{LICENCA_DADOS_URL}" rel="noopener" class="underline">{LICENCA_DADOS}</a>: pode usar e adaptar, citando a fonte com link.</p></section>
        <p class="mt-10 text-center text-xs text-slate-400"><a href="imprensa" class="text-sky-400 underline">Imprensa</a> · <a href="financiamento-veiculos" class="text-sky-400 underline">Parcela por valor e prazo</a> · <a href="dados-abertos" class="text-sky-400 underline">Dados abertos</a></p>
    </main>"""
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
    with open(os.path.join(pasta_saida, "analise-do-mes.html"), "w", encoding="utf-8") as f:
        f.write(corrigir_concordancia(html))
    return [url]


# ---------------------------------------------------------------------------
# Home nova (20/11/2026): mesmo template do Home Equity (006), Auto Equity (007) e Condomínio (008), em azul de veículos.
# HTML em layout_home.py, estilo em src/home.css, lógica em src/home.js. Sem style nem script inline (CSP própria da home).
# ---------------------------------------------------------------------------

VALORES_SIMULADOR = {
    "novo": {"min": 30_000, "max": 400_000, "passo": 5_000, "padrao": 80_000},
    "usado": {"min": 15_000, "max": 250_000, "passo": 5_000, "padrao": 50_000},
    "moto": {"min": 5_000, "max": 80_000, "passo": 1_000, "padrao": 18_000},
}
PRAZO_PADRAO_SIMULADOR = 48
ASSETS_HOME = (("home.css", "home.css"), ("home.js", "home.js"), ("menu.js", "menu.js"))


def _hash_arquivo(caminho):
    import hashlib
    with open(caminho, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:10]


def copiar_assets_home(pasta_saida):
    """Copia src/home.css, src/home.js e src/menu.js para a pasta de saída e devolve {nome: hash} (cache imutável com ?v=)."""
    import shutil
    aqui = os.path.dirname(os.path.abspath(__file__))
    versoes = {}
    for origem, destino in ASSETS_HOME:
        caminho = os.path.join(aqui, "src", origem)
        shutil.copyfile(caminho, os.path.join(pasta_saida, destino))
        versoes[destino] = _hash_arquivo(caminho)
    return versoes


def dados_simulador_home():
    """Bloco JSON lido por src/home.js: taxas por banco (ordenadas), entrada mínima e limites de valor por categoria."""
    bancos = {}
    for categoria in CATEGORIAS:
        ordenados = sorted(bancos_para_categoria(categoria).items(), key=lambda kv: (kv[1]["taxa_am"], kv[0]))
        bancos[categoria] = [{"k": k, "n": obter_regra(k)["nome_exibicao"] or k, "am": v["taxa_am"], "aa": v["taxa_aa"], "pm": v["prazo_max"]}
                             for k, v in ordenados]
    return {"entradaMin": {c: entrada_minima(c) for c in CATEGORIAS}, "valores": VALORES_SIMULADOR, "bancos": bancos,
            "periodo": periodo_taxa_bacen() or ""}


def padrao_simulador_home():
    """Cenário padrão da home (carro novo, R$ 80 mil, entrada mínima, 48 meses, média dos bancos): mesma conta do home.js."""
    c = "novo"
    taxas = [v["taxa_am"] for v in bancos_para_categoria(c).values()]
    tx = sum(taxas) / len(taxas)
    valor = VALORES_SIMULADOR[c]["padrao"]
    entrada = valor * entrada_minima(c)
    fin = valor - entrada
    prazo = PRAZO_PADRAO_SIMULADOR
    pmt = calcular_pmt_price(fin, prazo, tx)
    total = pmt * prazo
    return {"valor": valor, "entrada": entrada, "fin": fin, "prazo": prazo, "taxa": tx, "parcela": pmt, "total": total,
            "juros": total - fin, "cet": calcular_cet_veiculo(fin, prazo, tx), "taxas": taxas}


def _num_br(v, casas=0):
    return f"{v:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _linhas_amort_anual(fin, prazo, tx):
    i = tx / 100
    pmt = calcular_pmt_price(fin, prazo, tx)
    saldo, linhas, ano, j, a = fin, [], 0, 0.0, 0.0
    for m in range(1, prazo + 1):
        juros = saldo * i
        am = pmt - juros
        saldo = max(0.0, saldo - am)
        j += juros
        a += am
        if m % 12 == 0 or m == prazo:
            ano += 1
            linhas.append((ano, j, a, 0.0 if saldo < 0.005 else saldo))
            j = a = 0.0
    return linhas


def html_tabelas_taxas_home():
    """Tabela única 'taxa de hoje por banco' da home. O Banco Central não separa carro novo, usado e moto nesta modalidade e
    os bancos têm a mesma taxa nas três: uma tabela só (com a coluna 'vale para'), sem repetir o mesmo conteúdo três vezes.
    Achado real (04/11/2026, Bing > AI Performance): a home foi citada 41 vezes pelo Copilot para 'taxa financiamento carro novo'
    quando não tinha taxa nenhuma; os números são os mesmos dos hubs."""
    pct = lambda v: f"{v:.2f}".replace('.', ',') + "%"
    todos = {}
    for categoria in CATEGORIAS:
        for banco in bancos_para_categoria(categoria):
            todos.setdefault(banco, []).append(categoria)
    bancos = sorted(todos, key=lambda b: (obter_regra(b)["taxa_am"], b))
    linhas = []
    for b in bancos:
        r = obter_regra(b)
        cats = todos[b]
        vale = "Carro novo, usado e moto" if len(cats) == len(CATEGORIAS) else " e ".join(CATEGORIA_LABEL[c] for c in cats)
        linhas.append(f'<tr><td><a href="/{slug_hub(cats[0], b)}">{r["nome_exibicao"] or b}</a></td>'
                      f'<td data-l="Taxa ao mês">{pct(r["taxa_am"])}</td><td data-l="Taxa ao ano">{pct(r["taxa_aa"])}</td>'
                      f'<td data-l="Vale para">{vale}</td></tr>')
    nome = lambda b: obter_regra(b)["nome_exibicao"] or b
    periodo = periodo_taxa_bacen()
    quando = f"Na semana de {periodo}, a última divulgada pelo Banco Central" if periodo else "Na última semana divulgada pelo Banco Central"
    resumo = (f"{quando}, a taxa de financiamento de veículos nos bancos que acompanhamos vai de {pct(obter_regra(bancos[0])['taxa_am'])} ao mês "
              f"({nome(bancos[0])}) a {pct(obter_regra(bancos[-1])['taxa_am'])} ({nome(bancos[-1])}).")
    links = " · ".join(f'<a href="/{slug_comparador(c)}">Comparar CET e parcela de {CATEGORIA_LABEL[c].lower()}</a>' for c in CATEGORIAS)
    return f'''<p class="amsub">{resumo}</p>
    <div class="prose flat"><div class="tw"><table>
      <caption>Taxa média efetivamente contratada, por banco</caption>
      <thead><tr><th scope="col">Banco</th><th scope="col">Taxa ao mês</th><th scope="col">Taxa ao ano</th><th scope="col">Vale para</th></tr></thead>
      <tbody>{"".join(linhas)}</tbody></table></div></div>
    <p class="hint">{links}</p>'''


def _cartoes_categoria_home():
    cartoes = []
    # entrada e prazo são convenção de mercado, não regra confirmada banco a banco (ver ITENS_A_VALIDAR em bancos_veiculos.py)
    descr = {"novo": "Simulação com entrada de 20% (convenção de mercado) e prazo até 60 meses.",
             "usado": "Simulação com entrada de 30% (convenção de mercado) e prazo até 60 meses.",
             "moto": "Inclui as financeiras da Honda e da Yamaha (prazo até 48 meses)."}
    for c in CATEGORIAS:
        n = len(bancos_para_categoria(c))
        cartoes.append(f'<a class="card" href="/{slug_comparador(c)}"><h4>{CATEGORIA_LABEL[c]}</h4>'
                       f'<p>Compare {n} bancos pelo CET e pela parcela. {descr[c]}</p><span class="go">Ver comparador →</span></a>')
    return "".join(cartoes)


def _cartoes_guias_home():
    escolhidos = ["aprenda-o-que-e-cet", "aprenda-tabela-price", "aprenda-financiamento-x-consorcio-veiculo"]
    por_slug = {a["slug"]: a for a in ARTIGOS_APRENDA}
    cartoes = []
    for sl in escolhidos:
        a = por_slug.get(sl)
        if a:
            cartoes.append(f'<a class="card" href="/{sl}"><h4>{a["titulo_h1"]}</h4><p>{a["resumo_card"]}</p><span class="go">Ler o guia →</span></a>')
    return "".join(cartoes)


def _faq_home(perguntas):
    itens = "".join(f"<details><summary>{q}</summary><p>{a}</p></details>" for q, a in perguntas)
    schema = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in perguntas],
    }
    return itens, schema


def _rodape_home():
    li = lambda href, rotulo: f'<li><a href="{href}">{rotulo}</a></li>'
    entenda = "".join([li("/aprenda", "Aprenda"), li("/taxas-financiamento-veiculos", "Taxas mês a mês"), li("/renda-para-financiar-veiculo", "Renda para financiar"),
                       li("/financiamento-veiculos", "Parcela por valor e prazo"), li("/analise-do-mes", "Análise do mês")])
    transp = "".join([li("/metodologia", "Como calculamos"), li("/dados-abertos", "Dados abertos"), li("/atualizacoes", "O que mudou na semana"),
                      li("/sobre", "Sobre a Datalab Global"), li("/imprensa", "Imprensa"), li("/incorporar", "Simulador para o seu site")])
    legal = "".join([li("https://www.datalabglobal.com/privacidade/", "Privacidade"), li("https://www.datalabglobal.com/termos/", "Termos")])
    outros = "".join([li("https://homeequity.datalabglobal.com/", "Home Equity"), li("https://autoequity.datalabglobal.com/", "Auto Equity"),
                      li("https://condominio.datalabglobal.com/", "Empréstimo para Condomínios"), li("https://simulador.datalabglobal.com/", "Financiamento imobiliário"),
                      li("https://emprestimo.datalabglobal.com/", "Empréstimo com crédito do cartão"), li("https://dados.datalabglobal.com/", "Lente B2B: dados de empresas"),
                      li("https://www.datalabglobal.com/", "Todos os produtos Datalab")])
    return entenda, transp, legal, outros


def gerar_index(data_atualizacao, versoes_assets=None):
    versoes = versoes_assets or {n: "0" for _, n in ASSETS_HOME}
    url_home = f"{DOMINIO}/"
    data_br = date.fromisoformat(data_atualizacao).strftime('%d/%m/%Y')
    titulo_pagina = "Simulador de Financiamento de Veículos: Carro e Moto"  # ≤ 60 caracteres (sem o sufixo de marca)
    meta_description = (
        "Compare taxas reais de financiamento de carro novo, usado e moto entre os principais bancos "
        "do Brasil, com dados do Banco Central. Simule parcela e CET."
    )
    d = padrao_simulador_home()
    periodo = periodo_taxa_bacen() or data_br
    c = "novo"
    ordenados = sorted(bancos_para_categoria(c).items(), key=lambda kv: (kv[1]["taxa_am"], kv[0]))
    nome_b = lambda b: obter_regra(b)["nome_exibicao"] or b
    menor, maior = ordenados[0], ordenados[-1]
    todos = {b for cat in CATEGORIAS for b in bancos_para_categoria(cat)}

    schema_breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": url_home}],
    }
    schema_website = {
        "@context": "https://schema.org", "@type": "WebSite",
        "name": "Datalab Global", "url": url_home, "dateModified": data_atualizacao,
        "publisher": {"@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global", "url": "https://www.datalabglobal.com/"},
    }
    schema_app = {
        "@context": "https://schema.org", "@type": "WebApplication", "name": "Simulador de Financiamento de Veículos",
        "url": url_home, "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "inLanguage": "pt-BR",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "BRL"},
        "publisher": {"@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global"},
    }
    # "founder"/"contactPoint": sinais legíveis por máquina de que há gente real e contato real por trás do site (E-E-A-T/YMYL, 12/set/2026).
    schema_organization = {
        "@context": "https://schema.org", "@type": "Organization", "@id": "https://www.datalabglobal.com/#organization",
        "name": "Datalab Global", "url": "https://www.datalabglobal.com/", "logo": f"{DOMINIO}/logo-schema.png",
        "sameAs": ["https://huggingface.co/datalabglobal"],
        "founder": {"@type": "Person", "name": "Rodolfo Delfino", "sameAs": ["https://github.com/rldelfino", "https://www.kaggle.com/rodolfodelfino", "https://www.linkedin.com/in/rodolfo-leal-delfino"]},
        "contactPoint": {"@type": "ContactPoint", "email": "contato@datalabglobal.com", "contactType": "customer service"},
    }
    perguntas = [
        ("Como funciona o simulador de financiamento de veículos da Datalab?",
         "Você escolhe o tipo de veículo (carro novo, carro usado ou moto), o valor, a entrada e o prazo, e vê a parcela, o CET e o total pago "
         "com a taxa de um banco ou a média dos bancos. Os dados de taxa vêm do Banco Central e são atualizados semanalmente."),
        ("As taxas mostradas são reais ou só uma estimativa de marketing?",
         "São a taxa média efetivamente contratada por cada banco nessa modalidade, apurada pelo Banco Central (BACEN) — não é uma taxa "
         "promocional \"a partir de\". Sua taxa final depende do seu relacionamento com o banco e da análise de crédito."),
        ("O simulador cobra alguma coisa pra usar?",
         "Não, simular é 100% gratuito. A Datalab é remunerada pelo correspondente bancário quando você pede "
         "uma análise por aqui — isso não muda o valor da sua parcela nem qual banco você escolhe."),
    ]
    faq_html, schema_faq = _faq_home(perguntas)
    json_ld = render_json_ld(schema_breadcrumb, schema_website, schema_app, schema_organization, schema_faq,
                             schema_webpage(url_home, titulo_pagina, meta_description, data_atualizacao))
    medicao = ''.join('\n' + t for t in tags_medicao())

    from layout_home import HOME_MAIN, LAYOUT, LOGO
    linhas_am = _linhas_amort_anual(d["fin"], d["prazo"], d["taxa"])
    j1, a1 = linhas_am[0][1], linhas_am[0][2]
    pj = d["juros"] / d["total"]
    hoje = date.today()
    fim_m = hoje.month - 1 + d["prazo"]
    k_quita = f"{MESES_PT_ABREV[fim_m % 12]}/{hoje.year + fim_m // 12}"
    itens = []
    for b, v in ordenados:
        p = min(d["prazo"], v["prazo_max"])
        itens.append((b, calcular_pmt_price(d["fin"], p, v["taxa_am"]) * p - d["fin"]))
    j_menor = min(itens, key=lambda x: x[1])
    j_maior = max(itens, key=lambda x: x[1])

    entenda, transp, legal, outros = _rodape_home()
    nav = ('<a href="#simulador">Simular</a><a href="#comparar">Comparar bancos</a><a href="#taxas">Taxas de hoje</a>'
           '<a href="/aprenda">Aprenda</a><a href="/metodologia">Como calculamos</a>')
    subs = {
        "@@PERIODO@@": periodo,
        "@@D_HINT_BANCO@@": f"Média simples das taxas dos {len(ordenados)} bancos que acompanhamos (Banco Central). Escolha um banco para usar a taxa dele.",
        "@@D_PARCELA@@": "R$ " + _num_br(d["parcela"], 2),
        "@@D_SUB@@": f"em {d['prazo']} meses · taxa {_num_br(d['taxa'], 2)}% a.m.",
        "@@D_TOTAL@@": "R$ " + _num_br(d["total"]),
        "@@D_CET@@": _num_br(d["cet"], 2) + "% a.a.",
        "@@D_RESUMO@@": f"Você financia R$ {_num_br(d['fin'])} e paga R$ {_num_br(d['total'])} no total: R$ {_num_br(d['juros'])} a mais em juros.",
        "@@D_PCT_JUROS@@": str(round(pj * 100)),
        "@@D_ROSCA_P@@": f"{(1 - pj) * 289.0265:.1f}",
        "@@D_L_CRED@@": "R$ " + _num_br(d["fin"]),
        "@@D_L_JUROS@@": "R$ " + _num_br(d["juros"]),
        "@@D_VALOR@@": "R$ " + _num_br(d["valor"]),
        "@@D_BARRA@@": f"{(1 - entrada_minima(c)) * 100:.1f}",
        "@@D_FINANCIADO@@": "R$ " + _num_br(d["fin"]),
        "@@D_ENTRADA@@": "R$ " + _num_br(d["entrada"]),
        "@@D_K_QUITA@@": k_quita,
        "@@D_K_QUITA_S@@": f"{d['prazo']} parcelas, se contratar este mês",
        "@@D_K_JURO1@@": "R$ " + _num_br(d["juros"] / d["fin"], 2),
        "@@D_K_AA@@": _num_br(((1 + d["taxa"] / 100) ** 12 - 1) * 100, 2) + "%",
        "@@FATO_BANCOS@@": str(len(todos)),
        "@@FATO_MIN@@": _num_br(menor[1]["taxa_am"], 2) + "%",
        "@@FATO_MIN_NOME@@": nome_b(menor[0]),
        "@@FATO_MAX@@": _num_br(maior[1]["taxa_am"], 2) + "%",
        "@@FATO_MAX_NOME@@": nome_b(maior[0]),
        "@@D_CM_LEAD@@": f"Quanto o mesmo carro novo de R$ {_num_br(d['valor'])} custa em cada banco, com a mesma entrada e o mesmo prazo, ordenado do menor para o maior CET.",
        "@@D_CM_GAPV@@": "R$ " + _num_br(j_maior[1] - j_menor[1]),
        "@@D_CM_GAP@@": f"É a diferença nos juros pagos entre {nome_b(j_maior[0])} e {nome_b(j_menor[0])} neste cenário. Vale pedir mais de uma proposta.",
        "@@LINK_COMPARADOR@@": f"/{slug_comparador(c)}",
        "@@CAT_COMPARADOR@@": CATEGORIA_LABEL[c].lower(),
        "@@D_RAIO@@": f"Com a estimativa de R$ {_num_br(d['parcela'], 2)} por mês, veja o que muda com a mesma taxa:",
        "@@D_RENDA@@": (f"Com a referência de até cerca de 30% da renda, a parcela estimada de R$ {_num_br(d['parcela'], 2)} pede uma renda mensal "
                        f"comprovada de cerca de R$ {_num_br(d['parcela'] / 0.3)} (conta nossa, não é análise de crédito)."),
        "@@D_AMORT_PCT@@": str(round(j1 / (j1 + a1) * 100)),
        "@@D_AMORT_RESUMO@@": (f"No primeiro ano, de R$ {_num_br(j1 + a1)} pagos em parcelas, R$ {_num_br(j1)} são juros e só R$ {_num_br(a1)} "
                               "abatem a dívida. Por isso pagar a mais cedo faz diferença."),
        "@@D_AM_TAXA@@": _num_br(((1 + d["taxa"] / 100) ** 12 - 1) * 100, 2) + "%",
        "@@D_AMORT_LINHAS@@": "".join(
            f'<tr><th scope="row">Ano {a}</th><td>R$ {_num_br(j)}</td><td>R$ {_num_br(am)}</td><td>R$ {_num_br(s)}</td></tr>' for a, j, am, s in linhas_am),
        "@@D_AMORT_TOTAL@@": (f'<tr><th scope="row">Total</th><td>R$ {_num_br(sum(x[1] for x in linhas_am))}</td>'
                              f'<td>R$ {_num_br(sum(x[2] for x in linhas_am))}</td><td>—</td></tr>'),
        "@@TABELAS_TAXAS@@": html_tabelas_taxas_home() + (
            f'\n    <p class="hint">Taxa média efetivamente contratada, atualizada em {data_br}, com base no Banco Central do Brasil. '
            f'Não é oferta de crédito: a sua taxa depende da análise do banco. Veja a <a href="/metodologia">metodologia</a>.</p>'),
        "@@CARTOES_CATEGORIA@@": _cartoes_categoria_home(),
        "@@CARTOES_GUIAS@@": _cartoes_guias_home(),
        "@@FAQ@@": faq_html,
        "@@PARCEIRO@@": LINK_FINANCIA_TUDO,
    }
    main = HOME_MAIN
    for k, v in subs.items():
        main = main.replace(k, v)
    dados_json = json.dumps(dados_simulador_home(), ensure_ascii=False, separators=(",", ":"))
    scripts = (f'<script type="application/json" id="dados-sim">{dados_json}</script>\n'
               f'<script src="/calculo.js?v={VERSAO_BUILD}"></script>\n'
               f'<script src="/home.js?v={versoes["home.js"]}"></script>\n'
               f'<script src="/menu.js?v={versoes["menu.js"]}"></script>\n')
    pagina = LAYOUT
    trocas = {
        "@@TITLE@@": html.escape(titulo_pagina), "@@DESC@@": html.escape(meta_description), "@@CANONICAL@@": url_home,
        "@@ICONV@@": "20261120", "@@DOMINIO@@": DOMINIO, "@@CSSV@@": versoes["home.css"], "@@JSONLD@@": json_ld + "\n",
        "@@MEDICAO@@": medicao, "@@LOGO@@": LOGO, "@@NAV@@": nav, "@@NAVMOBILE@@": nav + '<a href="/sobre">Sobre</a>',
        "@@FOOT_ENTENDA@@": entenda, "@@FOOT_TRANSP@@": transp, "@@FOOT_LEGAL@@": legal, "@@FOOT_OUTROS@@": outros,
        "@@ATUALIZADO@@": data_br, "@@PERIODO@@": periodo, "@@RAZAO@@": EMPRESA_RODAPE, "@@SCRIPTS@@": scripts, "@@MAIN@@": main,
    }
    for k, v in trocas.items():
        pagina = pagina.replace(k, v)
    return pagina


_EXEMPLOS_GUIAS = None


def _exemplos_guias():
    """Exemplos calculados dos guias (ver exemplos_guias.py); montados na primeira chamada."""
    global _EXEMPLOS_GUIAS
    if _EXEMPLOS_GUIAS is None:
        import exemplos_guias
        _EXEMPLOS_GUIAS = exemplos_guias.montar_exemplos(
            calcular_pmt_price, calcular_iof_veiculo, calcular_cet_veiculo, TARIFA_REGISTRO_CONTRATO, formatar_reais, calcular_renda_sugerida)
    return _EXEMPLOS_GUIAS


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
    bloco_exemplo = _exemplos_guias().get(art["slug"], "")
    bloco_fontes = html_fontes_guia(art["slug"], art.get("fontes"))
    bloco_exemplo_html = ("\n            " + bloco_exemplo) if bloco_exemplo else ""
    # Data REAL da última mudança do texto do guia (hash do conteúdo, ver lastmod.py), não a data das taxas.
    data_guia_iso = lastmod.registrar(_MANIFESTO_LASTMOD, "guia:" + art["slug"],
                                      art["titulo_h1"] + art["meta_description"] + art["corpo_html"] + bloco_exemplo + bloco_fontes)
    schema_article = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": art["titulo_h1"], "url": url_canonica,
        "author": {"@type": "Organization", "@id": "https://www.datalabglobal.com/#organization", "name": "Datalab Global", "url": f"{DOMINIO}/sobre"},
        "publisher": {
            "@type": "Organization", "name": "Datalab Global",
            "logo": {"@type": "ImageObject", "url": f"{DOMINIO}/logo-schema.png"},
        },
        "dateModified": data_guia_iso[:10], "mainEntityOfPage": url_canonica,
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
            {art["corpo_html"]}{bloco_exemplo_html}
            {bloco_fontes}
        </div>
        <p class="text-xs text-slate-400 mt-4">Texto atualizado em {lastmod.data_br(data_guia_iso)}. Conteúdo educativo da Datalab Global (<a href="/sobre" class="underline">quem somos</a> · <a href="/metodologia" class="underline">como calculamos</a>); não é recomendação de crédito.</p>
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
            "sameAs": ["https://huggingface.co/datalabglobal"],
            "founder": {"@type": "Person", "name": "Rodolfo Delfino", "sameAs": ["https://github.com/rldelfino", "https://www.kaggle.com/rodolfodelfino", "https://www.linkedin.com/in/rodolfo-leal-delfino"]},
            "contactPoint": {"@type": "ContactPoint", "email": "contato@datalabglobal.com", "contactType": "customer service"},
        },
    }
    schema_bc_sobre = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Datalab Global", "item": f"{DOMINIO}/"},
        {"@type": "ListItem", "position": 2, "name": "Sobre", "item": url_canonica}]}
    head = render_head(titulo_pagina, meta_description, url_canonica, [schema_bc_sobre, schema_sobre])
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

def gerar_sitemap(urls, data_atualizacao, pasta_saida="paginas_seo"):
    """Sitemap com `lastmod` REAL por URL (ISO 8601 com hora, UTC): a data só avança quando o HTML da página muda
    (ver lastmod.py). `changefreq` e `priority` não entram: o Bing diz que ignora (blog do Bing, jul/2025) e o
    Google também não usa."""
    def lm(url):
        caminho = url[len(DOMINIO):].strip("/")
        arquivo = os.path.join(pasta_saida, (caminho or "index") + ".html")
        if os.path.exists(arquivo):
            with open(arquivo, "rb") as f:
                # O link do CSS leva um carimbo de build (styles.css?v=AAAAMMDDHHMMSS) que muda a cada
                # geração; ele não conta como mudança de conteúdo da página.
                # CRLF vira LF: gerar no Windows grava CRLF e o git guarda LF; sem isso o resumo muda de uma
                # plataforma para a outra e TODAS as URLs ganham lastmod novo (visto em 17/nov/2026)
                conteudo = re.sub(rb"styles\.css\?v=\d+", b"styles.css?v=0", f.read().replace(b"\r\n", b"\n"))
                # idem para calculo.js/medicao.js: tira o carimbo (sem bump falso de lastmod ao introduzi-lo)
                conteudo = re.sub(rb"\.js\?v=\d{14}", b".js", conteudo)
                return lastmod.registrar(_MANIFESTO_LASTMOD, "url:" + url, conteudo)
        return f"{data_atualizacao}T00:00:00+00:00"
    partes = ['<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url in [f"{DOMINIO}/"] + list(urls):
        partes.append(f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{lm(url)}</lastmod>\n  </url>")
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
    <link rel="icon" href="favicon.ico?v=20261120" sizes="any">
    <link rel="icon" href="favicon-32.png?v=20261120" type="image/png" sizes="32x32">
    <link rel="icon" href="favicon-192.png?v=20261120" type="image/png" sizes="192x192">
    <link rel="apple-touch-icon" href="apple-touch-icon.png?v=20261120">
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


def gerar_llms_txt(total_paginas, data_atualizacao):  # total_paginas = número de hubs por banco
    return f"""# Datalab Global — Financiamento de Veículos

> Simulador de financiamento de veículos (carro novo, carro usado e moto) para os principais bancos do Brasil (Caixa, Banco do Brasil, Bradesco, Santander, Itaú, Banco Inter, C6 Bank, BV Financeira, Banco Pan, Omni Financeira, Banco Honda, Banco Yamaha). Taxas com base no Relatório de Taxas de Juros por Instituição Financeira do Banco Central. Calcula parcela (Tabela Price), CET estimado (incluindo IOF) e tabela de amortização.

Dados atualizados em: {data_atualizacao}
Páginas por banco (carro novo e usado, e moto): {total_paginas}

## Páginas
- [Home]({DOMINIO}/)
- [Comparador Carro Novo]({DOMINIO}/{slug_comparador('novo')})
- [Comparador Carro Usado]({DOMINIO}/{slug_comparador('usado')})
- [Comparador Moto]({DOMINIO}/{slug_comparador('moto')})
- [Financiamento de veículo: parcela por valor e prazo]({DOMINIO}/financiamento-veiculos)
- [Dados abertos: taxas de financiamento por banco, série mensal em CSV e JSON]({DOMINIO}/dados-abertos) (cópia no Kaggle: {URL_KAGGLE})
- [Simulador de financiamento de veículos para incorporar no seu site (grátis)]({DOMINIO}/incorporar)
- [Imprensa: números atualizados para citar]({DOMINIO}/imprensa)
- [Taxas de financiamento de veículos mês a mês, desde 2024]({DOMINIO}/taxas-financiamento-veiculos)
- [Metodologia: fonte das taxas e fórmulas]({DOMINIO}/metodologia)
- [O que mudou esta semana nas taxas]({DOMINIO}/atualizacoes)
- [Feed Atom das atualizações de taxa]({DOMINIO}/feed.xml)
- [Renda necessária para financiar um veículo, por valor]({DOMINIO}/renda-para-financiar-veiculo)
- [Versão completa com os números atuais]({DOMINIO}/llms-full.txt)
- [Sitemap completo]({DOMINIO}/sitemap.xml)

## Sobre os dados
Taxa de juros e prazo máximo são específicos de cada instituição e categoria de veículo. Prazo máximo e entrada mínima seguem convenção geral de mercado (ainda não confirmada banco a banco em fonte oficial — ver bancos_veiculos.py). Cada página de simulação (padrão de URL: /financiamento-{{categoria}}-{{banco}}-{{valor}}-mil-{{prazo}}-meses) traz parcela, CET e tabela de amortização completa para o cenário daquele banco/valor/prazo específico. As taxas são simulações representativas, não uma cotação — a taxa final de cada cliente depende de fatores fora do nosso controle (relacionamento bancário, histórico de crédito, seguradora escolhida).
"""


# Verificação do Yandex Webmaster (20/11/2026): o mesmo arquivo serve a todos os subdomínios da Datalab. Conteúdo exato pedido pelo Yandex.
YANDEX_VERIFICACAO = "90c15c3be650b0ed"


def gerar_verificacao_yandex(pasta_saida):
    conteudo = ('<html>\n<head>\n<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">\n</head>\n'
                f'<body>Verification: {YANDEX_VERIFICACAO}</body>\n</html>')
    with open(os.path.join(pasta_saida, f"yandex_{YANDEX_VERIFICACAO}.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(conteudo)


CSP_HOME = ("default-src 'self'; script-src 'self' https://cloud.umami.is; style-src 'self'; img-src 'self' data:; font-src 'self'; "
            "connect-src 'self' https://cloud.umami.is https://api-gateway.umami.dev https://gateway.umami.is; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'; object-src 'none'")


# ---------------------------------------------------------------------------
# Enxugamento (21/11/2026): páginas que saíram e para onde redirecionam (301). Ver AVALIACAO-SUBPAGINAS.md.
# Cloudflare Pages: _redirects aceita 2.000 regras estáticas e 100 com asterisco ou :placeholder; vale a primeira regra que casar.
# ---------------------------------------------------------------------------
LIMITE_REDIRECTS_ESTATICOS = 2000
LIMITE_REDIRECTS_DINAMICOS = 100


def regras_redirect():
    """[(origem, destino)] na ordem de avaliação. Os endereços com .html (que o Google chegou a indexar) casam nas mesmas regras de asterisco;
    as regras estáticas ganham também a variante .html."""
    regras = []
    for categoria in CATEGORIAS:
        for banco in bancos_para_categoria(categoria):
            regras.append((f"/financiamento-{CATEGORIA_SLUG[categoria]}-{slugificar_banco(banco)}-*", "/" + slug_hub(categoria, banco)))
    estaticas = []
    for banco in bancos_para_categoria("usado"):
        estaticas.append((f"/hub-{slugificar_banco(banco)}-carro-usado", "/" + slug_hub("usado", banco)))
    for categoria in CATEGORIAS:
        regras.append((f"/financiamento-{CATEGORIA_SLUG[categoria]}-*", "/" + slug_comparador(categoria)))
        regras.append((f"/renda-para-financiar-{CATEGORIA_SLUG[categoria]}-*", "/" + SLUG_INDICE_RENDA))
    meses = sorted({r["mes_referencia"] for r in historico_cache()})
    # Todo mês desde out/2024 (o primeiro que chegou a ser publicado, mesmo fora da série atual) até o último que perdeu a página.
    if meses:
        ano, mes = 2024, 10
        limite = meses[-MESES_INDEXAVEIS_MENSAL - 1] if len(meses) > MESES_INDEXAVEIS_MENSAL else "2024-10"
        while f"{ano}-{mes:02d}" <= limite:
            estaticas.append(("/" + slug_mes(f"{ano}-{mes:02d}"), "/" + SLUG_INDICE_MENSAL))
            ano, mes = (ano + 1, 1) if mes == 12 else (ano, mes + 1)
    # Regras estáticas primeiro: no Cloudflare Pages toda regra que vem DEPOIS de uma com asterisco passa a contar no limite de 100 das dinâmicas
    # (achado no wrangler pages dev em 21/11/2026: com as estáticas no fim, 5 regras foram descartadas). As origens estáticas não casam com os asteriscos.
    primeiras = []
    for origem, destino in estaticas:
        primeiras.append((origem, destino))
        primeiras.append((origem + ".html", destino))
    return primeiras + regras


def gerar_redirects():
    regras = regras_redirect()
    din = [r for r in regras if "*" in r[0] or ":" in r[0]]
    est = [r for r in regras if r not in din]
    assert len(din) <= LIMITE_REDIRECTS_DINAMICOS and len(est) <= LIMITE_REDIRECTS_ESTATICOS, (len(din), len(est))
    linhas = ["# Gerado por gerador_veiculos.py (regras_redirect). Páginas removidas no enxugamento de 21/11/2026 (ver AVALIACAO-SUBPAGINAS.md).",
              "# Ordem importa: vale a primeira regra que casar. Nenhuma URL do sitemap aparece como origem."]
    # O Cloudflare Pages redireciona /arquivo.html para /arquivo (308); o Yandex quer o 200 direto no endereço com .html: regra de reescrita (200).
    linhas.append(f"/yandex_{YANDEX_VERIFICACAO}.html /yandex_{YANDEX_VERIFICACAO} 200")
    linhas += [f"{o} {d} 301" for o, d in regras]
    return "\n".join(linhas) + "\n"


def _arquivo_removido(nome):
    """True para o nome de um .html de página que saiu do site (e agora redireciona)."""
    base = nome[:-5] if nome.endswith(".html") else nome
    if re.match(r"financiamento-(carro-novo|carro-usado|moto)-.+", base):
        return True
    if re.match(r"renda-para-financiar-(carro-novo|carro-usado|moto)-.+", base):
        return True
    if re.match(r"hub-.+-carro-usado$", base):
        return True
    m = re.match(rf"{SLUG_INDICE_MENSAL}-([a-z]+)-(\d{{4}})$", base)
    if m:
        meses = sorted({r["mes_referencia"] for r in historico_cache()})
        recentes = {slug_mes(x) for x in meses[-MESES_INDEXAVEIS_MENSAL:]}
        return base not in recentes
    return False


def limpar_paginas_obsoletas(pasta_saida):
    """Apaga os .html das páginas que viraram 301 (o gerador só escreve, nunca apagava)."""
    apagados = []
    for nome in sorted(os.listdir(pasta_saida)):
        if nome.endswith(".html") and _arquivo_removido(nome):
            os.remove(os.path.join(pasta_saida, nome))
            apagados.append(nome)
    return apagados


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
        "img-src 'self' data: https:; connect-src 'self' https://cloudflareinsights.com https://cloud.umami.is https://gateway.umami.is; frame-ancestors 'none'; "
        "base-uri 'self'; form-action 'self'\n\n"
        "# A home (/) usa CSP sem 'unsafe-inline' (sem style nem script inline). O '!' remove a CSP herdada de /* antes de definir a própria.\n"
        "/\n"
        "  ! Content-Security-Policy\n"
        f"  Content-Security-Policy: {CSP_HOME}\n\n"
        "/styles.css\n"
        "  Cache-Control: public, max-age=31536000, immutable\n\n"
        "/home.css\n"
        "  Cache-Control: public, max-age=31536000, immutable\n\n"
        "/home.js\n"
        "  Cache-Control: public, max-age=31536000, immutable\n\n"
        "/menu.js\n"
        "  Cache-Control: public, max-age=31536000, immutable\n\n"
        "/fonts/*\n"
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
    global _MANIFESTO_LASTMOD
    os.makedirs(pasta_saida, exist_ok=True)
    _MANIFESTO_LASTMOD = lastmod.carregar()
    data_atualizacao = obter_data_ultima_atualizacao()

    # Enxugamento (21/11/2026): as páginas banco x valor x prazo (840) e comparação sem marca (80) não são mais geradas; a grade só alimenta os hubs.
    paginas = gerar_grade_paginas()
    lookup = {}

    urls_sitemap = []

    hubs = {}
    for p in paginas:
        if p["categoria"] == "usado":
            continue  # o hub de carro usado é o de carro novo (mesma taxa por banco no Banco Central)
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
    urls_sitemap.extend(gerar_analise_do_mes(pasta_saida, data_atualizacao))
    urls_sitemap.extend(gerar_paginas_mensais(pasta_saida, data_atualizacao, historico_cache()))
    urls_sitemap.extend(gerar_pagina_metodologia(pasta_saida, data_atualizacao))
    historico_semanal = registrar_snapshot_semanal(data_atualizacao)
    urls_sitemap.extend(gerar_pagina_atualizacoes(pasta_saida, data_atualizacao, historico_semanal))
    gerar_feed_atom(pasta_saida, data_atualizacao, historico_cache(), historico_semanal)
    urls_sitemap.extend(gerar_paginas_renda(pasta_saida, data_atualizacao))
    gerar_llms_full_txt(pasta_saida, data_atualizacao, historico_cache())
    gerar_medicao_js(pasta_saida)

    versoes_home = copiar_assets_home(pasta_saida)
    with open(os.path.join(pasta_saida, "index.html"), "w", encoding="utf-8") as f:
        f.write(gerar_index(data_atualizacao, versoes_home))
    gerar_verificacao_yandex(pasta_saida)

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

    # Logo, favicons, apple-touch-icon, logo-schema, logo-header e og-image: arquivos ESTÁTICOS versionados em paginas_seo/, gerados por
    # gerar_icones.py (desenho em SVG em layout_home.py; precisa de Playwright e Pillow, por isso não roda aqui nem no CI).

    with open(os.path.join(pasta_saida, "calculo.js"), "w", encoding="utf-8") as f:
        f.write(gerar_calculo_js())

    with open(os.path.join(pasta_saida, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(gerar_sitemap(urls_sitemap, data_atualizacao, pasta_saida))
    # o manifesto de lastmod só guarda as URLs que ainda estão no sitemap (as páginas removidas no enxugamento saem dele)
    vivas = {"url:" + u for u in [f"{DOMINIO}/"] + list(urls_sitemap)}
    for chave in [k for k in _MANIFESTO_LASTMOD if k.startswith("url:") and k not in vivas]:
        del _MANIFESTO_LASTMOD[chave]
    lastmod.salvar(_MANIFESTO_LASTMOD)

    removidos = limpar_paginas_obsoletas(pasta_saida)
    with open(os.path.join(pasta_saida, "_redirects"), "w", encoding="utf-8", newline="\n") as f:
        f.write(gerar_redirects())
    if removidos:
        print(f"Removidos {len(removidos)} arquivos de páginas que agora redirecionam (301).")

    with open(os.path.join(pasta_saida, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(gerar_robots_txt())

    with open(os.path.join(pasta_saida, "404.html"), "w", encoding="utf-8") as f:
        f.write(gerar_404())

    with open(os.path.join(pasta_saida, "llms.txt"), "w", encoding="utf-8") as f:
        f.write(gerar_llms_txt(len(hubs), data_atualizacao))

    with open(os.path.join(pasta_saida, "_headers"), "w", encoding="utf-8") as f:
        f.write(gerar_headers())

    total_arquivos = len(hubs) + len(CATEGORIAS) + 1
    print(f"Gerado: {len(hubs)} hubs, {len(CATEGORIAS)} comparadores, "
          f"1 index — {total_arquivos} páginas HTML no total, em '{pasta_saida}/'.")
    return paginas


if __name__ == "__main__":
    gerar_site()
