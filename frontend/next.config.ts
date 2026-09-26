// No @sentry/nextjs 11 o withSentryConfig saiu do entrypoint principal e
// vive no subpath "/config" — importar da raiz devolve undefined.
import { withSentryConfig } from "@sentry/nextjs/config";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Gera um bundle autocontido em .next/standalone: a imagem de produção
  // roda `node server.js` sem precisar de node_modules nem do Next instalado.
  output: "standalone",

  // Sem isto o Next sobe um nível procurando lockfile e escolhe a raiz errada.
  turbopack: { root: __dirname },

  // O `poweredByHeader` entrega a stack de graça para quem varre a internet.
  poweredByHeader: false,

  // Barra final consistente evita 308 desnecessário e URLs duplicadas no
  // índice de busca.
  trailingSlash: false,

  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

/**
 * O wrapper do Sentry é aplicado sempre, mas só faz algo com DSN definido.
 * O upload de sourcemaps exige SENTRY_AUTH_TOKEN, SENTRY_ORG e SENTRY_PROJECT;
 * sem eles o build segue normalmente e apenas não sobe os mapas — importante
 * para o build não depender de segredos em quem faz fork do projeto.
 */
export default withSentryConfig(nextConfig, {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,

  silent: !process.env.CI,

  // Sourcemaps vão para o Sentry e são apagados do bundle público: sem isso o
  // código-fonte original fica servido junto com o site.
  sourcemaps: { deleteSourcemapsAfterUpload: true },

  // Rota interna que faz proxy dos eventos, para que bloqueadores de anúncio
  // não impeçam o relato de erros.
  tunnelRoute: "/monitoring",
});
