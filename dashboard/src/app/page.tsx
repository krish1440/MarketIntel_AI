import { Metadata } from 'next';
import LandingPageClient from './LandingPageClient';

export const metadata: Metadata = {
  title: 'Total Market Intelligence | AI-Powered Stock Monitoring',
  description: 'Harnessing 5-year historical depth and AI-driven predictive modeling for the entire Indian Market Spectrum. Real-time NSE/BSE analytics and institutional-grade forecasting.',
  openGraph: {
    title: 'MarketIntel AI: Total Market Intelligence',
    description: 'Advanced AI-driven stock prediction and monitoring for the Indian equity market.',
    url: 'https://marketintel-ai.vercel.app',
  },
  alternates: {
    canonical: '/',
  },
};

export default function Page() {
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "MarketIntel AI",
    "url": "https://marketintel-ai.vercel.app",
    "logo": "https://marketintel-ai.vercel.app/icon.png",
    "sameAs": [
      "https://github.com/krish1440/MarketIntel_AI"
    ],
    "description": "Production-grade Indian stock market monitoring and prediction platform."
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <LandingPageClient />
    </>
  );
}

