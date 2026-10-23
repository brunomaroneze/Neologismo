"use client";

import { use, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  Archive,
  ArrowLeft,
  CalendarDays,
  Clock3,
  ExternalLink,
  Link2,
  PenLine,
  Quote,
  User,
} from "lucide-react";
import BotaoCurtir from "@/components/BotaoCurtir";
import { useToast } from "@/components/Toast";
import { ApiError, buscarNeologismo, curtirNeologismo } from "@/lib/api";
import type { Neologismo } from "@/types";

export default function NeologismoDetalhe({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { avisar } = useToast();

  const [verbete, setVerbete] = useState<Neologismo | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<{ texto: string; status: number } | null>(null);
  const [curtindo, setCurtindo] = useState(false);
  const [copiado, setCopiado] = useState(false);

  const [gatilho, setGatilho] = useState(0);
  const carregar = useCallback(() => setGatilho((g) => g + 1), []);

  useEffect(() => {
    // O verbete é buscado no cliente porque o token da sessão (necessário
    // para `curtido_por_mim` e para ver o próprio rascunho) está no
    // localStorage.
    let cancelado = false;

    async function buscar() {
      setCarregando(true);
      setErro(null);
      try {
        const dados = await buscarNeologismo(id);
        if (!cancelado) setVerbete(dados);
      } catch (e) {
        if (cancelado) return;
        setErro({
          texto: e instanceof ApiError ? e.message : "Erro ao carregar o verbete.",
          status: e instanceof ApiError ? e.status : 0,
        });
      } finally {
        if (!cancelado) setCarregando(false);
      }
    }

    buscar();

    return () => {
      cancelado = true;
    };
  }, [id, gatilho]);

  async function curtir() {
    if (!verbete || curtindo) return;

    const anterior = {
      curtido_por_mim: verbete.curtido_por_mim,
      total_likes: verbete.total_likes,
    };

    setVerbete({
      ...verbete,
      curtido_por_mim: !anterior.curtido_por_mim,
      total_likes: anterior.total_likes + (anterior.curtido_por_mim ? -1 : 1),
    });
    setCurtindo(true);

    try {
      const resposta = await curtirNeologismo(verbete.id);
      setVerbete((atual) =>
        atual
          ? {
              ...atual,
              curtido_por_mim: resposta.curtido_por_mim,
              total_likes: resposta.total_likes,
            }
          : atual
      );
    } catch (e) {
      setVerbete((atual) => (atual ? { ...atual, ...anterior } : atual));
      if (e instanceof ApiError && e.precisaLogin) {
        avisar("Entre na sua conta para curtir verbetes.", "info", {
          rotulo: "Entrar",
          href: `/login?next=/neologismo/${id}`,
        });
      } else {
        avisar(
          e instanceof ApiError ? e.message : "Não foi possível curtir.",
          "erro"
        );
      }
    } finally {
      setCurtindo(false);
    }
  }

  async function copiarLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      avisar("Não foi possível copiar o link.", "erro");
    }
  }

  if (carregando) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
        <div className="mb-4 h-5 w-28 rounded esqueleto" />
        <div className="cartao p-8">
          <div className="mb-4 h-6 w-32 rounded-full esqueleto" />
          <div className="mb-6 h-12 w-2/3 rounded esqueleto" />
          <div className="space-y-3">
            <div className="h-4 w-full rounded esqueleto" />
            <div className="h-4 w-11/12 rounded esqueleto" />
            <div className="h-4 w-3/4 rounded esqueleto" />
          </div>
        </div>
      </div>
    );
  }

  if (erro || !verbete) {
    const naoEncontrado = erro?.status === 404;
    return (
      <div className="mx-auto max-w-md px-4 py-24 text-center">
        <p className="font-display text-3xl font-black text-texto">
          {naoEncontrado ? "Verbete não encontrado" : "Deu ruim"}
        </p>
        <p className="mt-3 text-sm leading-relaxed text-suave">
          {naoEncontrado
            ? "Esta palavra não existe, foi removida ou ainda está aguardando moderação."
            : erro?.texto}
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/"
            className="w-full rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 sm:w-auto"
          >
            Voltar ao banco
          </Link>
          {!naoEncontrado && (
            <button
              onClick={carregar}
              className="w-full rounded-full border border-borda-forte px-6 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta sm:w-auto"
            >
              Tentar de novo
            </button>
          )}
        </div>
      </div>
    );
  }

  const criadoEm = new Date(verbete.data_criacao).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <article className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <Link
        href="/"
        className="mb-6 inline-flex items-center gap-1.5 text-sm font-medium text-suave transition-colors hover:text-marca"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Voltar ao dicionário
      </Link>

      {verbete.status !== "aprovado" && (
        <div className="mb-6 rounded-xl border border-amber-500/40 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:bg-amber-950/50 dark:text-amber-100">
          {verbete.status === "pendente" ? (
            <p>
              <strong>Em moderação.</strong> Só você e a equipe conseguem ver
              este verbete até que ele seja aprovado.
            </p>
          ) : (
            <p>
              <strong>Rejeitado.</strong>{" "}
              {verbete.motivo_rejeicao || "Sem motivo registrado."}
            </p>
          )}
        </div>
      )}

      <header className="cartao p-6 sm:p-8">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center rounded-full bg-marca-suave px-3 py-1 text-[11px] font-bold uppercase tracking-wider text-marca">
            {verbete.classe_gramatical}
          </span>
          {verbete.tipologia && (
            <span className="inline-flex items-center rounded-full border border-marca/30 px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-marca">
              {verbete.tipologia}
            </span>
          )}
          {verbete.tags.map((tag) => (
            <Link
              key={tag}
              href={`/?tag=${encodeURIComponent(tag)}`}
              className="rounded-full bg-superficie-alta px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-suave transition-colors hover:text-marca"
            >
              {tag}
            </Link>
          ))}
        </div>

        <h1 className="font-display text-4xl font-black leading-tight text-texto sm:text-5xl">
          {verbete.titulo.toLocaleLowerCase("pt-BR")}
        </h1>

        <p className="mt-5 text-lg leading-relaxed text-texto">
          {verbete.definicao}
        </p>

        <div className="mt-7 flex flex-wrap items-center justify-between gap-4 border-t border-borda pt-5">
          <dl className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-tenue">
            <div className="flex items-center gap-1.5">
              <dt className="sr-only">Autor</dt>
              <User className="h-3.5 w-3.5" aria-hidden="true" />
              <dd>{verbete.autor_nome}</dd>
            </div>
            <div className="flex items-center gap-1.5">
              <dt className="sr-only">Publicado em</dt>
              <CalendarDays className="h-3.5 w-3.5" aria-hidden="true" />
              <dd>
                <time dateTime={verbete.data_criacao}>{criadoEm}</time>
              </dd>
            </div>
            {verbete.elaborado_por && (
              <div className="flex items-center gap-1.5">
                <dt className="sr-only">Elaborado por</dt>
                <PenLine className="h-3.5 w-3.5" aria-hidden="true" />
                <dd>elaborado por {verbete.elaborado_por}</dd>
              </div>
            )}
            {verbete.data_registro && (
              <div className="flex items-center gap-1.5">
                <dt className="sr-only">Registrado na fonte em</dt>
                <Archive className="h-3.5 w-3.5" aria-hidden="true" />
                <dd>
                  registrado em{" "}
                  <time dateTime={verbete.data_registro}>
                    {new Date(verbete.data_registro).toLocaleDateString("pt-BR")}
                  </time>
                </dd>
              </div>
            )}
            {verbete.reativado_em && (
              <div className="flex items-center gap-1.5">
                <dt className="sr-only">Reativado em</dt>
                <Clock3 className="h-3.5 w-3.5" aria-hidden="true" />
                <dd>
                  reativado em{" "}
                  {new Date(verbete.reativado_em).toLocaleDateString("pt-BR")}
                </dd>
              </div>
            )}
          </dl>

          <div className="flex items-center gap-1">
            <button
              onClick={copiarLink}
              className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium text-suave transition-colors hover:bg-superficie-alta hover:text-texto"
            >
              <Link2 className="h-4 w-4" aria-hidden="true" />
              {copiado ? "Link copiado!" : "Copiar link"}
            </button>
            <BotaoCurtir
              curtido={verbete.curtido_por_mim}
              total={verbete.total_likes}
              ocupado={curtindo}
              tamanho="md"
              titulo={verbete.titulo}
              onToggle={curtir}
            />
          </div>
        </div>
      </header>

      {verbete.contexto_uso && (
        <section className="mt-8">
          <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-tenue">
            Exemplo de uso
          </h2>
          <blockquote className="cartao border-l-4 border-l-marca p-5">
            <p className="text-base italic leading-relaxed text-texto">
              &ldquo;{verbete.contexto_uso}&rdquo;
            </p>
          </blockquote>
        </section>
      )}

      {verbete.contextos.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 text-xs font-bold uppercase tracking-wider text-tenue">
            {verbete.contextos.length === 1
              ? "Citação registrada"
              : `${verbete.contextos.length} citações registradas`}
          </h2>
          <ul className="space-y-4">
            {verbete.contextos.map((contexto) => (
              <li key={contexto.id} className="cartao p-5">
                <Quote
                  className="mb-2 h-4 w-4 text-marca"
                  aria-hidden="true"
                />
                <p className="text-sm leading-relaxed text-texto">
                  {contexto.citacao}
                </p>
                {(contexto.fonte || contexto.link) && (
                  <footer className="mt-3 flex flex-wrap items-center gap-3 border-t border-borda pt-3 text-xs text-tenue">
                    {contexto.fonte && <cite className="not-italic">{contexto.fonte}</cite>}
                    {contexto.link && (
                      <a
                        href={contexto.link}
                        target="_blank"
                        rel="noopener noreferrer nofollow"
                        className="inline-flex items-center gap-1 font-medium text-marca hover:underline"
                      >
                        Ver fonte
                        <ExternalLink className="h-3 w-3" aria-hidden="true" />
                      </a>
                    )}
                  </footer>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="mt-12 rounded-2xl border border-dashed border-borda-forte p-8 text-center">
        <p className="font-display text-xl font-bold text-texto">
          Conhece uma palavra que ainda não está aqui?
        </p>
        <p className="mx-auto mt-2 max-w-md text-sm text-suave">
          O banco de neologismos cresce com quem usa a língua todo dia.
        </p>
        <Link
          href="/enviar"
          className="mt-5 inline-flex rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90"
        >
          Enviar um neologismo
        </Link>
      </section>
    </article>
  );
}
