import Link from "next/link";

const colunas = [
  {
    titulo: "Explorar",
    itens: [
      { href: "/", label: "Todos os verbetes" },
      { href: "/enviar", label: "Enviar um neologismo" },
    ],
  },
  {
    titulo: "O projeto",
    itens: [
      { href: "/sobre", label: "Sobre" },
      { href: "/equipe", label: "Equipe" },
      { href: "/indicacoes-de-leitura", label: "Indicações de leitura" },
    ],
  },
];

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-borda bg-fundo-sutil">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <p className="font-display text-lg font-bold text-texto">Neoscópio</p>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-suave">
              Dicionário colaborativo dos neologismos que moldam o português
              brasileiro do nosso tempo. Cada verbete passa por moderação antes
              de ser publicado.
            </p>
          </div>

          {colunas.map((coluna) => (
            <nav key={coluna.titulo} aria-label={coluna.titulo}>
              <h2 className="text-xs font-bold uppercase tracking-wider text-tenue">
                {coluna.titulo}
              </h2>
              <ul className="mt-3 space-y-2">
                {coluna.itens.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="text-sm text-suave transition-colors hover:text-marca"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
          ))}
        </div>

        <div className="mt-10 flex flex-col gap-2 border-t border-borda pt-6 text-xs text-tenue sm:flex-row sm:items-center sm:justify-between">
          <p>
            © {new Date().getFullYear()} Neoscópio — projeto de iniciação
            científica.
          </p>
          <p>Feito com pesquisa, código aberto e muita palavra nova.</p>
        </div>
      </div>
    </footer>
  );
}
