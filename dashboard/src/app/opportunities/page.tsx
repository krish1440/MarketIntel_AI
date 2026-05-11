import OpportunitiesClient from './OpportunitiesClient';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

export const metadata = {
  title: 'Top Swing Opportunities | MarketIntel AI',
  description: 'AI-curated high-conviction trading setups for institutional swing traders.',
};

export default function OpportunitiesPage() {
  return (
    <main className="min-h-screen bg-[#0a0b10] text-white">
      <div className="max-w-[1600px] mx-auto px-6 py-12">
        <header className="mb-16">
          <Link 
            href="/market" 
            className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full text-xs font-bold text-slate-400 hover:text-white hover:bg-white/10 hover:border-blue-500/50 transition-all mb-8 group"
          >
            <ArrowLeft className="w-3 h-3 group-hover:-translate-x-1 transition-transform" />
            Back to Terminal
          </Link>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-2 h-10 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full animate-pulse shadow-[0_0_20px_rgba(59,130,246,0.5)]" />
            <h1 className="text-5xl font-black tracking-tighter bg-gradient-to-r from-white via-white to-slate-500 bg-clip-text text-transparent">
              Market Intelligence <span className="text-blue-500 font-light italic">Alpha</span>
            </h1>
          </div>
          <p className="text-slate-400 text-xl font-medium max-w-3xl leading-relaxed">
            Scanning <span className="text-white font-bold">2,300+</span> symbols with neural confluence. 
            surfacing the highest probability <span className="text-indigo-400">swing setups</span> for the next 20 sessions.
          </p>
        </header>

        <OpportunitiesClient />
      </div>
    </main>
  );
}
