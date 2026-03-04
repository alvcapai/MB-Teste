from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'quotes.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    parts = db.Column(db.Text, nullable=True)
    labor_cost = db.Column(db.Float, nullable=False, default=0.0)

    def __repr__(self):
        return f"<Quote {self.plate} {self.model}>"

@app.route('/')
def index():
    quotes = Quote.query.all()
    return render_template('index.html', quotes=quotes)

@app.route('/new', methods=['GET', 'POST'])
def new_quote():
    if request.method == 'POST':
        plate = request.form.get('plate')
        model = request.form.get('model')
        parts = request.form.get('parts')
        labor_cost = request.form.get('labor_cost', 0)
        try:
            labor_cost = float(labor_cost)
        except ValueError:
            labor_cost = 0.0

        quote = Quote(plate=plate, model=model, parts=parts, labor_cost=labor_cost)
        db.session.add(quote)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('new_quote.html')

@app.route('/quote/<int:quote_id>')
def view_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    return render_template('view_quote.html', quote=quote)

@app.route('/history/<plate>')
def history(plate):
    # return a short list of previous quotes for this plate
    results = Quote.query.filter_by(plate=plate).order_by(Quote.id.desc()).all()
    data = []
    for q in results:
        data.append({
            'id': q.id,
            'model': q.model,
            'labor_cost': q.labor_cost
        })
    return jsonify(data)

# demo data helper
from os_generator import (
    Cliente, Veiculo, ItemServico, ItemProduto, OrdemDeServico, ConfigEmpresa, gerar_os, env
)
# Note: PDF generation uses ReportLab (pure Python) for compatibility with minimal environments

@app.route('/os/preview')
def os_preview():
    # example data
    cliente = Cliente(nome="João da Silva", endereco="Rua A, 123, Cidade", telefone="(11) 99999-0000")
    veiculo = Veiculo(marca="Fiat", modelo="Uno", cor="Prata", ano=2015, placa="ABC-1234", chassi="9BWZZZ377VT004251", km=75000)
    servicos = [ItemServico(descricao="Troca de óleo", valor=120.0, realizado=True),
                ItemServico(descricao="Alinhamento", valor=85.0, realizado=False)]
    produtos = [ItemProduto(descricao="Filtro de óleo", valor_unitario=25.0, quantidade=1, total=25.0, aplicado=True),
                ItemProduto(descricao="Pastilha de freio", valor_unitario=40.0, quantidade=2, total=80.0, aplicado=False)]
    os_obj = OrdemDeServico(numero=1001, data_emissao=date.today(), status="ABERTA",
                             cliente=cliente, veiculo=veiculo,
                             servicos=servicos, produtos=produtos)
    config = ConfigEmpresa(nome_empresa="Oficina MB", endereco="Av. Exemplo, 456", telefone1="(11) 1234-5678", telefone2="(11) 8765-4321", email="contato@oficinamb.com", logo_path=None)
    # render template directly for preview
    template = env.get_template('os_template.html')
    data_emissao = os_obj.data_emissao.strftime('%d/%m/%Y') if isinstance(os_obj.data_emissao, date) else os_obj.data_emissao
    return template.render(os=os_obj, config=config, data_emissao=data_emissao, preview=True)

@app.route('/os/pdf')
def os_pdf():
    # generate PDF same as preview data
    cliente = Cliente(nome="João da Silva", endereco="Rua A, 123, Cidade", telefone="(11) 99999-0000")
    veiculo = Veiculo(marca="Fiat", modelo="Uno", cor="Prata", ano=2015, placa="ABC-1234", chassi="9BWZZZ377VT004251", km=75000)
    servicos = [ItemServico(descricao="Troca de óleo", valor=120.0, realizado=True),
                ItemServico(descricao="Alinhamento", valor=85.0, realizado=False)]
    produtos = [ItemProduto(descricao="Filtro de óleo", valor_unitario=25.0, quantidade=1, total=25.0, aplicado=True),
                ItemProduto(descricao="Pastilha de freio", valor_unitario=40.0, quantidade=2, total=80.0, aplicado=False)]
    os_obj = OrdemDeServico(numero=1001, data_emissao=date.today(), status="ABERTA",
                             cliente=cliente, veiculo=veiculo,
                             servicos=servicos, produtos=produtos)
    config = ConfigEmpresa(nome_empresa="Oficina MB", endereco="Av. Exemplo, 456", telefone1="(11) 1234-5678", telefone2="(11) 8765-4321", email="contato@oficinamb.com", logo_path=None)
    pdf_bytes = gerar_os(os_obj, config)
    return (pdf_bytes, 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="os.pdf"'
    })


if __name__ == '__main__':
    # create database if not exists
    if not os.path.exists(db_path):
        with app.app_context():
            db.create_all()
    app.run(debug=True)
