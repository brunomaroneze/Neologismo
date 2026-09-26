// Sentry no navegador. O Next carrega este arquivo automaticamente.
import * as Sentry from "@sentry/nextjs";
import { opcoesComuns } from "./sentry.shared";

Sentry.init({
  ...opcoesComuns,
  // Replay e profiling ficam de fora: gravar a sessão de quem navega é um
  // dado sensível que este projeto não tem motivo para coletar.
  integrations: [],
});

// Necessário para o Sentry associar erros a navegações do App Router.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
