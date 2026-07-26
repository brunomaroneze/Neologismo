"use client";

import Link from "next/link";
import Header from "@/components/Header";
import {
  Sparkles,
  BookOpen,
  Users,
  Search,
  MessageSquare,
  ShieldCheck,
} from "lucide-react";

const steps = [
  {
    icon: BookOpen,
    title: "Registre",
    text: "Cadastre uma palavra nova com definição, classe gramatical, exemplos de uso e até citações com fonte.",
  },
  {
    icon: Search,
    title: "Explore",
    text: "Navegue e pesquise pelos neologismos já registrados, filtrando por categorias como internetês, anglicismo e gíria.",
  },
  {
    icon: MessageSquare,
    title: "Discuta",
    text: "Curta, comente e ajude a comunidade a entender como e onde cada palavra está sendo usada.",
  },
];

const goals = [
  {
    icon: Users,
    title: "Linguagem viva",
    text: "Tratar o português como ele realmente é: uma língua viva, moldada todos os dias por quem fala.",
  },
  {
    icon: ShieldCheck,
    title: "Registro confiável",
    text: "Cada sugestão passa por moderação antes de ser publicada, garantindo qualidade e seriedade ao acervo.",
  },
  {
    icon: Sparkles,
    title: "Colaboração aberta",
    text: "Qualquer pessoa pode contribuir. O dicionário cresce com a participação de toda a comunidade.",
  },
];

export default function SobrePage() {
  return (
    <>
      <Header />

      {/* Hero */}
      <section className="bg-gradient-to-br from-white to-purple-light/20 py-14 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <span className="inline-block text-xs font-bold uppercase tracking-wider text-purple-dark border border-purple-light rounded-full px-4 py-1.5 mb-4">
            Sobre o projeto
          </span>
          <h1 className="font-sans text-3xl sm:text-4xl font-extrabold text-gray-900 leading-tight mb-3">
            O que é um neologismo?
          </h1>
          <p className="text-base text-gray-600 max-w-2xl mx-auto">
            Neologismo é toda palavra, expressão ou sentido novo que surge e
            passa a circular em uma língua. São as palavras que a sociedade
            inventa para nomear o que ainda não tinha nome — ou para dizer de um
            jeito novo o que já existia.
          </p>
        </div>
      </section>

      {/* Definição mais detalhada */}
      <section className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
        <div className="prose-none space-y-5 text-gray-600 leading-relaxed">
          <p>
            A língua portuguesa está em constante transformação. A cada dia, nas
            redes sociais, nas conversas de rua, na música e na cultura digital,
            surgem palavras novas que descrevem comportamentos, sentimentos e
            fenômenos do nosso tempo. Termos como{" "}
            <span className="font-semibold text-purple-dark">«biscoitar»</span>,{" "}
            <span className="font-semibold text-purple-dark">«cringe»</span> ou{" "}
            <span className="font-semibold text-purple-dark">«crush»</span> são
            exemplos de neologismos que entraram no vocabulário cotidiano sem
            pedir licença aos dicionários tradicionais.
          </p>
          <p>
            O problema é que essas criações linguísticas costumam nascer e
            circular de forma dispersa, sem nenhum registro organizado. Muitas
            desaparecem antes mesmo de serem documentadas; outras se consolidam,
            mas ninguém sabe ao certo de onde vieram ou o que realmente
            significam.
          </p>
        </div>
      </section>

      {/* A proposta */}
      <section className="bg-purple-light/10 py-14 px-4">
        <div className="max-w-3xl mx-auto text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-gray-900 mb-3">
            A proposta do Neoscópio
          </h2>
          <p className="text-base text-gray-600 max-w-2xl mx-auto">
            O <span className="font-semibold text-purple-dark">Neoscópio</span>{" "}
            é um dicionário colaborativo dedicado a registrar, explorar e
            discutir os neologismos que moldam o português do nosso tempo. A
            ideia é simples: dar um lugar para as palavras que o brasileiro cria
            todos os dias.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto">
          {steps.map((step) => (
            <div
              key={step.title}
              className="bg-white rounded-2xl border border-gray-200 p-6 text-center"
            >
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-purple-light/30 text-purple-dark mb-4">
                <step.icon className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-2">
                {step.title}
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                {step.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* Por que isso importa */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-14">
        <div className="max-w-3xl mx-auto text-center mb-10">
          <h2 className="text-2xl sm:text-3xl font-extrabold text-gray-900 mb-3">
            Por que isso importa
          </h2>
          <p className="text-base text-gray-600 max-w-2xl mx-auto">
            Documentar neologismos é documentar a própria evolução cultural. As
            palavras que criamos contam a história de quem somos.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {goals.map((goal) => (
            <div key={goal.title} className="flex flex-col gap-3">
              <div className="inline-flex items-center justify-center w-11 h-11 rounded-xl bg-purple-light/30 text-purple-dark">
                <goal.icon className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-gray-900">{goal.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                {goal.text}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-br from-white to-purple-light/20 py-14 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-extrabold text-gray-900 mb-3">
            Faça parte deste registro
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            Conhece uma palavra nova que ainda não está aqui? Contribua e ajude a
            mapear o português do nosso tempo.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/enviar"
              className="px-5 py-2 text-sm font-semibold text-white bg-purple-dark rounded-full hover:bg-purple-dark transition-colors"
            >
              Enviar uma palavra
            </Link>
            <Link
              href="/"
              className="px-5 py-2 text-sm font-semibold text-purple-dark border border-purple-dark rounded-full hover:bg-purple-light/20 transition-colors"
            >
              Explorar neologismos
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
