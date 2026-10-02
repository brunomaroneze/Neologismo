import type {
  ConsultaNeologismos,
  CurtidaResponse,
  Facetas,
  LoginPayload,
  Neologismo,
  NeologismoCreate,
  Paginado,
  RegistroPayload,
  ResumoModeracao,
  Sessao,
} from "@/types";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"
).replace(/\/$/, "");

const CHAVE_TOKEN = "auth_token";
const CHAVE_USERNAME = "auth_username";
const CHAVE_IS_ADMIN = "auth_is_admin";

/**
 * Erro de API com o status HTTP preservado.
 *
 * A camada de UI precisa distinguir "precisa entrar" (401) de "não pode" (403)
 * e de "caiu" (500) para escolher a mensagem certa — com `Error` puro toda
 * falha virava o mesmo texto genérico.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly campos: Record<string, string[]>;

  constructor(
    message: string,
    status: number,
    campos: Record<string, string[]> = {}
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.campos = campos;
  }

  get precisaLogin() {
    return this.status === 401;
  }

  get semPermissao() {
    return this.status === 403;
  }

  get excedeuLimite() {
    return this.status === 429;
  }
}

function mensagemPadrao(status: number, fallback: string) {
  if (status === 401) return "Entre na sua conta para continuar.";
  if (status === 403) return "Você não tem permissão para isso.";
  if (status === 404) return "Não encontramos o que você procura.";
  if (status === 429) return "Muitas tentativas seguidas. Aguarde um instante.";
  if (status >= 500) return "O servidor falhou. Tente de novo em instantes.";
  return fallback;
}

async function lancarErro(res: Response, fallback: string): Promise<never> {
  let mensagem = mensagemPadrao(res.status, fallback);
  const campos: Record<string, string[]> = {};

  try {
    const corpo = await res.json();

    if (typeof corpo?.detail === "string") {
      mensagem = corpo.detail;
    } else if (corpo && typeof corpo === "object") {
      // DRF devolve {campo: ["msg"], ...}. Guardamos por campo para o
      // formulário marcar o input certo, e usamos a primeira como resumo.
      for (const [campo, valor] of Object.entries(corpo)) {
        campos[campo] = Array.isArray(valor) ? valor.map(String) : [String(valor)];
      }
      const primeira = Object.values(campos)[0]?.[0];
      if (primeira) mensagem = primeira;
    }
  } catch {
    // Resposta sem JSON (502 de proxy, por exemplo): fica a mensagem padrão.
  }

  throw new ApiError(mensagem, res.status, campos);
}

function cabecalhos(comCorpo = false): Record<string, string> {
  const headers: Record<string, string> = {};
  if (comCorpo) headers["Content-Type"] = "application/json";

  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;

  return headers;
}

async function requisitar<T>(
  caminho: string,
  init: RequestInit & { fallback?: string } = {}
): Promise<T> {
  const { fallback = "Não foi possível completar a operação.", ...opcoes } = init;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${caminho}`, {
      ...opcoes,
      cache: "no-store",
    });
  } catch {
    // Falha de rede: o fetch rejeita antes de existir um status.
    throw new ApiError(
      "Não conseguimos falar com o servidor. Verifique sua conexão.",
      0
    );
  }

  if (!res.ok) await lancarErro(res, fallback);
  if (res.status === 204) return undefined as T;

  return res.json();
}

function querystring(consulta: ConsultaNeologismos = {}): string {
  const params = new URLSearchParams();
  for (const [chave, valor] of Object.entries(consulta)) {
    if (valor === undefined || valor === null || valor === "") continue;
    params.set(chave, String(valor));
  }
  const texto = params.toString();
  return texto ? `?${texto}` : "";
}

// --- Neologismos ------------------------------------------------------------

export function listarNeologismos(
  consulta: ConsultaNeologismos = {}
): Promise<Paginado<Neologismo>> {
  return requisitar(`/neologismos/${querystring(consulta)}`, {
    headers: cabecalhos(),
    fallback: "Falha ao carregar os neologismos.",
  });
}

export function listarMeusNeologismos(
  consulta: ConsultaNeologismos = {}
): Promise<Paginado<Neologismo>> {
  return requisitar(`/neologismos/meus/${querystring(consulta)}`, {
    headers: cabecalhos(),
    fallback: "Falha ao carregar seus envios.",
  });
}

export function buscarNeologismo(id: number | string): Promise<Neologismo> {
  return requisitar(`/neologismos/${id}/`, {
    headers: cabecalhos(),
    fallback: "Falha ao carregar o verbete.",
  });
}

export function buscarFacetas(): Promise<Facetas> {
  return requisitar("/neologismos/facetas/", {
    headers: cabecalhos(),
    fallback: "Falha ao carregar os filtros.",
  });
}

export function criarNeologismo(dados: NeologismoCreate): Promise<Neologismo> {
  return requisitar("/neologismos/", {
    method: "POST",
    headers: cabecalhos(true),
    body: JSON.stringify(dados),
    fallback: "Falha ao enviar o neologismo.",
  });
}

export function curtirNeologismo(id: number): Promise<CurtidaResponse> {
  return requisitar(`/neologismos/${id}/curtir/`, {
    method: "POST",
    headers: cabecalhos(),
    fallback: "Falha ao registrar a curtida.",
  });
}

// --- Moderação --------------------------------------------------------------

export function buscarResumoModeracao(): Promise<ResumoModeracao> {
  return requisitar("/neologismos/resumo/", {
    headers: cabecalhos(),
    fallback: "Falha ao carregar o resumo.",
  });
}

export function aprovarNeologismo(id: number): Promise<Neologismo> {
  return requisitar(`/neologismos/${id}/aprovar/`, {
    method: "POST",
    headers: cabecalhos(),
    fallback: "Falha ao aprovar.",
  });
}

export function rejeitarNeologismo(
  id: number,
  motivo: string
): Promise<Neologismo> {
  return requisitar(`/neologismos/${id}/rejeitar/`, {
    method: "POST",
    headers: cabecalhos(true),
    body: JSON.stringify({ motivo_rejeicao: motivo }),
    fallback: "Falha ao rejeitar.",
  });
}

export function reativarNeologismo(id: number): Promise<Neologismo> {
  return requisitar(`/neologismos/${id}/reativar/`, {
    method: "POST",
    headers: cabecalhos(),
    fallback: "Falha ao reativar.",
  });
}

// --- Sessão -----------------------------------------------------------------

export async function login(payload: LoginPayload): Promise<Sessao> {
  const sessao = await requisitar<Sessao>("/login/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    fallback: "Usuário ou senha inválidos.",
  });
  salvarSessao(sessao);
  return sessao;
}

export async function cadastrar(payload: RegistroPayload): Promise<Sessao> {
  const sessao = await requisitar<Sessao>("/cadastro/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    fallback: "Falha ao criar a conta.",
  });
  salvarSessao(sessao);
  return sessao;
}

export async function logout(): Promise<void> {
  // Revoga o token no servidor antes de limpar o storage. Se a chamada
  // falhar (offline, token já expirado), a sessão local é limpa mesmo assim.
  try {
    if (getToken()) {
      await requisitar("/logout/", { method: "POST", headers: cabecalhos() });
    }
  } catch {
    // Ignora: o objetivo local é sair.
  } finally {
    limparSessao();
  }
}

function salvarSessao(sessao: Sessao): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(CHAVE_TOKEN, sessao.token);
  localStorage.setItem(CHAVE_USERNAME, sessao.username);
  localStorage.setItem(CHAVE_IS_ADMIN, String(sessao.is_admin));
  window.dispatchEvent(new Event("auth-change"));
}

export function limparSessao(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(CHAVE_TOKEN);
  localStorage.removeItem(CHAVE_USERNAME);
  localStorage.removeItem(CHAVE_IS_ADMIN);
  window.dispatchEvent(new Event("auth-change"));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(CHAVE_TOKEN);
  } catch {
    // Safari em navegação privada pode lançar ao ler o storage.
    return null;
  }
}

export function getUsername(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(CHAVE_USERNAME);
  } catch {
    return null;
  }
}

export function getIsAdmin(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(CHAVE_IS_ADMIN) === "true";
  } catch {
    return false;
  }
}

// --- Recuperação de senha ---------------------------------------------------

export function pedirRecuperacaoSenha(email: string): Promise<{ detail: string }> {
  return requisitar("/senha/recuperar/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
    fallback: "Falha ao pedir a recuperação de senha.",
  });
}

export async function redefinirSenha(payload: {
  uid: string;
  token: string;
  password: string;
}): Promise<Sessao> {
  // A API devolve uma sessão nova, então a pessoa já entra logada depois de
  // redefinir — evita pedir a senha que ela acabou de digitar.
  const sessao = await requisitar<Sessao>("/senha/redefinir/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    fallback: "Falha ao redefinir a senha.",
  });
  salvarSessao(sessao);
  return sessao;
}
