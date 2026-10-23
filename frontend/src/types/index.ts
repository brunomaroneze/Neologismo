export type NeologismoStatus = "pendente" | "aprovado" | "rejeitado";

export interface Contexto {
  id: number;
  citacao: string;
  fonte: string;
  link: string;
}

export interface ContextoCreate {
  citacao: string;
  fonte?: string;
  link?: string;
}

export interface Neologismo {
  id: number;
  /** Data informada na planilha de origem (importação CSV), não a de criação. */
  data_registro: string | null;
  titulo: string;
  slug: string;
  classe_gramatical: string;
  /** Processo de formação. Ex.: "derivação prefixal". */
  tipologia: string;
  elaborado_por: string;
  definicao: string;
  contexto_uso: string;
  contextos: Contexto[];
  tags: string[];
  status: NeologismoStatus;
  motivo_rejeicao: string | null;
  reativado_em: string | null;
  moderado_em: string | null;
  data_criacao: string;
  data_atualizacao: string;
  autor: number;
  autor_nome: string;
  total_likes: number;
  /** Se o usuário da requisição curtiu este verbete. Falso para anônimos. */
  curtido_por_mim: boolean;
  /** Presentes apenas quando quem pede é da equipe de moderação. */
  total_deslikes?: number;
  autor_email?: string;
  moderado_por_nome?: string | null;
}

export interface NeologismoCreate {
  titulo: string;
  classe_gramatical: string;
  definicao: string;
  contexto_uso: string;
  contextos?: ContextoCreate[];
  tags: string[];
}

/** Envelope devolvido por toda listagem da API. */
export interface Paginado<T> {
  count: number;
  page: number;
  total_pages: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface CurtidaResponse {
  id: number;
  curtido_por_mim: boolean;
  total_likes: number;
}

export interface Faceta {
  nome: string;
  total: number;
}

export interface Facetas {
  total: number;
  tags: Faceta[];
  classes: Faceta[];
}

export interface ResumoModeracao {
  pendente: number;
  aprovado: number;
  rejeitado: number;
  total: number;
}

export type Ordenacao = "recentes" | "antigos" | "populares" | "alfabetica";

export interface ConsultaNeologismos {
  search?: string;
  tag?: string;
  classe?: string;
  ordering?: Ordenacao;
  status?: NeologismoStatus;
  page?: number;
  page_size?: number;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export interface RegistroPayload {
  username: string;
  email?: string;
  password: string;
}

export interface Sessao {
  token: string;
  user_id: number;
  username: string;
  email: string;
  is_admin: boolean;
}
