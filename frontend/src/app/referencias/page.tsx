"use client";

import Link from "next/link";
import Header from "@/components/Header";
import { BookMarked, ExternalLink } from "lucide-react";

type Reference = {
  authors: string;
  year: string;
  title: string;
  source: string;
  url?: string;
};

// Referências em formato ABNT (autor, ano, título, fonte).
const references: Reference[] = [
  {
    authors: "ALVES, Ieda Maria.",
    year: "2007",
    title: "Neologismo: criação lexical.",
    source: "3. ed. São Paulo: Ática, 2007.",
  },
  {
    authors: "BASÍLIO, Margarida.",
    year: "2004",
    title: "Formação e classes de palavras no português do Brasil.",
    source: "São Paulo: Contexto, 2004.",
  },
  {
    authors: "CARVALHO, Nelly.",
    year: "2009",
    title: "Empréstimos linguísticos na língua portuguesa.",
    source: "São Paulo: Cortez, 2009.",
  },
  {
    authors: "CORREIA, Margarita; ALMEIDA, Gladis Maria de Barcellos.",
    year: "2012",
    title: "Neologia em português.",
    source: "São Paulo: Parábola Editorial, 2012.",
  },
  {
    authors: "HOUAISS, Antônio; VILLAR, Mauro de Salles.",
    year: "2009",
    title: "Dicionário Houaiss da língua portuguesa.",
    source: "Rio de Janeiro: Objetiva, 2009.",
  },
  {
    authors: "ACADEMIA BRASILEIRA DE LETRAS.",
    year: "2021",
    title: "Vocabulário Ortográfico da Língua Portuguesa (VOLP).",
    source: "6. ed. Rio de Janeiro: ABL, 2021.",
    url: "https://www.academia.org.br/nossa-lingua/busca-no-vocabulario",
  },
  {
    authors: "SAUSSURE, Ferdinand de.",
    year: "2006",
    title: "Curso de linguística geral.",
    source: "27. ed. São Paulo: Cultrix, 2006.",
  },
];

export default function ReferenciasPage() {
  return (
    <>
      <Header />

      {/* Hero */}
      <section className="bg-gradient-to-br from-white to-purple-light/20 py-14 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <span className="inline-block text-xs font-bold uppercase tracking-wider text-purple-dark border border-purple-light rounded-full px-4 py-1.5 mb-4">
            Fontes do projeto
          </span>
          <h1 className="font-sans text-3xl sm:text-4xl font-extrabold text-gray-900 leading-tight mb-3">
            Referências bibliográficas
          </h1>
          <p className="text-base text-gray-600 max-w-2xl mx-auto">
            Obras, dicionários e materiais que embasam o trabalho de registro e
            curadoria dos neologismos no Neoscópio. As referências seguem o
            padrão ABNT.
          </p>
        </div>
      </section>

      {/* Lista de referências */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-14">
        <ul className="space-y-4">
          {references.map((ref) => (
            <li
              key={ref.title}
              className="bg-white rounded-2xl border border-gray-200 p-5 flex gap-4"
            >
              <div className="inline-flex items-center justify-center w-10 h-10 shrink-0 rounded-full bg-purple-light/30 text-purple-dark">
                <BookMarked className="w-5 h-5" />
              </div>
              <div className="text-sm text-gray-600 leading-relaxed">
                <span className="font-semibold text-gray-900">
                  {ref.authors}
                </span>{" "}
                <span className="italic">{ref.title}</span> {ref.source}
                {ref.url && (
                  <a
                    href={ref.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 mt-2 text-purple-dark font-medium hover:underline"
                  >
                    Acessar fonte
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-br from-white to-purple-light/20 py-14 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-extrabold text-gray-900 mb-3">
            Conhece outra fonte relevante?
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            O acervo de referências também cresce com a comunidade. Contribua com
            novas palavras e ajude a mapear o português do nosso tempo.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/enviar"
              className="px-5 py-2 text-sm font-semibold text-white bg-purple-dark rounded-full hover:bg-purple-dark transition-colors"
            >
              Enviar uma palavra
            </Link>
            <Link
              href="/sobre"
              className="px-5 py-2 text-sm font-semibold text-purple-dark border border-purple-dark rounded-full hover:bg-purple-light/20 transition-colors"
            >
              Sobre o projeto
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}