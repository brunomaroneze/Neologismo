import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  buscarNeologismo,
  curtirNeologismo,
  getIsAdmin,
  getToken,
  getUsername,
  limparSessao,
  listarNeologismos,
  login,
  logout,
} from "./api";

/**
 * Testes da camada de API.
 *
 * É o único lugar do frontend que traduz resposta de servidor em mensagem de
 * tela e em estado de sessão, então é onde um erro silencioso custa mais: um
 * 401 tratado como 500 manda a pessoa "tentar de novo" em vez de pedir
 * login, e um token que não é apagado no logout deixa a sessão viva.
 */

/** Resposta falsa, no formato que `fetch` devolve. */
function resposta(corpo: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  } as Response;
}

/** Resposta sem JSON válido — o 502 de um proxy, por exemplo. */
function respostaSemJson(status: number) {
  return {
    ok: false,
    status,
    json: async () => {
      throw new Error("not json");
    },
  } as unknown as Response;
}

const fetchFalso = vi.fn();

beforeEach(() => {
  fetchFalso.mockReset();
  vi.stubGlobal("fetch", fetchFalso);
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("tradução de erro HTTP", () => {
  it("401 vira pedido de login, não erro genérico", async () => {
    fetchFalso.mockResolvedValue(resposta({}, 401));

    const erro = await curtirNeologismo(1).catch((e) => e);

    expect(erro).toBeInstanceOf(ApiError);
    expect(erro.status).toBe(401);
    expect(erro.precisaLogin).toBe(true);
    expect(erro.semPermissao).toBe(false);
    expect(erro.message).toMatch(/entre na sua conta/i);
  });

  it("403 é falta de permissão, e não falta de login", async () => {
    fetchFalso.mockResolvedValue(resposta({}, 403));

    const erro = await curtirNeologismo(1).catch((e) => e);

    expect(erro.semPermissao).toBe(true);
    expect(erro.precisaLogin).toBe(false);
  });

  it("429 avisa para esperar", async () => {
    fetchFalso.mockResolvedValue(resposta({}, 429));

    const erro = await curtirNeologismo(1).catch((e) => e);

    expect(erro.excedeuLimite).toBe(true);
    expect(erro.message).toMatch(/aguarde/i);
  });

  it("detail do DRF tem prioridade sobre a mensagem padrão", async () => {
    fetchFalso.mockResolvedValue(
      resposta({ detail: "Usuário ou senha inválidos." }, 401)
    );

    const erro = await login({ username: "a", password: "b" }).catch((e) => e);

    expect(erro.message).toBe("Usuário ou senha inválidos.");
  });

  it("erros por campo ficam acessíveis para marcar o input", async () => {
    fetchFalso.mockResolvedValue(
      resposta(
        {
          titulo: ["O título precisa ter ao menos 2 caracteres."],
          definicao: ["Descreva o significado com ao menos 10 caracteres."],
        },
        400
      )
    );

    const erro = await curtirNeologismo(1).catch((e) => e);

    expect(erro.campos.titulo).toEqual([
      "O título precisa ter ao menos 2 caracteres.",
    ]);
    expect(erro.campos.definicao).toHaveLength(1);
    // O resumo exibido é a primeira mensagem, não um texto genérico.
    expect(erro.message).toMatch(/ao menos 2 caracteres/);
  });

  it("resposta sem JSON cai na mensagem padrão do status", async () => {
    fetchFalso.mockResolvedValue(respostaSemJson(502));

    const erro = await curtirNeologismo(1).catch((e) => e);

    expect(erro.status).toBe(502);
    expect(erro.message).toMatch(/servidor falhou/i);
  });

  it("queda de rede é distinguível de erro do servidor", async () => {
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));

    const erro = await curtirNeologismo(1).catch((e) => e);

    // status 0: não houve resposta HTTP nenhuma.
    expect(erro.status).toBe(0);
    expect(erro.message).toMatch(/conexão/i);
  });
});

describe("montagem da query string", () => {
  it("omite filtros vazios em vez de mandar search=", async () => {
    fetchFalso.mockResolvedValue(resposta({ results: [] }));

    await listarNeologismos({
      search: "",
      tag: undefined,
      classe: "Substantivo",
      ordering: "populares",
      page: 2,
    });

    const url = fetchFalso.mock.calls[0][0] as string;
    expect(url).not.toContain("search=");
    expect(url).not.toContain("tag=");
    expect(url).toContain("classe=Substantivo");
    expect(url).toContain("ordering=populares");
    expect(url).toContain("page=2");
  });

  it("escapa o termo de busca", async () => {
    fetchFalso.mockResolvedValue(resposta({ results: [] }));

    await listarNeologismos({ search: "voçê & cia" });

    const url = fetchFalso.mock.calls[0][0] as string;
    expect(url).toContain("search=vo%C3%A7%C3%AA+%26+cia");
  });

  it("sem filtro nenhum não deixa um '?' sobrando", async () => {
    fetchFalso.mockResolvedValue(resposta({ results: [] }));

    await listarNeologismos();

    expect(fetchFalso.mock.calls[0][0]).toMatch(/\/neologismos\/$/);
  });
});

describe("sessão", () => {
  it("login guarda token, nome e flag de admin", async () => {
    fetchFalso.mockResolvedValue(
      resposta({
        token: "abc123",
        user_id: 7,
        username: "joao",
        email: "j@exemplo.com",
        is_admin: true,
      })
    );

    await login({ username: "joao", password: "SenhaForte123" });

    expect(getToken()).toBe("abc123");
    expect(getUsername()).toBe("joao");
    expect(getIsAdmin()).toBe(true);
  });

  it("is_admin falso não deixa resquício que libere o painel", async () => {
    fetchFalso.mockResolvedValue(
      resposta({
        token: "abc123",
        user_id: 7,
        username: "joao",
        email: "",
        is_admin: false,
      })
    );

    await login({ username: "joao", password: "SenhaForte123" });

    expect(getIsAdmin()).toBe(false);
  });

  it("requisição autenticada manda o header Token", async () => {
    localStorage.setItem("auth_token", "abc123");
    fetchFalso.mockResolvedValue(resposta({ id: 1 }));

    await buscarNeologismo(1);

    const init = fetchFalso.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBe(
      "Token abc123"
    );
  });

  it("requisição anônima não manda Authorization", async () => {
    fetchFalso.mockResolvedValue(resposta({ id: 1 }));

    await buscarNeologismo(1);

    const init = fetchFalso.mock.calls[0][1] as RequestInit;
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("logout revoga o token no servidor e limpa o storage", async () => {
    localStorage.setItem("auth_token", "abc123");
    localStorage.setItem("auth_username", "joao");
    fetchFalso.mockResolvedValue(resposta(null, 204));

    await logout();

    const [url, init] = fetchFalso.mock.calls[0];
    expect(url).toMatch(/\/logout\/$/);
    expect((init as RequestInit).method).toBe("POST");
    expect(getToken()).toBeNull();
    expect(getUsername()).toBeNull();
  });

  it("logout limpa a sessão local mesmo se o servidor falhar", async () => {
    // Offline ou token já expirado: o objetivo local é sair de qualquer jeito.
    localStorage.setItem("auth_token", "abc123");
    fetchFalso.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(logout()).resolves.toBeUndefined();
    expect(getToken()).toBeNull();
  });

  it("logout sem token não chama a API", async () => {
    await logout();

    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("limparSessao avisa a interface para se atualizar", () => {
    localStorage.setItem("auth_token", "abc123");
    const ouvinte = vi.fn();
    window.addEventListener("auth-change", ouvinte);

    limparSessao();

    expect(ouvinte).toHaveBeenCalled();
    window.removeEventListener("auth-change", ouvinte);
  });
});

describe("respostas sem corpo", () => {
  it("204 não tenta parsear JSON", async () => {
    localStorage.setItem("auth_token", "abc123");
    fetchFalso.mockResolvedValue({
      ok: true,
      status: 204,
      json: async () => {
        throw new Error("não deveria ser chamado");
      },
    } as unknown as Response);

    await expect(logout()).resolves.toBeUndefined();
  });
});
