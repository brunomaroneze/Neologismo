/**
 * Leituras públicas da API feitas no servidor (sitemap, robots, metadata).
 *
 * Separado de `lib/api.ts` por dois motivos:
 *
 * 1. **Endereço.** `NEXT_PUBLIC_API_URL` é o endereço que o *navegador* usa,
 *    e ele é embutido no bundle no momento do build. Dentro do container o
 *    Next alcança o Django direto pela rede do Compose, sem sair para a
 *    internet e voltar pelo Caddy — `API_URL_INTERNA` existe para isso e é
 *    lida em runtime, por não ter o prefixo `NEXT_PUBLIC_`.
 *
 * 2. **Cache.** As chamadas do cliente usam `no-store` (a curtida tem que
 *    aparecer na hora). Aqui o oposto: sitemap e preview de link podem ser
 *    servidos de um cache de minutos, senão cada rastreador do Google vira
 *    uma varredura no banco.
 *
 * Nenhuma função daqui manda token: só enxergam o que é público.
 */

import type { Neologismo, Paginado } from "@/types";

/** Base usada só no servidor. Cai para a pública quando não há rede interna. */
const BASE = (
  process.env.API_URL_INTERNA ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000/api"
).replace(/\/$/, "");

export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"
).replace(/\/$/, "");

/** Quanto tempo o Next guarda a resposta antes de perguntar de novo. */
const REVALIDAR_SEGUNDOS = 3600;

/** O maior `page_size` que a API aceita (ver PaginacaoPadrao.max_page_size). */
const POR_PAGINA = 100;

/**
 * Teto de páginas percorridas pelo sitemap.
 *
 * Um sitemap tem limite de 50 mil URLs, mas o motivo real do teto é não
 * deixar um laço de paginação rodar indefinidamente se a API passar a
 * devolver `next` sempre preenchido.
 */
const MAX_PAGINAS = 100;

async function buscar<T>(caminho: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE}${caminho}`, {
      headers: { Accept: "application/json" },
      next: { revalidate: REVALIDAR_SEGUNDOS },
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    // O sitemap e o preview de link não valem derrubar a página: sem a API,
    // devolvemos o que der e o chamador decide o fallback.
    return null;
  }
}

/** Um verbete aprovado, ou `null` se não existe / não é público. */
export function buscarVerbetePublico(
  id: string | number
): Promise<Neologismo | null> {
  return buscar<Neologismo>(`/neologismos/${encodeURIComponent(String(id))}/`);
}

/** Todos os verbetes aprovados, paginando até o fim. */
export async function listarVerbetesPublicos(): Promise<Neologismo[]> {
  const verbetes: Neologismo[] = [];

  for (let pagina = 1; pagina <= MAX_PAGINAS; pagina++) {
    const resposta = await buscar<Paginado<Neologismo>>(
      `/neologismos/?ordering=recentes&page_size=${POR_PAGINA}&page=${pagina}`
    );
    if (!resposta?.results?.length) break;

    verbetes.push(...resposta.results);
    if (!resposta.next) break;
  }

  return verbetes;
}
