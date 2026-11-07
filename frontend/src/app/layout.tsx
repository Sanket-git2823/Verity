import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { TooltipProvider } from "@/components/ui/tooltip";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Verity — RAG Research Platform",
  description: "Institutional-grade retrieval-augmented generation research platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans`}>
        <TooltipProvider delayDuration={200}>
          <Sidebar />
          <main className="ml-48 min-h-screen">{children}</main>
        </TooltipProvider>
      </body>
    </html>
  );
}
