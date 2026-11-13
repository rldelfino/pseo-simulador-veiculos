"""IndexNow: a chave publicada prova a posse do site e o script nunca derruba o pipeline."""
import os
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import indexnow

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_arquivo_da_chave_existe_e_contem_a_chave():
    caminho = os.path.join(RAIZ, "paginas_seo", f"{indexnow.CHAVE}.txt")
    assert os.path.isfile(caminho), "arquivo da chave IndexNow ausente em paginas_seo/"
    assert open(caminho, encoding="utf-8").read().strip() == indexnow.CHAVE
    assert len(indexnow.CHAVE) >= 8 and indexnow.CHAVE.isalnum()


def test_payload_tem_host_chave_e_local_da_chave():
    p = indexnow.montar_payload(["https://veiculos.datalabglobal.com/a", "https://veiculos.datalabglobal.com/b"])
    assert p["host"] == "veiculos.datalabglobal.com"
    assert p["keyLocation"] == f"https://veiculos.datalabglobal.com/{indexnow.CHAVE}.txt"
    assert p["urlList"] == ["https://veiculos.datalabglobal.com/a", "https://veiculos.datalabglobal.com/b"]


def test_urls_do_sitemap_so_inclui_o_proprio_host(tmp_path):
    sm = tmp_path / "sitemap.xml"
    sm.write_text("<urlset><url><loc>https://veiculos.datalabglobal.com/x</loc></url>"
                  "<url><loc>https://outro.com/y</loc></url></urlset>", encoding="utf-8")
    assert indexnow.urls_do_sitemap(str(sm)) == ["https://veiculos.datalabglobal.com/x"]


def test_main_nao_levanta_excecao_em_falha_de_rede(monkeypatch, tmp_path, capsys):
    sm = tmp_path / "sitemap.xml"
    sm.write_text("<urlset><url><loc>https://veiculos.datalabglobal.com/x</loc></url></urlset>", encoding="utf-8")

    def falha(*a, **k):
        raise urllib.error.URLError("sem rede")

    monkeypatch.setattr(indexnow, "enviar", falha)
    assert indexnow.main(str(sm)) == 0
    assert "falha de rede" in capsys.readouterr().out


def test_lotes_respeitam_o_limite(monkeypatch, tmp_path):
    sm = tmp_path / "sitemap.xml"
    locs = "".join(f"<url><loc>https://veiculos.datalabglobal.com/p{i}</loc></url>" for i in range(25))
    sm.write_text(f"<urlset>{locs}</urlset>", encoding="utf-8")
    enviados = []
    monkeypatch.setattr(indexnow, "TAMANHO_LOTE", 10)
    monkeypatch.setattr(indexnow, "enviar", lambda payload, *a, **k: enviados.append(len(payload["urlList"])) or 200)
    indexnow.main(str(sm))
    assert enviados == [10, 10, 5]


def test_urls_recentes_so_traz_o_que_mudou_na_janela(tmp_path):
    from datetime import datetime, timezone
    sm = tmp_path / "sitemap.xml"
    sm.write_text(
        "<urlset>"
        "<url><loc>https://veiculos.datalabglobal.com/novo</loc><lastmod>2026-11-13T20:00:00+00:00</lastmod></url>"
        "<url><loc>https://veiculos.datalabglobal.com/velho</loc><lastmod>2026-11-08T15:10:30+00:00</lastmod></url>"
        "<url><loc>https://veiculos.datalabglobal.com/sem-data</loc></url>"
        "<url><loc>https://outro.com/z</loc><lastmod>2026-11-13T20:00:00+00:00</lastmod></url>"
        "</urlset>", encoding="utf-8")
    agora = datetime(2026, 11, 13, 22, 0, tzinfo=timezone.utc)
    assert indexnow.urls_recentes(str(sm), 6, agora) == [
        "https://veiculos.datalabglobal.com/novo", "https://veiculos.datalabglobal.com/sem-data"]


def test_poucas_urls_vao_uma_a_uma_e_muitas_vao_em_lote(monkeypatch, tmp_path):
    sm = tmp_path / "sitemap.xml"
    locs = "".join(f"<url><loc>https://veiculos.datalabglobal.com/p{i}</loc></url>" for i in range(5))
    sm.write_text(f"<urlset>{locs}</urlset>", encoding="utf-8")
    unicos, lotes = [], []
    monkeypatch.setattr(indexnow, "enviar_url", lambda u, *a, **k: unicos.append(u) or 200)
    monkeypatch.setattr(indexnow, "enviar", lambda p, *a, **k: lotes.append(len(p["urlList"])) or 200)
    monkeypatch.setattr(indexnow.time, "sleep", lambda s: None)
    indexnow.main(str(sm), individual_ate=10)
    assert len(unicos) == 5 and lotes == []
    unicos.clear()
    indexnow.main(str(sm), individual_ate=3)
    assert unicos == [] and lotes == [5]


def test_cli_padrao_envia_so_as_recentes(monkeypatch, tmp_path):
    sm = tmp_path / "sitemap.xml"
    sm.write_text("<urlset><url><loc>https://veiculos.datalabglobal.com/velho</loc><lastmod>2020-01-01T00:00:00+00:00</lastmod></url></urlset>", encoding="utf-8")
    chamadas = []
    monkeypatch.setattr(indexnow, "enviar_url", lambda u, *a, **k: chamadas.append(u) or 200)
    monkeypatch.setattr(indexnow, "enviar", lambda p, *a, **k: chamadas.append("lote") or 200)
    assert indexnow._cli([str(sm)]) == 0
    assert chamadas == []
