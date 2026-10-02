import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Mesmo alias do tsconfig: os módulos importam "@/lib/api".
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  test: {
    // jsdom porque `lib/api.ts` fala com localStorage e com window.
    environment: "jsdom",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      // `hooks` entra na medição mesmo sem teste nenhum ainda: tirá-lo daqui
      // deixaria o número bonito e esconderia a lacuna. Testá-los exige
      // @testing-library/react — está anotado como pendência no README.
      //
      // Sem limite mínimo de propósito: o piso existe no backend, onde está
      // a lógica de permissão e moderação. Aqui o número serve para
      // acompanhar, e um piso agora só travaria PRs sem melhorar nada.
      include: ["src/lib/**", "src/hooks/**"],
    },
  },
});
