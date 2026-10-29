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
