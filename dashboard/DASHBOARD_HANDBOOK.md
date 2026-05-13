# 🖥️ MarketIntel AI: Dashboard Handbook
**Layer: Presentation & Real-Time Visualization**

The dashboard is a high-performance Next.js application built to provide institutional-grade visualization of market signals, sentiment trends, and predictive analytics.

---

## 🏛️ Technical Stack
*   **Framework**: Next.js 15 (App Router).
*   **Styling**: TailwindCSS with custom glassmorphism and motion variants.
*   **State Management**: React Hooks + Server Components for data fetching.
*   **Real-Time**: 30-second background polling synchronized with the backend ingestion heartbeat.
*   **Institutional Layout**: Optimized 3-column grid for high-density information display.

---

## 🏛️ Institutional Terminal V2 Standards
- **Full-Name Priority**: The UI is configured to prioritize the verified company name (e.g., 'Tata Consultancy Services Limited') as the primary H1/H2 element, with ticker symbols demoted to sub-labels.
- **Dynamic Title Sync**: The browser tab title dynamically updates with the company name once the neural signal is loaded, improving the multi-tab research experience.
- **30s Pulse**: Both the Market and Detail pages implement background polling to ensure prices, neural signals, and news stay fresh without manual reloads.
- **Hydration Resilience**: Uses `mounted` state checks and `suppressHydrationWarning` to ensure zero-crash performance during SSR.

---

## 🏗️ Folder Structure

### `/src/app`
The core of the application.
*   **`page.tsx`**: The main terminal landing page. Features the global market status and hero sections.
*   **`layout.tsx`**: Manages the persistent viewport, typography, and background notification listeners.
*   **`/stock/[ticker]`**: Dynamic route for deep-dive analysis of individual equities.
*   **`/market`**: Broad market overview and NSE/BSE performance tracking.

### `/src/components`
Reusable UI components designed with modern aesthetics:
*   **`NotificationCenter`**: An asynchronous listener that displays triggered alerts to the user.
*   **`PriceChart`**: Interactive time-series visualization using high-alpha palettes.
*   **`SentimentCard`**: Displays AI sentiment scores with color-coded bullish/bearish indicators.

### `/src/lib`
*   **`api.ts`**: Centralized Axios/Fetch client for communicating with the FastAPI backend.
*   **`utils.ts`**: Data formatting helpers for currency and percentage calculations.

---

## 🚀 Development Workflow
To start the dashboard in isolation:
1. `cd dashboard`
2. `npm install`
3. `npm run dev`

Access the UI at `http://localhost:3000`.

---
*Maintained by MarketIntel AI UX Engineering.*
