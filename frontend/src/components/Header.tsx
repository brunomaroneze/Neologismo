"use client";

import { useEffect, useRef, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogOut, Menu, Shield, SquarePen, User, X } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

interface ItemNav {
  href: string;
  label: string;
}

export default function Header() {
  const pathname = usePathname();
  const { username, isAuthenticated, isAdmin, ready, logout } = useAuth();
  // A rota é guardada junto do estado do menu: quando ela muda, o painel
  // fecha no próprio render. Fazer isso num efeito custaria um render extra
  // com o menu ainda aberto por cima da página nova.
  const [menu, setMenu] = useState({ aberto: false, rota: pathname });
  const menuAberto = menu.rota === pathname && menu.aberto;
  if (menu.rota !== pathname) {
    setMenu({ aberto: false, rota: pathname });
  }
  const setMenuAberto = (
    valor: boolean | ((aberto: boolean) => boolean)
  ) =>
    setMenu((atual) => ({
      rota: pathname,
      aberto: typeof valor === "function" ? valor(atual.aberto) : valor,
    }));

  const botaoMenu = useRef<HTMLButtonElement>(null);

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  const links: ItemNav[] = [
    { href: "/", label: "Explorar" },
    { href: "/enviar", label: "Enviar" },
    { href: "/sobre", label: "Sobre" },
    { href: "/equipe", label: "Equipe" },
    { href: "/indicacoes-de-leitura", label: "Indicações de leitura" },
  ];

  const linksSessao: ItemNav[] = [
    ...(isAuthenticated ? [{ href: "/minhas-palavras", label: "Minhas palavras" }] : []),
    ...(isAdmin ? [{ href: "/admin-painel", label: "Moderação" }] : []),
  ];

  // Esc fecha e devolve o foco ao botão; o body trava o scroll enquanto
  // o painel está aberto.
  useEffect(() => {
    if (!menuAberto) return;

    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") {
        // `setMenu` (do useState) é estável; o helper setMenuAberto não é,
        // e entraria na lista de dependências do efeito sem necessidade.
        setMenu((atual) => ({ ...atual, aberto: false }));
        botaoMenu.current?.focus();
      }
    };

    document.addEventListener("keydown", aoTeclar);
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", aoTeclar);
      document.body.style.overflow = overflowAnterior;
    };
  }, [menuAberto]);

  const classeLink = (href: string) =>
    `relative text-sm font-medium transition-colors ${
      isActive(href)
        ? "text-barra-texto"
        : "text-barra-suave hover:text-barra-texto"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-barra-borda bg-barra text-barra-texto">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between gap-4">
          <Link
            href="/"
            className="flex shrink-0 items-center gap-2"
            aria-label="Neoscópio — página inicial"
          >
            <Image
              src="/logo.png"
              alt="Neoscópio"
              width={140}
              height={32}
              priority
              className="h-8 w-auto"
            />
          </Link>

          <nav
            aria-label="Navegação principal"
            className="hidden items-center gap-7 md:flex"
          >
            {[...links, ...linksSessao].map((link) => (
              <Link
                key={link.href}
                href={link.href}
                aria-current={isActive(link.href) ? "page" : undefined}
                className={classeLink(link.href)}
              >
                {link.label}
                {isActive(link.href) && (
                  <span className="absolute -bottom-1.5 left-0 right-0 h-0.5 rounded-full bg-barra-texto" />
                )}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            {/* `ready` evita o piscar entre "Entrar" e o nome do usuário na
                hidratação, já que a sessão só existe no cliente. */}
            {!ready ? (
              <div className="h-8 w-24 rounded-full bg-white/15" aria-hidden="true" />
            ) : isAuthenticated ? (
              <>
                <span className="hidden text-sm font-medium text-barra-suave lg:inline">
                  Olá, <strong className="text-barra-texto">{username}</strong>
                </span>
                <button
                  onClick={logout}
                  className="hidden items-center gap-1.5 rounded-full border border-barra-suave/40 px-4 py-1.5 text-sm font-medium text-barra-texto transition-colors hover:bg-white/10 sm:inline-flex"
                >
                  <LogOut className="h-4 w-4" aria-hidden="true" />
                  Sair
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden items-center rounded-full border border-barra-suave/40 px-4 py-1.5 text-sm font-medium text-barra-texto transition-colors hover:bg-white/10 sm:inline-flex"
                >
                  Entrar
                </Link>
                <Link
                  href="/cadastro"
                  className="hidden items-center rounded-full bg-white px-4 py-1.5 text-sm font-semibold text-marca transition-opacity hover:opacity-90 sm:inline-flex"
                >
                  Cadastrar-se
                </Link>
              </>
            )}

            <button
              ref={botaoMenu}
              onClick={() => setMenuAberto((aberto) => !aberto)}
              aria-expanded={menuAberto}
              aria-controls="menu-mobile"
              aria-label={menuAberto ? "Fechar menu" : "Abrir menu"}
              className="inline-flex items-center justify-center rounded-lg p-2 text-barra-texto transition-colors hover:bg-white/10 md:hidden"
            >
              {menuAberto ? (
                <X className="h-5 w-5" aria-hidden="true" />
              ) : (
                <Menu className="h-5 w-5" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Painel mobile. Antes desta versão não havia navegação alguma abaixo
          de 768px: todos os links estavam em `hidden md:flex`. */}
      {menuAberto && (
        <>
          <div
            className="fixed inset-0 top-16 z-30 bg-black/30 md:hidden"
            onClick={() => setMenuAberto(false)}
            aria-hidden="true"
          />
          <nav
            id="menu-mobile"
            aria-label="Navegação principal"
            className="animate-surgir absolute inset-x-0 top-16 z-40 border-b border-borda bg-superficie px-4 pb-6 pt-2 shadow-lg md:hidden"
          >
            <ul className="flex flex-col">
              {links.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    aria-current={isActive(link.href) ? "page" : undefined}
                    className={`block rounded-lg px-3 py-3 text-base font-medium transition-colors ${
                      isActive(link.href)
                        ? "bg-marca-suave text-marca"
                        : "text-texto hover:bg-superficie-alta"
                    }`}
                  >
                    {link.label}
                  </Link>
                </li>
              ))}

              {linksSessao.length > 0 && (
                <li className="my-2 border-t border-borda" aria-hidden="true" />
              )}

              {linksSessao.map((link) => (
                <li key={link.href}>
                  <Link
                    href={link.href}
                    aria-current={isActive(link.href) ? "page" : undefined}
                    className={`flex items-center gap-2 rounded-lg px-3 py-3 text-base font-medium transition-colors ${
                      isActive(link.href)
                        ? "bg-marca-suave text-marca"
                        : "text-texto hover:bg-superficie-alta"
                    }`}
                  >
                    {link.href === "/admin-painel" ? (
                      <Shield className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <SquarePen className="h-4 w-4" aria-hidden="true" />
                    )}
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>

            <div className="mt-4 border-t border-borda pt-4">
              {isAuthenticated ? (
                <div className="flex items-center justify-between gap-3">
                  <span className="flex items-center gap-2 text-sm text-suave">
                    <User className="h-4 w-4" aria-hidden="true" />
                    {username}
                  </span>
                  <button
                    onClick={logout}
                    className="inline-flex items-center gap-1.5 rounded-full border border-borda-forte px-4 py-2 text-sm font-medium text-suave transition-colors hover:bg-superficie-alta"
                  >
                    <LogOut className="h-4 w-4" aria-hidden="true" />
                    Sair
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  <Link
                    href="/login"
                    className="rounded-full border border-borda-forte px-4 py-2.5 text-center text-sm font-medium text-texto transition-colors hover:bg-superficie-alta"
                  >
                    Entrar
                  </Link>
                  <Link
                    href="/cadastro"
                    className="rounded-full bg-marca px-4 py-2.5 text-center text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90"
                  >
                    Cadastrar-se
                  </Link>
                </div>
              )}
            </div>
          </nav>
        </>
      )}
    </header>
  );
}
