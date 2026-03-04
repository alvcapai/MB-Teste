from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import date
import os
import uuid
import json
from werkzeug.utils import secure_filename

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'quotes.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8MB limit per request (approx)

# ensure upload dir exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    parts = db.Column(db.Text, nullable=True)
    labor_cost = db.Column(db.Float, nullable=False, default=0.0)
    # JSON array (as text) with filenames stored under static/uploads
    images = db.Column(db.Text, nullable=True)
    # indicates whether the quote has been finished/finalized
    finalized = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<Quote {self.plate} {self.model} {'(finalizado)' if self.finalized else ''}>"

# Ensure the database tables are created on application startup. This
# runs under an application context so it works when Gunicorn imports
# the app.
with app.app_context():
    db.create_all()
    # if the database already existed before we added the `finalized` column,
    # add it now so the application continues working without a full migration
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    cols = [c.get('name') for c in inspector.get_columns(Quote.__tablename__)]
    if 'finalized' not in cols:
        # SQLite doesn't support ALTER TABLE ADD COLUMN with a non-null default easily,
        # but this will add the column with default 0 and update existing rows automatically.
        try:
            db.engine.execute('ALTER TABLE quote ADD COLUMN finalized BOOLEAN NOT NULL DEFAULT 0')
        except Exception:
            # if anything goes wrong, just ignore – the column may already exist
            pass

if __name__ == '__main__':
    # local development server only
    app.run(debug=True)

@app.route('/')
def index():
    # only show cars/quotes that are still in progress (not finalizados)
    quotes = Quote.query.filter_by(finalized=False).all()
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

        # handle uploaded photos (input name: photos)
        saved_files = []
        files = request.files.getlist('photos') if 'photos' in request.files else []
        for f in files:
            if f and f.filename:
                filename = secure_filename(f.filename)
                # generate unique name to avoid collisions
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                dest = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                try:
                    f.save(dest)
                    saved_files.append(unique_name)
                except Exception:
                    # skip problematic files
                    continue

        images_json = json.dumps(saved_files) if saved_files else None

        quote = Quote(plate=plate, model=model, parts=parts, labor_cost=labor_cost, images=images_json)
        db.session.add(quote)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('new_quote.html')

@app.route('/quote/<int:quote_id>')
def view_quote(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    images = []
    if quote.images:
        try:
            images = json.loads(quote.images)
        except Exception:
            images = []
    return render_template('view_quote.html', quote=quote, images=images)

@app.route('/history/<plate>')
def history(plate):
    # return a short list of previous quotes for this plate (regardless of status)
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


@app.route('/finalizados')
def finalized_quotes():
    """List all quotes that have been marked as finalizado (historical control)."""
    quotes = Quote.query.filter_by(finalized=True).all()
    return render_template('finalized.html', quotes=quotes)


@app.route('/quote/<int:quote_id>/pdf')
def quote_pdf(quote_id):
    q = Quote.query.get_or_404(quote_id)
    from io import BytesIO
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    def safe(s):
        if not s:
            return ''
        return s.encode('latin-1', errors='replace').decode('latin-1')

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    _, height = A4
    y = height - 50

    c.setFont("Helvetica-Bold", 16)
    c.drawString(40, y, safe(f"Cotacao #{q.id}"))
    y -= 30

    c.setFont("Helvetica", 12)
    c.drawString(40, y, safe(f"Placa: {q.plate}")); y -= 20
    c.drawString(40, y, safe(f"Modelo: {q.model}")); y -= 20
    c.drawString(40, y, safe(f"Mao de obra: R$ {q.labor_cost:.2f}")); y -= 30

    if q.parts:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y, "Pecas:"); y -= 18
        c.setFont("Helvetica", 11)
        for line in q.parts.splitlines():
            if y < 60:
                c.showPage()
                y = height - 40
                c.setFont("Helvetica", 11)
            c.drawString(60, y, safe(line)); y -= 16

    c.showPage()
    c.save()
    buffer.seek(0)
    return (buffer.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': f'inline; filename="cotacao_{q.id}.pdf"'
    })


@app.route('/quote/<int:quote_id>/finalize', methods=['POST'])
def finalize_quote(quote_id):
    q = Quote.query.get_or_404(quote_id)
    q.finalized = True
    db.session.commit()
    return redirect(url_for('finalized_quotes'))


@app.route('/quote/<int:quote_id>/unfinalize', methods=['POST'])
def unfinalize_quote(quote_id):
    q = Quote.query.get_or_404(quote_id)
    q.finalized = False
    db.session.commit()
    return redirect(url_for('index'))


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
    # local development server only
    app.run(debug=True)
