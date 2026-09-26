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

export default nextConfig;
