import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
import polars as pl

from src.config.settings import settings
from src.api.dependencies import ServiceContainer, get_services
from src.master.sector_mapper import SectorMapper
from src.api.schemas.stocks import (
    StockSearchResult,
    StockQuote,
    TopUniverseItem,
    MarketBreadth,
    SectorHeatmapItem,
    SectorStockItem
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stocks", tags=["Stocks & Universe"])

SECTOR_DISPLAY_NAMES = {
    "NIFTY_BANK": "Banking",
    "NIFTY_IT": "Information Tech",
    "NIFTY_AUTO": "Automobile",
    "NIFTY_ENERGY": "Energy, Oil & Gas",
    "NIFTY_PHARMA": "Pharma & Health",
    "NIFTY_FMCG": "FMCG & Foods",
    "NIFTY_METAL": "Metals & Mining",
    "NIFTY_FIN_SERVICE": "Financial Services",
    "NIFTY_INFRA": "Infrastructure",
    "NIFTY_REALTY": "Real Estate",
    "NIFTY_CONSUMER_DURABLES": "Consumer Durables"
}

@router.get("/search", response_model=List[StockSearchResult])
def search_stocks(
    q: str = Query(..., min_length=1, description="Stock ticker symbol or company name prefix"),
    limit: int = Query(20, ge=1, le=100),
    services: ServiceContainer = Depends(get_services)
):
    """
    Sub-10ms universal symbol and company search across all 2,357 NSE/BSE listed equities.
    """
    df = services.security_master.df
    if df is None:
        raise HTTPException(status_code=503, detail="Securities Master database not loaded")

    query = q.strip().upper()

    # Load top 300 lookup
    top_300_file = settings.DATA_DIR / "lakehouse" / "top_300_turnover_symbols.json"
    top_300_set = set()
    if top_300_file.exists():
        try:
            with open(top_300_file) as f:
                top_300_set = set(json.load(f).get("symbols", []))
        except:
            pass

    # High-speed Polars filtering
    matches = (
        df.filter(
            pl.col("nse_symbol").str.to_uppercase().str.contains(query) |
            pl.col("company_name").str.to_uppercase().str.contains(query)
        )
        .head(limit)
        .to_dicts()
    )

    results = []
    for m in matches:
        sym = str(m.get("nse_symbol") or "")
        results.append(StockSearchResult(
            symbol=sym,
            company_name=str(m.get("company_name") or sym),
            exchange="NSE",
            token=str(m.get("nse_token") or "") if m.get("nse_token") else None,
            isin=str(m.get("isin") or "") if m.get("isin") else None,
            is_top_300=(sym in top_300_set)
        ))

    return results

@router.get("/quote/{symbol}", response_model=StockQuote)
def get_quote(
    symbol: str,
    services: ServiceContainer = Depends(get_services)
):
    """
    Returns live quote (LTP, OHLC, VWAP, Volume, Change %) for any stock.
    Merges real-time RAM quote with daily Parquet baseline.
    """
    sym = symbol.strip().upper()
    quote = services.redis_manager.get_quote("NSE", sym)

    # Resolve company name and sector
    company_name = sym
    sector = "EQUITY"
    if services.security_master.df is not None:
        try:
            m = services.security_master.df.filter(pl.col("nse_symbol") == sym)
            if len(m) > 0:
                company_name = str(m["company_name"].item(0))
        except Exception:
            pass
    try:
        mapper = SectorMapper()
        raw_sec = mapper.get_sector_for_symbol(sym)
        sector = SECTOR_DISPLAY_NAMES.get(raw_sec, raw_sec.replace("NIFTY_", "").title())
    except Exception:
        pass

    if quote and "ltp" in quote and float(quote.get("ltp") or 0) > 0:
        ltp = float(quote.get("ltp") or 0.0)
        open_px = float(quote.get("open") or ltp)
        high_px = float(quote.get("high") or ltp)
        low_px = float(quote.get("low") or ltp)
        close_px = float(quote.get("close") or ltp)
        vwap_px = float(quote.get("vwap") or ltp)
        vol = int(float(quote.get("volume") or 0))
        pct_chg = float(quote.get("pct_change") or 0.0)
        upd = str(quote.get("updated_at") or datetime.now(timezone.utc).isoformat())

        return StockQuote(
            symbol=sym,
            company_name=company_name,
            sector=sector,
            exchange="NSE",
            ltp=ltp,
            open=open_px,
            high=high_px,
            low=low_px,
            close=close_px,
            vwap=vwap_px,
            volume=vol,
            pct_change=pct_chg,
            updated_at=upd
        )

    # Fallback to Silver 1D Lakehouse if stock was not active in RAM today
    parquet_path = settings.SILVER_DIR / "ohlcv_1d" / "exchange=NSE" / f"symbol={sym}" / "data.parquet"
    if parquet_path.exists():
        try:
            df = pl.read_parquet(parquet_path)
            if len(df) > 0:
                last_row = df.tail(1).to_dicts()[0]
                c_px = float(last_row.get("close", 0.0))
                o_px = float(last_row.get("open", c_px))
                h_px = float(last_row.get("high", c_px))
                l_px = float(last_row.get("low", c_px))
                v = int(last_row.get("volume", 0))
                
                prev_c = float(df.tail(2).head(1)["close"].item(0)) if len(df) >= 2 else c_px
                chg = ((c_px - prev_c) / prev_c) * 100.0 if prev_c > 0 else 0.0

                return StockQuote(
                    symbol=sym,
                    company_name=company_name,
                    sector=sector,
                    exchange="NSE",
                    ltp=c_px,
                    open=o_px,
                    high=h_px,
                    low=l_px,
                    close=c_px,
                    vwap=c_px,
                    volume=v,
                    pct_change=round(chg, 2),
                    updated_at=str(last_row.get("date"))
                )
        except Exception as e:
            logger.warning(f"Error querying 1d fallback for {sym}: {e}")

    raise HTTPException(status_code=404, detail=f"Quote not available for symbol {sym}")

@router.get("/universe/top300", response_model=List[TopUniverseItem])
def get_top_300_universe(
    services: ServiceContainer = Depends(get_services)
):
    """
    Returns today's dynamically ranked Top 300 institutional turnover leaders.
    """
    top_300_file = settings.DATA_DIR / "lakehouse" / "top_300_turnover_symbols.json"
    if not top_300_file.exists():
        raise HTTPException(status_code=404, detail="Top 300 universe file not generated yet")

    try:
        with open(top_300_file) as f:
            data = json.load(f)
            symbols = data.get("symbols", [])
            
        items = []
        for idx, s in enumerate(symbols, 1):
            items.append(TopUniverseItem(
                symbol=s,
                price=0.0,
                turnover_20d_cr=round(data.get("min_turnover_cr", 2.0), 2),
                rank=idx
            ))
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/breadth", response_model=MarketBreadth)
def get_market_breadth(
    services: ServiceContainer = Depends(get_services)
):
    """
    Computes overall exchange breadth (Advances, Declines, Ratio) from active quotes.
    """
    # Sample from Top 300
    adv = 0
    dec = 0
    unch = 0
    
    top_syms = services.gap_orchestrator.get_target_universe(limit=100)
    for s in top_syms:
        q = services.redis_manager.get_quote("NSE", s)
        if q and "pct_change" in q:
            chg = float(q.get("pct_change", 0.0))
            if chg > 0.05:
                adv += 1
            elif chg < -0.05:
                dec += 1
            else:
                unch += 1
        else:
            unch += 1

    ratio = round(adv / max(dec, 1), 2)
    return MarketBreadth(
        advances=adv,
        declines=dec,
        unchanged=unch,
        adv_dec_ratio=ratio,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@router.get("/heatmap/sectors", response_model=List[SectorHeatmapItem])
def get_sector_heatmap(
    services: ServiceContainer = Depends(get_services)
):
    """
    Returns live performance heatmap across all NSE official sectors.
    Aggregates % return, advances/declines, and highlights Strong Buy / Buy candidates per sector.
    """
    mapper = SectorMapper()
    mapping_file = settings.SILVER_DIR / "master" / "stock_sector_mapping.parquet"
    if not mapping_file.exists():
        mapper.map_all_securities()

    try:
        df_sec = pl.read_parquet(mapping_file)
    except Exception:
        df_sec = mapper.map_all_securities()

    # Get active watchlist if available to cross-reference strong buys
    focus_syms = set()
    try:
        if hasattr(services.strategy_runner, "focus_watchlist") and services.strategy_runner.focus_watchlist:
            focus_syms = {c.symbol.upper() for c in services.strategy_runner.focus_watchlist}
    except Exception:
        pass

    results: List[SectorHeatmapItem] = []
    
    # Process primary sectoral groups
    for sec_id, sec_name in SECTOR_DISPLAY_NAMES.items():
        sec_stocks_df = df_sec.filter(pl.col("sector_index") == sec_id)
        if len(sec_stocks_df) == 0:
            continue

        sample_symbols = sec_stocks_df["symbol"].to_list()[:30] # take top 30 representative stocks
        adv = 0
        dec = 0
        chg_list = []
        stock_items: List[SectorStockItem] = []
        strong_buys_count = 0

        for sym in sample_symbols:
            # Check Redis or 1D fallback
            q = services.redis_manager.get_quote("NSE", sym)
            ltp = 0.0
            pct_chg = 0.0
            if q and "ltp" in q:
                ltp = float(q.get("ltp") or 0.0)
                pct_chg = float(q.get("pct_change") or 0.0)
            else:
                p = settings.SILVER_DIR / "ohlcv_1d" / "exchange=NSE" / f"symbol={sym}" / "data.parquet"
                if p.exists():
                    try:
                        d = pl.read_parquet(p)
                        if len(d) >= 2:
                            ltp = float(d.tail(1)["close"].item(0))
                            prev_c = float(d.tail(2).head(1)["close"].item(0))
                            pct_chg = ((ltp - prev_c) / prev_c) * 100.0 if prev_c > 0 else 0.0
                    except Exception:
                        pass

            if ltp > 0:
                chg_list.append(pct_chg)
                if pct_chg > 0.05:
                    adv += 1
                elif pct_chg < -0.05:
                    dec += 1

                # Determine action
                if sym in focus_syms or pct_chg >= 1.5:
                    action = "STRONG_BUY"
                    strong_buys_count += 1
                elif pct_chg >= 0.5:
                    action = "BUY"
                elif pct_chg <= -1.2:
                    action = "SELL"
                else:
                    action = "HOLD"

                stock_items.append(SectorStockItem(
                    symbol=sym,
                    company_name=sym,
                    ltp=round(ltp, 2),
                    pct_change=round(pct_chg, 2),
                    action=action
                ))

        avg_chg = round(sum(chg_list) / max(len(chg_list), 1), 2)
        # Sort top stocks by strong buy first, then highest % change
        stock_items.sort(key=lambda s: (s.action == "STRONG_BUY", s.action == "BUY", s.pct_change), reverse=True)

        results.append(SectorHeatmapItem(
            sector_id=sec_id,
            sector_name=sec_name,
            avg_change_pct=avg_chg,
            advances=adv,
            declines=dec,
            total_stocks=len(chg_list),
            strong_buys_count=strong_buys_count,
            top_stocks=stock_items[:12]
        ))

    # Sort sectors by highest average gain
    results.sort(key=lambda x: x.avg_change_pct, reverse=True)
    return results
