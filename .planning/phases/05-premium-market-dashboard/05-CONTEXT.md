# Phase 5: Premium Market Dashboard - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase delivers the user-facing interface: a professional-grade market intelligence dashboard. It transitions the system from a set of scripts to a "Moneycontrol-like" application that visualizes live data and AI-driven signals using a premium design system (Stitch).

</domain>

<decisions>
## Implementation Decisions

### Frontend Stack
- **Framework**: Next.js 14+ (App Router).
- **Styling**: Tailwind CSS (as per modern standards and Stitch compatibility).
- **Icons**: Lucide React.
- **Charts**: Recharts or Lightweight Charts (TradingView).

### UI Design (Stitch)
- **Theme**: "Indigo Midnight" (Dark mode with vibrant primary colors).
- **Layout**: Sidebar navigation, multi-column dashboard.
- **Components**: 
  - Glassmorphic cards for stock summaries.
  - Interactive "Sentiment Gauge".
  - "Signal Badge" (BUY/SELL/HOLD) with confidence pulse animation.

### Backend Integration
- **Framework**: FastAPI (to run alongside the Python data scripts).
- **Endpoints**:
  - `/api/stocks`: List tracked stocks with latest LTP.
  - `/api/predict/{ticker}`: Get signal from `PredictionService`.
  - `/api/news/{ticker}`: Get latest news with sentiment.

</decisions>

<canonical_refs>
## Canonical References
- `.planning/research/FEATURES.md` (Moneycontrol-like feature list)
- `.planning/REQUIREMENTS.md` (DASH-01 to DASH-05)

</canonical_refs>

<specifics>
## Specific Ideas
- Use Stitch `generate_screen_from_text` for the initial landing page.
- Implement a "Live Ticker Tape" at the top of the screen.

</specifics>

---
*Phase: 05-premium-market-dashboard*
*Context gathered: 2026-04-25*
