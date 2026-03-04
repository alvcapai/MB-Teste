from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
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
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)


class Quote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), nullable=False)
    model = db.Column(db.String(80), nullable=False)
    parts = db.Column(db.Text, nullable=True)  # kept for legacy data
    labor_cost = db.Column(db.Float, nullable=False, default=0.0)
    images = db.Column(db.Text, nullable=True)
    finalized = db.Column(db.Boolean, nullable=False, default=False)
    items = db.relationship('QuoteItem', backref='quote', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Quote {self.plate} {self.model}>"


class QuoteItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_id = db.Column(db.Integer, db.ForeignKey('quote.id'), nullable=False)
    descricao = db.Column(db.String(200), nullable=False)
    quantidade = db.Column(db.Float, nullable=False, default=1.0)
    valor = db.Column(db.Float, nullable=False, default=0.0)

    @property
    def total(self):
        return self.quantidade * self.valor


with app.app_context():
    db.create_all()
    from sqlalchemy import inspect, text
    inspector = inspect(db.engine)
    cols = [c.get('name') for c in inspector.get_columns(Quote.__tablename__)]
    if 'finalized' not in cols:
        try:
            with db.engine.connect() as conn:
                conn.execute(text('ALTER TABLE quote ADD COLUMN finalized BOOLEAN NOT NULL DEFAULT 0'))
                conn.commit()
        except Exception:
            pass


@app.route('/')
def index():
    quotes = Quote.query.filter_by(finalized=False).all()
    return render_template('index.html', quotes=quotes)


@app.route('/new', methods=['GET', 'POST'])
def new_quote():
    if request.method == 'POST':
        plate = request.form.get('plate')
        model = request.form.get('model')
        labor_cost = request.form.get('labor_cost', 0)
        try:
            labor_cost = float(labor_cost)
        except ValueError:
            labor_cost = 0.0

        saved_files = []
        files = request.files.getlist('photos') if 'photos' in request.files else []
        for f in files:
            if f and f.filename:
                filename = secure_filename(f.filename)
                unique_name = f"{uuid.uuid4().hex}_{filename}"
                dest = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
                try:
                    f.save(dest)
                    saved_files.append(unique_name)
                except Exception:
                    continue

        images_json = json.dumps(saved_files) if saved_files else None
        quote = Quote(plate=plate, model=model, labor_cost=labor_cost, images=images_json)
        db.session.add(quote)
        db.session.flush()  # get quote.id before committing

        descricoes = request.form.getlist('descricao[]')
        quantidades = request.form.getlist('quantidade[]')
        valores = request.form.getlist('valor[]')
        for desc, qtd, val in zip(descricoes, quantidades, valores):
            desc = desc.strip()
            if not desc:
                continue
            try:
                qtd = float(qtd)
            except ValueError:
                qtd = 1.0
            try:
                val = float(val)
            except ValueError:
                val = 0.0
            db.session.add(QuoteItem(quote_id=quote.id, descricao=desc, quantidade=qtd, valor=val))

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


@app.route('/quote/<int:quote_id>/edit', methods=['GET', 'POST'])
def edit_quote(quote_id):
    q = Quote.query.get_or_404(quote_id)
    if request.method == 'POST':
        q.plate = request.form.get('plate', q.plate).strip()
        q.model = request.form.get('model', q.model).strip()
        try:
            q.labor_cost = float(request.form.get('labor_cost', q.labor_cost))
        except ValueError:
            pass
        db.session.commit()
        return redirect(url_for('view_quote', quote_id=q.id))
    return render_template('edit_quote.html', quote=q)


@app.route('/quote/<int:quote_id>/add_item', methods=['POST'])
def add_item(quote_id):
    q = Quote.query.get_or_404(quote_id)
    descricao = request.form.get('descricao', '').strip()
    if descricao:
        try:
            quantidade = float(request.form.get('quantidade', 1))
        except ValueError:
            quantidade = 1.0
        try:
            valor = float(request.form.get('valor', 0))
        except ValueError:
            valor = 0.0
        db.session.add(QuoteItem(quote_id=q.id, descricao=descricao, quantidade=quantidade, valor=valor))
        db.session.commit()
    return redirect(url_for('view_quote', quote_id=quote_id))


@app.route('/quote/<int:quote_id>/delete_item/<int:item_id>', methods=['POST'])
def delete_item(quote_id, item_id):
    item = QuoteItem.query.filter_by(id=item_id, quote_id=quote_id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('view_quote', quote_id=quote_id))


@app.route('/history/<plate>')
def history(plate):
    results = Quote.query.filter_by(plate=plate).order_by(Quote.id.desc()).all()
    data = [{'id': q.id, 'model': q.model, 'labor_cost': q.labor_cost} for q in results]
    return jsonify(data)


from os_generator import (
    Cliente, Veiculo, ItemServico, ItemProduto, OrdemDeServico, ConfigEmpresa, gerar_os, env
)

_CONFIG_EMPRESA = ConfigEmpresa(
    nome_empresa='Oficina MB',
    endereco='Av. Exemplo, 456',
    telefone1='(11) 1234-5678',
    telefone2='(11) 8765-4321',
    email='contato@oficinamb.com',
    logo_path=None,
)


def _quote_to_os(q):
    """Map a Quote + its QuoteItems to OrdemDeServico data classes."""
    servicos = []
    if q.labor_cost and q.labor_cost > 0:
        servicos.append(ItemServico(descricao='Mão de obra', valor=q.labor_cost, realizado=True))

    produtos = []
    for item in q.items:
        produtos.append(ItemProduto(
            descricao=item.descricao,
            valor_unitario=item.valor,
            quantidade=item.quantidade,
            total=item.total,
            aplicado=True,
        ))
    # fallback: legacy free-text parts
    if not produtos and q.parts:
        for line in q.parts.splitlines():
            line = line.strip()
            if line:
                produtos.append(ItemProduto(descricao=line, valor_unitario=0.0, quantidade=1, total=0.0, aplicado=True))

    return OrdemDeServico(
        numero=q.id,
        data_emissao=date.today(),
        status='FINALIZADA' if q.finalized else 'ABERTA',
        cliente=Cliente(nome='—', endereco='—'),
        veiculo=Veiculo(marca='', modelo=q.model, cor='', ano='', placa=q.plate),
        servicos=servicos,
        produtos=produtos,
    )


@app.route('/quote/<int:quote_id>/print')
def quote_print(quote_id):
    q = Quote.query.get_or_404(quote_id)
    os_obj = _quote_to_os(q)
    template = env.get_template('os_template.html')
    html = template.render(os=os_obj, config=_CONFIG_EMPRESA,
                           data_emissao=os_obj.data_emissao.strftime('%d/%m/%Y'),
                           preview=True)
    return html


@app.route('/quote/<int:quote_id>/pdf')
def quote_pdf(quote_id):
    """Generate a PDF of the quote for WhatsApp sharing."""
    q = Quote.query.get_or_404(quote_id)
    os_obj = _quote_to_os(q)

    from io import BytesIO
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"Cotação #{q.id}", styles['Title']))
    story.append(Paragraph(f"Data: {date.today().strftime('%d/%m/%Y')}", styles['Normal']))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"<b>Placa:</b> {q.plate}", styles['Normal']))
    story.append(Paragraph(f"<b>Modelo:</b> {q.model}", styles['Normal']))
    story.append(Spacer(1, 6*mm))

    # items table
    header = [['Descrição', 'Qtd', 'Valor Unit.', 'Total']]
    rows = []
    grand_total = 0.0

    for item in q.items:
        rows.append([item.descricao,
                     f'{item.quantidade:g}',
                     f'R$ {item.valor:.2f}',
                     f'R$ {item.total:.2f}'])
        grand_total += item.total

    if q.labor_cost and q.labor_cost > 0:
        rows.append(['Mão de obra', '1', f'R$ {q.labor_cost:.2f}', f'R$ {q.labor_cost:.2f}'])
        grand_total += q.labor_cost

    if rows:
        data = header + rows + [['', '', 'TOTAL', f'R$ {grand_total:.2f}']]
        col_w = [95*mm, 15*mm, 35*mm, 35*mm]
        t = Table(data, colWidths=col_w)
        t.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, 0),  colors.HexColor('#343a40')),
            ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
            ('FONTNAME',     (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTNAME',     (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN',        (1, 0), (-1, -1), 'RIGHT'),
            ('GRID',         (0, 0), (-1, -2), 0.4, colors.grey),
            ('BOX',          (0, 0), (-1, -1), 0.8, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(t)
    elif q.parts:
        story.append(Paragraph(f"<b>Peças:</b> {q.parts}", styles['Normal']))
        if q.labor_cost:
            story.append(Paragraph(f"<b>Mão de obra:</b> R$ {q.labor_cost:.2f}", styles['Normal']))

    doc.build(story)
    buffer.seek(0)
    return Response(buffer.read(), status=200,
                    headers={'Content-Type': 'application/pdf',
                             'Content-Disposition': f'inline; filename="cotacao_{q.id}.pdf"'})


@app.route('/finalizados')
def finalized_quotes():
    quotes = Quote.query.filter_by(finalized=True).all()
    return render_template('finalized.html', quotes=quotes)


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
    cliente = Cliente(nome="João da Silva", endereco="Rua A, 123, Cidade", telefone="(11) 99999-0000")
    veiculo = Veiculo(marca="Fiat", modelo="Uno", cor="Prata", ano=2015, placa="ABC-1234", chassi="9BWZZZ377VT004251", km=75000)
    servicos = [ItemServico(descricao="Troca de óleo", valor=120.0, realizado=True),
                ItemServico(descricao="Alinhamento", valor=85.0, realizado=False)]
    produtos = [ItemProduto(descricao="Filtro de óleo", valor_unitario=25.0, quantidade=1, total=25.0, aplicado=True),
                ItemProduto(descricao="Pastilha de freio", valor_unitario=40.0, quantidade=2, total=80.0, aplicado=False)]
    os_obj = OrdemDeServico(numero=1001, data_emissao=date.today(), status="ABERTA",
                            cliente=cliente, veiculo=veiculo, servicos=servicos, produtos=produtos)
    template = env.get_template('os_template.html')
    return template.render(os=os_obj, config=_CONFIG_EMPRESA,
                           data_emissao=os_obj.data_emissao.strftime('%d/%m/%Y'), preview=True)


@app.route('/os/pdf')
def os_pdf():
    cliente = Cliente(nome="João da Silva", endereco="Rua A, 123, Cidade", telefone="(11) 99999-0000")
    veiculo = Veiculo(marca="Fiat", modelo="Uno", cor="Prata", ano=2015, placa="ABC-1234", chassi="9BWZZZ377VT004251", km=75000)
    servicos = [ItemServico(descricao="Troca de óleo", valor=120.0, realizado=True),
                ItemServico(descricao="Alinhamento", valor=85.0, realizado=False)]
    produtos = [ItemProduto(descricao="Filtro de óleo", valor_unitario=25.0, quantidade=1, total=25.0, aplicado=True),
                ItemProduto(descricao="Pastilha de freio", valor_unitario=40.0, quantidade=2, total=80.0, aplicado=False)]
    os_obj = OrdemDeServico(numero=1001, data_emissao=date.today(), status="ABERTA",
                            cliente=cliente, veiculo=veiculo, servicos=servicos, produtos=produtos)
    pdf_bytes = gerar_os(os_obj, _CONFIG_EMPRESA)
    return Response(pdf_bytes, status=200,
                    headers={'Content-Type': 'application/pdf',
                             'Content-Disposition': 'attachment; filename="os.pdf"'})


if __name__ == '__main__':
    app.run(debug=True)
