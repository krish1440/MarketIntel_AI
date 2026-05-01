"use client";

import { useEffect, useState } from 'react';
import { getAlerts } from '@/lib/api';

export default function NotificationCenter() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [hasNew, setHasNew] = useState(false);

  useEffect(() => {
    // Request notification permission on mount
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }

    const fetchAlerts = async () => {
      try {
        const data = await getAlerts();
        
        // If there are new alerts since last fetch, trigger a system notification
        if (alerts.length > 0 && data.length > 0 && data[0].id !== alerts[0].id) {
          setHasNew(true);
          const newAlert = data[0];
          
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification(`MarketIntel Alert: ${newAlert.ticker}`, {
              body: newAlert.message,
              icon: '/icon.png'
            });
          }
        }
        
        setAlerts(data);
      } catch (err) {
        console.error("Failed to fetch alerts:", err);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, [alerts]);

  return (
    <div className="fixed bottom-8 right-8 z-50">
      <button 
        onClick={() => { setIsOpen(!isOpen); setHasNew(false); }}
        className={`p-4 rounded-full shadow-2xl transition-all hover:scale-110 active:scale-95 border border-slate-800 ${hasNew ? 'bg-indigo-600 animate-pulse' : 'bg-slate-900'}`}
      >
        <div className="relative">
          <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          {hasNew && <span className="absolute top-0 right-0 block h-2.5 w-2.5 rounded-full bg-rose-500 ring-2 ring-slate-900" />}
        </div>
      </button>

      {isOpen && (
        <div className="absolute bottom-20 right-0 w-80 max-h-96 bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col backdrop-blur-2xl bg-opacity-95">
          <div className="p-4 border-b border-slate-800 flex justify-between items-center bg-slate-900/50">
            <h3 className="font-bold text-sm uppercase tracking-widest text-slate-400">Market Alerts</h3>
            <span className="text-[10px] bg-indigo-500/20 text-indigo-400 px-2 py-0.5 rounded-full font-bold">LIVE</span>
          </div>
          
          <div className="overflow-y-auto flex-1 custom-scrollbar">
            {alerts.length === 0 ? (
              <div className="p-8 text-center text-slate-600 text-xs italic">
                No alerts detected. Monitoring market activity...
              </div>
            ) : (
              alerts.map((alert) => (
                <div key={alert.id} className="p-4 border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                  <div className="flex justify-between items-start mb-1">
                    <span className="text-indigo-400 font-bold text-xs">{alert.ticker}</span>
                    <span className="text-[9px] text-slate-500">{new Date(alert.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-relaxed">{alert.message}</p>
                </div>
              ))
            )}
          </div>
          
          <div className="p-3 bg-slate-950 text-center border-t border-slate-800">
            <button className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors uppercase font-bold tracking-tighter">Clear All History</button>
          </div>
        </div>
      )}
      
    </div>
  );
}

