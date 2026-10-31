"""
Pacote de publicação dos dados abertos de financiamento de veículos em sites
especializados (Kaggle, Hugging Face, dados.gov.br) e nota de imprensa do mês.

Por que existe (31/out/2026): publicar o conjunto de dados onde analistas e
jornalistas procuram dados gera links e citações reais, sem postar para
ninguém e sem gastar. O que depende de conta (login) fica pronto aqui, em
publicacao/, para ser enviado em minutos; o resto (texto, metadados, licença,
período) é gerado dos mesmos arquivos de paginas_seo/dados/, então se atualiza
sozinho todo mês junto com o ETL.

Rodar: python publicacao.py   (depois de python gerador_veiculos.py)
"""
import json
import os
import shutil
import sys

PASTA_DADOS = os.path.join("paginas_seo", "dados")
PASTA_SAIDA = "publicacao"
DOMINIO = "https://veiculos.datalabglobal.com"
NOME = "taxas-financiamento-veiculos"
LICENCA = "CC BY 4.0"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _mes(iso):
    return f"{MESES[int(iso[5:7]) - 1]} de {iso[:4]}"


def _ler():
    pacote = json.load(open(os.path.join(PASTA_DADOS, "datapackage.json"), encoding="utf-8"))
    linhas = json.load(open(os.path.join(PASTA_DADOS, f"{NOME}.json"), encoding="utf-8"))
    return pacote, linhas


def _escrever(caminho, conteudo):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(conteudo)


def gerar():
    pacote, linhas = _ler()
    if isinstance(linhas, dict):
        linhas = linhas.get("dados") or linhas.get("data") or []
    descricao = pacote["description"]
    titulo = pacote["title"]
    ini = min(r["periodo_inicio"] for r in linhas)
    fim = max(r["periodo_fim"] for r in linhas)
    instituicoes = sorted({r["instituicao"] for r in linhas})
    csv_url = f"{DOMINIO}/dados/{NOME}.csv"
    shutil.rmtree(PASTA_SAIDA, ignore_errors=True)

    # Kaggle (kaggle datasets create -p publicacao/kaggle)
    meta = {
        "title": "Taxas de financiamento de veículos por banco (Brasil, BACEN)",
        "id": "SEU_USUARIO_KAGGLE/taxas-financiamento-veiculos-brasil",
        "subtitle": "Taxa média mensal contratada por banco, % ao mês e ao ano, atualizada toda semana",
        "description": f"{descricao}\n\nLicença: {LICENCA}. Fonte: Banco Central do Brasil. Atualizado todo mês em {DOMINIO}/dados-abertos.",
        "licenses": [{"name": "CC-BY-4.0"}],
        "keywords": ["finance", "brazil", "banking", "interest rates", "vehicle loans"],
        "resources": [{"path": f"{NOME}.csv", "description": "Série mensal: mes_referencia, periodo_inicio, periodo_fim, instituicao, taxa_juros_am_pct, taxa_juros_aa_pct"}],
    }
    _escrever(os.path.join(PASTA_SAIDA, "kaggle", "dataset-metadata.json"), json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    shutil.copy(os.path.join(PASTA_DADOS, f"{NOME}.csv"), os.path.join(PASTA_SAIDA, "kaggle", f"{NOME}.csv"))

    # Hugging Face (dataset card + CSV)
    card = f"""---
license: cc-by-4.0
language:
- pt
pretty_name: Taxas de financiamento de veículos por banco (Brasil, BACEN)
size_categories:
- n<1K
task_categories:
- tabular-regression
tags:
- finance
- brazil
- interest-rates
- vehicle-loans
---

# {titulo}

{descricao}

## Colunas
- `mes_referencia`: mês (AAAA-MM). `periodo_inicio`, `periodo_fim`: primeiro e último dia com dado dentro do mês.
- `instituicao`: banco.
- `taxa_juros_am_pct`, `taxa_juros_aa_pct`: taxa média efetivamente contratada, em % ao mês e ao ano.

## Cobertura
{_mes(ini)} a {_mes(fim)}; {len(instituicoes)} instituições: {', '.join(instituicoes)}.

## Fonte e licença
Banco Central do Brasil (API pública de taxas de juros, modalidade 401101: aquisição de veículos, pessoa física, pré-fixada). Licença {LICENCA}: cite "Datalab Global ({DOMINIO}/dados-abertos)". Atualizado toda semana.
"""
    _escrever(os.path.join(PASTA_SAIDA, "huggingface", "README.md"), card)
    shutil.copy(os.path.join(PASTA_DADOS, f"{NOME}.csv"), os.path.join(PASTA_SAIDA, "huggingface", f"{NOME}.csv"))

    # dados.gov.br aceita recurso por link (CKAN): não precisa subir arquivo
    gov = f"""# Cadastro no dados.gov.br

Campos para copiar (portal de dados abertos, "Cadastrar conjunto de dados"):

- **Título:** {titulo}
- **Descrição:** {descricao}
- **Organização / publicador:** Datalab Global (Satori Soluções Comerciais LTDA, CNPJ 63.998.502/0001-73)
- **Licença:** {LICENCA}
- **Frequência de atualização:** semanal (série mensal)
- **Cobertura temporal:** {ini} a {fim}
- **Tags:** financiamento de veículos, taxa de juros, CDC, carro, moto, bancos, Banco Central
- **Recursos (por link, sem upload):**
  - CSV: {csv_url}
  - JSON: {DOMINIO}/dados/{NOME}.json
  - Data package: {DOMINIO}/dados/datapackage.json
- **Fonte original:** {pacote['sources'][0]['path']}
"""
    _escrever(os.path.join(PASTA_SAIDA, "dados-gov-br", "cadastro.md"), gov)

    # nota de imprensa do mês (números calculados dos dados)
    mes_ult = max(r["mes_referencia"] for r in linhas)
    ultimo = mes_ult + "-01"
    atual = {r["instituicao"]: r["taxa_juros_am_pct"] for r in linhas if r["mes_referencia"] == mes_ult}
    menor = min(atual, key=atual.get)
    maior = max(atual, key=atual.get)
    media = sum(atual.values()) / len(atual)
    fmt = lambda v: f"{v:.2f}".replace(".", ",")
    nota = f"""# Nota: taxas do financiamento de veículos em {_mes(ultimo)}

Dados do Banco Central compilados pela Datalab Global. Livre para uso com citação da fonte ({LICENCA}).

- Menor taxa média contratada: **{menor}**, {fmt(atual[menor])}% ao mês.
- Maior taxa média contratada: **{maior}**, {fmt(atual[maior])}% ao mês.
- Média simples dos {len(atual)} bancos: {fmt(media)}% ao mês.
- Série completa (CSV/JSON): {DOMINIO}/dados-abertos
- Taxas mês a mês: {DOMINIO}/taxas-financiamento-veiculos
- Metodologia: {DOMINIO}/metodologia

Contato: contato@datalabglobal.com
"""
    _escrever(os.path.join(PASTA_SAIDA, f"nota-imprensa-{ultimo[:7]}.md"), nota)

    _escrever(os.path.join(PASTA_SAIDA, "LEIA-ME.md"), f"""# Publicação dos dados abertos

Esta pasta é gerada por `publicacao.py` (toda semana, pelo robô). O que cada site pede:

1. **Kaggle:** troque `SEU_USUARIO_KAGGLE` em `kaggle/dataset-metadata.json` pelo seu usuário e rode `kaggle datasets create -p publicacao/kaggle` (nas semanas seguintes, `kaggle datasets version -p publicacao/kaggle -m "atualização semanal"`).
2. **Hugging Face:** crie um dataset em huggingface.co/new-dataset e envie os dois arquivos de `huggingface/`.
3. **dados.gov.br:** copie os campos de `dados-gov-br/cadastro.md` (os recursos entram por link).
4. **Imprensa:** a `nota-imprensa-AAAA-MM.md` do mês está pronta.
""")
    print(f"publicacao/: pacote de {len(linhas)} linhas ({_mes(ini)} a {_mes(fim)})")


if __name__ == "__main__":
    sys.exit(gerar() or 0)
