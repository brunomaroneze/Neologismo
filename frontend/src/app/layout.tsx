import type { Metadata, Viewport } from "next";
import { Fraunces, Inter } from "next/font/google";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { ToastProvider } from "@/components/Toast";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

// Uma serifada com contraste alto para os títulos: um dicionário ganha em
// parecer um dicionário, e diferencia a marca da fonte de interface.
const fraunces = Fraunces({
  variable: "--font-fraunces",
  subsets: ["latin"],
  display: "swap",
  axes: ["SOFT", "WONK", "opsz"],
});

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Neoscópio — Banco de Neologismos",
    template: "%s · Neoscópio",
  },
  description:
    "Registre, explore e discuta os neologismos que moldam o português do nosso tempo.",
  applicationName: "Neoscópio",
  keywords: [
    "neologismo",
    "dicionário",
    "português brasileiro",
    "linguística",
    "gírias",
  ],
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: siteUrl,
    siteName: "Neoscópio",
    title: "Neoscópio — Banco de Neologismos",
    description:
      "Registre, explore e discuta os neologismos que moldam o português do nosso tempo.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Neoscópio — Banco de Neologismos",
    description:
      "Registre, explore e discuta os neologismos que moldam o português do nosso tempo.",
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#14121a" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="pt-BR"
      className={`${inter.variable} ${fraunces.variable} h-full antialiased`}
    >
      <body className="flex min-h-full flex-col bg-fundo font-sans text-texto">
        <ToastProvider>
          {/* Atalho para quem navega por teclado pular o menu inteiro. */}
          <a
            href="#conteudo"
            className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-marca focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-marca-contraste"
          >
            Pular para o conteúdo
          </a>

          <Header />
          <main id="conteudo" className="flex-1">
            {children}
          </main>
          <Footer />
        </ToastProvider>
      </body>
    </html>
  );
}
