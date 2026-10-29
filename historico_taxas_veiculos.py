"""
Histórico mensal de taxas de juros do financiamento de veículos por banco, da
mesma fonte oficial que o etl_taxas_veiculos.py usa (API pública do BACEN,
modalidade 401101 — "Aquisição de veículos, pessoa física, taxa pré-fixada").

Por que existe (auditoria de SEO, 29/out/2026): o ETL guarda só a última janela
de 5 dias úteis de cada banco. Uma página "taxas por banco" que mostra também a
EVOLUÇÃO mês a mês é o tipo de dado que blogs e jornalistas citam, e é a base
do conjunto de dados abertos publicado em /dados-abertos. A API do BACEN guarda
a série mensal desde 2012; aqui guardamos os últimos MESES_HISTORICO meses em
historico_taxas.csv e, a cada execução do ETL, acrescentamos só os que faltam.

Atenção 1: a modalidade 401101 é uma só para carro novo, carro usado e moto —
o BACEN não separa por tipo de veículo. O histórico (e os dados abertos)
herdam essa limitação, que está dita nos textos publicados.

Atenção 2: para esta modalidade o BACEN publica o agregado MENSAL só em alguns
meses (a resposta vem vazia em metade deles — conferido em 29/out/2026). O que
existe sem falhas são as janelas de 5 dias úteis (tipo "D"), a mesma
granularidade que o ETL e as páginas do site já usam. Por isso a série usa, para
cada mês FECHADO, a última janela que termina dentro dele (colunas
inicio_periodo/fim_periodo mostram qual). Mês em andamento não entra.

Rodar: python historico_taxas_veiculos.py   (idempotente; falha de rede NÃO
derruba o pipeline: avisa e sai com código 0, mantendo o CSV que já existe).
"""
import csv
import re
import sys
from datetime import date

import requests

from etl_taxas_veiculos import (
    ALIASES_BACEN_VEICULO,
    FONTE_BACEN_API_DADOS,
    FONTE_BACEN_API_DATAS,
    FONTE_BACEN_CODIGO_MODALIDADE,
    FONTE_BACEN_PAGINA_HUMANA,
    TAXA_AA_MAXIMA_PLAUSIVEL,
    TAXA_AA_MINIMA_PLAUSIVEL,
    TAXA_AM_MAXIMA_PLAUSIVEL,
    TAXA_AM_MINIMA_PLAUSIVEL,
    _normalizar_nome_instituicao,
)

ARQUIVO_HISTORICO = "historico_taxas.csv"
CABECALHO = ["mes_referencia", "inicio_periodo", "fim_periodo", "banco", "taxa_am", "taxa_aa"]
MESES_HISTORICO = 24
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; datalab-global-etl/1.0; +https://www.datalabglobal.com)"}


def ler_historico(caminho=ARQUIVO_HISTORICO):
    """Lista de dicts {mes_referencia, inicio_periodo, fim_periodo, banco,
    taxa_am, taxa_aa}, ordenada por mês e banco. Arquivo ausente -> vazia."""
    try:
        with open(caminho, encoding="utf-8", newline="") as f:
            linhas = [
                {"mes_referencia": r["mes_referencia"], "inicio_periodo": r["inicio_periodo"], "fim_periodo": r["fim_periodo"],
                 "banco": r["banco"], "taxa_am": float(r["taxa_am"]), "taxa_aa": float(r["taxa_aa"])}
                for r in csv.DictReader(f, delimiter=";")
            ]
    except FileNotFoundError:
        return []
    return sorted(linhas, key=lambda r: (r["mes_referencia"], r["banco"]))


def _fim_do_periodo(texto_periodo):
    m = re.search(r"a\s+(\d{2})/(\d{2})/(\d{4})", texto_periodo or "")
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""


def listar_periodos_mensais(hoje=None):
    """Para cada mês FECHADO, a última janela de 5 dias úteis (tipo "D") que
    termina dentro dele, do mês mais recente pro mais antigo:
    [{'mes': '2026-09', 'inicio': '2026-09-24', 'fim': '2026-09-30'}, ...]."""
    hoje = hoje or date.today()
    mes_atual = f"{hoje.year:04d}-{hoje.month:02d}"
    resp = requests.get(
        FONTE_BACEN_API_DATAS,
        params={"codigoSegmento": "1", "codigoModalidade": FONTE_BACEN_CODIGO_MODALIDADE},
        headers=_HEADERS, timeout=30,
    )
    resp.raise_for_status()
    conteudo = resp.json().get("conteudo")
    if not isinstance(conteudo, list):
        raise ValueError("resposta de ConsultaDatas mudou de formato (sem 'conteudo')")
    por_mes = {}
    for p in conteudo:
        if p.get("tipoModalidade") != "D":
            continue
        fim = _fim_do_periodo(p.get("Periodo", ""))
        if not fim or fim[:7] >= mes_atual:
            continue
        mes = fim[:7]
        if mes not in por_mes or fim > por_mes[mes]["fim"]:
            por_mes[mes] = {"mes": mes, "inicio": p["InicioPeriodo"], "fim": fim}
    return [por_mes[m] for m in sorted(por_mes, reverse=True)]


def buscar_taxas_periodo(inicio_periodo):
    """{banco: (taxa_am, taxa_aa)} dos bancos de ALIASES_BACEN_VEICULO no
    período mensal. Mesma regra de casamento/plausibilidade do ETL."""
    filtro = (
        f"(codigoSegmento eq '1') and (codigoModalidade eq '{FONTE_BACEN_CODIGO_MODALIDADE}') "
        f"and (InicioPeriodo eq '{inicio_periodo}')"
    )
    resp = requests.get(FONTE_BACEN_API_DADOS, params={"filtro": filtro}, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    linhas = resp.json().get("conteudo")
    if not isinstance(linhas, list):
        raise ValueError("resposta do BACEN mudou de formato (sem 'conteudo')")
    resultado = {}
    for linha in linhas:
        nome = _normalizar_nome_instituicao(str(linha.get("InstituicaoFinanceira", "")))
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
            if banco in resultado:
                continue
            if any(_normalizar_nome_instituicao(a) in nome for a in aliases):
                resultado[banco] = (taxa_am, taxa_aa)
    return resultado


def salvar_historico(linhas, caminho=ARQUIVO_HISTORICO):
    linhas = sorted(linhas, key=lambda r: (r["mes_referencia"], r["banco"]))
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";", lineterminator="\n")
        w.writerow(CABECALHO)
        for r in linhas:
            w.writerow([r["mes_referencia"], r["inicio_periodo"], r["fim_periodo"], r["banco"], f"{r['taxa_am']:.2f}", f"{r['taxa_aa']:.2f}"])


def atualizar_historico(caminho=ARQUIVO_HISTORICO, meses=MESES_HISTORICO):
    """Acrescenta ao CSV os meses (dos últimos `meses` publicados) que ainda
    não estão lá. Devolve (qtd_meses_novos, total_de_meses)."""
    existentes = ler_historico(caminho)
    ja_tem = {r["mes_referencia"] for r in existentes}
    periodos = listar_periodos_mensais()[:meses]
    linhas = list(existentes)
    adicionados = 0
    for p in [p for p in periodos if p["mes"] not in ja_tem]:
        try:
            taxas = buscar_taxas_periodo(p["inicio"])
        except (requests.RequestException, ValueError) as e:
            print(f"⚠️  histórico: falha no mês {p['mes']} ({e}) — segue sem ele")
            continue
        if not taxas:
            print(f"⚠️  histórico: mês {p['mes']} sem nenhum banco casado — ignorado")
            continue
        for banco, (am, aa) in taxas.items():
            linhas.append({"mes_referencia": p["mes"], "inicio_periodo": p["inicio"], "fim_periodo": p["fim"],
                           "banco": banco, "taxa_am": am, "taxa_aa": aa})
        adicionados += 1
    janela = {p["mes"] for p in periodos}
    linhas = [r for r in linhas if r["mes_referencia"] in janela] or linhas
    salvar_historico(linhas, caminho)
    return adicionados, len({r["mes_referencia"] for r in linhas})


if __name__ == "__main__":
    try:
        novos, total = atualizar_historico()
        print(f"✅ histórico de taxas: {novos} mês(es) novo(s); {total} mês(es) no total em {ARQUIVO_HISTORICO} (fonte: {FONTE_BACEN_PAGINA_HUMANA})")
    except (requests.RequestException, ValueError) as e:
        print(f"⚠️  histórico de taxas não atualizado ({e}); mantendo o arquivo existente.")
    sys.exit(0)
