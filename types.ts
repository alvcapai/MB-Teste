// TypeScript interfaces for Ordem de Serviço module

export interface ItemServico {
  descricao: string;
  valor: number;
  realizado: boolean;
}

export interface ItemProduto {
  descricao: string;
  valor_unitario: number;
  quantidade: number;
  total: number;
  aplicado: boolean;
}

export interface Cliente {
  nome: string;
  endereco: string;
  telefone?: string;
}

export interface Veiculo {
  marca: string;
  modelo: string;
  cor: string;
  ano: number | string;
  placa: string;
  chassi?: string;
  km?: number | string;
}

export interface OrdemDeServico {
  numero: number;
  data_emissao: string; // dd/mm/aaaa
  status: 'ABERTA' | 'FINALIZADA' | 'CANCELADA';
  cliente: Cliente;
  veiculo: Veiculo;
  servicos: ItemServico[];
  produtos: ItemProduto[];
}

export interface ConfigEmpresa {
  nomeEmpresa: string;
  logoPath?: string;
  endereco?: string;
  telefone1?: string;
  telefone2?: string;
  email?: string;
}
