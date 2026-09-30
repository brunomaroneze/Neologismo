"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Loader2, Search, SlidersHorizontal, X } from "lucide-react";
import NeologismCard, {
  NeologismCardEsqueleto,
} from "@/components/NeologismCard";
import { useDebounce, useNeologismos } from "@/hooks/useNeologismos";
import { buscarFacetas } from "@/lib/api";
import type { Faceta, Ordenacao } from "@/types";

const ORDENACOES: { id: Ordenacao; label: string }[] = [
  { id: "recentes", label: "Mais recentes" },
  { id: "populares", label: "Mais curtidos" },
  { id: "alfabetica", label: "A–Z" },
  { id: "antigos", label: "Mais antigos" },
];

export default function Home() {
  const [busca, setBusca] = useState("");
  const [tag, setTag] = useState("");
  const [ordering, setOrdering] = useState<Ordenacao>("recentes");
  const [tags, setTags] = useState<Faceta[]>([]);

  // Sem o debounce, cada tecla digitada viraria uma requisição.
  const buscaAtrasada = useDebounce(busca);

  const consulta = useMemo(
    () => ({ search: buscaAtrasada, tag, ordering }),
    [buscaAtrasada, tag, ordering]
  );

  const {
    itens,
    total,
    carregando,
    carregandoMais,
    erro,
    temMais,
    curtindo,
    curtir,
    carregarMais,
    recarregar,
  } = useNeologismos(consulta);

  // As tags vêm da base (endpoint /facetas/) em vez de uma lista fixa no
  // código, que ficava dessincronizada do que existe de fato.
  useEffect(() => {
    let ativo = true;
    buscarFacetas()
      .then((facetas) => {
        if (ativo) setTags(facetas.tags.slice(0, 8));
      })
      .catch(() => {
        // Sem facetas a página segue funcionando, só sem os atalhos de tag.
      });
    return () => {
      ativo = false;
    };
  }, []);

  const temFiltro = busca !== "" || tag !== "" || ordering !== "recentes";

  function limparFiltros() {
    setBusca("");
    setTag("");
    setOrdering("recentes");
  }

  return (
    <>
      <section className="border-b border-borda bg-gradient-to-b from-marca-suave/50 to-fundo px-4 py-14">
        <div className="mx-auto max-w-3xl text-center">
          <span className="inline-block rounded-full border border-marca/30 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-marca">
            Dicionário Colaborativo
          </span>

          <h1 className="mt-4 font-display text-4xl font-black leading-[1.1] text-texto sm:text-5xl">
            O brasileiro precisa ser estudado.
            <br />
            <span className="text-marca">As palavras que ele cria também.</span>
          </h1>

          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-suave">
            Registre, explore e discuta os neologismos que moldam o português do
            nosso tempo.
          </p>

          <div className="mt-7 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href="/enviar"
              className="w-full rounded-full bg-marca px-6 py-3 text-center text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 sm:w-auto"
            >
              Enviar uma palavra
            </Link>
            <Link
              href="/sobre"
              className="w-full rounded-full border border-borda-forte px-6 py-3 text-center text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta sm:w-auto"
            >
              Como funciona
            </Link>
          </div>
        </div>
      </section>

      <section
        id="explorar"
        className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8"
      >
        <div className="mx-auto mb-6 max-w-2xl">
          <label htmlFor="busca" className="sr-only">
            Buscar neologismos
          </label>
          <div className="relative">
            <Search
              className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-tenue"
              aria-hidden="true"
            />
            <input
              id="busca"
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar por palavra, definição ou tag…"
              className="campo !rounded-full !py-3 !pl-12 !pr-11"
            />
            {busca && (
              <button
                onClick={() => setBusca("")}
                aria-label="Limpar busca"
                className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full p-1.5 text-tenue transition-colors hover:bg-superficie-alta hover:text-texto"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        <div className="mb-8 flex flex-col gap-4">
          <div className="flex flex-wrap items-center justify-center gap-2">
            <button
              onClick={() => setTag("")}
              aria-pressed={tag === ""}
              className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                tag === ""
                  ? "bg-marca text-marca-contraste"
                  : "border border-borda-forte text-suave hover:bg-superficie-alta"
              }`}
            >
              Todos
            </button>
            {tags.map((faceta) => (
              <button
                key={faceta.nome}
                onClick={() => setTag(faceta.nome)}
                aria-pressed={tag === faceta.nome}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  tag === faceta.nome
                    ? "bg-marca text-marca-contraste"
                    : "border border-borda-forte text-suave hover:bg-superficie-alta"
                }`}
              >
                {faceta.nome}
                <span className="ml-1.5 text-xs opacity-60">{faceta.total}</span>
              </button>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-borda pt-4">
            <p className="text-sm text-suave" aria-live="polite">
              {carregando ? (
                "Carregando…"
              ) : (
                <>
                  <strong className="text-texto">{total}</strong>{" "}
                  {total === 1 ? "verbete" : "verbetes"}
                  {temFiltro && " para os filtros atuais"}
                </>
              )}
            </p>

            <div className="flex items-center gap-2">
              {temFiltro && (
                <button
                  onClick={limparFiltros}
                  className="text-sm font-medium text-marca hover:underline"
                >
                  Limpar filtros
                </button>
              )}
              <label
                htmlFor="ordenacao"
                className="flex items-center gap-1.5 text-sm text-suave"
              >
                <SlidersHorizontal className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only sm:not-sr-only">Ordenar por</span>
              </label>
              <select
                id="ordenacao"
                value={ordering}
                onChange={(e) => setOrdering(e.target.value as Ordenacao)}
                className="campo !w-auto !py-1.5 !text-sm"
              >
                {ORDENACOES.map((opcao) => (
                  <option key={opcao.id} value={opcao.id}>
                    {opcao.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {erro && (
          <div className="mx-auto max-w-md rounded-xl border border-red-500/30 bg-red-50 px-4 py-6 text-center dark:bg-red-950/40">
            <p className="mb-4 text-sm text-red-700 dark:text-red-200">{erro}</p>
            <button
              onClick={recarregar}
              className="rounded-full bg-marca px-5 py-2 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {carregando && !erro && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <NeologismCardEsqueleto key={i} />
            ))}
          </div>
        )}

        {!carregando && !erro && itens.length === 0 && (
          <div className="py-20 text-center">
            <p className="font-display text-xl font-bold text-texto">
              Nenhum verbete encontrado
            </p>
            <p className="mx-auto mt-2 max-w-sm text-sm text-suave">
              {temFiltro
                ? "Tente outra palavra ou remova os filtros."
                : "A base ainda está vazia. Que tal enviar a primeira palavra?"}
            </p>
            <div className="mt-6">
              {temFiltro ? (
                <button
                  onClick={limparFiltros}
                  className="rounded-full border border-borda-forte px-5 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta"
                >
                  Limpar filtros
                </button>
              ) : (
                <Link
                  href="/enviar"
                  className="inline-flex rounded-full bg-marca px-5 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90"
                >
                  Enviar um neologismo
                </Link>
              )}
            </div>
          </div>
        )}

        {!carregando && !erro && itens.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {itens.map((neologismo) => (
                <NeologismCard
                  key={neologismo.id}
                  neologismo={neologismo}
                  curtindo={curtindo.has(neologismo.id)}
                  onCurtir={curtir}
                />
              ))}
            </div>

            {temMais && (
              <div className="mt-10 text-center">
                <button
                  onClick={carregarMais}
                  disabled={carregandoMais}
                  className="inline-flex items-center gap-2 rounded-full border border-borda-forte px-6 py-3 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta disabled:opacity-60"
                >
                  {carregandoMais && (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  )}
                  Carregar mais
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}
