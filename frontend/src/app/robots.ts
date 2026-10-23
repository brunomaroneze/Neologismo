import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/api-servidor";

/**
 * robots.txt.
 *
 * O acervo é público e queremos que seja indexado. O que fica de fora são as
 * rotas que não têm conteúdo para buscador nenhum: formulários de conta,
 * painel de moderação e o túnel de telemetria do Sentry. Deixá-las no índice
 * só gera resultado de busca que cai numa tela de login.
 *
 * `Disallow` não é controle de acesso — quem protege essas páginas é a
 * autenticação. Isto é só higiene de indexação.
 */

const PRIVADAS = [
  "/admin-painel",
  "/minhas-palavras",
  "/enviar",
  "/login",
  "/cadastro",
  "/recuperar-senha",
  "/redefinir-senha",
  "/monitoring",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        // Sem barra no fim: em robots.txt o caminho casa por prefixo,
        // então "/redefinir-senha" já cobre /redefinir-senha/<uid>/<token>.
        disallow: PRIVADAS,
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
