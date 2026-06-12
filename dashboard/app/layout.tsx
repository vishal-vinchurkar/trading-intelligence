import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Trading Intelligence",
  description:
    "Multi-agent equity analysis — two isolated analysts, one arbitrator. Experimental research tooling, not financial advice.",
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
            <Link href="/" className="flex items-baseline gap-2">
              <span className="font-mono text-lg font-bold tracking-tight">
                trading-intelligence
              </span>
              <span className="text-xs text-muted">US · India</span>
            </Link>
            <span className="text-xs text-muted">free-tier models · $0 inference</span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        <footer className="mx-auto max-w-6xl px-6 py-10 text-xs text-muted">
          Two AI analysts run in parallel — one blind to fundamentals, one blind to
          price — and a larger model arbitrates the final verdict. Experimental
          research tooling. Not financial advice.
        </footer>
      </body>
    </html>
  );
}
