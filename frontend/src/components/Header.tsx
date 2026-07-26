"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { LogOut } from "lucide-react";

export default function Header() {
  const pathname = usePathname();
  const { username, isAuthenticated, isAdmin, ready, logout } = useAuth();

  const isActive = (href: string) =>
    href === "/" ? pathname === "/" : pathname.startsWith(href);

  const visibleLinks = [
    { href: "/", label: "Explorar" },
    { href: "/enviar", label: "Enviar Neologismo" },
    { href: "/sobre", label: "Sobre" },
    { href: "/equipe", label: "Equipe" },
    { href: "/referencias", label: "Referências" },
    ...(isAdmin ? [{ href: "/admin-painel", label: "Admin" }] : []),
  ];

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <img src="/logo.png" alt="Neoscópio" className="h-8 w-auto" />
          </Link>

          <nav className="hidden md:flex items-center gap-8">
            {visibleLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`relative text-sm font-medium transition-colors ${
                  isActive(link.href)
                    ? "text-purple-dark"
                    : "text-gray-500 hover:text-purple-dark"
                }`}
              >
                {link.label}
                {isActive(link.href) && (
                  <span className="absolute -bottom-1 left-0 right-0 h-0.5 bg-purple-dark rounded-full" />
                )}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            {ready && isAuthenticated ? (
              <>
                <span className="hidden sm:inline text-sm font-medium text-gray-700">
                  Olá, {username}
                </span>
                <button
                  onClick={logout}
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sair
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden sm:inline-flex items-center px-4 py-1.5 text-sm font-medium text-gray-700 border border-gray-300 rounded-full hover:bg-gray-50 transition-colors"
                >
                  Entrar
                </Link>
                <Link
                  href="/cadastro"
                  className="hidden sm:inline-flex items-center px-4 py-1.5 text-sm font-medium text-white bg-purple-dark rounded-full hover:bg-purple-dark transition-colors"
                >
                  Cadastrar
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
