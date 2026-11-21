# AVALIAÇÃO DAS SUBPÁGINAS — veiculos.datalabglobal.com (21/11/2026)

> **Status:** recomendação B (enxugar) APROVADA em 21/11/2026 e aplicada no PR de enxugamento. O que mudou no código: ver a seção 6; o `_redirects` é gerado por `gerar_redirects()` em `gerador_veiculos.py`.

Pedido do dono: as ~165 URLs do sitemap (e ~1.020 arquivos) valem a pena? **Nada foi apagado nem redirecionado.** Este arquivo é só a análise e a proposta, para a sessão principal aprovar.

## 1. Resposta curta
**Recomendação: ENXUGAR.** Manter 49 URLs com conteúdo próprio e redirecionar (301) os outros 969 arquivos para a melhor página. Em 3 meses o host inteiro teve **2 cliques e 47 impressões** no Google; a grade de ~1.000 páginas por banco x valor x prazo é, em quase tudo, o mesmo texto com números trocados, e o Google não a indexa (rastreia e recusa). Cortar não custa tráfego (hoje não há) e deixa o Google avaliar o site pelas páginas boas.

## 2. Dados (Search Console, propriedade `sc-domain:datalabglobal.com`, coletados em 20/11/2026)
Limite da ferramenta: o relatório de indexação **não separa por host** (o dado mais recente é de 15/11) e os detalhes mostram no máximo 1.000 URLs de amostra por motivo. Por isso os números de `veiculos.` abaixo são **contagens dentro dessas amostras**, não totais.

**Domínio todo (os 8 sites juntos):** 1,55 mil indexadas x 17,5 mil não indexadas. Motivos: rastreada, mas não indexada **9.671**; detectada, mas não indexada **2.617**; página com redirecionamento 3.346; 404 956; excluída por `noindex` 804; erro 5xx 96; canônica alternativa 20; outros 3.

**Sitemap de veículos:** 165 URLs lidas (processado em 18/11). O filtro por sitemap no relatório de indexação respondeu "dados em processamento", então não deu para ver o status só dele.

**Amostras com URLs de `veiculos.` (únicas):**

| Situação | URLs de veículos na amostra | O que são |
|---|---|---|
| Indexadas (amostra de 1.000) | 109 | 73 simulações banco x valor x prazo, **32 variantes `.html`** das mesmas páginas, 3 hubs, /sobre. Home e comparadores **não** estavam na amostra |
| Rastreada, mas não indexada (amostra de 1.000) | 46 | 27 simulações, 5 hubs, 3 comparadores, **a home**, /financiamento-veiculos, /metodologia, /atualizacoes, /dados-abertos, 1 mês de taxas, 1 guia |
| Detectada, mas não indexada (amostra de 1.000) | 50 | 28 simulações, 9 "renda para financiar", 5 meses de taxas, 4 guias |

Antes disso (nota no código, 13/11, API de inspeção em 1.004 URLs): 7 indexadas, 763 rastreadas e recusadas, 234 nunca descobertas. A grade já foi posta em `noindex` e fora do sitemap (840 páginas); o gráfico de indexadas do domínio cai de ~9 mil para 1,55 mil desde setembro.

**Desempenho, últimos 3 meses, só `veiculos.datalabglobal.com`:** 2 cliques, 47 impressões, CTR 4,3%, posição média 11,1. 28 páginas tiveram alguma impressão (a tabela de baixo soma 27 que consegui ler):

| Tipo | Páginas com impressão | Cliques | Impressões |
|---|---|---|---|
| Simulação banco x valor x prazo (todas `noindex`) | 16 | 1 | 19 |
| Hubs por banco | 6 | 0 | 12 |
| /sobre | 1 | 0 | 8 |
| Guias `aprenda` | 2 | 0 | 3 |
| Comparador (versão `.html`) | 1 | 0 | 2 |
| Home | 1 | 1 | 1 |

O único clique em simulação foi em `financiamento-carro-usado-caixa-60-mil-24-meses` (2 impressões). Impressões em URLs `.html` mostram que o Google também mostra a variante com extensão.

## 3. Qualidade das páginas (conta feita nos arquivos gerados, números mascarados)

| Tipo | Arquivos | Palavras (mediana) | Semelhança entre irmãs (5-gramas) |
|---|---|---|---|
| Simulação banco x valor x prazo | 840 | 1.317 | 0,97 a 1,00 (mesmo texto, só os números mudam) |
| Comparação sem marca (valor x prazo) | 80 | 558 | 1,00 |
| Renda para financiar (por valor) | 17 | 387 | 0,98 |
| Hub por banco (mesma categoria) | 32 | 987 | 0,73 a 0,79 entre bancos; **0,84 entre carro novo e usado do mesmo banco** |
| Comparadores (3), guias (10), metodologia etc. | ~25 | 195 a 883 | texto próprio |

- **Duplicação estrutural:** o Banco Central publica uma modalidade só (aquisição de veículos); carro novo, usado e moto têm **a mesma taxa por banco**. Os hubs novo/usado/moto do mesmo banco repetem os mesmos números.
- **Canibalização:** para "financiamento <banco>" competem hub novo, hub usado, hub moto, as 25 simulações do banco e o comparador. Para "financiamento 60 mil 48 meses" competem a comparação sem marca, o índice /financiamento-veiculos e a home.
- **Texto fino:** /renda-para-financiar-veiculo tem 118 palavras; /sobre 195.
- **Conversão para o simulador:** as simulações por banco têm simulador e botão próprios, então **não levam** ninguém ao simulador da home; a home agora é o simulador. NÃO verificado: o Umami (cliques por página no botão do parceiro) não foi consultado, então não dá para dizer quantos pedidos vieram das subpáginas; com 2 cliques orgânicos em 3 meses, o efeito só pode ser pequeno.

## 4. Opções

| Opção | O que fica | Resultado |
|---|---|---|
| A. Manter tudo | 165 URLs no sitemap, ~1.020 arquivos | Nada muda; o Google segue recusando; build e repositório pesados |
| **B. Enxugar (recomendada)** | **49 URLs**: home, 3 comparadores, 22 hubs (10 de carro novo e 12 de moto; os de carro usado viram o de carro novo, mesma taxa), 11 de guias (10 + índice), metodologia, sobre, dados abertos, atualizações, análise do mês, taxas mês a mês (índice + 2 meses), financiamento-veiculos, renda-para-financiar-veiculo, imprensa, incorporar | Menos duplicação, mais autoridade por página; os mesmos assuntos continuam respondidos |
| C. Só o núcleo | ~25 URLs (sem hubs) | Perde as páginas por banco, que são as que mais têm impressão (12) e a consulta "taxa <banco>" |

## 5. Mapa de redirecionamentos 301 proposto (opção B)
Arquivo `_redirects` do Cloudflare Pages (colocar em `paginas_seo/`): **71 regras** (38 com asterisco, 33 estáticas; limites do Pages: 100 dinâmicas e 2.000 estáticas). A ordem importa (vale a primeira que casa). Simulei as regras sobre os 1.020 arquivos: **969 casam, todos caem numa página que continua existindo, sem cadeia de redirecionamento**; 51 arquivos ficam (inclui 404 e embed).

Resumo do que vai para onde:
- 840 simulações banco x valor x prazo → hub do mesmo banco (carro usado → hub de carro novo).
- 80 comparações sem marca → comparador da categoria.
- 17 "renda para financiar" por valor → /renda-para-financiar-veiculo (que precisa absorver a tabela por valor).
- 10 hubs de carro usado → hub de carro novo do mesmo banco.
- 23 meses antigos de taxas → /taxas-financiamento-veiculos (ficam os 2 mais recentes).

```
/financiamento-carro-novo-banco-do-brasil-* /hub-banco-do-brasil-carro-novo 301
/financiamento-carro-usado-banco-do-brasil-* /hub-banco-do-brasil-carro-novo 301
/financiamento-carro-novo-banco-inter-* /hub-banco-inter-carro-novo 301
/financiamento-carro-usado-banco-inter-* /hub-banco-inter-carro-novo 301
/financiamento-carro-novo-banco-pan-* /hub-banco-pan-carro-novo 301
/financiamento-carro-usado-banco-pan-* /hub-banco-pan-carro-novo 301
/financiamento-carro-novo-bradesco-* /hub-bradesco-carro-novo 301
/financiamento-carro-usado-bradesco-* /hub-bradesco-carro-novo 301
/financiamento-carro-novo-bv-financeira-* /hub-bv-financeira-carro-novo 301
/financiamento-carro-usado-bv-financeira-* /hub-bv-financeira-carro-novo 301
/financiamento-carro-novo-c6-bank-* /hub-c6-bank-carro-novo 301
/financiamento-carro-usado-c6-bank-* /hub-c6-bank-carro-novo 301
/financiamento-carro-novo-caixa-* /hub-caixa-carro-novo 301
/financiamento-carro-usado-caixa-* /hub-caixa-carro-novo 301
/financiamento-carro-novo-itau-* /hub-itau-carro-novo 301
/financiamento-carro-usado-itau-* /hub-itau-carro-novo 301
/financiamento-carro-novo-omni-financeira-* /hub-omni-financeira-carro-novo 301
/financiamento-carro-usado-omni-financeira-* /hub-omni-financeira-carro-novo 301
/financiamento-carro-novo-santander-* /hub-santander-carro-novo 301
/financiamento-carro-usado-santander-* /hub-santander-carro-novo 301
/financiamento-moto-banco-do-brasil-* /hub-banco-do-brasil-moto 301
/financiamento-moto-banco-inter-* /hub-banco-inter-moto 301
/financiamento-moto-banco-pan-* /hub-banco-pan-moto 301
/financiamento-moto-bradesco-* /hub-bradesco-moto 301
/financiamento-moto-bv-financeira-* /hub-bv-financeira-moto 301
/financiamento-moto-c6-bank-* /hub-c6-bank-moto 301
/financiamento-moto-caixa-* /hub-caixa-moto 301
/financiamento-moto-itau-* /hub-itau-moto 301
/financiamento-moto-omni-financeira-* /hub-omni-financeira-moto 301
/financiamento-moto-santander-* /hub-santander-moto 301
/financiamento-moto-banco-honda-* /hub-banco-honda-moto 301
/financiamento-moto-banco-yamaha-* /hub-banco-yamaha-moto 301
/hub-banco-do-brasil-carro-usado /hub-banco-do-brasil-carro-novo 301
/hub-banco-inter-carro-usado /hub-banco-inter-carro-novo 301
/hub-banco-pan-carro-usado /hub-banco-pan-carro-novo 301
/hub-bradesco-carro-usado /hub-bradesco-carro-novo 301
/hub-bv-financeira-carro-usado /hub-bv-financeira-carro-novo 301
/hub-c6-bank-carro-usado /hub-c6-bank-carro-novo 301
/hub-caixa-carro-usado /hub-caixa-carro-novo 301
/hub-itau-carro-usado /hub-itau-carro-novo 301
/hub-omni-financeira-carro-usado /hub-omni-financeira-carro-novo 301
/hub-santander-carro-usado /hub-santander-carro-novo 301
/financiamento-carro-novo-* /comparador-carro-novo 301
/financiamento-carro-usado-* /comparador-carro-usado 301
/financiamento-moto-* /comparador-moto 301
/renda-para-financiar-carro-novo-* /renda-para-financiar-veiculo 301
/renda-para-financiar-carro-usado-* /renda-para-financiar-veiculo 301
/renda-para-financiar-moto-* /renda-para-financiar-veiculo 301
/taxas-financiamento-veiculos-abril-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-abril-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-agosto-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-agosto-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-dezembro-2024 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-dezembro-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-fevereiro-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-fevereiro-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-janeiro-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-janeiro-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-julho-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-julho-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-junho-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-junho-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-maio-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-maio-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-marco-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-marco-2026 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-novembro-2024 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-novembro-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-outubro-2024 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-outubro-2025 /taxas-financiamento-veiculos 301
/taxas-financiamento-veiculos-setembro-2025 /taxas-financiamento-veiculos 301
```

## 6. Tudo no SEO que muda se aprovar
- **Gerador:** parar de gerar as 920 páginas de simulação/comparação, as 17 de renda e os hubs de carro usado; remover `PAGINAS_VALOR_INDEXAVEIS`, `gerar_grade_paginas` e quem usa `lookup`. O repositório cai de ~1.140 para ~170 arquivos e o build fica bem mais rápido.
- **Sitemap:** de 165 para ~48 URLs. `lastmod_manifest.json` perde as entradas removidas.
- **Canonical:** hubs de carro novo passam a cobrir "carro novo e usado" (título e H1 ≤ 60 caracteres, por exemplo "Financiamento de carro novo e usado no <banco>"); a canônica deles não muda. Hubs de moto iguais.
- **Links internos que quebram e precisam de ajuste:** índice /financiamento-veiculos (80 links para comparações), hubs (lista de simulações por valor e "vizinhas"), comparadores (links para comparações e simulações), guias (`cta_href` e links contextuais), /renda-para-financiar-veiculo, home (tabela já aponta para hubs de carro novo), `analise-do-mes`, `imprensa` e `incorporar` (exemplos e códigos).
- **llms.txt e llms-full.txt:** a contagem de páginas e as listas de URLs; remover as removidas.
- **feed.xml (Atom):** entradas que citam páginas removidas passam para as mantidas.
- **JSON-LD:** somem BreadcrumbList, FAQPage e WebPage das páginas removidas; os hubs de carro novo precisam do breadcrumb "Carro novo e usado".
- **Dados abertos:** `README`, `datapackage.json` e a página /dados-abertos citam as páginas por banco (conferir links); `publicacao.py` (Kaggle, Hugging Face, dados.gov.br, nota de imprensa) cita URLs do site.
- **IndexNow (`indexnow.py`):** parar de enviar as URLs removidas; enviar uma vez as mantidas alteradas.
- **Testes:** `test_paginas_geradas.py` e outros assumem a grade (ex.: 840 páginas, CTA em toda simulação); precisam de ajuste.
- **Search Console/Bing:** depois do deploy, enviar o sitemap novo e pedir "validar correção" nos motivos de redirecionamento; nenhuma remoção manual é necessária.
- **Reversibilidade:** tudo está no git; as regras saem do `_redirects` e as páginas voltam com `git revert`.

## 7. Revisão de SEO das páginas que ficam (conta feita nos arquivos gerados)
Nas 57 páginas mantidas (home, comparadores, hubs, guias, institucionais, taxas, renda e financiamento-veiculos): título ≤ 60 caracteres, descrição entre 70 e 160, **um** H1, canonical correto, JSON-LD e BreadcrumbList presentes. Exceções: **/sobre sem BreadcrumbList** e texto curto (195 palavras); **/renda-para-financiar-veiculo com 118 palavras** (precisa da tabela por valor que hoje está nas 17 páginas). Os meses antigos de taxas já estão em `noindex` e fora do sitemap.

## 8. O que NÃO foi verificado
- Umami (conversão por página) e Bing Webmaster não foram consultados.
- Contagens por host dependem de amostras de até 1.000 URLs por motivo, com dado de 15/11.
- Não testei os redirecionamentos no Cloudflare (a simulação foi local, sobre os nomes dos arquivos).
