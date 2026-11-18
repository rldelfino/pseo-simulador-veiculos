# Graph Report - 003-pseo-simulador-veiculo  (2026-11-13)

## Corpus Check
- 12 files · ~4,093,114 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 6 file(s) not represented in the graph (top: (none) 2, .css 2, .ico 1)

## Summary
- 241 nodes · 459 edges · 14 communities (12 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `3401959a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_calculos_veiculos.py
- test_bancos_veiculos.py
- test_paginas_geradas.py
- gerador_veiculos.py
- etl_taxas_veiculos.py
- calculo.js
- gerar_pagina_individual
- gerar_comparador
- render_head
- package.json
- test_calculo_js.mjs
- formatar_reais
- rasterizar_favicon_png

## God Nodes (most connected - your core abstractions)
1. `gerar_pagina_individual()` - 21 edges
2. `gerar_site()` - 17 edges
3. `comparar_bancos_categoria()` - 15 edges
4. `gerar_grade_paginas()` - 15 edges
5. `gerar_hub()` - 15 edges
6. `gerar_comparador()` - 15 edges
7. `bancos_para_categoria()` - 14 edges
8. `calcular_cet_veiculo()` - 12 edges
9. `calcular_pmt_price()` - 11 edges
10. `icone()` - 11 edges

## Surprising Connections (you probably didn't know these)
- `test_normalizar_chave_remove_acentos()` --calls--> `normalizar_chave()`  [EXTRACTED]
  tests/test_bancos_veiculos.py → bancos_veiculos.py
- `test_obter_regra_banco_desconhecido_usa_fallback()` --calls--> `obter_regra()`  [EXTRACTED]
  tests/test_bancos_veiculos.py → bancos_veiculos.py
- `test_obter_regra_tolera_variacao_de_acentuacao()` --calls--> `obter_regra()`  [EXTRACTED]
  tests/test_bancos_veiculos.py → bancos_veiculos.py
- `test_banco_honda_e_yamaha_so_aparecem_em_moto()` --calls--> `bancos_para_categoria()`  [EXTRACTED]
  tests/test_bancos_veiculos.py → bancos_veiculos.py
- `test_bancos_cativos_de_moto_nao_aparecem_em_carro()` --calls--> `bancos_para_categoria()`  [EXTRACTED]
  tests/test_bancos_veiculos.py → bancos_veiculos.py

## Import Cycles
- None detected.

## Communities (14 total, 2 thin omitted)

### Community 0 - "test_calculos_veiculos.py"
Cohesion: 0.06
Nodes (37): calcular_cet_veiculo(), calcular_iof_veiculo(), calcular_pmt_price(), calcular_renda_sugerida(), comparar_bancos_categoria(), gerar_grade_paginas(), gerar_slug_pagina(), gerar_tabela_amortizacao() (+29 more)

### Community 1 - "test_bancos_veiculos.py"
Cohesion: 0.09
Nodes (17): _aplicar_cache_taxas(), bancos_para_categoria(), entrada_minima(), nome_exibicao(), normalizar_chave(), obter_regra(), test_banco_honda_e_yamaha_so_aparecem_em_moto(), test_bancos_cativos_de_moto_nao_aparecem_em_carro() (+9 more)

### Community 2 - "test_paginas_geradas.py"
Cohesion: 0.08
Nodes (14): _arquivos_html(), test_calculo_js_existe_e_e_referenciado_pelas_paginas_individuais(), test_comparador_linka_para_hub_de_todos_os_bancos_da_categoria(), test_dominio_correto_em_todas_as_paginas(), test_faixa_de_mercado_nunca_linka_direto_pra_pagina_de_outro_banco(), test_headers_tem_hsts_e_libera_beacon_do_cloudflare_analytics(), test_html_sem_tags_desbalanceadas(), test_pagina_404_tem_noindex() (+6 more)

### Community 3 - "gerador_veiculos.py"
Cohesion: 0.14
Nodes (10): gerar_404(), gerar_calculo_js(), gerar_favicon_svg(), gerar_headers(), gerar_llms_txt(), gerar_logo_svg(), gerar_robots_txt(), gerar_site() (+2 more)

### Community 4 - "etl_taxas_veiculos.py"
Cohesion: 0.14
Nodes (7): atualizar_data_referencia(), _buscar_taxas_bacen(), _carregar_cache(), _extrair_conteudo_ou_avisar_schema(), _normalizar_nome_instituicao(), obter_taxas_reais_mercado(), _salvar_cache()

### Community 5 - "calculo.js"
Cohesion: 0.29
Nodes (15): atualizarValor(), calcularCetVeiculo(), calcularFaixaMercado(), calcularIofVeiculo(), calcularPmtPrice(), calcularRendaSugerida(), formatarReais(), formatCurrency() (+7 more)

### Community 6 - "gerar_pagina_individual"
Cohesion: 0.22
Nodes (6): favicon_com_fallback(), gerar_pagina_individual(), renderizar_faixa_mercado(), svg_donut_capital_juros(), icone(), tooltip()

### Community 7 - "gerar_comparador"
Cohesion: 0.23
Nodes (10): formatar_valor_curto(), gerar_comparador(), gerar_hub(), gerar_index(), ilustracao_categoria(), render_faq_visual(), slug_comparador(), slug_hub() (+2 more)

### Community 8 - "render_head"
Cohesion: 0.24
Nodes (8): gerar_hub_aprenda(), gerar_pagina_aprenda(), gerar_pagina_sobre(), render_breadcrumb(), render_footer(), render_head(), render_json_ld(), render_nav()

### Community 9 - "package.json"
Cohesion: 0.20
Nodes (9): description, devDependencies, tailwindcss, name, private, scripts, build:css, version (+1 more)

### Community 10 - "test_calculo_js.mjs"
Cohesion: 0.20
Nodes (4): caminhoCalculoJs, CASOS, __dirname, sandbox

### Community 11 - "formatar_reais"
Cohesion: 0.67
Nodes (3): formatar_reais(), linha_tabela_amortizacao_html(), test_formatar_reais_sempre_duas_casas_decimais()

## Knowledge Gaps
- **11 isolated node(s):** `name`, `private`, `version`, `description`, `build:css` (+6 more)
  These have ≤1 connection - possible missing edges. (Counts symbols only; 95 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `bancos_para_categoria()` connect `test_bancos_veiculos.py` to `test_calculos_veiculos.py`, `gerador_veiculos.py`, `gerar_pagina_individual`, `gerar_comparador`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `normalizar_chave()` connect `test_bancos_veiculos.py` to `test_calculos_veiculos.py`, `gerador_veiculos.py`, `etl_taxas_veiculos.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_calculos_veiculos.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06289308176100629 - nodes in this community are weakly interconnected._
- **Should `test_bancos_veiculos.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08912655971479501 - nodes in this community are weakly interconnected._
- **Should `test_paginas_geradas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.08143939393939394 - nodes in this community are weakly interconnected._
- **Should `gerador_veiculos.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1368421052631579 - nodes in this community are weakly interconnected._