"""
ETL semanal de taxas de financiamento de veículos — atualiza taxa_am/taxa_aa
de cada banco em BANCOS_VEICULOS (bancos_veiculos.py) a partir do relatório
oficial do Banco Central, na mesma modalidade já usada como fonte manual do
produto (ver PERIODO_REFERENCIA_TAXAS/FONTE_TAXAS_URL em bancos_veiculos.py):
"Pessoa Física - Aquisição de veículos - Prefixado" (código 401101).

Implementado nos mesmos moldes do etl_taxas.py do projeto irmão (imobiliário),
com duas diferenças estruturais reais, não cosméticas:

1. Automação SEMANAL (pedido explícito do usuário), não mensal — diferente
   da modalidade imobiliária (903201), que só publica agregado MENSAL
   ("M" em ConsultaDatas), a modalidade de veículo (401101) só tem períodos
   "D" (achado ao vivo, 08/set/2026, antes de escrever este arquivo:
   ConsultaDatas pra 401101 não devolveu nenhum "M" recente — teria sido
   erro copiar o filtro "M" do projeto irmão sem checar). "D" aqui NÃO é
   "diário" nem estritamente "semanal": é uma janela móvel de ~5 dias úteis
   publicada A CADA dia útil (períodos observados ao vivo se sobrepõem,
   ex. "17/08 a 21/08" seguido de "18/08 a 24/08") — na prática, o dado
   mais recente muda com frequência maior que uma vez por semana. A
   automação em si roda semanalmente por escolha do usuário (frequência
   de publicação da fonte não obriga a mesma frequência de coleta); cada
   rodagem pega o período "D" mais recente disponível NO MOMENTO em que
   roda, então nunca fica mais de ~1 semana desatualizada mesmo rodando
   só 1x/semana.

2. UMA fonte só (o BACEN), não uma lista com fallback de blog — diferente do
   imobiliário (que precisa de 2 fontes de blog pra cobrir BRB/Poupex, que a
   modalidade 903201 não lista), esta modalidade cobriu TODOS os 12 bancos de
   BANCOS_VEICULOS na checagem ao vivo feita antes de escrever este arquivo
   (08/set/2026) — não existe hoje nenhum banco órfão que precise de fonte
   alternativa. Por isso _ESTRATEGIAS_BUSCA/FONTES_TAXA_TIPICA do projeto
   irmão (que existem pra generalizar múltiplos tipos de fonte) não têm
   equivalente aqui — seria complexidade sem uso real. Se um dia um banco
   novo entrar em BANCOS_VEICULOS sem cobertura nesta modalidade, ele cai no
   mesmo fallback de 3 níveis (achado hoje > cache > taxa curada à mão) que
   todos os outros já usam, então nada quebra — só não tem fonte "extra" além
   do BACEN configurada ainda.

Diferença arquitetural (não de fonte de dado, de ONDE o resultado é
persistido): o projeto irmão guarda o resultado em dados.csv, um arquivo
externo que gerador.py lê. Este produto não tem CSV — BANCOS_VEICULOS é um
dict Python hardcoded em bancos_veiculos.py, importado direto por
gerador_veiculos.py. Reescrever código-fonte Python via regex a cada rodagem
do ETL seria frágil (um comentário ou formatação diferente quebra o regex).
Em vez disso, este ETL escreve um cache externo (taxas_cache_veiculos.json,
mesmo nome/formato de arquivo que o projeto irmão já usa) e
bancos_veiculos.py aplica esse cache POR CIMA dos valores hardcoded logo após
definir BANCOS_VEICULOS (ver _aplicar_cache_taxas lá) — os valores no dict
continuam sendo o "bootstrap" curado à mão (documentado como snapshot de
17-21/ago/2026), e o cache é a fonte de verdade quando existe. Mesmo
princípio do projeto irmão (taxa_padrao em bancos.py = bootstrap; dados.csv =
verdade corrente), só que sem precisar de um CSV pra um produto que nunca
teve um.
"""

import json
import os
import re
from datetime import date

import requests

from bancos_veiculos import BANCOS_VEICULOS, normalizar_chave

# Resolvido via __file__, não cwd — mesmo motivo do _ARQUIVO_CACHE_TAXAS em
# bancos_veiculos.py: garante que este script escreve exatamente o arquivo
# que aquele módulo lê, não importa de qual diretório o ETL é lançado (o
# GitHub Actions roda `python etl_taxas_veiculos.py` da raiz do checkout,
# mas nada garante isso pra sempre).
_PASTA_PROJETO = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_ULTIMA_ATUALIZACAO = os.path.join(_PASTA_PROJETO, 'ultima_atualizacao_taxas.txt')
ARQUIVO_CACHE_TAXAS = os.path.join(_PASTA_PROJETO, 'taxas_cache_veiculos.json')
ARQUIVO_RELATORIO = os.path.join(_PASTA_PROJETO, 'relatorio_atualizacao_taxas.txt')

# Faixas de sanidade (protegem contra parsing errado — ex: pegar um CPF ou
# um código de linha por engano). Calibradas contra a faixa REAL observada
# ao vivo na modalidade 401101 (08/set/2026): taxa_am de 0,61% (Mercedes-
# Benz) a 3,31% (Omni), taxa_aa de 7,61% a 47,88% — margem generosa nos dois
# lados de cada faixa.
TAXA_AM_MINIMA_PLAUSIVEL = 0.2
TAXA_AM_MAXIMA_PLAUSIVEL = 6.0
TAXA_AA_MINIMA_PLAUSIVEL = 3.0
TAXA_AA_MAXIMA_PLAUSIVEL = 70.0

# Mesma API JSON pública que o projeto irmão usa (a própria página do BACEN
# consome internamente) — não precisa parsing de HTML, mais robusto a
# mudança de layout do que uma fonte de blog.
FONTE_BACEN_API_DADOS = "https://www.bcb.gov.br/api/servico/sitebcb/historicotaxajurosdiario/atual"
FONTE_BACEN_API_DATAS = "https://www.bcb.gov.br/api/servico/sitebcb/HistoricoTaxaJurosDiario/ConsultaDatas"
FONTE_BACEN_PAGINA_HUMANA = "https://www.bcb.gov.br/estatisticas/reporttxjuros?codigoSegmento=1&codigoModalidade=401101"
FONTE_BACEN_CODIGO_MODALIDADE = "401101"

# Razão social exata observada ao vivo no relatório (08/set/2026, período
# 18/08/2026 a 24/08/2026) — mesmo cuidado do projeto irmão: usar a razão
# social INTEIRA como alias, não um pedaço genérico tipo só "BRADESCO",
# porque essa modalidade lista TANTO "BCO BRADESCO S.A." (banco de varejo)
# QUANTO "BCO BRADESCO FINANC. S.A." (financeira separada, taxa bem
# diferente) — um alias parcial "BRADESCO" bateria nos dois. A comparação já
# tolera acento/caixa via _normalizar_nome_instituicao, então não precisa
# escrever a acentuação exata aqui (ITAÚ vs ITAU tanto faz).
ALIASES_BACEN_VEICULO = {
    "Caixa": ["CAIXA ECONOMICA FEDERAL"],
    "Banco do Brasil": ["BCO DO BRASIL S.A."],
    "Bradesco": ["BCO BRADESCO S.A."],
    "Santander": ["SANTANDER SCFI S.A."],
    "Itau": ["ITAU UNIBANCO HOLDING S.A."],
    "Banco Inter": ["BANCO INTER"],
    "C6 Bank": ["BCO C6 S.A."],
    "BV Financeira": ["BCO VOTORANTIM S.A."],
    "Banco Pan": ["BANCO PAN"],
    "Omni Financeira": ["OMNI SA CFI"],
    "Banco Honda": ["BCO HONDA S.A."],
    "Banco Yamaha": ["BCO YAMAHA MOTOR S.A."],
}

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DatalabGlobalBot/1.0; +https://datalabglobal.com.br)"}


def _normalizar_nome_instituicao(texto):
    """Uppercase + remove acento (reaproveita normalizar_chave de
    bancos_veiculos.py) + remove pontuação solta + colapsa espaço — mesma
    função do projeto irmão, mesmo motivo (tolerar variação de formatação
    da razão social entre atualizações do relatório)."""
    sem_pontuacao = re.sub(r"[.,]", "", texto)
    sem_espaco_duplo = re.sub(r"\s+", " ", sem_pontuacao).strip()
    return normalizar_chave(sem_espaco_duplo).upper()


def _extrair_conteudo_ou_avisar_schema(corpo_json, nome_endpoint):
    """Mesma função do projeto irmão (ver etl_taxas.py): diferencia "a API
    mudou de formato" (🛑, chave 'conteudo' ausente) de "esse período não
    tem dado ainda" (⚠️, lista vazia) — sem isso os dois casos viram lista
    vazia igual e uma mudança real de schema passaria despercebida."""
    if "conteudo" not in corpo_json:
        print(
            f"🛑 BACEN: resposta de {nome_endpoint} mudou de formato — chave 'conteudo' não "
            f"existe (chaves recebidas: {list(corpo_json.keys())}). A API pode ter mudado; "
            f"confira manualmente {FONTE_BACEN_PAGINA_HUMANA}."
        )
        return None
    return corpo_json["conteudo"]


def _buscar_taxas_bacen():
    """Busca o período tipo 'D' (janela móvel de ~5 dias úteis — ver
    docstring do módulo) mais recente já publicado pra modalidade 401101,
    e extrai taxa_am + taxa_aa de cada
    banco reconhecido em ALIASES_BACEN_VEICULO. 2 requisições sempre (uma
    pra descobrir o período mais recente, uma pra buscar os dados dele) —
    mesma estratégia do projeto irmão, ver _buscar_bacen_json em
    etl_taxas.py pro raciocínio completo de por que 2 chamadas em vez de
    adivinhar o período às cegas.

    Retorna {banco: {"taxa_am": float, "taxa_aa": float, "fonte": url,
    "periodo": "dd/mm/aaaa a dd/mm/aaaa"}}."""
    try:
        resp_datas = requests.get(
            FONTE_BACEN_API_DATAS,
            params={"codigoSegmento": "1", "codigoModalidade": FONTE_BACEN_CODIGO_MODALIDADE},
            headers=_HEADERS, timeout=20,
        )
        resp_datas.raise_for_status()
        corpo_datas = resp_datas.json()
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️  BACEN: falha ao consultar períodos disponíveis: {e}")
        return {}

    periodos = _extrair_conteudo_ou_avisar_schema(corpo_datas, "ConsultaDatas")
    if periodos is None:
        return {}

    periodos_semanais = [p for p in periodos if p.get("tipoModalidade") == "D"]
    if not periodos_semanais:
        print("⚠️  BACEN: nenhum período tipo 'D' encontrado em ConsultaDatas")
        return {}
    periodo_mais_recente = periodos_semanais[0]  # o mais recente vem primeiro na lista
    inicio_periodo = periodo_mais_recente["InicioPeriodo"]

    filtro = (
        f"(codigoSegmento eq '1') and (codigoModalidade eq '{FONTE_BACEN_CODIGO_MODALIDADE}') "
        f"and (InicioPeriodo eq '{inicio_periodo}')"
    )
    try:
        resp = requests.get(FONTE_BACEN_API_DADOS, params={"filtro": filtro}, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
        corpo = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️  BACEN: falha ao consultar período {inicio_periodo}: {e}")
        return {}

    linhas = _extrair_conteudo_ou_avisar_schema(corpo, "historicotaxajurosdiario/atual")
    if linhas is None:
        return {}
    if not linhas:
        print(f"⚠️  BACEN: período {inicio_periodo} (apontado por ConsultaDatas) veio vazio — confira {FONTE_BACEN_PAGINA_HUMANA}")
        return {}

    resultado = {}
    for linha in linhas:
        nome_bacen_norm = _normalizar_nome_instituicao(str(linha.get("InstituicaoFinanceira", "")))
        try:
            taxa_am = float(str(linha["TaxaJurosAoMes"]).replace(",", "."))
            taxa_aa = float(str(linha["TaxaJurosAoAno"]).replace(",", "."))
        except (KeyError, ValueError, TypeError):
            continue
        if not (TAXA_AM_MINIMA_PLAUSIVEL <= taxa_am <= TAXA_AM_MAXIMA_PLAUSIVEL):
            continue
        if not (TAXA_AA_MINIMA_PLAUSIVEL <= taxa_aa <= TAXA_AA_MAXIMA_PLAUSIVEL):
            continue
        for banco, aliases in ALIASES_BACEN_VEICULO.items():
            if not any(_normalizar_nome_instituicao(alias) in nome_bacen_norm for alias in aliases):
                continue
            if banco in resultado:
                # Ver nota sobre BCO BRADESCO S.A. vs BCO BRADESCO FINANC.
                # S.A. acima — se algum dia isso disparar de verdade, é
                # sinal de alias ambíguo, não é esperado no fluxo normal.
                print(f"⚠️  BACEN: mais de uma linha bateu no alias de {banco} — mantendo a primeira encontrada, ignorando '{linha.get('InstituicaoFinanceira')}'")
                continue
            resultado[banco] = {
                "taxa_am": taxa_am, "taxa_aa": taxa_aa,
                "fonte": FONTE_BACEN_PAGINA_HUMANA, "periodo": periodo_mais_recente["Periodo"],
            }

    if resultado:
        print(f"✅ BACEN: {len(resultado)} banco(s) encontrados pro período {periodo_mais_recente['Periodo']} ({FONTE_BACEN_PAGINA_HUMANA})")
    return resultado


def _carregar_cache():
    try:
        with open(ARQUIVO_CACHE_TAXAS, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _salvar_cache(cache):
    with open(ARQUIVO_CACHE_TAXAS, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2, sort_keys=True)


def obter_taxas_reais_mercado():
    """Busca taxa_am/taxa_aa reais de cada banco no BACEN. Regra de
    fallback, em ordem de prioridade (mesma do projeto irmão):

      1. Achou no BACEN hoje?                    -> usa o valor novo.
      2. Não achou, mas tem cache de semana(s)
         anterior(es)?                            -> mantém o valor do
                                                       cache (não regride
                                                       pro hardcoded de
                                                       bancos_veiculos.py).
      3. Nunca teve nenhum valor confirmado
         (banco novo, ou a modalidade parou de
         cobrir ele)?                             -> usa taxa_am/taxa_aa
                                                       curados à mão em
                                                       BANCOS_VEICULOS.

    Sempre grava relatorio_atualizacao_taxas.txt dizendo qual banco caiu em
    qual caso, pra auditar se o ETL está achando dado fresco de verdade."""
    print("Buscando taxas típicas de mercado (BACEN, modalidade Aquisição de Veículos - Prefixado) ...")
    achadas_hoje = _buscar_taxas_bacen()
    cache = _carregar_cache()
    hoje = date.today().isoformat()

    taxas_finais = {}
    linhas_relatorio = [f"Atualização de taxas — {hoje}", "=" * 40]

    for banco, regra in BANCOS_VEICULOS.items():
        if banco in achadas_hoje:
            dados = achadas_hoje[banco]
            cache[banco] = {**dados, "atualizado_em": hoje}
            linhas_relatorio.append(
                f"✅ {banco}: {dados['taxa_am']}% a.m. / {dados['taxa_aa']}% a.a. "
                f"(encontrado agora, período {dados['periodo']})"
            )
        elif banco in cache:
            dados = cache[banco]
            data_cache = dados.get("atualizado_em", "?")
            linhas_relatorio.append(
                f"↪️  {banco}: {dados['taxa_am']}% a.m. / {dados['taxa_aa']}% a.a. "
                f"(sem fonte nova hoje — mantido do cache de {data_cache})"
            )
        else:
            dados = {"taxa_am": regra["taxa_am"], "taxa_aa": regra["taxa_aa"]}
            linhas_relatorio.append(
                f"⚠️  {banco}: {dados['taxa_am']}% a.m. / {dados['taxa_aa']}% a.a. "
                f"(nenhuma fonte configurada ainda — usando valor curado em bancos_veiculos.py)"
            )

        taxas_finais[banco] = dados
        print(f"  {banco}: {dados['taxa_am']}% a.m. / {dados['taxa_aa']}% a.a.")

    _salvar_cache(cache)

    with open(ARQUIVO_RELATORIO, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas_relatorio) + "\n")
    print(f"\nRelatório detalhado salvo em {ARQUIVO_RELATORIO}")

    return taxas_finais


def atualizar_data_referencia():
    """Grava a data real da última atualização de dados — usada pelo
    gerador_veiculos.py como <lastmod> do sitemap e dateModified do schema.
    Igual ao projeto irmão: só reescrevemos isso quando as taxas de fato
    são recuradas (rodagem semanal do ETL), nunca a cada deploy — 'lastmod
    sempre = hoje' é sinal de frescor falso pro Google."""
    with open(ARQUIVO_ULTIMA_ATUALIZACAO, 'w', encoding='utf-8') as f:
        f.write(date.today().isoformat())


if __name__ == "__main__":
    obter_taxas_reais_mercado()
    atualizar_data_referencia()
    print("\n🚀 taxas_cache_veiculos.json atualizado com taxas REAIS de mercado do BACEN!")
    print("   Rode 'python gerador_veiculos.py' em seguida pra regerar o site com essas taxas.")
