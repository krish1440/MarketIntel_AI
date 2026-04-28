"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';

export default function LandingPage() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <main className="min-h-screen bg-[#020617] text-slate-50 selection:bg-indigo-500/30 overflow-hidden relative font-sans">
      
      {/* --- ADVANCED BACKGROUND SYSTEM --- */}
      <div className="fixed inset-0 z-[-1]">
        {/* Animated Mesh Gradient */}
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/20 rounded-full blur-[120px] animate-pulse"></div>
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/20 rounded-full blur-[120px] delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay"></div>
      </div>

      {/* --- FLOATING 3D NEURAL SPHERE --- */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 -z-10">
        <div className="w-[500px] h-[500px] rounded-full bg-gradient-to-br from-indigo-500/20 via-purple-500/10 to-transparent blur-3xl animate-spin-slow"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 rounded-full border border-white/5 bg-white/5 backdrop-blur-3xl shadow-[0_0_80px_-20px_rgba(99,102,241,0.5)] flex items-center justify-center">
            <div className="w-32 h-32 bg-indigo-500/20 rounded-full blur-2xl animate-ping"></div>
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-400/20 to-transparent rounded-full"></div>
        </div>
      </div>

      {/* --- STICKY NAV --- */}
      <nav className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${scrolled ? 'bg-slate-950/80 backdrop-blur-xl border-b border-white/5 py-4' : 'py-8'}`}>
        <div className="max-w-7xl mx-auto px-8 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
               <span className="font-black text-xl italic">M</span>
            </div>
            <span className="font-black tracking-tighter text-2xl bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">MarketIntel AI</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
            <Link href="#features" className="hover:text-white transition-colors">Technology</Link>
            <Link href="#spectrum" className="hover:text-white transition-colors">Spectrum</Link>
            <Link href="https://github.com/krish1440/MarketIntel_AI" target="_blank" className="hover:text-white transition-colors">Repository</Link>
            <Link href="/market" className="px-6 py-2 bg-white text-black rounded-full hover:bg-indigo-400 transition-all">Launch</Link>
          </div>
        </div>
      </nav>

      {/* --- HERO SECTION --- */}
      <section className="relative pt-52 pb-32 px-8">
        <div className="max-w-5xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10 text-indigo-400 text-[10px] font-black uppercase tracking-[0.3em] mb-12 shadow-2xl backdrop-blur-md">
            <span className="w-2 h-2 bg-indigo-500 rounded-full animate-pulse shadow-[0_0_8px_#6366f1]"></span>
            Next-Gen Financial Intelligence
          </div>
          
          <h1 className="text-6xl md:text-8xl font-black mb-8 tracking-tighter leading-[0.9] text-white drop-shadow-2xl">
            Total Market <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-purple-300 to-emerald-400">Intelligence.</span>
          </h1>
          
          <p className="max-w-2xl mx-auto text-slate-400 text-lg md:text-xl mb-16 font-medium leading-relaxed">
            Harnessing 5-year historical depth and AI-driven predictive modeling for the entire <span className="text-white underline decoration-indigo-500/50 underline-offset-4">Indian Market Spectrum</span>.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-6">
            <Link 
              href="/market"
              className="w-full sm:w-auto px-10 py-5 bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-black uppercase tracking-widest text-xs rounded-2xl transition-all shadow-[0_20px_50px_-10px_rgba(99,102,241,0.5)] hover:-translate-y-1 active:translate-y-0"
            >
              Enter Global Terminal
            </Link>
            <Link 
              href="https://github.com/krish1440/MarketIntel_AI"
              target="_blank"
              className="w-full sm:w-auto px-10 py-5 bg-white/5 border border-white/10 hover:bg-white/10 text-white font-black uppercase tracking-widest text-xs rounded-2xl transition-all backdrop-blur-md"
            >
              Github Repo
            </Link>
          </div>
        </div>
      </section>

      {/* --- INTERACTIVE TICKER --- */}
      <div className="w-full bg-white/5 border-y border-white/5 py-4 overflow-hidden relative">
        <div className="flex whitespace-nowrap animate-ticker gap-12">
          {['RELIANCE +2.4%', 'TCS -1.2%', 'HDFCBANK +0.8%', 'INFY +3.1%', 'ICICIBANK -0.4%', 'SBIN +1.5%', 'BHARTIARTL +2.2%', 'HINDUNILVR -0.7%'].map((t, i) => (
            <span key={i} className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                <span className={t.includes('+') ? 'text-emerald-400' : 'text-rose-400'}>●</span> {t}
            </span>
          ))}
          {/* Duplicate for seamless loop */}
          {['RELIANCE +2.4%', 'TCS -1.2%', 'HDFCBANK +0.8%', 'INFY +3.1%', 'ICICIBANK -0.4%', 'SBIN +1.5%', 'BHARTIARTL +2.2%', 'HINDUNILVR -0.7%'].map((t, i) => (
            <span key={i} className="text-[10px] font-black uppercase tracking-widest text-slate-400">
                <span className={t.includes('+') ? 'text-emerald-400' : 'text-rose-400'}>●</span> {t}
            </span>
          ))}
        </div>
      </div>

      {/* --- ADVANCED FEATURES SECTION --- */}
      <section id="spectrum" className="py-32 px-8 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-12">
            {[
                { 
                    title: "Real-Time Nexus", 
                    desc: "Multi-threaded polling tracks 2,361+ symbols across NSE/BSE every 60 seconds with sub-second accuracy.",
                    icon: "M13 10V3L4 14h7v7l9-11h-7z",
                    color: "indigo"
                },
                { 
                    title: "Neural Core", 
                    desc: "State-of-the-art LSTM forecasting models trained on 1.6M+ data points for institutional-grade price prediction.",
                    icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0012 18.75c-1.03 0-1.9-.4-2.593-1.1l-.548-.547z",
                    color: "purple"
                },
                { 
                    title: "Total Spectrum", 
                    desc: "5-year comprehensive historical mapping. A massive data foundation for backtesting and long-term intelligence.",
                    icon: "M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4",
                    color: "emerald"
                }
            ].map((f, i) => (
                <div key={i} className="group p-10 rounded-[3rem] bg-white/[0.02] border border-white/5 hover:border-white/10 transition-all hover:bg-white/[0.04] relative">
                    <div className={`w-14 h-14 bg-${f.color}-500/10 rounded-2xl flex items-center justify-center mb-8 border border-${f.color}-500/20 group-hover:scale-110 transition-transform`}>
                        <svg className={`w-7 h-7 text-${f.color}-400`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={f.icon} />
                        </svg>
                    </div>
                    <h3 className="text-2xl font-black mb-4 tracking-tighter">{f.title}</h3>
                    <p className="text-slate-500 text-sm leading-relaxed font-medium">{f.desc}</p>
                </div>
            ))}
        </div>
      </section>

      {/* --- ADD CUSTOM STYLES --- */}
      <style jsx global>{`
        @keyframes ticker {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-ticker {
          animation: ticker 30s linear infinite;
        }
        .animate-spin-slow {
          animation: spin 12s linear infinite;
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

    </main>
  );
}
