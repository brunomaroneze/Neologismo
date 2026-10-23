"use client";

import { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Check, Eye, EyeOff, Loader2, X } from "lucide-react";
import { ApiError, cadastrar } from "@/lib/api";

/** Espelha os AUTH_PASSWORD_VALIDATORS do Django, para a pessoa saber o que
 *  falta antes de o servidor recusar. */
function avaliarSenha(senha: string, username: string) {
  return [
    { rotulo: "Pelo menos 8 caracteres", ok: senha.length >= 8 },
    { rotulo: "Não pode ser só números", ok: !/^\d+$/.test(senha) },
    {
      rotulo: "Diferente do nome de usuário",
      ok:
        senha.length > 0 &&
        username.trim().length > 0 &&
        !senha.toLocaleLowerCase().includes(username.trim().toLocaleLowerCase()),
    },
  ];
}

function Formulario() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const destinoBruto = searchParams.get("next") || "/";
  const destino =
    destinoBruto.startsWith("/") && !destinoBruto.startsWith("//")
      ? destinoBruto
      : "/";

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({});
  const [criando, setCriando] = useState(false);

  const requisitos = useMemo(
    () => avaliarSenha(password, username),
    [password, username]
  );
  const senhaOk = requisitos.every((r) => r.ok);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);
    setErrosCampo({});

    if (username.trim().length < 3) {
      setErro("O nome de usuário precisa ter ao menos 3 caracteres.");
      return;
    }
    if (!senhaOk) {
      setErro("A senha ainda não atende aos requisitos abaixo.");
      return;
    }
    if (password !== confirmacao) {
      setErro("As senhas não coincidem.");
      return;
    }

    setCriando(true);
    try {
      await cadastrar({
        username: username.trim(),
        email: email.trim(),
        password,
      });
      router.push(destino);
      router.refresh();
    } catch (e) {
      if (e instanceof ApiError) {
        setErro(e.message);
        const mapeados: Record<string, string> = {};
        for (const [campo, mensagens] of Object.entries(e.campos)) {
          mapeados[campo] = mensagens[0];
        }
        setErrosCampo(mapeados);
      } else {
        setErro("Falha ao criar a conta.");
      }
    } finally {
      setCriando(false);
    }
  }

  return (
    <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-gradient-to-b from-marca-suave/40 to-fundo px-4 py-16">
      <div className="w-full max-w-md">
        <div className="cartao p-8">
          <h1 className="font-display text-3xl font-black text-texto">
            Criar conta
          </h1>
          <p className="mt-1.5 text-sm text-suave">
            Junte-se ao banco de neologismos colaborativo.
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
                aria-invalid={!!errosCampo.username}
                className="campo"
              />
              {errosCampo.username && (
                <p role="alert" className="mt-1.5 text-xs font-medium text-red-600 dark:text-red-400">
                  {errosCampo.username}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-texto"
              >
                E-mail <span className="font-normal text-tenue">(opcional)</span>
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                aria-invalid={!!errosCampo.email}
                className="campo"
              />
              {errosCampo.email && (
                <p role="alert" className="mt-1.5 text-xs font-medium text-red-600 dark:text-red-400">
                  {errosCampo.email}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-texto"
              >
                Senha
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={mostrarSenha ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  aria-invalid={!!errosCampo.password}
                  aria-describedby="requisitos-senha"
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

              {password.length > 0 && (
                <ul id="requisitos-senha" className="mt-2.5 space-y-1">
                  {requisitos.map((requisito) => (
                    <li
                      key={requisito.rotulo}
                      className={`flex items-center gap-1.5 text-xs ${
                        requisito.ok
                          ? "text-emerald-600 dark:text-emerald-400"
                          : "text-tenue"
                      }`}
                    >
                      {requisito.ok ? (
                        <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      ) : (
                        <X className="h-3.5 w-3.5" aria-hidden="true" />
                      )}
                      {requisito.rotulo}
                    </li>
                  ))}
                </ul>
              )}
              {errosCampo.password && (
                <p role="alert" className="mt-1.5 text-xs font-medium text-red-600 dark:text-red-400">
                  {errosCampo.password}
                </p>
              )}
            </div>

            <div>
              <label
                htmlFor="confirmacao"
                className="mb-1.5 block text-sm font-medium text-texto"
              >
                Confirmar senha
              </label>
              <input
                id="confirmacao"
                type={mostrarSenha ? "text" : "password"}
                value={confirmacao}
                onChange={(e) => setConfirmacao(e.target.value)}
                autoComplete="new-password"
                className="campo"
              />
              {confirmacao.length > 0 && confirmacao !== password && (
                <p className="mt-1.5 text-xs font-medium text-red-600 dark:text-red-400">
                  As senhas não coincidem.
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={criando}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-marca px-6 py-3 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {criando && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              {criando ? "Criando…" : "Cadastrar"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-suave">
            Já tem conta?{" "}
            <Link
              href={`/login${
                destino !== "/" ? `?next=${encodeURIComponent(destino)}` : ""
              }`}
              className="font-semibold text-marca hover:underline"
            >
              Entrar
            </Link>
          </p>
        </div>
      </div>
    </section>
  );
}

export default function CadastroPage() {
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
