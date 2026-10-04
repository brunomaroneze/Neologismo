import Link from "next/link";

export const metadata = { title: "Página não encontrada" };

export default function NaoEncontrado() {
  return (
    <section className="mx-auto flex max-w-md flex-col items-center px-4 py-32 text-center">
      <p className="font-display text-7xl font-black text-marca">404</p>
      <h1 className="mt-4 font-display text-3xl font-black text-texto">
        Essa página não existe
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-suave">
        O endereço pode ter mudado, ou a palavra que você procura ainda não foi
        registrada no banco.
      </p>
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <Link
          href="/"
          className="rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90"
        >
          Ir para o banco
        </Link>
        <Link
          href="/enviar"
          className="rounded-full border border-borda-forte px-6 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta"
        >
          Enviar um neologismo
        </Link>
      </div>
    </section>
  );
}
