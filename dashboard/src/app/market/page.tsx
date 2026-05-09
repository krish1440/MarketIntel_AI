import { Metadata } from 'next';
import MarketClient from './MarketClient';

export const metadata: Metadata = {
  title: 'Market Terminal | Live Indian Stock Spectrum',
  description: 'Access real-time data for over 2,300+ NSE/BSE symbols. Monitor price changes, manage your watchlist, and explore institutional-grade stock intelligence.',
  openGraph: {
    title: 'Market Terminal: Live Stock Monitoring',
    description: 'Comprehensive market dashboard for real-time Indian stock analytics.',
    url: 'https://marketintel-ai.vercel.app/market',
  },
  alternates: {
    canonical: '/market',
  },
};

export default function Page() {
  return <MarketClient />;
}
