"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Eye, EyeOff, Loader2 } from "lucide-react";
import { ApiError, login } from "@/lib/api";

function Formulario() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // `next` devolve a pessoa para onde ela estava quando o login foi exigido.
  // Só aceitamos caminhos internos: uma URL absoluta aqui seria um open
  // redirect para fora do site.
  const destinoBruto = searchParams.get("next") || "/";
  const destino = destinoBruto.startsWith("/") && !destinoBruto.startsWith("//")
    ? destinoBruto
    : "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [entrando, setEntrando] = useState(false);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!username.trim() || !password) {
      setErro("Preencha usuário e senha.");
      return;
    }

    setEntrando(true);
    try {
      await login({ username: username.trim(), password });
      router.push(destino);
      router.refresh();
    } catch (e) {
      setErro(e instanceof ApiError ? e.message : "Falha no login.");
    } finally {
      setEntrando(false);
    }
  }

  return (
    <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-gradient-to-b from-marca-suave/40 to-fundo px-4 py-16">
      <div className="w-full max-w-md">
        <div className="cartao p-8">
          <h1 className="font-display text-3xl font-black text-texto">Entrar</h1>
          <p className="mt-1.5 text-sm text-suave">
            Acesse para enviar e curtir neologismos.
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
                htmlFor="username"
                className="mb-1.5 block text-sm font-medium text-texto"
              >
                Usuário
              </label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                autoFocus
                className="campo"
              />
            </div>

            <div>
              <div className="mb-1.5 flex items-baseline justify-between gap-3">
                <label
                  htmlFor="password"
                  className="block text-sm font-medium text-texto"
                >
                  Senha
                </label>
                <Link
                  href="/recuperar-senha"
                  className="text-xs font-medium text-marca hover:underline"
                >
                  Esqueci a senha
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  type={mostrarSenha ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  className="campo !pr-11"
                />
                <button
                  type="button"
                  onClick={() => setMostrarSenha((v) => !v)}
                  aria-label={mostrarSenha ? "Ocultar senha" : "Mostrar senha"}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-lg p-2 text-tenue transition-colors hover:text-texto"
                >
                  {mostrarSenha ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={entrando}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-marca px-6 py-3 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {entrando && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              {entrando ? "Entrando…" : "Entrar"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-suave">
            Não tem conta?{" "}
            <Link
              href={`/cadastro${
                destino !== "/" ? `?next=${encodeURIComponent(destino)}` : ""
              }`}
              className="font-semibold text-marca hover:underline"
            >
              Cadastre-se
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}

export default function LoginPage() {
  // useSearchParams exige um limite de Suspense para o build estático.
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center py-32">
          <Loader2 className="h-8 w-8 animate-spin text-marca" aria-hidden="true" />
        </div>
      }
    >
      <Formulario />
    </Suspense>
  );
}
