// Sentry no servidor (Node e edge). O Next chama `register` no boot.
import * as Sentry from "@sentry/nextjs";
import { opcoesComuns } from "./sentry.shared";

export async function register() {
  Sentry.init(opcoesComuns);
}

// Captura erros de Server Components, que não passam pelo error.tsx.
export const onRequestError = Sentry.captureRequestError;
