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
