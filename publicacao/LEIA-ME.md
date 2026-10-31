# Publicação dos dados abertos

Esta pasta é gerada por `publicacao.py` (toda semana, pelo robô). O que cada site pede:

1. **Kaggle:** troque `SEU_USUARIO_KAGGLE` em `kaggle/dataset-metadata.json` pelo seu usuário e rode `kaggle datasets create -p publicacao/kaggle` (nas semanas seguintes, `kaggle datasets version -p publicacao/kaggle -m "atualização semanal"`).
2. **Hugging Face:** crie um dataset em huggingface.co/new-dataset e envie os dois arquivos de `huggingface/`.
3. **dados.gov.br:** copie os campos de `dados-gov-br/cadastro.md` (os recursos entram por link).
4. **Imprensa:** a `nota-imprensa-AAAA-MM.md` do mês está pronta.
