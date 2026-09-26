/**
 * Opções comuns às três execuções do Sentry (navegador, servidor Node e edge).
 *
 * Tudo aqui é desligado por padrão: sem `NEXT_PUBLIC_SENTRY_DSN` o SDK não
 * inicializa e nenhuma requisição sai do navegador. Isso mantém o projeto
 * rodando em desenvolvimento e em quem faz fork sem precisar de conta.
 */
export const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN;

export const opcoesComuns = {
  dsn,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? process.env.NODE_ENV,

  // 0 por padrão: só erros, sem tracing. Tracing em projeto pequeno gasta
  // cota rápido e não responde nenhuma pergunta que ainda não temos.
  tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? 0),

  // Não envia IP nem cabeçalhos que identifiquem a pessoa.
  sendDefaultPii: false,

  // Sem DSN o SDK fica completamente inerte.
  enabled: Boolean(dsn),

  // Ruído que não é bug da aplicação: extensões de navegador e falhas de
  // rede do próprio usuário gerariam alerta sem nada para corrigir.
  ignoreErrors: [
    "ResizeObserver loop limit exceeded",
    "ResizeObserver loop completed with undelivered notifications",
    /^Failed to fetch$/,
    /^NetworkError/,
    /^Load failed$/,
    /extension:\//,
  ],
};
