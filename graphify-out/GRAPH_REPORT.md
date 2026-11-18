# Graph Report - 003-pseo-simulador-veiculo  (2026-11-15)

## Corpus Check
- 37 files · ~5,166,478 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 13 file(s) not represented in the graph (top: .csv 5, .xml 3, (none) 2)

## Summary
- 544 nodes · 1186 edges · 31 communities (23 shown, 8 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `52eb9792`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_calculos_veiculos.py
- bancos_para_categoria
- test_paginas_geradas.py
- gerar_site
- os
- calculo.js
- gerar_pagina_individual
- gerar_comparador
- gerar_paginas_comparacao
- package.json
- test_calculo_js.mjs
- test_motor_v3.py
- rasterizar_favicon_png
- gerador_veiculos.py
- test_comparacao_sem_marca.py
- indexnow.py
- test_lastmod_e_fontes.py
- test_concordancia_e_metas.py
- gerar_paginas_renda
- exemplos_guias.py
- registrar_snapshot_semanal
- tags_medicao
- Simulador de Financiamento de Veículos — Datalab Global
- Taxas médias de juros do financiamento de veículos por banco (BACEN)
- gerar_sitemap
- Taxas médias de juros do financiamento de veículos por banco
- cadastro.md
- LEIA-ME.md
- nota-imprensa-2026-10.md

## God Nodes (most connected - your core abstractions)
1. `gerar_site()` - 35 edges
2. `gerar_pagina_individual()` - 30 edges
3. `calcular_pmt_price()` - 24 edges
4. `bancos_para_categoria()` - 23 edges
5. `gerar_paginas_comparacao()` - 23 edges
6. `gerar_comparador()` - 22 edges
7. `gerar_hub()` - 21 edges
8. `gerar_paginas_renda()` - 21 edges
9. `render_head()` - 20 edges
10. `corrigir_concordancia()` - 19 edges

## Surprising Connections (you probably didn't know these)
- `test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo()` --indirect_call--> `calcular_pmt_price()`  [INFERRED]
  tests/test_lastmod_e_fontes.py → gerador_veiculos.py
- `test_formatar_valor_curto()` --calls--> `formatar_valor_curto()`  [EXTRACTED]
  tests/test_calculos_veiculos.py → gerador_veiculos.py
- `test_renda_minima_cai_com_mais_entrada_e_prazo_maior()` --calls--> `renda_minima()`  [EXTRACTED]
  tests/test_motor_v3.py → gerador_veiculos.py
- `test_normalizar_chave_remove_acentos()` --calls--> `normalizar_chave()`  [EXTRACTED]
  tests/test_bancos_veiculos.py → bancos_veiculos.py
- `test_obter_regra_banco_desconhecido_usa_fallback()` --calls--> `obter_regra()`  [EXTRACTED]
  tests/test_bancos_veiculos.py → bancos_veiculos.py

## Import Cycles
- None detected.

## Communities (31 total, 8 thin omitted)

### Community 0 - "test_calculos_veiculos.py"
Cohesion: 0.06
Nodes (38): calcular_cet_veiculo(), calcular_iof_veiculo(), calcular_pmt_price(), calcular_renda_sugerida(), comparar_bancos_categoria(), _exemplos_guias(), gerar_grade_paginas(), gerar_slug_pagina() (+30 more)

### Community 1 - "bancos_para_categoria"
Cohesion: 0.09
Nodes (17): _aplicar_cache_taxas(), bancos_para_categoria(), nome_exibicao(), normalizar_chave(), obter_regra(), _hub_do_banco(), test_banco_honda_e_yamaha_so_aparecem_em_moto(), test_bancos_cativos_de_moto_nao_aparecem_em_carro() (+9 more)

### Community 2 - "test_paginas_geradas.py"
Cohesion: 0.08
Nodes (16): _arquivos_html(), _eh_noindex(), _paginas_individuais_de_banco(), test_calculo_js_existe_e_e_referenciado_pelas_paginas_individuais(), test_comparador_linka_para_hub_de_todos_os_bancos_da_categoria(), test_dominio_correto_em_todas_as_paginas(), test_faixa_de_mercado_nunca_linka_direto_pra_pagina_de_outro_banco(), test_headers_tem_hsts_e_libera_beacon_do_cloudflare_analytics() (+8 more)

### Community 3 - "gerar_site"
Cohesion: 0.15
Nodes (8): gerar_404(), gerar_calculo_js(), gerar_embed(), gerar_headers(), gerar_llms_txt(), gerar_robots_txt(), gerar_site(), obter_data_ultima_atualizacao()

### Community 4 - "os"
Cohesion: 0.05
Nodes (27): atualizar_data_referencia(), _buscar_taxas_bacen(), _carregar_cache(), _extrair_conteudo_ou_avisar_schema(), _normalizar_nome_instituicao(), obter_taxas_reais_mercado(), _salvar_cache(), atualizar_historico() (+19 more)

### Community 5 - "calculo.js"
Cohesion: 0.29
Nodes (15): atualizarValor(), calcularCetVeiculo(), calcularFaixaMercado(), calcularIofVeiculo(), calcularPmtPrice(), calcularRendaSugerida(), formatarReais(), formatCurrency() (+7 more)

### Community 6 - "gerar_pagina_individual"
Cohesion: 0.12
Nodes (15): favicon_com_fallback(), formatar_reais(), formatar_valor_curto(), gerar_hub(), gerar_pagina_individual(), historico_cache(), html_mais_sobre_banco(), html_projecao_price() (+7 more)

### Community 7 - "gerar_comparador"
Cohesion: 0.27
Nodes (8): gerar_comparador(), gerar_index(), html_taxas_hoje_home(), ilustracao_categoria(), schema_webpage(), slug_comparador(), slug_hub(), test_slug_hub_e_comparador_diferenciam_categoria()

### Community 8 - "gerar_paginas_comparacao"
Cohesion: 0.12
Nodes (22): corrigir_concordancia(), _cta_comparacao(), _escolher_que_cabe(), gerar_hub_aprenda(), gerar_indice_comparacao(), gerar_pagina_aprenda(), gerar_pagina_imprensa(), gerar_pagina_incorporar() (+14 more)

### Community 9 - "package.json"
Cohesion: 0.20
Nodes (9): description, devDependencies, tailwindcss, name, private, scripts, build:css, version (+1 more)

### Community 10 - "test_calculo_js.mjs"
Cohesion: 0.20
Nodes (4): caminhoCalculoJs, CASOS, __dirname, sandbox

### Community 11 - "test_motor_v3.py"
Cohesion: 0.06
Nodes (38): carregar_historico(), gerar_tabela_amortizacao(), html_requisitos_aprovacao(), pagina_valor_indexavel(), posicao_no_mercado(), projecao_price(), _saldo_apos(), serie_do_banco() (+30 more)

### Community 14 - "gerador_veiculos.py"
Cohesion: 0.11
Nodes (20): comparar_snapshots(), _data_br(), gerar_dados_abertos(), gerar_favicon_svg(), gerar_feed_atom(), gerar_llms_full_txt(), gerar_logo_svg(), gerar_pagina_atualizacoes() (+12 more)

### Community 15 - "test_comparacao_sem_marca.py"
Cohesion: 0.12
Nodes (19): linhas_comparacao(), resumo_historico(), slug_comparacao(), ler_historico(), test_cada_guia_recebe_varios_links_contextuais_e_paginas_novas_sao_alcancaveis(), test_calculo_do_embed_bate_com_o_calculo_do_site(), test_comparacao_nunca_inclui_banco_com_prazo_menor_que_o_pedido(), test_comparador_tem_mes_no_titulo_evolucao_so_com_bancos_da_categoria_e_faq() (+11 more)

### Community 16 - "indexnow.py"
Cohesion: 0.11
Nodes (14): _cli(), enviar(), enviar_url(), main(), montar_payload(), urls_do_sitemap(), urls_recentes(), test_cli_padrao_envia_so_as_recentes() (+6 more)

### Community 17 - "test_lastmod_e_fontes.py"
Cohesion: 0.12
Nodes (14): agora_iso(), carregar(), data_br(), hash_de(), registrar(), salvar(), test_data_br(), test_fontes_dos_guias_sao_https_e_sem_duplicata() (+6 more)

### Community 18 - "test_concordancia_e_metas.py"
Cohesion: 0.24
Nodes (5): test_corrigir_concordancia(), test_descriptions_e_titles_cabem_sem_corte(), test_paginas_sem_artigo_masculino_diante_de_banco_feminino(), test_rodape_linka_privacidade_e_termos(), test_rodape_mostra_identidade_da_empresa()

### Community 19 - "gerar_paginas_renda"
Cohesion: 0.24
Nodes (8): entrada_minima(), bancos_com_prazo(), _entradas_da_categoria(), gerar_paginas_renda(), _mediana(), pagina_comparacao_existe(), renda_minima(), slug_renda()

### Community 20 - "exemplos_guias.py"
Cohesion: 0.33
Nodes (5): _a(), _b(), montar_exemplos(), _pct(), _price_com_extra()

### Community 21 - "registrar_snapshot_semanal"
Cohesion: 0.40
Nodes (4): _escrever_historico_semanal(), ler_historico_semanal(), registrar_snapshot_semanal(), test_historico_semanal_idempotente_e_limitado_a_26_semanas()

### Community 22 - "tags_medicao"
Cohesion: 0.33
Nodes (4): gerar_medicao_js(), tags_medicao(), test_geradores_apontam_css_e_js_com_carimbo_de_versao(), test_tags_de_medicao_so_com_id_e_seletor_do_parceiro()

### Community 23 - "Simulador de Financiamento de Veículos — Datalab Global"
Cohesion: 0.33
Nodes (5): Como funciona, Dados abertos, Rodar localmente, Simulador de Financiamento de Veículos — Datalab Global, Sobre

### Community 24 - "Taxas médias de juros do financiamento de veículos por banco (BACEN)"
Cohesion: 0.40
Nodes (4): Cobertura, Colunas, Fonte e licença, Taxas médias de juros do financiamento de veículos por banco (BACEN)

## Knowledge Gaps
- **22 isolated node(s):** `name`, `private`, `version`, `description`, `build:css` (+17 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 202 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `calcular_pmt_price()` connect `test_calculos_veiculos.py` to `gerar_pagina_individual`, `gerar_paginas_comparacao`, `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`, `test_lastmod_e_fontes.py`, `gerar_paginas_renda`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `bancos_para_categoria()` connect `bancos_para_categoria` to `test_calculos_veiculos.py`, `gerar_pagina_individual`, `gerar_comparador`, `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`, `gerar_paginas_renda`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **Why does `corrigir_concordancia()` connect `gerar_paginas_comparacao` to `bancos_para_categoria`, `gerar_site`, `gerar_pagina_individual`, `test_motor_v3.py`, `gerador_veiculos.py`, `test_concordancia_e_metas.py`, `gerar_paginas_renda`?**
  _High betweenness centrality (0.018) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `calcular_pmt_price()` (e.g. with `_exemplos_guias()` and `test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo()`) actually correct?**
  _`calcular_pmt_price()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _22 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_calculos_veiculos.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06359189378057302 - nodes in this community are weakly interconnected._
- **Should `bancos_para_categoria` be split into smaller, more focused modules?**
  _Cohesion score 0.08712121212121213 - nodes in this community are weakly interconnected._