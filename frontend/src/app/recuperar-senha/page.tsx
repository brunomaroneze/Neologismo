"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, MailCheck } from "lucide-react";
import { ApiError, pedirRecuperacaoSenha } from "@/lib/api";

export default function RecuperarSenhaPage() {
  const [email, setEmail] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [enviado, setEnviado] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!email.trim()) {
      setErro("Informe o e-mail da sua conta.");
      return;
    }

    setEnviando(true);
    try {
      await pedirRecuperacaoSenha(email.trim());
      setEnviado(true);
    } catch (e) {
      setErro(
        e instanceof ApiError ? e.message : "Falha ao pedir a recuperação."
      );
    } finally {
      setEnviando(false);
    }
  }

  if (enviado) {
    return (
      <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-gradient-to-b from-marca-suave/40 to-fundo px-4 py-16">
        <div className="w-full max-w-md text-center">
          <MailCheck
            className="mx-auto mb-5 h-14 w-14 text-marca"
            aria-hidden="true"
          />
          <h1 className="font-display text-3xl font-black text-texto">
            Verifique seu e-mail
          </h1>
          {/* A mensagem não confirma se o e-mail existe: a própria API é
              deliberadamente ambígua para não virar um verificador de
              cadastros. A interface precisa ser coerente com isso. */}
          <p className="mt-3 text-sm leading-relaxed text-suave">
            Se existe uma conta com <strong className="text-texto">{email}</strong>,
            o link de redefinição já está a caminho. Ele vale por 2 horas.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-tenue">
            Não chegou? Confira a caixa de spam ou tente de novo em alguns
            minutos.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/login"
              className="w-full rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 sm:w-auto"
            >
              Voltar para o login
            </Link>
            <button
              onClick={() => {
                setEnviado(false);
                setErro(null);
              }}
              className="w-full rounded-full border border-borda-forte px-6 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta sm:w-auto"
            >
              Usar outro e-mail
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-gradient-to-b from-marca-suave/40 to-fundo px-4 py-16">
      <div className="w-full max-w-md">
        <div className="cartao p-8">
          <Link
            href="/login"
            className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-suave transition-colors hover:text-marca"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Voltar para o login
          </Link>

          <h1 className="font-display text-3xl font-black text-texto">
            Esqueceu a senha?
          </h1>
          <p className="mt-1.5 text-sm text-suave">
            Informe o e-mail da sua conta e enviamos um link para criar uma
            nova.
          </p>

          {erro && (
            <div
              role="alert"
              className="mt-5 rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200"
            >
              {erro}
            </div>
          )}

          <form onSubmit={enviar} noValidate className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-texto"
              >
                E-mail
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                autoFocus
                placeholder="voce@exemplo.com"
                className="campo"
              />
            </div>

            <button
              type="submit"
              disabled={enviando}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-marca px-6 py-3 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {enviando && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              {enviando ? "Enviando…" : "Enviar link de redefinição"}
            </button>
          </form>

          <p className="mt-6 text-center text-xs leading-relaxed text-tenue">
            Cadastrou-se sem informar e-mail? Nesse caso não há como recuperar
            a senha automaticamente — fale com a equipe do projeto.
          </p>
        </div>
      </div>
    </section>
  );
}
