"use client";

import Link from "next/link";
import Header from "@/components/Header";
import { Users } from "lucide-react";

// Ícones de marca (GitHub/LinkedIn) não existem mais no lucide-react,
// então usamos SVGs inline para manter os logos das redes.
function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M12 .5C5.37.5 0 5.87 0 12.5c0 5.3 3.44 9.8 8.21 11.39.6.11.82-.26.82-.58v-2.03c-3.34.73-4.04-1.61-4.04-1.61-.55-1.39-1.34-1.76-1.34-1.76-1.09-.75.08-.73.08-.73 1.2.09 1.84 1.24 1.84 1.24 1.07 1.83 2.81 1.3 3.5.99.11-.78.42-1.3.76-1.6-2.67-.3-5.47-1.34-5.47-5.95 0-1.31.47-2.39 1.24-3.23-.13-.3-.54-1.52.12-3.17 0 0 1.01-.32 3.3 1.23a11.5 11.5 0 0 1 6 0c2.29-1.55 3.3-1.23 3.3-1.23.66 1.65.25 2.87.12 3.17.77.84 1.23 1.92 1.23 3.23 0 4.62-2.81 5.64-5.49 5.94.43.37.81 1.1.81 2.22v3.29c0 .32.22.69.83.58A12 12 0 0 0 24 12.5C24 5.87 18.63.5 12 .5Z" />
    </svg>
  );
}

function LinkedinIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.07 2.07 0 1 1 0-4.14 2.07 2.07 0 0 1 0 4.14ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.8 0 0 .77 0 1.73v20.54C0 23.22.8 24 1.77 24h20.45c.98 0 1.78-.78 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z" />
    </svg>
  );
}

type Member = {
  name: string;
  role: string;
  bio: string;
  github?: string;
  linkedin?: string;
};

const team: Member[] = [
  {
    name: "João Victor",
    role: "Desenvolvedor Full Stack",
    bio: "Responsável pela arquitetura do projeto, integração entre frontend e API e pela experiência de uso da plataforma.",
    github: "#",
    linkedin: "#",
  },
  {
    name: "Integrante 2",
    role: "Pesquisa & Conteúdo",
    bio: "Cuida da curadoria linguística, dos critérios de moderação e da qualidade do acervo de neologismos.",
    github: "#",
    linkedin: "#",
  },
  {
    name: "Integrante 3",
    role: "Design & Interface",
    bio: "Define a identidade visual, o design das telas e a usabilidade do dicionário colaborativo.",
    github: "#",
    linkedin: "#",
  },
];

export default function EquipePage() {
  return (
    <>
      <Header />

      {/* Hero */}
      <section className="bg-gradient-to-br from-white to-purple-light/20 py-14 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <span className="inline-block text-xs font-bold uppercase tracking-wider text-purple-dark border border-purple-light rounded-full px-4 py-1.5 mb-4">
            Quem faz acontecer
          </span>
          <h1 className="font-sans text-3xl sm:text-4xl font-extrabold text-gray-900 leading-tight mb-3">
            Nossa equipe
          </h1>
          <p className="text-base text-gray-600 max-w-2xl mx-auto">
            O Neoscópio é construído por um time apaixonado pela língua
            portuguesa e pela forma como ela se reinventa todos os dias. Conheça
            quem está por trás do projeto.
          </p>
        </div>
      </section>

      {/* Cards da equipe — mesmo padrão de card da página Sobre */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-14">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {team.map((member) => (
            <div
              key={member.name}
              className="bg-white rounded-2xl border border-gray-200 p-6 text-center"
            >
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-purple-light/30 text-purple-dark mb-4">
                <Users className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-gray-900 mb-1">
                {member.name}
              </h3>
              <p className="text-xs font-semibold uppercase tracking-wide text-purple-dark mb-3">
                {member.role}
              </p>
              <p className="text-sm text-gray-500 leading-relaxed mb-4">
                {member.bio}
              </p>
              <div className="flex items-center justify-center gap-3">
                {member.github && (
                  <a
                    href={member.github}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center w-9 h-9 rounded-full border border-gray-200 text-gray-500 hover:text-purple-dark hover:border-purple-light transition-colors"
                    aria-label={`GitHub de ${member.name}`}
                  >
                    <GithubIcon className="w-4 h-4" />
                  </a>
                )}
                {member.linkedin && (
                  <a
                    href={member.linkedin}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center justify-center w-9 h-9 rounded-full border border-gray-200 text-gray-500 hover:text-purple-dark hover:border-purple-light transition-colors"
                    aria-label={`LinkedIn de ${member.name}`}
                  >
                    <LinkedinIcon className="w-4 h-4" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-gradient-to-br from-white to-purple-light/20 py-14 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-extrabold text-gray-900 mb-3">
            Quer fazer parte?
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            O Neoscópio cresce com a colaboração da comunidade. Contribua com
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
