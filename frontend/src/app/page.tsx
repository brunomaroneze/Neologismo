"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import Header from "@/components/Header";
import NeologismCard from "@/components/NeologismCard";
import { useNeologismos } from "@/hooks/useNeologismos";
import { Search, Loader2 } from "lucide-react";

const filterCategories = [
  { id: "all", label: "Todos" },
  { id: "Internetês", label: "Internetês" },
  { id: "Anglicismo", label: "Anglicismo" },
  { id: "Comportamento", label: "Comportamento" },
  { id: "Verbalização", label: "Verbalização" },
  { id: "Gíria", label: "Gíria" },
];

export default function Home() {
  const [activeCategory, setActiveCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Aguarda o usuário parar de digitar antes de refazer a busca no servidor.
  useEffect(() => {
    const timeout = setTimeout(() => setDebouncedSearch(searchQuery), 400);
    return () => clearTimeout(timeout);
  }, [searchQuery]);

  const { data, loading, loadingMore, hasMore, error, refetch, loadMore, onLike, onDeslike } =
    useNeologismos({
      search: debouncedSearch || undefined,
      tag: activeCategory === "all" ? undefined : activeCategory,
    });

  const sentinelRef = useRef<HTMLDivElement | null>(null);

  // Dispara o carregamento da próxima página quando o sentinela entra na tela.
  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMore();
        }
      },
      { rootMargin: "200px" }
    );

    observer.observe(node);
    return () => observer.disconnect();
  }, [loadMore]);


  return (
    <>
      <Header />

      <section className="bg-gradient-to-br from-white to-purple-light/20 py-6 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <span className="inline-block text-xs font-bold uppercase tracking-wider text-purple-dark border border-purple-light rounded-full px-4 py-1.5 mb-3">
            Dicionário Colaborativo
          </span>

          <h1 className="font-sans text-3xl sm:text-4xl font-extrabold text-gray-900 leading-tight mb-2">
            O brasileiro deve ser estudado.
            <br />
            As palavras que ele cria também.
          </h1>

          <p className="text-sm text-gray-500 mb-4 max-w-xl mx-auto">
            Registre, explore e discuta os neologismos que moldam o português do nosso tempo.
          </p>

          <div className="flex items-center justify-center gap-3">
            <Link
              href="/enviar"
              className="px-5 py-2 text-sm font-semibold text-white bg-purple-dark rounded-full hover:bg-purple-dark transition-colors"
            >
              Enviar uma palavra
            </Link>
            <a
              href="#explorar"
              className="px-5 py-2 text-sm font-semibold text-purple-dark border border-purple-dark rounded-full hover:bg-purple-light/20 transition-colors"
            >
              Como funciona
            </a>
          </div>
        </div>
      </section>

      <section id="explorar" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="max-w-2xl mx-auto mb-8">
          <div className="relative">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Buscar neologismos, ex: «biscoitar», «cringe»..."
              className="w-full pl-12 pr-4 py-3 bg-white border border-gray-200 rounded-full text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-primary focus:border-transparent"
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-2 mb-10">
          {filterCategories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-4 py-2 text-sm font-medium rounded-full transition-colors ${
                activeCategory === cat.id
                  ? "bg-purple-light text-purple-dark"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {loading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-purple-dark animate-spin" />
          </div>
        )}

        {error && (
          <div className="text-center py-12">
            <p className="text-red-500 text-sm mb-4">{error}</p>
            <button
              onClick={refetch}
              className="px-4 py-2 text-sm font-medium text-white bg-purple-dark rounded-full hover:bg-purple-dark"
            >
              Tentar novamente
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
              {data.map((neologismo) => (
                <NeologismCard
                  key={neologismo.id}
                  neologismo={neologismo}
                  onLike={onLike}
                  onDeslike={onDeslike}
                />
              ))}
            </div>

            {data.length === 0 && (
              <div className="text-center py-16">
                <p className="text-gray-500 text-sm">
                  Nenhum neologismo encontrado para os filtros selecionados.
                </p>
              </div>
            )}

            {/* Sentinela invisível: dispara loadMore quando entra na viewport ao rolar a página. */}
            {hasMore && (
              <div ref={sentinelRef} className="flex items-center justify-center py-10">
                {loadingMore && <Loader2 className="w-6 h-6 text-purple-dark animate-spin" />}
              </div>
            )}
          </>
        )}
      </section>
    </>
  );
}
