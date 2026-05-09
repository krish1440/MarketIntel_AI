/**
 * MarketIntel AI: Root Layout
 * ==========================
 * 
 * Defines the foundational UI structure for the dashboard, including 
 * global styles, typography (Geist), and the persistent notification 
 * engine.
 */
import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import NotificationCenter from "./components/NotificationCenter";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const viewport: Viewport = {
  themeColor: "#020617",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL("https://marketintel-ai.vercel.app"),
  title: {
    default: "MarketIntel AI | Total Market Intelligence",
    template: "%s | MarketIntel AI",
  },
  description: "Advanced Indian stock market monitoring and AI-driven prediction platform. Harness institutional-grade analytics for NSE/BSE symbols with LSTM forecasting.",
  keywords: ["stock market", "AI prediction", "NSE", "BSE", "Indian stocks", "algorithmic trading", "financial intelligence", "LSTM forecasting", "market monitoring"],
  authors: [{ name: "Krish Chaudhary", url: "https://krish-chaudhary.me/" }],
  creator: "Krish Chaudhary",
  publisher: "Krish Chaudhary",
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  openGraph: {
    type: "website",
    locale: "en_IN",
    url: "https://marketintel-ai.vercel.app",
    siteName: "MarketIntel AI",
    title: "MarketIntel AI | Advanced Stock Intelligence",
    description: "Production-grade Indian stock market monitoring and prediction platform using Deep Learning.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "MarketIntel AI Dashboard",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "MarketIntel AI | Total Market Intelligence",
    description: "Advanced AI-driven stock prediction for the Indian Market.",
    creator: "@krish_chaudhary",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
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
        <NotificationCenter />
        <footer className="border-t border-slate-900 bg-slate-950 py-8 text-center">
          <p className="text-slate-500 text-sm tracking-widest font-medium">
            Designed and developed by <Link href="https://portfolio-krish-chaudhary.vercel.app/" target="_blank" className="text-slate-300 font-bold hover:text-indigo-400 transition-colors">Krish Chaudhary</Link>
          </p>
        </footer>
      </body>
    </html>
  );
}

