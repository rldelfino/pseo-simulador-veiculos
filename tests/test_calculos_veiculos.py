"""
Testes de regressão pro motor de cálculo de financiamento de veículo
(gerador_veiculos.py). Mesmo espírito do test_calculos.py do projeto
irmão: trava a MATEMÁTICA antes que um bug sutil de cálculo chegue a uma
página publicada.

Rodar com: python -m pytest tests/ -v
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gerador_veiculos import (
    PRAZOS_MESES,
    VALORES_POR_CATEGORIA,
    calcular_cet_veiculo,
    calcular_iof_veiculo,
    calcular_pmt_price,
    calcular_renda_sugerida,
    comparar_bancos_categoria,
    formatar_reais,
    formatar_valor_curto,
    gerar_grade_paginas,
    gerar_slug_pagina,
    gerar_tabela_amortizacao,
    montar_lookup,
    slug_comparador,
    slug_hub,
    slugificar_banco,
)
from bancos_veiculos import BANCOS_VEICULOS, bancos_para_categoria


# ---------------------------------------------------------------------------
# calcular_pmt_price
# ---------------------------------------------------------------------------

def test_pmt_bate_formula_manual_da_tabela_price():
    """Confere contra a fórmula fechada da Tabela Price calculada à mão,
    com números redondos fáceis de conferir na calculadora."""
    valor_financiado, prazo, taxa_am = 10_000, 12, 2.0
    i = taxa_am / 100
    esperado = valor_financiado * (i * (1 + i) ** prazo) / ((1 + i) ** prazo - 1)
    assert abs(calcular_pmt_price(valor_financiado, prazo, taxa_am) - esperado) < 0.01


def test_pmt_zero_quando_nao_ha_financiamento():
    assert calcular_pmt_price(0, 48, 2.0) == 0.0
    assert calcular_pmt_price(10_000, 0, 2.0) == 0.0


def test_pmt_com_taxa_zero_e_divisao_simples():
    assert calcular_pmt_price(12_000, 12, 0.0) == 1_000.0


def test_pmt_e_estritamente_fixa_ao_longo_do_prazo():
    """Regra da Tabela Price: parcela igual do primeiro ao último mês —
    valida indiretamente via gerar_tabela_amortizacao, que devolve a
    mesma parcela usada em cada linha."""
    linhas = gerar_tabela_amortizacao(20_000, 36, 1.86)
    parcelas = {round(l["parcela"], 6) for l in linhas}
    assert len(parcelas) == 1


# ---------------------------------------------------------------------------
# calcular_iof_veiculo — alíquota de lei (Decreto 6.306/2007, art. 7º)
# ---------------------------------------------------------------------------

def test_iof_soma_aliquota_fixa_e_diaria_sem_teto():
    valor_financiado, prazo = 20_000, 12  # 360 dias, ainda não bate no teto de 365
    esperado = valor_financiado * (0.0038 + 0.000082 * 360)
    assert abs(calcular_iof_veiculo(valor_financiado, prazo) - esperado) < 0.01


def test_iof_aplica_teto_de_365_dias():
    """A partir de 13 meses (390 dias, já acima do teto), o IOF não deve
    mais crescer com o prazo — regressão específica pra não esquecer o
    teto ao mexer na fórmula."""
    valor_financiado = 20_000
    iof_13_meses = calcular_iof_veiculo(valor_financiado, 13)
    iof_60_meses = calcular_iof_veiculo(valor_financiado, 60)
    esperado_no_teto = valor_financiado * (0.0038 + 0.000082 * 365)
    assert abs(iof_13_meses - esperado_no_teto) < 0.01
    assert abs(iof_60_meses - esperado_no_teto) < 0.01


def test_iof_e_proporcional_ao_valor_financiado():
    assert calcular_iof_veiculo(40_000, 24) == calcular_iof_veiculo(20_000, 24) * 2


def test_iof_zero_quando_sem_financiamento():
    assert calcular_iof_veiculo(0, 24) == 0.0


# ---------------------------------------------------------------------------
# calcular_cet_veiculo
# ---------------------------------------------------------------------------

def test_cet_e_sempre_maior_que_a_taxa_nominal():
    """CET soma IOF + tarifa de registro + seguro prestamista à taxa pura
    — matematicamente tem que ficar acima da taxa de juros nominal, assim
    como no financiamento imobiliário."""
    taxa_am = 1.86  # Banco Inter
    taxa_aa_equivalente = ((1 + taxa_am / 100) ** 12 - 1) * 100
    cet = calcular_cet_veiculo(20_000, 48, taxa_am)
    assert cet > taxa_aa_equivalente


def test_cet_zero_quando_nao_ha_financiamento():
    assert calcular_cet_veiculo(0, 48, 2.0) == 0.0
    assert calcular_cet_veiculo(20_000, 0, 2.0) == 0.0


def test_cet_escala_com_a_taxa_nominal():
    """Se a taxa nominal sobe, o CET tem que subir junto — nunca pode
    ficar preso independente da taxa de entrada (mesma regressão do
    Banco Inter travada no projeto irmão)."""
    cet_baixo = calcular_cet_veiculo(20_000, 48, 1.01)   # Caixa
    cet_alto = calcular_cet_veiculo(20_000, 48, 3.35)    # Omni
    assert cet_alto > cet_baixo


def test_cet_cai_com_prazo_maior_pro_mesmo_banco():
    """Contraintuitivo à primeira vista, mas correto: IOF e tarifa de
    registro são custos FIXOS de uma vez só. Num prazo curto, esse custo
    fixo pesa muito mais sobre poucos meses de parcela (CET bem acima da
    taxa nominal); num prazo longo, o mesmo custo fixo se dilui ao longo
    de mais meses e o CET se aproxima mais da taxa nominal anualizada.
    Essa é a mesma razão pela qual, na vida real, financiamentos muito
    curtos costumam anunciar CET desproporcionalmente alto."""
    cet_curto = calcular_cet_veiculo(20_000, 12, 1.86)
    cet_longo = calcular_cet_veiculo(20_000, 60, 1.86)
    assert cet_curto > cet_longo


# ---------------------------------------------------------------------------
# calcular_renda_sugerida
# ---------------------------------------------------------------------------

def test_renda_sugerida_cobre_30_por_cento_da_parcela():
    parcela = 900.0
    renda = calcular_renda_sugerida(parcela)
    assert abs(renda * 0.30 - parcela) < 0.01


def test_renda_sugerida_zero_sem_parcela():
    assert calcular_renda_sugerida(0) == 0.0


# ---------------------------------------------------------------------------
# comparar_bancos_categoria
# ---------------------------------------------------------------------------

def test_ranking_vem_ordenado_por_cet():
    ranking = comparar_bancos_categoria("novo", 100_000, 48)
    cets = [r["cet"] for r in ranking]
    assert cets == sorted(cets)


def test_ranking_carro_novo_nao_inclui_cativas_de_moto():
    ranking = comparar_bancos_categoria("novo", 100_000, 48)
    bancos = {r["banco"] for r in ranking}
    assert "Banco Honda" not in bancos
    assert "Banco Yamaha" not in bancos


def test_ranking_moto_inclui_cativas_e_universais():
    ranking = comparar_bancos_categoria("moto", 15_000, 24)
    bancos = {r["banco"] for r in ranking}
    assert "Banco Honda" in bancos
    assert "Banco Yamaha" in bancos
    assert "Itau" in bancos


def test_ranking_respeita_prazo_maximo_de_cada_banco():
    """Honda/Yamaha têm prazo_max=48 — pedindo 60 meses, essas duas
    entradas do ranking devem vir capadas em 48, não em 60."""
    ranking = comparar_bancos_categoria("moto", 15_000, 60)
    por_banco = {r["banco"]: r for r in ranking}
    assert por_banco["Banco Honda"]["prazo"] == 48
    assert por_banco["Banco Yamaha"]["prazo"] == 48
    assert por_banco["Itau"]["prazo"] == 60


def test_ranking_cobre_todos_os_bancos_elegiveis_da_categoria():
    for categoria in ("novo", "usado", "moto"):
        ranking = comparar_bancos_categoria(categoria, VALORES_POR_CATEGORIA[categoria][0], 24)
        assert {r["banco"] for r in ranking} == set(bancos_para_categoria(categoria).keys())


# ---------------------------------------------------------------------------
# Slugs
# ---------------------------------------------------------------------------

def test_slugificar_banco_remove_acento_e_espaco():
    assert slugificar_banco("Itau") == "itau"
    assert slugificar_banco("Banco Inter") == "banco-inter"
    assert slugificar_banco("BV Financeira") == "bv-financeira"


def test_slug_pagina_segue_o_padrao_combinado():
    slug = gerar_slug_pagina("novo", "Itau", 80_000, 48)
    assert slug == "financiamento-carro-novo-itau-80-mil-48-meses"


def test_slug_hub_e_comparador_diferenciam_categoria():
    assert slug_hub("novo", "Itau") == "hub-itau-carro-novo"
    assert slug_hub("usado", "Itau") == "hub-itau-carro-usado"
    assert slug_comparador("moto") == "comparador-moto"


# ---------------------------------------------------------------------------
# gerar_grade_paginas / montar_lookup — integridade estrutural da árvore
# ---------------------------------------------------------------------------

def test_grade_nao_tem_slugs_duplicados():
    paginas = gerar_grade_paginas()
    slugs = [p["slug"] for p in paginas]
    assert len(slugs) == len(set(slugs)), "slug duplicado na grade — duas páginas colidiriam no mesmo arquivo"


def test_grade_respeita_prazo_maximo_por_banco():
    paginas = gerar_grade_paginas()
    for p in paginas:
        assert p["prazo"] <= BANCOS_VEICULOS[p["banco"]]["prazo_max"]


def test_grade_nao_gera_cativa_de_moto_fora_de_moto():
    paginas = gerar_grade_paginas()
    for p in paginas:
        if p["banco"] in ("Banco Honda", "Banco Yamaha"):
            assert p["categoria"] == "moto"


def test_grade_cobre_as_tres_categorias():
    paginas = gerar_grade_paginas()
    categorias_geradas = {p["categoria"] for p in paginas}
    assert categorias_geradas == {"novo", "usado", "moto"}


def test_grade_valor_financiado_e_menor_que_valor_do_veiculo():
    for p in gerar_grade_paginas():
        assert 0 < p["valor_financiado"] < p["valor_veiculo"]


def test_montar_lookup_encontra_toda_pagina_da_grade():
    paginas = gerar_grade_paginas()
    lookup = montar_lookup(paginas)
    for p in paginas:
        chave = (p["categoria"], p["banco"], p["valor_veiculo"], p["prazo"])
        assert lookup[chave] == p["slug"]


# ---------------------------------------------------------------------------
# formatar_reais / formatar_valor_curto
# ---------------------------------------------------------------------------

def test_formatar_reais_sempre_duas_casas_decimais():
    assert formatar_reais(1000) == "R$ 1.000,00"
    assert formatar_reais(1000.7) == "R$ 1.000,70"


def test_formatar_valor_curto():
    assert formatar_valor_curto(80_000) == "80 mil"
    assert formatar_valor_curto(8_000) == "8 mil"
