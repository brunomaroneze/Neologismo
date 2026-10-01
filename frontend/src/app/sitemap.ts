import type { MetadataRoute } from "next";
import { listarVerbetesPublicos, SITE_URL } from "@/lib/api-servidor";

/**
 * Sitemap do dicionário.
 *
 * Sem ele, um buscador só encontra um verbete se alguém já tiver linkado —
 * e como a Home carrega a lista por JavaScript, a maior parte do acervo
 * ficava invisível. Aqui cada verbete aprovado entra com a data da última
 * alteração, que é o que faz o Google voltar depois de uma edição.
 *
 * A rota é dinâmica de propósito. Se fosse pré-renderizada, o `next build`
 * tentaria falar com a API dentro do runner de CI — onde não há backend — e
 * a imagem sairia com um sitemap vazio gravado dentro dela, servido até o
 * primeiro revalidate. A resposta em si continua barata: a chamada à API é
 * guardada por uma hora no Data Cache (ver `api-servidor.ts`), então uma
 * sequência de visitas de rastreador não vira uma sequência de consultas.
 */

export const dynamic = "force-dynamic";

const PAGINAS_FIXAS: {
  caminho: string;
  prioridade: number;
  frequencia: MetadataRoute.Sitemap[number]["changeFrequency"];
}[] = [
  { caminho: "", prioridade: 1, frequencia: "daily" },
  { caminho: "/sobre", prioridade: 0.5, frequencia: "yearly" },
  { caminho: "/equipe", prioridade: 0.4, frequencia: "yearly" },
  { caminho: "/indicacoes-de-leitura", prioridade: 0.4, frequencia: "monthly" },
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const agora = new Date();

  const fixas: MetadataRoute.Sitemap = PAGINAS_FIXAS.map(
    ({ caminho, prioridade, frequencia }) => ({
      url: `${SITE_URL}${caminho}`,
      lastModified: agora,
      changeFrequency: frequencia,
      priority: prioridade,
    })
  );

  const verbetes = await listarVerbetesPublicos();

  return [
    ...fixas,
    ...verbetes.map((verbete) => ({
      url: `${SITE_URL}/neologismo/${verbete.id}`,
      lastModified: new Date(verbete.data_atualizacao || verbete.data_criacao),
      changeFrequency: "monthly" as const,
      priority: 0.8,
    })),
  ];
}
