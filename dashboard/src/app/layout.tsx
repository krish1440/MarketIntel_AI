import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "MarketIntel AI | Total Market Intelligence",
  description: "Production-grade Indian stock market monitoring and prediction platform.",
  icons: {
    icon: "/icon.png",
    shortcut: "/icon.png",
    apple: "/icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <div className="flex-grow">{children}</div>
        <footer className="border-t border-slate-900 bg-slate-950 py-8 text-center">
          <p className="text-slate-500 text-sm tracking-widest font-medium">
            Designed and developed by <Link href="https://portfolio-krish-chaudhary.vercel.app/" target="_blank" className="text-slate-300 font-bold hover:text-indigo-400 transition-colors">Krish Chaudhary</Link>
          </p>
        </footer>
      </body>
    </html>
  );
}
