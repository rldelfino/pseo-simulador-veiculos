import json
import os
import subprocess
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.mark.skipif(not os.path.isdir(os.path.join(RAIZ, "paginas_seo", "dados")), reason="paginas_seo/ não gerada")
def test_pacote_de_publicacao_gerado_dos_dados_abertos():
    subprocess.run([sys.executable, "publicacao.py"], cwd=RAIZ, check=True, capture_output=True)
    pasta = os.path.join(RAIZ, "publicacao")
    meta = json.load(open(os.path.join(pasta, "kaggle", "dataset-metadata.json"), encoding="utf-8"))
    assert meta["licenses"] == [{"name": "CC-BY-4.0"}] and meta["resources"][0]["path"].endswith(".csv")
    card = open(os.path.join(pasta, "huggingface", "README.md"), encoding="utf-8").read()
    assert card.startswith("---\nlicense: cc-by-4.0") and "Banco Central" in card
    gov = open(os.path.join(pasta, "dados-gov-br", "cadastro.md"), encoding="utf-8").read()
    assert "/dados/taxas-financiamento-veiculos.csv" in gov
    notas = [n for n in os.listdir(pasta) if n.startswith("nota-imprensa-")]
    assert len(notas) == 1
    assert "contato@datalabglobal.com" in open(os.path.join(pasta, notas[0]), encoding="utf-8").read()
