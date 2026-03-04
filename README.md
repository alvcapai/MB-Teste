# Workshop Repair Quotes

Simple Flask web application to create repair quotes for a car workshop.

## Adjusted for Azure deployment

This project has been slimmed down to run with minimal dependencies on Azure App Service (Linux).
- Uses SQLite (bundled with Python), no external database required.
- No native libraries necessary – PDF generation uses pure-Python ReportLab.
- Only core packages (`Flask`, `Flask-SQLAlchemy`, `reportlab`) are required, keeping the `requirements.txt` small.

A `.gitignore` file excludes virtual environment, database and cache files so the repository is clean for GitHub.

## Features

- Add a new quote with car plate, model, parts list, and labor cost
- View all quotes and details
- Demo OS preview and PDF generation (using ReportLab)

## Setup (local or Azure)

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Azure, you can configure a Python 3.10 web app and point the deployment to this repo; Azure will install dependencies via `requirements.txt` automatically.

The `install.sh` script is now trivial and no longer installs system packages.

## GitHub preparation

Before pushing to GitHub, ensure you remove any local virtual environment and database files. You can run the provided helper:

```bash
./cleanup.sh
```

or manually:

```bash
rm -rf venv quotes.db __pycache__
find . -name '.DS_Store' -delete
```

The `.gitignore` file will prevent these from being committed.

## Gerador de Ordem de Serviço (OS)

A aplicação inclui um módulo `os_generator.py` que exporta:

* Classes/data‑classes para tipos (`OrdemDeServico`, `ConfigEmpresa`, `ItemServico`, `ItemProduto`, etc.)
* Função `gerar_os(os_obj, config)` que retorna bytes de um PDF pronto para salvar ou enviar.

Também existem rotas de demonstração:

* `/os/preview` – pré‑visualiza em HTML um exemplo de OS (botão imprimir disponível)
* `/os/pdf` – gera o mesmo exemplo como PDF para download

### Exemplo de uso no Python

```python
from os_generator import OrdemDeServico, Cliente, Veiculo, ItemServico, ItemProduto, ConfigEmpresa, gerar_os
from datetime import date

cliente = Cliente(nome="Maria", endereco="Rua Bela, 10", telefone="(11) 98888-7777")
veiculo = Veiculo(marca="VW", modelo="Gol", cor="Preto", ano=2018, placa="XYZ-9876")
os = OrdemDeServico(
    numero=1,
    data_emissao=date.today(),
    status="ABERTA",
    cliente=cliente,
    veiculo=veiculo,
    servicos=[ItemServico("Troca de pneus", 200.0)],
    produtos=[ItemProduto("Pneu", 100.0, 4, 400.0)]
)
config = ConfigEmpresa(nome_empresa="Oficina MB", endereco="Av. Exemplo 123")
pdf_bytes = gerar_os(os, config)
with open('os.pdf', 'wb') as f:
    f.write(pdf_bytes)
```

