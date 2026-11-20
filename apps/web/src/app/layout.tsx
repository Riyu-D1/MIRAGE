import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";

import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "MIRAGE — Merchant X-Ray & KYB Lie-Detector",
  description:
    "Visual adversarial merchant forensics: dual-persona cloaking detection, DOM prompt-injection X-ray, sleeper watch, and zero-LLM regulator replay.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen bg-obsidian font-sans text-ink-primary antialiased">
        {children}
      </body>
    </html>
  );
}
