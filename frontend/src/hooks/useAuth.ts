"use client";

import { useCallback, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import {
  getIsAdmin,
  getToken,
  getUsername,
  logout as apiLogout,
} from "@/lib/api";

/**
 * A sessão vive no localStorage, que é um estado externo ao React. Ler isso
 * com useEffect + useState causa um render em cascata e um piscar entre
 * "deslogado" e "logado"; `useSyncExternalStore` é a API feita para o caso e
 * ainda entrega um snapshot estável para o servidor.
 */
function inscrever(aoMudar: () => void) {
  window.addEventListener("auth-change", aoMudar);
  // `storage` cobre o caso de a pessoa entrar ou sair em outra aba.
  window.addEventListener("storage", aoMudar);
  return () => {
    window.removeEventListener("auth-change", aoMudar);
    window.removeEventListener("storage", aoMudar);
  };
}

// O snapshot precisa ser uma string: devolver um objeto novo a cada leitura
// faria o useSyncExternalStore entrar em loop de re-render.
function lerSnapshot(): string {
  const token = getToken();
  if (!token) return "";
  return `${getUsername() ?? ""}|${getIsAdmin()}`;
}

// Sentinela: distingue "ainda não li o storage" (render do servidor e
// hidratação) de "li e não há sessão" (string vazia). Sem essa diferença,
// páginas protegidas redirecionariam para a home no primeiro render, antes
// de o cliente conseguir ler o token.
const NAO_LIDO = "\u0000";

function snapshotDoServidor(): string {
  return NAO_LIDO;
}

export function useAuth() {
  const router = useRouter();
  const snapshot = useSyncExternalStore(
    inscrever,
    lerSnapshot,
    snapshotDoServidor
  );

  const ready = snapshot !== NAO_LIDO;
  const [username, admin] =
    ready && snapshot ? snapshot.split("|") : [null, "false"];

  const logout = useCallback(async () => {
    await apiLogout();
    router.push("/");
  }, [router]);

  return {
    username: username || null,
    isAuthenticated: ready && !!snapshot,
    isAdmin: admin === "true",
    ready,
    logout,
  };
}
