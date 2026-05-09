import { Metadata } from 'next';
import StockDetailClient from './StockDetailClient';

type Props = {
  params: Promise<{ ticker: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const ticker = (await params).ticker;
  
  return {
    title: `${ticker} Analysis & Price Prediction`,
    description: `Deep-dive analysis for ${ticker}. Real-time technical indicators, AI-driven LSTM price forecasting, and bullish/bearish sentiment monitoring for institutional-grade intelligence.`,
    openGraph: {
      title: `${ticker} AI Market Intelligence`,
      description: `Live analytics and future price prediction for ${ticker} on MarketIntel AI.`,
      url: `https://marketintel-ai.vercel.app/stock/${ticker}`,
    },
    alternates: {
      canonical: `/stock/${ticker}`,
    },
  };
}


export default async function Page({ params }: Props) {
  const ticker = (await params).ticker;

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "FinancialService",
    "name": `${ticker} Analysis`,
    "description": `Real-time analytics and price prediction for ${ticker} on the Indian stock market.`,
    "provider": {
      "@type": "Organization",
      "name": "MarketIntel AI"
    },
    "serviceType": "Stock Market Analysis"
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <StockDetailClient />
    </>
  );
}

