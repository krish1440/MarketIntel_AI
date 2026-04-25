const API_BASE = "http://localhost:8000/api";

export async function getStocks() {
  const res = await fetch(`${API_BASE}/stocks`);
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
