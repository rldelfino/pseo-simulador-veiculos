# Graph Report - 003-pseo-simulador-veiculo  (2026-11-21)

## Corpus Check
- 54 files · ~230,704 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 19 file(s) not represented in the graph (top: .csv 5, (none) 4, .css 4)

## Summary
- 836 nodes · 1909 edges · 46 communities (37 shown, 9 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 27 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `c684c7f0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_calculos_veiculos.py
- bancos_para_categoria
- test_paginas_geradas.py
- gerar_site
- etl_taxas_veiculos.py
- calculo.js
- gerar_comparador
- gerar_pagina_atualizacoes
- gerar_indice_comparacao
- package.json
- test_calculo_js.mjs
- test_motor_v3.py
- paginas_seo/home.js
- gerador_veiculos.py
- test_comparacao_sem_marca.py
- indexnow.py
- test_lastmod_e_fontes.py
- calcular_cet_veiculo
- gerar_hub
- exemplos_guias.py
- src/home.js
- corrigir_concordancia
- Simulador de Financiamento de Veículos — Datalab Global
- Taxas médias de juros do financiamento de veículos por banco (BACEN)
- gerar_paginas_mensais
- Taxas médias de juros do financiamento de veículos por banco
- cadastro.md
- LEIA-ME.md
- nota-imprensa-2026-10.md
- re
- verifica_saude.py
- test_redirects.py
- os
- Handler
- testar_navegador.py
- AVALIAÇÃO DAS SUBPÁGINAS — veiculos.datalabglobal.com (21/11/2026)
- test_home_nova.py
- testar_aleatorio.py
- sys
- calcular_iof_veiculo
- calcular_pmt_price
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
- `test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo()` --indirect_call--> `calcular_pmt_price()`  [INFERRED]
  tests/test_lastmod_e_fontes.py → gerador_veiculos.py
- `6. Tudo no SEO que muda se aprovar` --references--> `gerar_grade_paginas()`  [INFERRED]
  AVALIACAO-SUBPAGINAS.md → gerador_veiculos.py
- `Home (template novo, 20/11/2026)` --references--> `regras_redirect()`  [INFERRED]
  README.md → gerador_veiculos.py
- `test_formatar_reais_sempre_duas_casas_decimais()` --calls--> `formatar_reais()`  [EXTRACTED]
  tests/test_calculos_veiculos.py → gerador_veiculos.py
- `test_formatar_valor_curto()` --calls--> `formatar_valor_curto()`  [EXTRACTED]
  tests/test_calculos_veiculos.py → gerador_veiculos.py

## Import Cycles
- None detected.

## Communities (46 total, 9 thin omitted)

### Community 0 - "test_calculos_veiculos.py"
Cohesion: 0.11
Nodes (22): comparar_bancos_categoria(), gerar_grade_paginas(), gerar_slug_pagina(), montar_lookup(), slugificar_banco(), test_formatar_reais_sempre_duas_casas_decimais(), test_formatar_valor_curto(), test_grade_cobre_as_tres_categorias() (+14 more)

### Community 1 - "bancos_para_categoria"
Cohesion: 0.11
Nodes (12): _aplicar_cache_taxas(), bancos_para_categoria(), nome_exibicao(), normalizar_chave(), test_banco_honda_e_yamaha_so_aparecem_em_moto(), test_bancos_cativos_de_moto_nao_aparecem_em_carro(), test_categoria_invalida_levanta_erro(), test_nome_exibicao_usa_acentuacao_correta() (+4 more)

### Community 2 - "test_paginas_geradas.py"
Cohesion: 0.08
Nodes (16): _arquivos_html(), _eh_noindex(), _paginas_individuais_de_banco(), test_calculo_js_existe_e_e_referenciado_pela_home(), test_comparador_linka_para_hub_de_todos_os_bancos_da_categoria(), test_dominio_correto_em_todas_as_paginas(), test_faixa_de_mercado_nunca_linka_direto_pra_pagina_de_outro_banco(), test_headers_tem_hsts_e_libera_beacon_do_cloudflare_analytics() (+8 more)

### Community 3 - "gerar_site"
Cohesion: 0.14
Nodes (9): copiar_assets_home(), gerar_404(), gerar_calculo_js(), gerar_embed(), gerar_robots_txt(), gerar_site(), gerar_verificacao_yandex(), _hash_arquivo() (+1 more)

### Community 4 - "etl_taxas_veiculos.py"
Cohesion: 0.10
Nodes (19): atualizar_data_referencia(), _buscar_taxas_bacen(), _carregar_cache(), _extrair_conteudo_ou_avisar_schema(), _normalizar_nome_instituicao(), obter_taxas_reais_mercado(), _salvar_cache(), atualizar_historico() (+11 more)

### Community 5 - "calculo.js"
Cohesion: 0.29
Nodes (15): atualizarValor(), calcularCetVeiculo(), calcularFaixaMercado(), calcularIofVeiculo(), calcularPmtPrice(), calcularRendaSugerida(), formatarReais(), formatCurrency() (+7 more)

### Community 6 - "gerar_comparador"
Cohesion: 0.19
Nodes (7): _cta_comparacao(), favicon_com_fallback(), gerar_comparador(), ilustracao_categoria(), renderizar_faixa_mercado(), icone(), tooltip()

### Community 7 - "gerar_pagina_atualizacoes"
Cohesion: 0.14
Nodes (16): comparar_snapshots(), _data_br(), gerar_analise_do_mes(), gerar_feed_atom(), gerar_pagina_atualizacoes(), html_como_citar(), html_evolucao_taxas(), html_link_e_compartilhar() (+8 more)

### Community 8 - "gerar_indice_comparacao"
Cohesion: 0.22
Nodes (5): formatar_valor_curto(), gerar_indice_comparacao(), gerar_paginas_comparacao(), _guias_html(), _reais_inteiros()

### Community 9 - "package.json"
Cohesion: 0.20
Nodes (9): description, devDependencies, tailwindcss, name, private, scripts, build:css, version (+1 more)

### Community 10 - "test_calculo_js.mjs"
Cohesion: 0.20
Nodes (4): caminhoCalculoJs, CASOS, __dirname, sandbox

### Community 11 - "test_motor_v3.py"
Cohesion: 0.06
Nodes (35): carregar_historico(), _escrever_historico_semanal(), gerar_tabela_amortizacao(), html_requisitos_aprovacao(), ler_historico_semanal(), posicao_no_mercado(), projecao_price(), registrar_snapshot_semanal() (+27 more)

### Community 12 - "paginas_seo/home.js"
Cohesion: 0.09
Nodes (64): ajustar(), anual(), atualizarEndereco(), bancos(), bancoSel(), brl(), brl2(), cartaoAlt() (+56 more)

### Community 14 - "gerador_veiculos.py"
Cohesion: 0.13
Nodes (19): _cartoes_categoria_home(), _cartoes_guias_home(), categoria_do_hub(), dados_simulador_home(), _faq_home(), gerar_index(), gerar_llms_full_txt(), gerar_llms_txt() (+11 more)

### Community 15 - "test_comparacao_sem_marca.py"
Cohesion: 0.13
Nodes (17): bancos_com_prazo(), linhas_comparacao(), pagina_comparacao_existe(), slug_comparacao(), test_cada_guia_recebe_varios_links_contextuais_e_paginas_novas_sao_alcancaveis(), test_calculo_do_embed_bate_com_o_calculo_do_site(), test_comparacao_nunca_inclui_banco_com_prazo_menor_que_o_pedido(), test_comparador_tem_mes_no_titulo_evolucao_so_com_bancos_da_categoria_e_faq() (+9 more)

### Community 16 - "indexnow.py"
Cohesion: 0.08
Nodes (20): _cli(), enviar(), enviar_url(), main(), montar_payload(), urls_do_sitemap(), urls_recentes(), test_corrigir_concordancia() (+12 more)

### Community 17 - "test_lastmod_e_fontes.py"
Cohesion: 0.10
Nodes (18): agora_iso(), carregar(), data_br(), hash_de(), registrar(), salvar(), test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo(), test_comparadores_citam_a_semana_do_dado_e_nao_a_data_de_geracao() (+10 more)

### Community 18 - "calcular_cet_veiculo"
Cohesion: 0.13
Nodes (9): entrada_minima(), calcular_cet_veiculo(), padrao_simulador_home(), test_entrada_minima_usado_e_moto_maior_ou_igual_a_novo(), test_cet_cai_com_prazo_maior_pro_mesmo_banco(), test_cet_e_sempre_maior_que_a_taxa_nominal(), test_cet_escala_com_a_taxa_nominal(), test_cet_zero_quando_nao_ha_financiamento() (+1 more)

### Community 19 - "gerar_hub"
Cohesion: 0.18
Nodes (9): obter_regra(), formatar_reais(), gerar_hub(), html_comparacao_mercado(), html_projecao_price(), link_simulador(), schema_webpage(), test_obter_regra_banco_desconhecido_usa_fallback() (+1 more)

### Community 20 - "exemplos_guias.py"
Cohesion: 0.33
Nodes (5): _a(), _b(), montar_exemplos(), _pct(), _price_com_extra()

### Community 21 - "src/home.js"
Cohesion: 0.09
Nodes (64): ajustar(), anual(), atualizarEndereco(), bancos(), bancoSel(), brl(), brl2(), cartaoAlt() (+56 more)

### Community 22 - "corrigir_concordancia"
Cohesion: 0.11
Nodes (20): corrigir_concordancia(), _entradas_da_categoria(), gerar_dados_abertos(), gerar_hub_aprenda(), gerar_pagina_aprenda(), gerar_pagina_imprensa(), gerar_pagina_incorporar(), gerar_pagina_metodologia() (+12 more)

### Community 23 - "Simulador de Financiamento de Veículos — Datalab Global"
Cohesion: 0.29
Nodes (6): Como funciona, Dados abertos, Home (template novo, 20/11/2026), Rodar localmente, Simulador de Financiamento de Veículos — Datalab Global, Sobre

### Community 24 - "Taxas médias de juros do financiamento de veículos por banco (BACEN)"
Cohesion: 0.40
Nodes (4): Cobertura, Colunas, Fonte e licença, Taxas médias de juros do financiamento de veículos por banco (BACEN)

### Community 25 - "gerar_paginas_mensais"
Cohesion: 0.14
Nodes (9): _arquivo_removido(), _escolher_que_cabe(), gerar_paginas_mensais(), historico_cache(), html_mais_sobre_banco(), limpar_paginas_obsoletas(), _mediana(), nome_mes() (+1 more)

### Community 31 - "re"
Cohesion: 0.07
Nodes (20): gerar_sitemap(), _fonte(), _icone_html(), main(), _og_html(), _svg(), _wordmark_html(), marca() (+12 more)

### Community 32 - "verifica_saude.py"
Cohesion: 0.18
Nodes (8): R, _site(), get(), test_detecta_adsense_noindex_no_sitemap_e_tamanho_fora_da_faixa(), test_site_saudavel_nao_falha(), get(), main(), verificar()

### Community 33 - "test_redirects.py"
Cohesion: 0.26
Nodes (10): slug_renda(), _casa(), _destino(), _regras(), test_nenhum_html_de_pagina_removida_continua_publicado_e_nenhuma_pagina_viva_casa_regra(), test_regras_cabem_nos_limites_do_cloudflare_pages(), test_sem_cadeia_sem_laco_e_nada_do_sitemap_redireciona(), test_toda_url_removida_redireciona_para_uma_pagina_que_existe() (+2 more)

### Community 34 - "os"
Cohesion: 0.13
Nodes (9): _regras_de_cabecalho(), subir(), externo(), links_de(), main(), paginas(), checa_removida(), checa_viva() (+1 more)

### Community 36 - "testar_navegador.py"
Cohesion: 0.31
Nodes (8): centavos(), confere(), esperado(), main(), pct(), reais(), rodar(), taxa_media()

### Community 37 - "AVALIAÇÃO DAS SUBPÁGINAS — veiculos.datalabglobal.com (21/11/2026)"
Cohesion: 0.20
Nodes (9): 1. Resposta curta, 2. Dados (Search Console, propriedade `sc-domain:datalabglobal.com`, coletados em 20/11/2026), 3. Qualidade das páginas (conta feita nos arquivos gerados, números mascarados), 4. Opções, 5. Mapa de redirecionamentos 301 proposto (opção B), 6. Tudo no SEO que muda se aprovar, 7. Revisão de SEO das páginas que ficam (conta feita nos arquivos gerados), 8. O que NÃO foi verificado (+1 more)

### Community 38 - "test_home_nova.py"
Cohesion: 0.23
Nodes (12): gerar_headers(), _num_br(), _home(), test_arquivo_do_yandex_esta_versionavel_e_fora_do_sitemap(), test_arquivo_do_yandex_tem_o_conteudo_exato(), test_bloco_de_dados_do_simulador_tem_as_taxas_de_cada_banco(), test_cenario_padrao_do_html_bate_com_a_conta_de_referencia(), test_csp_da_home_nao_tem_unsafe_inline_e_o_resto_do_site_segue_igual() (+4 more)

### Community 39 - "testar_aleatorio.py"
Cohesion: 0.48
Nodes (4): main(), num(), passo_confere(), sessao()

### Community 40 - "sys"
Cohesion: 0.21
Nodes (5): _escrever(), gerar(), _ler(), _mes(), test_pacote_de_publicacao_gerado_dos_dados_abertos()

### Community 41 - "calcular_iof_veiculo"
Cohesion: 0.15
Nodes (9): calcular_iof_veiculo(), calcular_renda_sugerida(), _exemplos_guias(), test_iof_aplica_teto_de_365_dias(), test_iof_e_proporcional_ao_valor_financiado(), test_iof_soma_aliquota_fixa_e_diaria_sem_teto(), test_iof_zero_quando_sem_financiamento(), test_renda_sugerida_cobre_30_por_cento_da_parcela() (+1 more)

### Community 44 - "calcular_pmt_price"
Cohesion: 0.17
Nodes (8): calcular_pmt_price(), renda_minima(), _saldo_apos(), test_pmt_bate_formula_manual_da_tabela_price(), test_pmt_com_taxa_zero_e_divisao_simples(), test_pmt_zero_quando_nao_ha_financiamento(), test_numeros_dos_guias_sao_coerentes(), test_renda_minima_cai_com_mais_entrada_e_prazo_maior()

### Community 45 - "tags_medicao"
Cohesion: 0.33
Nodes (4): gerar_medicao_js(), tags_medicao(), test_geradores_apontam_css_e_js_com_carimbo_de_versao(), test_tags_de_medicao_so_com_id_e_seletor_do_parceiro()

## Knowledge Gaps
- **29 isolated node(s):** `name`, `private`, `version`, `description`, `build:css` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 256 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `bancos_para_categoria()` connect `bancos_para_categoria` to `test_calculos_veiculos.py`, `test_redirects.py`, `testar_navegador.py`, `test_home_nova.py`, `testar_aleatorio.py`, `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`, `test_lastmod_e_fontes.py`, `calcular_cet_veiculo`, `gerar_hub`, `corrigir_concordancia`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Why does `calcular_pmt_price()` connect `calcular_pmt_price` to `test_calculos_veiculos.py`, `testar_navegador.py`, `test_home_nova.py`, `testar_aleatorio.py`, `calcular_iof_veiculo`, `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`, `test_lastmod_e_fontes.py`, `calcular_cet_veiculo`, `gerar_hub`, `gerar_paginas_mensais`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `ler_historico()` connect `etl_taxas_veiculos.py` to `test_motor_v3.py`, `gerador_veiculos.py`, `test_comparacao_sem_marca.py`?**
  _High betweenness centrality (0.015) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `calcular_pmt_price()` (e.g. with `_exemplos_guias()` and `test_amortizacao_extra_da_menos_juros_ao_encurtar_o_prazo()`) actually correct?**
  _`calcular_pmt_price()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _29 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_calculos_veiculos.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11375661375661375 - nodes in this community are weakly interconnected._
- **Should `bancos_para_categoria` be split into smaller, more focused modules?**
  _Cohesion score 0.1076923076923077 - nodes in this community are weakly interconnected._