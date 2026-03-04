from dataclasses import dataclass, field, asdict
from datetime import date
from typing import List, Optional, Union
from jinja2 import Environment, FileSystemLoader, select_autoescape
# PDF generation via ReportLab avoids native dependencies
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os

# data classes for order of service
@dataclass
class ItemServico:
    descricao: str
    valor: float
    realizado: bool = False

@dataclass
class ItemProduto:
    descricao: str
    valor_unitario: float
    quantidade: int
    total: float
    aplicado: bool = False

@dataclass
class Cliente:
    nome: str
    endereco: str
    telefone: Optional[str] = None

@dataclass
class Veiculo:
    marca: str
    modelo: str
    cor: str
    ano: Union[int, str]
    placa: str
    chassi: Optional[str] = None
    km: Optional[Union[int, str]] = None

@dataclass
class OrdemDeServico:
    numero: int
    data_emissao: Union[date, str]
    status: str  # 'ABERTA' | 'FINALIZADA' | 'CANCELADA'
    cliente: Cliente
    veiculo: Veiculo
    servicos: List[ItemServico] = field(default_factory=list)
    produtos: List[ItemProduto] = field(default_factory=list)

    def total_servicos(self) -> float:
        return sum(s.valor for s in self.servicos)

    def total_produtos(self) -> float:
        return sum(p.total for p in self.produtos)

    def total_geral(self) -> float:
        return self.total_servicos() + self.total_produtos()

@dataclass
class ConfigEmpresa:
    nome_empresa: str
    logo_path: Optional[str] = None
    endereco: Optional[str] = None
    telefone1: Optional[str] = None
    telefone2: Optional[str] = None
    email: Optional[str] = None

# setup jinja2 environment
_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates'))
env = Environment(loader=_loader, autoescape=select_autoescape(['html']))


def gerar_os(os_obj: OrdemDeServico, config: ConfigEmpresa) -> bytes:
    """Generate a PDF of the service order and return it as bytes.

    :param os_obj: OrdemDeServico instance containing all necessary fields
    :param config: ConfigEmpresa with company header data
    :returns: PDF file bytes
    """
    template = env.get_template('os_template.html')
    # convert date if needed
    data_emissao = os_obj.data_emissao
    if isinstance(data_emissao, date):
        data_emissao = data_emissao.strftime('%d/%m/%Y')
    html_str = template.render(os=os_obj, config=config, data_emissao=data_emissao)
    # generate a very basic PDF using ReportLab as fallback
    # for now, we just create a one-page PDF with the HTML as plain text
    from io import BytesIO
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    textobject = c.beginText(40, A4[1] - 40)
    for line in html_str.splitlines():
        textobject.textLine(line)
    c.drawText(textobject)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()

# TypeScript interfaces (as a docstring or separate if needed)
TYPESCRIPT_DEFS = """
interface ItemServico {
  descricao: string;
  valor: number;
  realizado: boolean;
}

interface ItemProduto {
  descricao: string;
  valor_unitario: number;
  quantidade: number;
  total: number;
  aplicado: boolean;
}

interface Cliente {
  nome: string;
  endereco: string;
  telefone?: string;
}

interface Veiculo {
  marca: string;
  modelo: string;
  cor: string;
  ano: number | string;
  placa: string;
  chassi?: string;
  km?: number | string;
}

interface OrdemDeServico {
  numero: number;
  data_emissao: string; // dd/mm/aaaa
  status: 'ABERTA' | 'FINALIZADA' | 'CANCELADA';
  cliente: Cliente;
  veiculo: Veiculo;
  servicos: ItemServico[];
  produtos: ItemProduto[];
}

interface ConfigEmpresa {
  nomeEmpresa: string;
  logoPath?: string;
  endereco?: string;
  telefone1?: string;
  telefone2?: string;
  email?: string;
}
"""
