# Simulador de Financiamento de Veículos — Datalab Global

Site estático (HTML gerado por Python) com simuladores e comparativos de financiamento de
carro novo, carro usado e moto, e dados abertos. No ar em
**https://veiculos.datalabglobal.com**, publicado pelo Cloudflare Pages.

- **Simulador por banco, valor e prazo:** parcela (Price), CET e simulação de amortização.
- **Comparação sem marca de banco:** [financiamento de veículo por valor e prazo](https://veiculos.datalabglobal.com/financiamento-veiculos).
- **Comparadores por categoria:** [carro novo](https://veiculos.datalabglobal.com/comparador-carro-novo), [carro usado](https://veiculos.datalabglobal.com/comparador-carro-usado), [moto](https://veiculos.datalabglobal.com/comparador-moto), com a evolução das taxas mês a mês.
- **Dados abertos:** [/dados-abertos](https://veiculos.datalabglobal.com/dados-abertos).

## Dados abertos

A série mensal de taxas médias de juros do financiamento de veículos por banco, do Banco
Central do Brasil (modalidade 401101), está em [`paginas_seo/dados/`](paginas_seo/dados):

| Arquivo | Conteúdo |
|---|---|
| `taxas-financiamento-veiculos.csv` | Série mensal por banco (UTF-8, vírgula), taxa ao mês e ao ano |
| `taxas-financiamento-veiculos.json` | Mesma série em JSON |
| `datapackage.json` | Metadados ([Frictionless Data](https://frictionlessdata.io)) |
| `README.md` | Descrição, limites e como citar |

Licença dos dados: **CC BY 4.0** (uso livre, citando a fonte). Para cada mês fechado, a série
usa a última janela de 5 dias úteis divulgada pelo BACEN (o agregado mensal só existe em alguns
meses). A modalidade não separa carro novo, usado e moto. São médias do que foi contratado,
não ofertas.

## Como funciona

1. `etl_taxas_veiculos.py` busca as taxas atuais (API pública do BACEN).
2. `historico_taxas_veiculos.py` acrescenta os meses fechados novos a `historico_taxas.csv`.
3. `gerador_veiculos.py` gera as páginas em `paginas_seo/`.
4. `npm run build:css` compila o Tailwind em `paginas_seo/styles.css`.
5. `indexnow.py` avisa o Bing das páginas atualizadas.

O workflow `.github/workflows/atualiza_taxas.yml` roda tudo isso toda segunda-feira.

## Rodar localmente

```bash
pip install -r requirements.txt pytest
python gerador_veiculos.py     # gera paginas_seo/
npm install && npm run build:css
python -m pytest               # testes (use Python 3.10, o mesmo do CI)
```

## Sobre

Mantido pela [Datalab Global](https://www.datalabglobal.com), marca de
Satori Soluções Comerciais LTDA (CNPJ 63.998.502/0001-73). As simulações são educativas e
não constituem oferta de crédito.
