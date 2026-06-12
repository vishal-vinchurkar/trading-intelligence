import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sovian — quant signals",
  description:
    "Deterministic quant conviction scores for US & India equities, backtested over 10 years. Experimental research tooling, not financial advice.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <header className="border-b border-border">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-7 w-7 items-center justify-center rounded-md bg-accent/15 font-mono text-sm font-bold text-accent">
                S
              </span>
              <span className="text-lg font-semibold tracking-tight">Sovian</span>
              <span className="text-xs text-muted">quant signals · US · India</span>
            </Link>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
