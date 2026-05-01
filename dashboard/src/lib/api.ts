const API_BASE = "http://localhost:8000/api";

export async function getStocks(page: number = 1, limit: number = 50, search: string = "") {
  const url = new URL(`${API_BASE}/stocks`);
  url.searchParams.append("page", page.toString());
  url.searchParams.append("limit", limit.toString());
  if (search) url.searchParams.append("search", search);
  
  const res = await fetch(url.toString());
  return res.json();
}

export async function getPrediction(ticker: string) {
  const res = await fetch(`${API_BASE}/predict/${ticker}`);
  return res.json();
}

export async function getNews(ticker: string) {
  const res = await fetch(`${API_BASE}/news/${ticker}`);
  return res.json();
}

export async function getHistory(ticker: string) {
  const res = await fetch(`${API_BASE}/history/${ticker}`);
  return res.json();
}

export async function getWatchlist() {
  const res = await fetch(`${API_BASE}/watchlist`);
  return res.json();
}

export async function addToWatchlist(stockId: number, targetAbove?: number, targetBelow?: number, sentimentThreshold: number = 0.7) {
  const url = new URL(`${API_BASE}/watchlist/${stockId}`);
  if (targetAbove !== undefined && targetAbove !== null) url.searchParams.append("target_above", targetAbove.toString());
  if (targetBelow !== undefined && targetBelow !== null) url.searchParams.append("target_below", targetBelow.toString());
  url.searchParams.append("sentiment_threshold", sentimentThreshold.toString());
  
  const res = await fetch(url.toString(), { 
    method: "POST",
    headers: { "Content-Type": "application/json" }
  });
  return res.json();
}



export async function removeFromWatchlist(stockId: number) {
  const res = await fetch(`${API_BASE}/watchlist/${stockId}`, { method: "DELETE" });
  return res.json();
}

export async function getAlerts() {
  const res = await fetch(`${API_BASE}/alerts`);
  return res.json();
}

