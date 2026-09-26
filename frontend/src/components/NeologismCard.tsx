"use client";

import Link from "next/link";
import type { Neologismo } from "@/types";
import BotaoCurtir from "./BotaoCurtir";

interface NeologismCardProps {
  neologismo: Neologismo;
  onCurtir: (id: number) => void;
  curtindo?: boolean;
}

export default function NeologismCard({
  neologismo,
  onCurtir,
  curtindo = false,
}: NeologismCardProps) {
  const data = new Date(neologismo.data_criacao);
  const dataFormatada = data.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return (
    // `relative` ancora o span que transforma o card inteiro em área de clique.
    <article className="group relative flex h-full flex-col cartao overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:[box-shadow:var(--sombra-card-alta)]">
      <div className="flex flex-1 flex-col p-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <span className="inline-flex items-center rounded-full bg-marca-suave px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-marca">
            {neologismo.classe_gramatical}
          </span>
          <time
            dateTime={neologismo.data_criacao}
            className="shrink-0 text-xs font-medium text-tenue"
          >
            {dataFormatada}
          </time>
        </div>

        <h2 className="mb-1.5 font-display text-2xl font-bold leading-tight">
          <Link
            href={`/neologismo/${neologismo.id}`}
            className="text-texto transition-colors hover:text-marca"
          >
            {/* O link cobre o card inteiro: o alvo de toque no celular passa a
                ser o cartão, não só as duas palavras do título. */}
            <span className="absolute inset-0 z-0" aria-hidden="true" />
            {neologismo.titulo.toLocaleLowerCase("pt-BR")}
          </Link>
        </h2>

        {/* Tipologia (processo de formação) vem da planilha de origem. */}
        {neologismo.tipologia && (
          <p className="mb-2 text-xs font-medium text-marca">
            {neologismo.tipologia}
          </p>
        )}

        <p className="mb-3 line-clamp-3 text-sm leading-relaxed text-suave">
          {neologismo.definicao}
        </p>

        {neologismo.contexto_uso && (
          <blockquote className="mb-4 rounded-xl bg-superficie-alta p-3">
            <p className="line-clamp-2 text-xs italic leading-relaxed text-suave">
              &ldquo;{neologismo.contexto_uso}&rdquo;
            </p>
            <footer className="mt-1 text-[10px] font-medium text-tenue">
              — {neologismo.autor_nome}
            </footer>
            {neologismo.contextos[0]?.link && (
              // z-10 porque o card inteiro é coberto por um link.
              <a
                href={neologismo.contextos[0].link}
                target="_blank"
                rel="noopener noreferrer nofollow"
                className="relative z-10 mt-1 block truncate text-[10px] font-medium text-marca hover:underline"
              >
                {neologismo.contextos[0].link}
              </a>
            )}
          </blockquote>
        )}

        <div className="mt-auto flex items-center justify-between gap-3 border-t border-borda pt-3">
          <ul className="flex flex-wrap gap-1.5">
            {neologismo.tags.slice(0, 3).map((tag) => (
              <li
                key={tag}
                className="rounded-full bg-superficie-alta px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-suave"
              >
                {tag}
              </li>
            ))}
            {neologismo.tags.length > 3 && (
              <li className="px-1 py-0.5 text-[10px] font-semibold text-tenue">
                +{neologismo.tags.length - 3}
              </li>
            )}
          </ul>

          {/* z-10 para o botão ficar acima do link que cobre o card. */}
          <div className="relative z-10 shrink-0">
            <BotaoCurtir
              curtido={neologismo.curtido_por_mim}
              total={neologismo.total_likes}
              ocupado={curtindo}
              titulo={neologismo.titulo}
              onToggle={() => onCurtir(neologismo.id)}
            />
          </div>
        </div>
      </div>
    </article>
  );
}

export function NeologismCardEsqueleto() {
  return (
    <div className="cartao p-5" aria-hidden="true">
      <div className="mb-3 flex justify-between">
        <div className="h-5 w-24 rounded-full esqueleto" />
        <div className="h-4 w-20 rounded esqueleto" />
      </div>
      <div className="mb-3 h-7 w-2/3 rounded esqueleto" />
      <div className="space-y-2">
        <div className="h-3 w-full rounded esqueleto" />
        <div className="h-3 w-11/12 rounded esqueleto" />
        <div className="h-3 w-4/6 rounded esqueleto" />
      </div>
      <div className="mt-4 h-14 w-full rounded-xl esqueleto" />
      <div className="mt-4 flex justify-between border-t border-borda pt-3">
        <div className="h-4 w-28 rounded-full esqueleto" />
        <div className="h-4 w-10 rounded-full esqueleto" />
      </div>
    </div>
  );
}
