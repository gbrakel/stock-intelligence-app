import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Stock Intelligence",
  description: "Daily stock scoring, risk assessment, and signal intelligence",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-gray-950 text-gray-100 min-h-screen`}>
        {/* Navigation */}
        <nav className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-14">
              <Link href="/" className="flex items-center gap-2 font-semibold text-lg">
                <span className="text-blue-400">SI</span>
                <span className="hidden sm:inline text-gray-300">Stock Intelligence</span>
              </Link>
              <div className="flex items-center gap-6 text-sm">
                <Link href="/" className="text-gray-400 hover:text-white transition-colors">
                  Dashboard
                </Link>
                <Link href="/watchlist" className="text-gray-400 hover:text-white transition-colors">
                  Watchlist
                </Link>
                <Link href="/history" className="text-gray-400 hover:text-white transition-colors">
                  History
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Main content */}
        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          {children}
        </main>

        {/* Disclaimer footer */}
        <footer className="border-t border-gray-800 py-4 mt-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <p className="text-xs text-gray-600 text-center">
              This is a research tool for informational purposes only. Not financial advice.
              Past performance does not guarantee future results.
              All signals are probabilistic estimates with inherent uncertainty.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
