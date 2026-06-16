import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
  display: "swap",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "AI Code Migration Agent — .NET to Java",
    template: "%s | AI Code Migration Agent",
  },
  description:
    "Migrate enterprise .NET codebases to Java using Gemini 2.5 Flash, RAG, LangGraph, ChromaDB, and MCP.",
  keywords: ["code migration", ".NET", "Java", "AI", "LLM", "Gemini", "RAG", "LangGraph"],
  authors: [{ name: "Code Migration Agent" }],
  openGraph: {
    type: "website",
    title: "AI Code Migration Agent",
    description: "AI-powered .NET to Java migration using RAG and LLM agents.",
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen`}
      >
        <ThemeProvider defaultTheme="dark" storageKey="cma-theme">
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
