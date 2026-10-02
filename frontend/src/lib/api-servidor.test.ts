import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { buscarVerbetePublico, listarVerbetesPublicos } from "./api-servidor";
import type { Neologismo } from "@/types";

/**
 * O sitemap depende destas funções, e um sitemap errado é pior que nenhum:
 * ou deixa metade do acervo de fora, ou responde 500 e o rastreador para de
 * voltar. Daí os testes cobrirem a paginação até o fim e a API fora do ar.
 */

function verbete(id: number): Neologismo {
  return {
    id,
    data_registro: null,
    titulo: `Palavra ${id}`,
    slug: `palavra-${id}`,
    classe_gramatical: "Substantivo",
    tipologia: "",
    elaborado_por: "",
    definicao: "Uma definição qualquer.",
    contexto_uso: "",
    contextos: [],
    tags: [],
    status: "aprovado",
    motivo_rejeicao: null,
    reativado_em: null,
    moderado_em: null,
    data_criacao: "2026-01-01T00:00:00Z",
    data_atualizacao: "2026-01-02T00:00:00Z",
    autor: 1,
    autor_nome: "equipe",
    total_likes: 0,
    curtido_por_mim: false,
  };
}

function pagina(ids: number[], proxima: string | null) {
  return {
    ok: true,
    status: 200,
    json: async () => ({
      count: 150,
      page: 1,
      total_pages: 2,
      next: proxima,
      previous: null,
      results: ids.map(verbete),
    }),
  } as Response;
}

const fetchFalso = vi.fn();

beforeEach(() => {
  fetchFalso.mockReset();
  vi.stubGlobal("fetch", fetchFalso);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("listarVerbetesPublicos", () => {
  it("segue a paginação até a última página", async () => {
    fetchFalso
      .mockResolvedValueOnce(pagina([1, 2], "/neologismos/?page=2"))
      .mockResolvedValueOnce(pagina([3], null));

    const verbetes = await listarVerbetesPublicos();

    expect(verbetes.map((v) => v.id)).toEqual([1, 2, 3]);
    expect(fetchFalso).toHaveBeenCalledTimes(2);
  });

  it("para na primeira página quando não há próxima", async () => {
    fetchFalso.mockResolvedValue(pagina([1], null));

    await listarVerbetesPublicos();

    expect(fetchFalso).toHaveBeenCalledTimes(1);
  });

  it("devolve lista vazia quando a API está fora do ar", async () => {
    // Melhor um sitemap só com as páginas fixas do que a rota inteira em 500.
    fetchFalso.mockRejectedValue(new Error("connect ECONNREFUSED"));

    await expect(listarVerbetesPublicos()).resolves.toEqual([]);
  });

  it("não manda token: só enxerga o que é público", async () => {
    fetchFalso.mockResolvedValue(pagina([1], null));

    await listarVerbetesPublicos();

    const init = fetchFalso.mock.calls[0][1] as RequestInit;
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("pede o maior page_size que a API aceita", async () => {
    fetchFalso.mockResolvedValue(pagina([1], null));

    await listarVerbetesPublicos();

    expect(fetchFalso.mock.calls[0][0]).toContain("page_size=100");
  });
});

describe("buscarVerbetePublico", () => {
  it("devolve o verbete quando existe", async () => {
    fetchFalso.mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => verbete(42),
    } as Response);

    const achado = await buscarVerbetePublico(42);

    expect(achado?.titulo).toBe("Palavra 42");
  });

  it("devolve null em 404 em vez de lançar", async () => {
    // Quem chama é o generateMetadata: lançar aqui quebraria a página toda.
    fetchFalso.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Não encontrado." }),
    } as Response);

    await expect(buscarVerbetePublico(999)).resolves.toBeNull();
  });

  it("escapa o id recebido da URL", async () => {
    fetchFalso.mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({}),
    } as Response);

    await buscarVerbetePublico("../facetas");

    expect(fetchFalso.mock.calls[0][0]).toContain("..%2Ffacetas");
  });
});
