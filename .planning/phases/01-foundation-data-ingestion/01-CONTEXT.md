# Phase 1: Foundation & Data Ingestion - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary
This phase establishes the core infrastructure for the project: a local PostgreSQL database and the initial data ingestion scripts for live NSE/BSE stock quotes. It ensures that the system can poll for real-time data and persist it for later analysis.

</domain>

<decisions>
## Implementation Decisions

### Database
- **Provider**: PostgreSQL (Local installation).
- **Schema**: Initial schema should include `stocks` (metadata) and `live_quotes` (real-time price updates).
- **Connection**: Use `psycopg2` or `SQLAlchemy` for Python integration.

### Live Data Ingestion
- **Library**: `nsepython` for NSE data and `bsedata` for BSE data.
- **Polling Strategy**: Polling every 1-5 minutes to avoid rate limiting and maintain a fresh data stream.
- **Stock Selection**: Initial focus on a predefined list of 10 major stocks (e.g., NIFTY 50 top constituents) to validate the pipeline.

### the agent's Discretion
- Exact database connection pooling settings.
- Specific table indexing (though `ticker` and `timestamp` are expected).
- Error handling/retry logic for the scraper.

</decisions>

<canonical_refs>
## Canonical References
- `.planning/PROJECT.md` — Project vision and core value.
- `.planning/REQUIREMENTS.md` — Requirement IDs DATA-01, DATA-04, SYS-02.
- `.planning/research/STACK.md` — Tech stack decisions.

</canonical_refs>

<specifics>
## Specific Ideas
- Use a `docker-compose.yml` file for the local PostgreSQL setup to ensure reproducibility on Windows.
- Implement a simple CLI script `fetch_prices.py` that can be run as a background task.

</specifics>

---
*Phase: 01-foundation-data-ingestion*
*Context gathered: 2026-04-24*
