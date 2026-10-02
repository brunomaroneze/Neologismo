import type { Metadata } from "next";
import { buscarVerbetePublico, SITE_URL } from "@/lib/api-servidor";

/**
 * Metadados do verbete.
 *
 * A página em si é um componente de cliente (precisa de estado para a
 * curtida e o botão de copiar link), e componente de cliente não exporta
 * `generateMetadata`. Resultado: todo link de verbete colado no WhatsApp, no
 * X ou no Discord mostrava o mesmo título genérico do site, qualquer que
 * fosse a palavra. Este layout roda no servidor só para resolver isso — ele
 * não desenha nada, apenas devolve `children`.
 *
 * O título e a definição também passam a existir no HTML inicial, que é o
 * que um buscador lê antes de executar JavaScript.
 */

type Props = {
  params: Promise<{ id: string }>;
};

/** Primeira frase da definição, cortada no limite que os previews mostram. */
function resumir(definicao: string, limite = 200): string {
  const limpa = definicao.replace(/\s+/g, " ").trim();
  if (limpa.length <= limite) return limpa;
  // Corta na última palavra inteira, para não terminar no meio de uma.
  const cortada = limpa.slice(0, limite);
  const ultimoEspaco = cortada.lastIndexOf(" ");
  return `${cortada.slice(0, ultimoEspaco > 0 ? ultimoEspaco : limite)}…`;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const verbete = await buscarVerbetePublico(id);

  if (!verbete) {
    // Verbete inexistente, ainda pendente ou API fora do ar. Sem `noindex`
    // aqui um 404 poderia entrar no índice de busca.
    return {
      title: "Verbete não encontrado",
      robots: { index: false, follow: false },
    };
  }

  const url = `${SITE_URL}/neologismo/${verbete.id}`;
  const classe = verbete.classe_gramatical
    ? `${verbete.classe_gramatical}. `
    : "";
  const descricao = `${classe}${resumir(verbete.definicao)}`;

  return {
    title: verbete.titulo,
    description: descricao,
    keywords: verbete.tags?.length ? verbete.tags : undefined,
    alternates: { canonical: url },
    openGraph: {
      type: "article",
      locale: "pt_BR",
      url,
      siteName: "Neoscópio",
      title: `${verbete.titulo} · Neoscópio`,
      description: descricao,
      publishedTime: verbete.data_criacao,
      modifiedTime: verbete.data_atualizacao,
      tags: verbete.tags,
    },
    twitter: {
      card: "summary",
      title: `${verbete.titulo} · Neoscópio`,
      description: descricao,
    },
  };
}

export default function LayoutVerbete({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
