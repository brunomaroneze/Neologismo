"use client";

import { use, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Check, Eye, EyeOff, Loader2, ShieldCheck, X } from "lucide-react";
import { useToast } from "@/components/Toast";
import { ApiError, redefinirSenha } from "@/lib/api";

/** Mesmos requisitos dos AUTH_PASSWORD_VALIDATORS do Django. */
function avaliarSenha(senha: string) {
  return [
    { rotulo: "Pelo menos 8 caracteres", ok: senha.length >= 8 },
    { rotulo: "Não pode ser só números", ok: !/^\d+$/.test(senha) },
  ];
}

export default function RedefinirSenhaPage({
  params,
}: {
  params: Promise<{ uid: string; token: string }>;
}) {
  const { uid, token } = use(params);
  const router = useRouter();
  const { avisar } = useToast();

  const [password, setPassword] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [mostrarSenha, setMostrarSenha] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [linkInvalido, setLinkInvalido] = useState(false);
  const [salvando, setSalvando] = useState(false);

  const requisitos = useMemo(() => avaliarSenha(password), [password]);
  const senhaOk = requisitos.every((r) => r.ok);

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErro(null);

    if (!senhaOk) {
      setErro("A senha ainda não atende aos requisitos abaixo.");
      return;
    }
    if (password !== confirmacao) {
      setErro("As senhas não coincidem.");
      return;
    }

    setSalvando(true);
    try {
      await redefinirSenha({ uid, token, password });
      avisar("Senha atualizada. Você já está conectado.", "sucesso");
      router.push("/");
    } catch (e) {
      if (e instanceof ApiError) {
        setErro(e.message);
        // Link gasto ou adulterado: não faz sentido manter o formulário,
        // a pessoa precisa pedir um link novo.
        if (e.campos.uid || e.campos.token) {
          setLinkInvalido(true);
        }
      } else {
        setErro("Falha ao redefinir a senha.");
      }
    } finally {
      setSalvando(false);
    }
  }

  if (linkInvalido) {
    return (
      <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center px-4 py-16">
        <div className="w-full max-w-md text-center">
          <h1 className="font-display text-3xl font-black text-texto">
            Link expirado
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-suave">
            {erro ??
              "Este link já foi usado ou passou da validade. Peça um novo para continuar."}
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/recuperar-senha"
              className="w-full rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 sm:w-auto"
            >
              Pedir novo link
            </Link>
            <Link
              href="/login"
              className="w-full rounded-full border border-borda-forte px-6 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta sm:w-auto"
            >
              Voltar para o login
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="flex min-h-[calc(100vh-4rem)] items-center justify-center bg-gradient-to-b from-marca-suave/40 to-fundo px-4 py-16">
      <div className="w-full max-w-md">
        <div className="cartao p-8">
          <ShieldCheck className="mb-4 h-10 w-10 text-marca" aria-hidden="true" />

          <h1 className="font-display text-3xl font-black text-texto">
            Criar nova senha
          </h1>
          <p className="mt-1.5 text-sm text-suave">
            Escolha uma senha nova. Ao salvar, as outras sessões da conta são
            desconectadas.
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
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-texto"
              >
                Nova senha
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={mostrarSenha ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="new-password"
                  autoFocus
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
            </div>

            <div>
              <label
                htmlFor="confirmacao"
                className="mb-1.5 block text-sm font-medium text-texto"
              >
                Confirmar nova senha
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
              disabled={salvando}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-marca px-6 py-3 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {salvando && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              {salvando ? "Salvando…" : "Salvar nova senha"}
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
