"""O histórico mensal de veículos troca o mês gravado com janela antiga quando sai a última janela do mês."""
import historico_taxas_veiculos as h


def _grava(caminho, mes, inicio, fim, taxa):
    h.salvar_historico([{"mes_referencia": mes, "inicio_periodo": inicio, "fim_periodo": fim,
                         "banco": "Caixa", "taxa_am": taxa, "taxa_aa": 12.0}], caminho)


def _simula(monkeypatch, periodos, taxas):
    monkeypatch.setattr(h, "listar_periodos_mensais", lambda hoje=None: periodos)
    monkeypatch.setattr(h, "buscar_taxas_periodo", lambda inicio: {"Caixa": (taxas[inicio], 12.5)})


def test_substitui_mes_gravado_com_janela_antiga(tmp_path, monkeypatch):
    caminho = str(tmp_path / "hist.csv")
    _grava(caminho, "2026-10", "2026-10-09", "2026-10-16", 1.01)
    _simula(monkeypatch, [{"mes": "2026-10", "inicio": "2026-10-26", "fim": "2026-10-30"}], {"2026-10-26": 1.02})
    novos, total = h.atualizar_historico(caminho)
    linhas = h.ler_historico(caminho)
    assert (novos, total) == (1, 1)
    assert len(linhas) == 1 and linhas[0]["fim_periodo"] == "2026-10-30" and linhas[0]["taxa_am"] == 1.02


def test_nao_mexe_em_mes_que_ja_tem_a_ultima_janela(tmp_path, monkeypatch):
    caminho = str(tmp_path / "hist.csv")
    _grava(caminho, "2026-10", "2026-10-26", "2026-10-30", 1.02)
    _simula(monkeypatch, [{"mes": "2026-10", "inicio": "2026-10-26", "fim": "2026-10-30"}], {})
    novos, _ = h.atualizar_historico(caminho)
    assert novos == 0 and h.ler_historico(caminho)[0]["taxa_am"] == 1.02


def test_falha_na_busca_preserva_o_mes_antigo(tmp_path, monkeypatch):
    caminho = str(tmp_path / "hist.csv")
    _grava(caminho, "2026-10", "2026-10-09", "2026-10-16", 1.01)
    monkeypatch.setattr(h, "listar_periodos_mensais", lambda hoje=None: [{"mes": "2026-10", "inicio": "2026-10-26", "fim": "2026-10-30"}])
    monkeypatch.setattr(h, "buscar_taxas_periodo", lambda inicio: {})
    novos, _ = h.atualizar_historico(caminho)
    assert novos == 0 and h.ler_historico(caminho)[0]["fim_periodo"] == "2026-10-16"
