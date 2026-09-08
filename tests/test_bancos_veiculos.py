"""
Testes de regressão pra matriz de bancos de financiamento veicular
(bancos_veiculos.py).

Por que isso existe: no projeto irmão (pseo_simulador), taxas erradas só
foram achadas por inspeção manual depois de já estarem em produção (ver
bancos.py de lá). Aqui a matriz de bancos é travada por teste ANTES de
existir motor de cálculo ou gerador — o objetivo é nunca deixar uma taxa
implausível, uma categoria mal atribuída ou uma regressão de dado chegar
ao gerador sem que um teste rejeite primeiro.

Rodar com: python -m pytest tests/ -v
(precisa estar na raiz do projeto — bancos_veiculos.py é importado com
path relativo).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bancos_veiculos import (
    BANCOS_VEICULOS,
    ENTRADA_MINIMA_POR_CATEGORIA,
    REGRA_FALLBACK,
    bancos_para_categoria,
    entrada_minima,
    nome_exibicao,
    normalizar_chave,
    obter_regra,
)


# ---------------------------------------------------------------------------
# Plausibilidade dos dados brutos
# ---------------------------------------------------------------------------

def test_todo_banco_tem_taxa_plausivel():
    """Faixa generosa (0,5% a 4,0% a.m. / 6% a 55% a.a.) cobre do banco
    cativo mais barato (Mercedes-Benz) ao mais caro do relatório BACEN
    (Omni) — qualquer valor fora disso é sinal de erro de digitação."""
    for banco, dados in BANCOS_VEICULOS.items():
        assert 0.5 <= dados["taxa_am"] <= 4.0, f"{banco} com taxa a.m. implausível: {dados['taxa_am']}"
        assert 6.0 <= dados["taxa_aa"] <= 55.0, f"{banco} com taxa a.a. implausível: {dados['taxa_aa']}"
        assert dados["prazo_max"] > 0
        assert set(dados["aplica_a"]) <= {"novo", "usado", "moto"}
        assert dados["aplica_a"], f"{banco} sem nenhuma categoria em aplica_a"


def test_taxa_aa_e_coerente_com_taxa_am_composta():
    """taxa_aa vem direto do BACEN (não é recalculada), mas tem que bater
    aproximadamente com a composição de taxa_am — uma divergência grande
    sinaliza taxa_am/taxa_aa trocadas entre bancos diferentes na cópia."""
    for banco, dados in BANCOS_VEICULOS.items():
        aa_esperado = ((1 + dados["taxa_am"] / 100) ** 12 - 1) * 100
        assert abs(aa_esperado - dados["taxa_aa"]) < 1.5, (
            f"{banco}: taxa_am={dados['taxa_am']} implica ~{aa_esperado:.2f}% a.a., "
            f"mas taxa_aa registrada é {dados['taxa_aa']}% — confira se não houve troca de valores."
        )


def test_nenhum_banco_com_taxa_zerada_ou_negativa():
    for banco, dados in BANCOS_VEICULOS.items():
        assert dados["taxa_am"] > 0 and dados["taxa_aa"] > 0, f"{banco} com taxa zerada/negativa"


# ---------------------------------------------------------------------------
# Trava de regressão contra as taxas "a partir de" (marketing) descartadas
# na pesquisa inicial — se algum merge reintroduzir esses valores otimistas
# demais, este teste avisa antes de ir pra produção.
# ---------------------------------------------------------------------------

def test_taxas_nao_regridem_para_valores_promocionais_descartados():
    valores_promocionais_descartados = {
        "BV Financeira": 1.14,
        "Santander": 1.29,
        "Bradesco": 1.55,
        "Banco Inter": 1.69,
        "Itau": 1.98,
    }
    for banco, taxa_promocional in valores_promocionais_descartados.items():
        assert BANCOS_VEICULOS[banco]["taxa_am"] != taxa_promocional, (
            f"{banco} voltou pra taxa promocional/marketing descartada "
            f"({taxa_promocional}% a.m.) em vez da média real do BACEN — "
            f"verifique se um merge não sobrescreveu a correção."
        )


# ---------------------------------------------------------------------------
# Segmentação por categoria de veículo (novo/usado/moto)
# ---------------------------------------------------------------------------

def test_bancos_cativos_de_moto_nao_aparecem_em_carro():
    for categoria in ("novo", "usado"):
        bancos = bancos_para_categoria(categoria)
        assert "Banco Honda" not in bancos
        assert "Banco Yamaha" not in bancos


def test_banco_honda_e_yamaha_so_aparecem_em_moto():
    bancos_moto = bancos_para_categoria("moto")
    assert "Banco Honda" in bancos_moto
    assert "Banco Yamaha" in bancos_moto


def test_categoria_invalida_levanta_erro():
    import pytest
    with pytest.raises(ValueError):
        bancos_para_categoria("caminhao")


def test_todas_categorias_tem_pelo_menos_um_banco():
    for categoria in ("novo", "usado", "moto"):
        assert len(bancos_para_categoria(categoria)) > 0


def test_entrada_minima_usado_e_moto_maior_ou_igual_a_novo():
    """Convenção de mercado: veículo usado/moto deprecia mais rápido, banco
    pede entrada maior (LTV menor) do que pra carro novo. Se isso inverter,
    é sinal de erro de configuração, não de dado real observado."""
    assert entrada_minima("usado") >= entrada_minima("novo")
    assert entrada_minima("moto") >= entrada_minima("novo")


def test_entrada_minima_cobre_as_tres_categorias():
    assert set(ENTRADA_MINIMA_POR_CATEGORIA.keys()) == {"novo", "usado", "moto"}
    for categoria, valor in ENTRADA_MINIMA_POR_CATEGORIA.items():
        assert 0 < valor < 1.0, f"entrada mínima implausível pra {categoria}: {valor}"


# ---------------------------------------------------------------------------
# obter_regra / nome_exibicao / normalizar_chave (tolerância a acentuação)
# ---------------------------------------------------------------------------

def test_obter_regra_tolera_variacao_de_acentuacao():
    assert obter_regra("Itau") == obter_regra("Itaú") == BANCOS_VEICULOS["Itau"]


def test_obter_regra_banco_desconhecido_usa_fallback():
    regra = obter_regra("Banco Que Nao Existe")
    assert regra["nome_exibicao"] == "Banco Que Nao Existe"
    assert regra["taxa_am"] == REGRA_FALLBACK["taxa_am"]


def test_nome_exibicao_usa_acentuacao_correta():
    assert nome_exibicao("Itau") == "Itaú"
    assert nome_exibicao("Banco Inter") == "Banco Inter"


def test_normalizar_chave_remove_acentos():
    assert normalizar_chave("Itaú") == "Itau"
