"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Clock3, Heart, Loader2, XCircle } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { ApiError, listarMeusNeologismos } from "@/lib/api";
import type { Neologismo, NeologismoStatus } from "@/types";

const ABAS: { id: NeologismoStatus | "todos"; label: string }[] = [
  { id: "todos", label: "Todos" },
  { id: "pendente", label: "Em moderação" },
  { id: "aprovado", label: "Publicados" },
  { id: "rejeitado", label: "Rejeitados" },
];

const SELO: Record<NeologismoStatus, { texto: string; classe: string }> = {
  pendente: {
    texto: "Em moderação",
    classe:
      "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200",
  },
  aprovado: {
    texto: "Publicado",
    classe:
      "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  },
  rejeitado: {
    texto: "Rejeitado",
    classe: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-200",
  },
};

export default function MinhasPalavras() {
  const router = useRouter();
  const { isAuthenticated, ready } = useAuth();

  const [aba, setAba] = useState<NeologismoStatus | "todos">("todos");
  const [itens, setItens] = useState<Neologismo[]>([]);
  const [total, setTotal] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  // Contador que permite refazer a busca sem mudar de aba ("tentar de novo").
  const [gatilho, setGatilho] = useState(0);
  const recarregar = useCallback(() => setGatilho((g) => g + 1), []);

  useEffect(() => {
    if (!ready) return;
    if (!isAuthenticated) {
      router.push("/login?next=/minhas-palavras");
      return;
    }

    // O fetch acontece aqui porque o token da sessão só existe no cliente.
    let cancelado = false;

    async function buscar() {
      setCarregando(true);
      setErro(null);
      try {
        const resposta = await listarMeusNeologismos(
          aba === "todos" ? {} : { status: aba }
        );
        if (cancelado) return;
        setItens(resposta.results);
        setTotal(resposta.count);
      } catch (e) {
        if (cancelado) return;
        if (e instanceof ApiError && e.precisaLogin) {
          router.push("/login?next=/minhas-palavras");
          return;
        }
        setErro(
          e instanceof ApiError ? e.message : "Erro ao carregar seus envios."
        );
      } finally {
        if (!cancelado) setCarregando(false);
      }
    }

    buscar();

    return () => {
      cancelado = true;
    };
  }, [ready, isAuthenticated, router, aba, gatilho]);

  if (!ready || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-marca" aria-hidden="true" />
        <span className="sr-only">Carregando</span>
      </div>
    );
  }

  return (
    <section className="mx-auto max-w-4xl px-4 py-10 sm:px-6 lg:px-8">
      <span className="inline-block rounded-full border border-marca/30 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-marca">
        Sua conta
      </span>
      <h1 className="mt-4 font-display text-4xl font-black text-texto">
        Minhas palavras
      </h1>
      <p className="mt-2 text-sm text-suave">
        Acompanhe o que você enviou e em que pé está a moderação.
      </p>

      <div
        role="tablist"
        aria-label="Filtrar por status"
        className="mt-8 flex flex-wrap gap-2 border-b border-borda pb-4"
      >
        {ABAS.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={aba === item.id}
            onClick={() => setAba(item.id)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
              aba === item.id
                ? "bg-marca text-marca-contraste"
                : "border border-borda-forte text-suave hover:bg-superficie-alta"
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {erro && (
        <div
          role="alert"
          className="mt-6 flex items-center justify-between gap-4 rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200"
        >
          <span>{erro}</span>
          <button onClick={recarregar} className="font-semibold hover:underline">
            Tentar de novo
          </button>
        </div>
      )}

      {carregando && (
        <div className="mt-6 space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="cartao h-32 esqueleto" aria-hidden="true" />
          ))}
        </div>
      )}

      {!carregando && !erro && itens.length === 0 && (
        <div className="py-20 text-center">
          <p className="font-display text-xl font-bold text-texto">
            {aba === "todos"
              ? "Você ainda não enviou nenhuma palavra"
              : "Nada por aqui"}
          </p>
          <p className="mx-auto mt-2 max-w-sm text-sm text-suave">
            {aba === "todos"
              ? "Conhece uma palavra nova que ninguém registrou? Comece por ela."
              : "Nenhum envio seu está nesse status."}
          </p>
          <Link
            href="/enviar"
            className="mt-6 inline-flex rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90"
          >
            Enviar um neologismo
          </Link>
        </div>
      )}

      {!carregando && !erro && itens.length > 0 && (
        <>
          <p className="mt-6 text-sm text-suave" aria-live="polite">
            <strong className="text-texto">{total}</strong>{" "}
            {total === 1 ? "envio" : "envios"}
          </p>

          <ul className="mt-4 space-y-4">
            {itens.map((verbete) => {
              const selo = SELO[verbete.status];
              return (
                <li key={verbete.id} className="cartao p-5">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="font-display text-xl font-bold text-texto">
                        {verbete.status === "aprovado" ? (
                          <Link
                            href={`/neologismo/${verbete.id}`}
                            className="transition-colors hover:text-marca"
                          >
                            {verbete.titulo.toLocaleLowerCase("pt-BR")}
                          </Link>
                        ) : (
                          verbete.titulo.toLocaleLowerCase("pt-BR")
                        )}
                      </h2>
                      <p className="mt-0.5 text-xs text-tenue">
                        {verbete.classe_gramatical} · enviado em{" "}
                        {new Date(verbete.data_criacao).toLocaleDateString("pt-BR")}
                      </p>
                    </div>

                    <span
                      className={`shrink-0 rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-wider ${selo.classe}`}
                    >
                      {selo.texto}
                    </span>
                  </div>

                  <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-suave">
                    {verbete.definicao}
                  </p>

                  {verbete.status === "rejeitado" && verbete.motivo_rejeicao && (
                    <div className="mt-4 flex gap-2.5 rounded-xl bg-red-50 p-3 dark:bg-red-950/40">
                      <XCircle
                        className="mt-0.5 h-4 w-4 shrink-0 text-red-600 dark:text-red-400"
                        aria-hidden="true"
                      />
                      <div>
                        <p className="text-xs font-semibold text-red-800 dark:text-red-200">
                          Motivo da rejeição
                        </p>
                        <p className="mt-0.5 text-xs leading-relaxed text-red-700 dark:text-red-300">
                          {verbete.motivo_rejeicao}
                        </p>
                      </div>
                    </div>
                  )}

                  {verbete.status === "pendente" && (
                    <p className="mt-4 flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-300">
                      <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                      Aguardando revisão da equipe.
                    </p>
                  )}

                  {verbete.status === "aprovado" && (
                    <p className="mt-4 flex items-center gap-1.5 text-xs text-suave">
                      <Heart className="h-3.5 w-3.5" aria-hidden="true" />
                      {verbete.total_likes}{" "}
                      {verbete.total_likes === 1 ? "curtida" : "curtidas"}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </>
      )}
    </section>
  );
}
