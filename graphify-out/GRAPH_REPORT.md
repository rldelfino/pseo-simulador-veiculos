# Graph Report - 003-pseo-simulador-veiculo  (2026-11-23)

## Corpus Check
- 54 files · ~230,736 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: .csv 5, (none) 4, .css 4)

## Summary
- 837 nodes · 1910 edges · 44 communities (34 shown, 10 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 27 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b2ccbc08`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_calculos_veiculos.py
- bancos_para_categoria
- test_paginas_geradas.py
- gerar_site
- etl_taxas_veiculos.py
- calculo.js
- icone
- gerar_pagina_atualizacoes
- gerar_paginas_mensais
- package.json
- test_calculo_js.mjs
- test_motor_v3.py
- paginas_seo/home.js
- gerador_veiculos.py
- test_comparacao_sem_marca.py
- indexnow.py
- test_lastmod_e_fontes.py
- gerar_icones.py
- gerar_hub
- exemplos_guias.py
- src/home.js
- gerar_comparador
- Simulador de Financiamento de Veículos — Datalab Global
- Taxas médias de juros do financiamento de veículos por banco (BACEN)
- test_cache_versao.py
- Taxas médias de juros do financiamento de veículos por banco
- cadastro.md
- LEIA-ME.md
- nota-imprensa-2026-10.md
- re
- verifica_saude.py
- sys
- os
- Handler
- testar_navegador.py
- AVALIAÇÃO DAS SUBPÁGINAS — veiculos.datalabglobal.com (21/11/2026)
- ilustracao_categoria
- testar_aleatorio.py
- publicacao.py
- tags_medicao

## God Nodes (most connected - your core abstractions)
1. `gerar_site()` - 37 edges
2. `bancos_para_categoria()` - 36 edges
3. `calcular_pmt_price()` - 30 edges
4. `desenhar()` - 28 edges
5. `desenhar()` - 28 edges
6. `gerar_hub()` - 24 edges
7. `gerar_comparador()` - 23 edges
8. `gerar_index()` - 21 edges
9. `calcular_cet_veiculo()` - 20 edges
10. `iniciar()` - 20 edges

## Surprising Connections (you probably didn't know these)
- `6. Tudo no SEO que muda se aprovar` --references--> `gerar_grade_paginas()`  [INFERRED]
  003-pseo-simulador-veiculo/AVALIACAO-SUBPAGINAS.md → 003-pseo-simulador-veiculo/gerador_veiculos.py
- `Home (template novo, 20/11/2026)` --references--> `regras_redirect()`  [INFERRED]
  003-pseo-simulador-veiculo/README.md → 003-pseo-simulador-veiculo/gerador_veiculos.py
- `AVALIAÇÃO DAS SUBPÁGINAS — veiculos.datalabglobal.com (21/11/2026)` --references--> `gerar_redirects()`  [INFERRED]
  003-pseo-simulador-veiculo/AVALIACAO-SUBPAGINAS.md → 003-pseo-simulador-veiculo/gerador_veiculos.py
- `test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo()` --indirect_call--> `calcular_pmt_price()`  [INFERRED]
  003-pseo-simulador-veiculo/tests/test_lastmod_e_fontes.py → 003-pseo-simulador-veiculo/gerador_veiculos.py
- `test_formatar_reais_sempre_duas_casas_decimais()` --calls--> `formatar_reais()`  [EXTRACTED]
  003-pseo-simulador-veiculo/tests/test_calculos_veiculos.py → 003-pseo-simulador-veiculo/gerador_veiculos.py

## Import Cycles
- None detected.

## Communities (44 total, 10 thin omitted)

### Community 0 - "test_calculos_veiculos.py"
Cohesion: 0.05
Nodes (44): calcular_cet_veiculo(), calcular_iof_veiculo(), calcular_pmt_price(), calcular_renda_sugerida(), comparar_bancos_categoria(), gerar_grade_paginas(), gerar_slug_pagina(), gerar_tabela_amortizacao() (+36 more)

### Community 1 - "bancos_para_categoria"
Cohesion: 0.07
Nodes (26): _aplicar_cache_taxas(), bancos_para_categoria(), nome_exibicao(), normalizar_chave(), obter_regra(), slug_renda(), test_banco_honda_e_yamaha_so_aparecem_em_moto(), test_bancos_cativos_de_moto_nao_aparecem_em_carro() (+18 more)

### Community 2 - "test_paginas_geradas.py"
Cohesion: 0.08
Nodes (16): _arquivos_html(), _eh_noindex(), _paginas_individuais_de_banco(), test_calculo_js_existe_e_e_referenciado_pela_home(), test_comparador_linka_para_hub_de_todos_os_bancos_da_categoria(), test_dominio_correto_em_todas_as_paginas(), test_faixa_de_mercado_nunca_linka_direto_pra_pagina_de_outro_banco(), test_headers_tem_hsts_e_libera_beacon_do_cloudflare_analytics() (+8 more)

### Community 3 - "gerar_site"
Cohesion: 0.11
Nodes (12): _arquivo_removido(), gerar_404(), gerar_calculo_js(), gerar_embed(), gerar_llms_txt(), gerar_robots_txt(), gerar_site(), gerar_verificacao_yandex() (+4 more)

### Community 4 - "etl_taxas_veiculos.py"
Cohesion: 0.10
Nodes (19): atualizar_data_referencia(), _buscar_taxas_bacen(), _carregar_cache(), _extrair_conteudo_ou_avisar_schema(), _normalizar_nome_instituicao(), obter_taxas_reais_mercado(), _salvar_cache(), atualizar_historico() (+11 more)

### Community 5 - "calculo.js"
Cohesion: 0.29
Nodes (15): atualizarValor(), calcularCetVeiculo(), calcularFaixaMercado(), calcularIofVeiculo(), calcularPmtPrice(), calcularRendaSugerida(), formatarReais(), formatCurrency() (+7 more)

### Community 6 - "icone"
Cohesion: 0.22
Nodes (5): _cta_comparacao(), favicon_com_fallback(), renderizar_faixa_mercado(), icone(), tooltip()

### Community 7 - "gerar_pagina_atualizacoes"
Cohesion: 0.24
Nodes (8): comparar_snapshots(), _data_br(), gerar_feed_atom(), gerar_pagina_atualizacoes(), _pct2(), _rfc3339(), _snapshots(), _texto_pontas()

### Community 8 - "gerar_paginas_mensais"
Cohesion: 0.09
Nodes (15): bancos_com_prazo(), _entradas_da_categoria(), _escolher_que_cabe(), formatar_valor_curto(), gerar_indice_comparacao(), gerar_paginas_comparacao(), gerar_paginas_mensais(), gerar_paginas_renda() (+7 more)

### Community 9 - "package.json"
Cohesion: 0.20
Nodes (9): description, devDependencies, tailwindcss, name, private, scripts, build:css, version (+1 more)

### Community 10 - "test_calculo_js.mjs"
Cohesion: 0.20
Nodes (4): caminhoCalculoJs, CASOS, __dirname, sandbox

### Community 11 - "test_motor_v3.py"
Cohesion: 0.06
Nodes (36): carregar_historico(), _escrever_historico_semanal(), html_requisitos_aprovacao(), ler_historico_semanal(), posicao_no_mercado(), registrar_snapshot_semanal(), _saldo_apos(), serie_do_banco() (+28 more)

### Community 12 - "paginas_seo/home.js"
Cohesion: 0.09
Nodes (64): ajustar(), anual(), atualizarEndereco(), bancos(), bancoSel(), brl(), brl2(), cartaoAlt() (+56 more)

### Community 14 - "gerador_veiculos.py"
Cohesion: 0.10
Nodes (24): entrada_minima(), _cartoes_categoria_home(), _cartoes_guias_home(), categoria_do_hub(), copiar_assets_home(), dados_simulador_home(), _faq_home(), gerar_index() (+16 more)

### Community 15 - "test_comparacao_sem_marca.py"
Cohesion: 0.13
Nodes (17): linhas_comparacao(), pagina_comparacao_existe(), slug_comparacao(), test_cada_guia_recebe_varios_links_contextuais_e_paginas_novas_sao_alcancaveis(), test_calculo_do_embed_bate_com_o_calculo_do_site(), test_comparacao_nunca_inclui_banco_com_prazo_menor_que_o_pedido(), test_comparador_tem_mes_no_titulo_evolucao_so_com_bancos_da_categoria_e_faq(), test_dados_abertos_batem_com_o_historico_e_so_tem_bancos_conhecidos() (+9 more)

### Community 16 - "indexnow.py"
Cohesion: 0.12
Nodes (14): _cli(), enviar(), enviar_url(), main(), montar_payload(), urls_do_sitemap(), urls_recentes(), test_cli_padrao_envia_so_as_recentes() (+6 more)

### Community 17 - "test_lastmod_e_fontes.py"
Cohesion: 0.11
Nodes (17): agora_iso(), carregar(), data_br(), hash_de(), registrar(), salvar(), test_comparadores_citam_a_semana_do_dado_e_nao_a_data_de_geracao(), test_dados_abertos_mostra_doi_hugging_face_e_markup_com_identifier() (+9 more)

### Community 18 - "gerar_icones.py"
Cohesion: 0.35
Nodes (6): _fonte(), _icone_html(), main(), _og_html(), _svg(), _wordmark_html()

### Community 19 - "gerar_hub"
Cohesion: 0.18
Nodes (8): _exemplos_guias(), formatar_reais(), gerar_hub(), html_como_citar(), html_comparacao_mercado(), html_link_e_compartilhar(), html_projecao_price(), html_serie_banco()

### Community 20 - "exemplos_guias.py"
Cohesion: 0.33
Nodes (5): _a(), _b(), montar_exemplos(), _pct(), _price_com_extra()

### Community 21 - "src/home.js"
Cohesion: 0.09
Nodes (64): ajustar(), anual(), atualizarEndereco(), bancos(), bancoSel(), brl(), brl2(), cartaoAlt() (+56 more)

### Community 22 - "gerar_comparador"
Cohesion: 0.13
Nodes (21): corrigir_concordancia(), gerar_analise_do_mes(), gerar_comparador(), gerar_dados_abertos(), gerar_hub_aprenda(), gerar_pagina_aprenda(), gerar_pagina_imprensa(), gerar_pagina_incorporar() (+13 more)

### Community 23 - "Simulador de Financiamento de Veículos — Datalab Global"
Cohesion: 0.29
Nodes (6): Como funciona, Dados abertos, Home (template novo, 20/11/2026), Rodar localmente, Simulador de Financiamento de Veículos — Datalab Global, Sobre

### Community 24 - "Taxas médias de juros do financiamento de veículos por banco (BACEN)"
Cohesion: 0.40
Nodes (4): Cobertura, Colunas, Fonte e licença, Taxas médias de juros do financiamento de veículos por banco (BACEN)

### Community 25 - "test_cache_versao.py"
Cohesion: 0.24
Nodes (4): gerar_sitemap(), _pagina(), test_lastmod_do_sitemap_ignora_fim_de_linha_crlf_do_windows(), test_lastmod_do_sitemap_ignora_o_carimbo_mas_acompanha_mudanca_real()

### Community 31 - "re"
Cohesion: 0.06
Nodes (29): gerar_headers(), _num_br(), marca(), _ler(), test_analise_do_mes_bate_com_a_serie_do_banco_central(), test_analise_do_mes_esta_no_sitemap_e_tem_o_basico(), test_botoes_de_citacao_copiam_o_link_em_html_nas_tres_paginas(), test_imprensa_e_dados_abertos_linkam_a_analise() (+21 more)

### Community 32 - "verifica_saude.py"
Cohesion: 0.17
Nodes (8): R, _site(), get(), test_detecta_adsense_noindex_no_sitemap_e_tamanho_fora_da_faixa(), test_site_saudavel_nao_falha(), get(), main(), verificar()

### Community 33 - "sys"
Cohesion: 0.32
Nodes (3): checa_removida(), checa_viva(), main()

### Community 34 - "os"
Cohesion: 0.17
Nodes (6): _regras_de_cabecalho(), subir(), externo(), links_de(), main(), paginas()

### Community 36 - "testar_navegador.py"
Cohesion: 0.31
Nodes (8): centavos(), confere(), esperado(), main(), pct(), reais(), rodar(), taxa_media()

### Community 37 - "AVALIAÇÃO DAS SUBPÁGINAS — veiculos.datalabglobal.com (21/11/2026)"
Cohesion: 0.20
Nodes (9): 1. Resposta curta, 2. Dados (Search Console, propriedade `sc-domain:datalabglobal.com`, coletados em 20/11/2026), 3. Qualidade das páginas (conta feita nos arquivos gerados, números mascarados), 4. Opções, 5. Mapa de redirecionamentos 301 proposto (opção B), 6. Tudo no SEO que muda se aprovar, 7. Revisão de SEO das páginas que ficam (conta feita nos arquivos gerados), 8. O que NÃO foi verificado (+1 more)

### Community 39 - "testar_aleatorio.py"
Cohesion: 0.48
Nodes (4): main(), num(), passo_confere(), sessao()

### Community 40 - "publicacao.py"
Cohesion: 0.43
Nodes (4): _escrever(), gerar(), _ler(), _mes()

### Community 45 - "tags_medicao"
Cohesion: 0.33
Nodes (4): gerar_medicao_js(), tags_medicao(), test_geradores_apontam_css_e_js_com_carimbo_de_versao(), test_tags_de_medicao_so_com_id_e_seletor_do_parceiro()

## Knowledge Gaps
- **29 isolated node(s):** `name`, `private`, `version`, `description`, `build:css` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 257 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `bancos_para_categoria()` connect `bancos_para_categoria` to `test_calculos_veiculos.py`, `testar_navegador.py`, `testar_aleatorio.py`, `gerar_paginas_mensais`, `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`, `test_lastmod_e_fontes.py`, `gerar_hub`, `gerar_comparador`, `re`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `calcular_pmt_price()` connect `test_calculos_veiculos.py` to `testar_navegador.py`, `testar_aleatorio.py`, `gerar_paginas_mensais`, `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`, `test_lastmod_e_fontes.py`, `gerar_hub`, `re`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `ler_historico()` connect `etl_taxas_veiculos.py` to `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `calcular_pmt_price()` (e.g. with `_exemplos_guias()` and `test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo()`) actually correct?**
  _`calcular_pmt_price()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_calculos_veiculos.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05288207297726071 - nodes in this community are weakly interconnected._
- **Should `bancos_para_categoria` be split into smaller, more focused modules?**
  _Cohesion score 0.07149758454106281 - nodes in this community are weakly interconnected._