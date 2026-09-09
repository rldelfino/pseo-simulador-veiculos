"""
Fonte única de verdade das regras de negócio por instituição financeira
para financiamento de veículos (carro novo, carro usado/seminovo, moto).

Segue o mesmo padrão do projeto irmão (pseo_simulador/bancos.py): uma
entrada por banco aqui, nada duplicado/hardcoded em outro lugar. Tanto o
etl_taxas_veiculos.py (atualização semanal automática) quanto o
gerador_veiculos.py (geração das páginas pSEO) importam deste módulo.

FONTE DAS TAXAS (campos taxa_am / taxa_aa)
-------------------------------------------
Banco Central do Brasil — Relatório de Taxas de Juros por Instituição
Financeira, modalidade "Pessoa Física - Aquisição de veículos -
Prefixado" (código de modalidade 401101):
https://www.bcb.gov.br/estatisticas/reporttxjuros?codigoSegmento=1&codigoModalidade=401101

Por que esta fonte e não comparativos de blog: é a taxa MÉDIA REAL
praticada em operações efetivamente contratadas, apurada semanalmente
pelo próprio BACEN — não uma taxa promocional "a partir de X%" de
material de marketing do banco. No projeto irmão (pseo_simulador), uma
taxa promocional do Banco Inter foi confundida com a taxa típica de
mercado e teve que ser corrigida (ver bancos.py); aqui evitamos o mesmo
erro usando a fonte regulatória desde o início. Uma pesquisa inicial via
blogs comparativos (idinheiro, creditas etc.) trouxe números bem mais
otimistas que o BACEN para praticamente todo banco (ex.: BV Financeira
"a partir de 1,14% a.m." vs. 2,25% a.m. na média real do BACEN) —
exatamente o tipo de dado que a lição do projeto irmão manda descartar.

Período de referência da última coleta: 17/08/2026 a 21/08/2026 (relatório
é semanal). Como atualizar: reabrir a URL acima, que lista ~37
instituições em 2 páginas ordenadas por taxa crescente, e atualizar
taxa_am/taxa_aa + PERIODO_REFERENCIA_TAXAS abaixo. taxa_am e taxa_aa vêm
como o BACEN reporta (aa não é simplesmente am composto no relatório
deles) — não recalcular um a partir do outro.

IMPORTANTE — o BACEN não publica prazo/entrada por modalidade de veículo
--------------------------------------------------------------------
O relatório acima tem UMA ÚNICA modalidade "Aquisição de veículos" — não
existe quebra oficial entre carro novo, usado e moto. Os campos abaixo
que dependem de política contratual de cada banco (prazo_max,
entrada_minima) NÃO vêm do BACEN e ainda NÃO foram confirmados banco a
banco em fonte oficial (site de cada instituição). Por ora usam a
convenção geral de mercado brasileiro (prazo máximo comum de até 60
meses; entrada mínima praticada na faixa de 20% para carro novo e
30% para usado/moto — veículo mais velho e mais depreciação implicam
menor LTV aceito pelos bancos). TRATAR COMO ESTIMATIVA DE LANÇAMENTO,
não como dado auditado — antes de publicar em produção, o ideal é
confirmar prazo_max e entrada_minima direto na página de cada banco (o
mesmo cuidado que já vale para taxa, lição acima).

Itaú tem uma linha promocional para elétricos/híbridos, confirmada por
imprensa especializada (Automotive Business), mas a taxa promocional
exata circulando em blogs (8,73% a.a.) não foi confirmada em fonte
primária do próprio Itaú — por isso NÃO está codificada como campo
numérico aqui ainda. Ver nota em ITENS_A_VALIDAR no fim do arquivo.
"""

import json
import os
import unicodedata

PERIODO_REFERENCIA_TAXAS = "17/08/2026 a 21/08/2026"
FONTE_TAXAS_URL = "https://www.bcb.gov.br/estatisticas/reporttxjuros?codigoSegmento=1&codigoModalidade=401101"

# Convenção geral de mercado (não é dado BACEN) usada como placeholder até
# confirmação banco a banco — ver docstring acima.
ENTRADA_MINIMA_POR_CATEGORIA = {"novo": 0.20, "usado": 0.30, "moto": 0.30}
PRAZO_MAX_PADRAO = 60  # meses

# chave = identidade estável do banco (sem acento, usada em slugs/URLs)
# nome_exibicao = como o nome aparece no texto (com acento, correto)
# taxa_am / taxa_aa = média real BACEN, ver PERIODO_REFERENCIA_TAXAS
# aplica_a = categorias de veículo em que este banco é relevante pro pSEO
BANCOS_VEICULOS = {
    "Caixa": {
        "nome_exibicao": "Caixa",
        "taxa_am": 1.01, "taxa_aa": 12.83,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "caixa.gov.br",
    },
    "Banco do Brasil": {
        "nome_exibicao": "Banco do Brasil",
        "taxa_am": 1.83, "taxa_aa": 24.26,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "bb.com.br",
    },
    "Bradesco": {
        "nome_exibicao": "Bradesco",
        "taxa_am": 1.78, "taxa_aa": 23.63,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "bradesco.com.br",
    },
    "Santander": {
        "nome_exibicao": "Santander",
        "taxa_am": 1.80, "taxa_aa": 23.80,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "santander.com.br",
    },
    "Itau": {
        "nome_exibicao": "Itaú",
        "taxa_am": 2.07, "taxa_aa": 27.88,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "itau.com.br",
    },
    "Banco Inter": {
        "nome_exibicao": "Banco Inter",
        "taxa_am": 1.86, "taxa_aa": 24.80,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "bancointer.com.br",
    },
    "C6 Bank": {
        "nome_exibicao": "C6 Bank",
        "taxa_am": 1.91, "taxa_aa": 25.44,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "c6bank.com.br",
    },
    "BV Financeira": {
        "nome_exibicao": "BV Financeira",
        # No relatório do BACEN esta instituição aparece com a razão social
        # "BCO VOTORANTIM S.A." (BV é o nome fantasia atual do antigo Banco
        # Votorantim) — mesma taxa, nome de exibição atualizado pro que o
        # público pesquisa hoje.
        "taxa_am": 2.25, "taxa_aa": 30.64,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "bv.com.br",
    },
    "Banco Pan": {
        "nome_exibicao": "Banco Pan",
        "taxa_am": 2.88, "taxa_aa": 40.61,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "bancopan.com.br",
    },
    "Omni Financeira": {
        "nome_exibicao": "Omni Financeira",
        # A razão social no relatório BACEN é "OMNI SA CFI".
        "taxa_am": 3.35, "taxa_aa": 48.42,
        "prazo_max": 60, "aplica_a": ["novo", "usado", "moto"],
        "dominio_favicon": "omni.com.br",
    },
    "Banco Honda": {
        "nome_exibicao": "Banco Honda",
        # Financeira cativa: só faz sentido pro público que busca
        # "financiamento moto Honda" — não incluir em páginas de carro.
        "taxa_am": 2.46, "taxa_aa": 33.79,
        "prazo_max": 48, "aplica_a": ["moto"],
        "dominio_favicon": "honda.com.br",
    },
    "Banco Yamaha": {
        "nome_exibicao": "Banco Yamaha",
        "taxa_am": 2.58, "taxa_aa": 35.77,
        "prazo_max": 48, "aplica_a": ["moto"],
        "dominio_favicon": "yamaha-motor.com.br",
    },
}

# Achado real (08/set/2026, "implemente o ETL semanal" pedido pelo usuário
# depois da auditoria de pronto-pra-subir): os taxa_am/taxa_aa acima são o
# snapshot "bootstrap" curado à mão (17-21/ago/2026, ver docstring do
# arquivo) — sem isso, o produto nasceria sem nenhum dado até a primeira
# rodagem do ETL. A partir da primeira rodagem de etl_taxas_veiculos.py,
# porém, a fonte de verdade passa a ser taxas_cache_veiculos.json (gerado
# por ele), aplicado aqui por cima do bootstrap logo após BANCOS_VEICULOS
# ser definido — mesmo princípio do projeto irmão (bancos.py guarda
# taxa_padrao de bootstrap, dados.csv guarda a verdade corrente), só que
# sem precisar de um CSV externo pra um produto que nunca teve um: aqui o
# "arquivo externo" é só o cache do próprio ETL.
#
# Path resolvido via os.path.dirname(__file__), não relativo ao cwd: este
# módulo é importado tanto por gerador_veiculos.py quanto pelos testes
# (tests/test_*.py, que rodam de um cwd diferente da raiz do projeto) — um
# path relativo ingênuo ("taxas_cache_veiculos.json" sem mais nada)
# funcionaria só quando o processo é lançado da raiz do projeto, e falharia
# silenciosamente (FileNotFoundError tratado como "cache não existe ainda")
# rodando de qualquer outro diretório.
_ARQUIVO_CACHE_TAXAS = os.path.join(os.path.dirname(__file__), "taxas_cache_veiculos.json")


def _aplicar_cache_taxas():
    """Sobrescreve taxa_am/taxa_aa em BANCOS_VEICULOS com o que
    etl_taxas_veiculos.py encontrou de mais recente, se o arquivo de cache
    existir. Nunca remove nem adiciona banco — só atualiza taxa de banco
    que já está na matriz; um banco no cache que não existe mais aqui
    (removido do produto) é ignorado silenciosamente, de propósito (a
    matriz de BANCOS_VEICULOS é sempre quem decide QUAIS bancos existem,
    o cache só decide a TAXA de quem já existe)."""
    try:
        with open(_ARQUIVO_CACHE_TAXAS, encoding="utf-8") as f:
            cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    for banco, dados in cache.items():
        if banco not in BANCOS_VEICULOS:
            continue
        if "taxa_am" in dados:
            BANCOS_VEICULOS[banco]["taxa_am"] = dados["taxa_am"]
        if "taxa_aa" in dados:
            BANCOS_VEICULOS[banco]["taxa_aa"] = dados["taxa_aa"]


_aplicar_cache_taxas()

REGRA_FALLBACK = {
    "nome_exibicao": None,
    # Média simples dos bancos universais listados acima (exclui as
    # financeiras cativas de moto) — usada só se um banco desconhecido for
    # consultado; nunca deveria aparecer em produção com a matriz completa.
    # Achado real (08/set/2026, auditoria pedida pelo usuário): taxa_aa
    # estava em 27.88 — igual ao Itaú, não a média real dos 10 bancos
    # (28.23, recalculada e conferida à mão). taxa_am já estava correto
    # (2.07 bate com a média real). Corrigido pra não mostrar uma taxa
    # anual levada errada no caminho de fallback, mesmo ele hoje nunca
    # sendo alcançado com a matriz completa.
    "taxa_am": 2.07, "taxa_aa": 28.23,
    "prazo_max": PRAZO_MAX_PADRAO, "aplica_a": ["novo", "usado", "moto"],
    "dominio_favicon": "google.com",
}

# Itens que saíram da pesquisa inicial mas foram descartados de propósito:
# Banco Volvo, Sinosserra, Banco CNH Industrial, Banco Komatsu, Banco
# Caterpillar, Scania, Banco Traton — aparecem no MESMO relatório BACEN
# (é uma lista única pra "aquisição de veículos", sem distinguir carro de
# caminhão/máquina agrícola), mas são financiamento de caminhão/máquina
# pesada, fora do público-alvo deste produto (carro de passeio e moto).


def normalizar_chave(nome):
    """Remove acentos/caixa para permitir lookup tolerante (ex: 'Itaú' -> 'Itau')."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    return sem_acento.strip()


_INDICE_NORMALIZADO = {normalizar_chave(k): k for k in BANCOS_VEICULOS}


def obter_regra(nome_banco):
    """Busca a regra do banco tolerando variações de acentuação (Itau/Itaú)."""
    if nome_banco in BANCOS_VEICULOS:
        return BANCOS_VEICULOS[nome_banco]
    chave_normalizada = normalizar_chave(nome_banco)
    if chave_normalizada in _INDICE_NORMALIZADO:
        return BANCOS_VEICULOS[_INDICE_NORMALIZADO[chave_normalizada]]
    regra = dict(REGRA_FALLBACK)
    regra["nome_exibicao"] = nome_banco
    return regra


def nome_exibicao(nome_banco):
    regra = obter_regra(nome_banco)
    return regra["nome_exibicao"] or nome_banco


def bancos_para_categoria(categoria):
    """categoria: 'novo' | 'usado' | 'moto'. Filtra a matriz pros bancos
    relevantes pra essa categoria de veículo (ex: Banco Honda só em 'moto')."""
    if categoria not in ("novo", "usado", "moto"):
        raise ValueError(f"categoria inválida: {categoria!r}")
    return {k: v for k, v in BANCOS_VEICULOS.items() if categoria in v["aplica_a"]}


def entrada_minima(categoria):
    if categoria not in ENTRADA_MINIMA_POR_CATEGORIA:
        raise ValueError(f"categoria inválida: {categoria!r}")
    return ENTRADA_MINIMA_POR_CATEGORIA[categoria]


# ---------------------------------------------------------------------------
# ITENS_A_VALIDAR — pendências explícitas antes de tratar este arquivo como
# fonte definitiva (não gerar conteúdo em massa antes disso; ver instrução
# do usuário sobre validar dados de banco antes do gerador).
# ---------------------------------------------------------------------------
ITENS_A_VALIDAR = [
    "prazo_max e ENTRADA_MINIMA_POR_CATEGORIA são convenção geral de "
    "mercado, não confirmados individualmente por banco em fonte oficial.",
    "Itaú: existe linha promocional real para elétricos/híbridos "
    "(confirmado via Automotive Business), mas a taxa exata (8,73% a.a. "
    "citada em pesquisa inicial) não foi confirmada em fonte primária do "
    "Itaú — não codificar sem essa confirmação.",
    "Moto: taxas de mercado geral (não-cativas) tendem a ser mais altas "
    "que carro pro mesmo banco: ainda não temos uma fonte BACEN separada "
    "por categoria pra confirmar o tamanho exato dessa diferença — os "
    "bancos universais acima usam a MESMA taxa pra novo/usado/moto por "
    "ora, o que provavelmente subestima a taxa real de moto.",
]
