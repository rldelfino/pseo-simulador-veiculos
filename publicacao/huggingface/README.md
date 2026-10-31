---
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

# Taxas médias de juros do financiamento de veículos por banco (BACEN)

Taxa média de juros efetivamente contratada no financiamento de veículos (aquisição de veículos, pessoa física, pré-fixada), por banco, ao mês e ao ano, segundo o Banco Central do Brasil. Para cada mês fechado, a última janela de 5 dias úteis divulgada. Cobre 24 meses (out/24 a set/26) e 12 instituições. O Banco Central publica uma única modalidade para aquisição de veículos (pessoa física, pré-fixada), sem separar carro novo, carro usado e moto: a taxa de cada banco é a mesma série para as três categorias.

## Colunas
- `mes_referencia`: mês (AAAA-MM). `periodo_inicio`, `periodo_fim`: primeiro e último dia com dado dentro do mês.
- `instituicao`: banco.
- `taxa_juros_am_pct`, `taxa_juros_aa_pct`: taxa média efetivamente contratada, em % ao mês e ao ano.

## Cobertura
outubro de 2024 a setembro de 2026; 12 instituições: BV Financeira, Banco Honda, Banco Inter, Banco Pan, Banco Yamaha, Banco do Brasil, Bradesco, C6 Bank, Caixa, Itaú, Omni Financeira, Santander.

## Fonte e licença
Banco Central do Brasil (API pública de taxas de juros, modalidade 401101: aquisição de veículos, pessoa física, pré-fixada). Licença CC BY 4.0: cite "Datalab Global (https://veiculos.datalabglobal.com/dados-abertos)". Atualizado toda semana.
