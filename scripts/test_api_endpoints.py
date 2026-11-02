import sys
import logging
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.main import app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("APITestSuite")


def run_tests():
    logger.info("Initializing TestClient for MarketIntel FastAPI Backend...")
    client = TestClient(app)

    passed = 0
    failed = 0

    def assert_test(name: str, condition: bool, details: str = ""):
        nonlocal passed, failed
        if condition:
            logger.info(f"PASS: {name}")
            passed += 1
        else:
            logger.error(f"FAIL: {name} | Details: {details}")
            failed += 1

    # 1. Root Endpoint
    r = client.get("/")
    assert_test("GET / (Root health)", r.status_code == 200 and r.json().get("status") == "ONLINE", f"{r.status_code}: {r.text}")

    # 2. Stock Search
    r = client.get("/api/stocks/search?q=RELIANCE&limit=5")
    data = r.json()
    assert_test(
        "GET /api/stocks/search (Polars Sub-10ms Search)", 
        r.status_code == 200 and isinstance(data, list) and any(d.get("symbol") == "RELIANCE" for d in data),
        f"{r.status_code}: {r.text}"
    )

    # 3. Stock Quote
    r = client.get("/api/stocks/quote/RELIANCE")
    assert_test(
        "GET /api/stocks/quote/RELIANCE", 
        r.status_code == 200 and r.json().get("symbol") == "RELIANCE",
        f"{r.status_code}: {r.text}"
    )

    # 4. Top 300 Universe
    r = client.get("/api/stocks/universe/top300?limit=10")
    assert_test(
        "GET /api/stocks/universe/top300", 
        r.status_code == 200 and len(r.json()) > 0,
        f"{r.status_code}: {r.text}"
    )

    # 5. Market Breadth
    r = client.get("/api/stocks/breadth")
    assert_test(
        "GET /api/stocks/breadth", 
        r.status_code == 200 and "advances" in r.json(),
        f"{r.status_code}: {r.text}"
    )

    # 6. Charts 1D (DuckDB High-Speed Parquet)
    r = client.get("/api/charts/RELIANCE?timeframe=1d&limit=20")
    candles = r.json().get("candles", [])
    assert_test(
        "GET /api/charts/RELIANCE (1D Timeframe)", 
        r.status_code == 200 and len(candles) > 0,
        f"{r.status_code}: {r.text}"
    )

    # 7. Charts 1M (Intraday Parquet + DuckDB)
    r = client.get("/api/charts/RELIANCE?timeframe=1m&limit=20")
    m_candles = r.json().get("candles", [])
    assert_test(
        "GET /api/charts/RELIANCE (1M Timeframe)", 
        r.status_code == 200 and len(m_candles) > 0,
        f"{r.status_code}: {r.text}"
    )

    # 8. AI Screener Focus Watchlist
    r = client.get("/api/ai/screener/focus?limit=10")
    assert_test(
        "GET /api/ai/screener/focus", 
        r.status_code == 200 and isinstance(r.json(), list),
        f"{r.status_code}: {r.text}"
    )

    # 9. AI Price Corridor Forecast (Model 3)
    r = client.get("/api/ai/forecast/corridor/RELIANCE")
    assert_test(
        "GET /api/ai/forecast/corridor/RELIANCE", 
        r.status_code == 200 and "p50_median" in r.json(),
        f"{r.status_code}: {r.text}"
    )

    # 10. AI Signal (Model 4)
    r = client.get("/api/ai/signal/RELIANCE")
    assert_test(
        "GET /api/ai/signal/RELIANCE", 
        r.status_code == 200 and "action" in r.json(),
        f"{r.status_code}: {r.text}"
    )

    # 11. Trading Portfolio Summary
    r = client.get("/api/trading/portfolio")
    assert_test(
        "GET /api/trading/portfolio", 
        r.status_code == 200 and "current_cash" in r.json(),
        f"{r.status_code}: {r.text}"
    )

    # 12. Trading Positions List
    r = client.get("/api/trading/positions")
    assert_test(
        "GET /api/trading/positions", 
        r.status_code == 200 and isinstance(r.json(), list),
        f"{r.status_code}: {r.text}"
    )

    # 13. Trading Trade History
    r = client.get("/api/trading/trades")
    assert_test(
        "GET /api/trading/trades", 
        r.status_code == 200 and isinstance(r.json(), list),
        f"{r.status_code}: {r.text}"
    )

    # 14. Manual Order Simulation: BUY SBIN
    # First ensure SBIN is not already in positions so test is idempotent
    client.post("/api/trading/close/SBIN")
    order_payload = {
        "symbol": "SBIN",
        "direction": "BUY"
    }
    r = client.post("/api/trading/order", json=order_payload)
    order_data = r.json()
    assert_test(
        "POST /api/trading/order (BUY SBIN)", 
        r.status_code == 200 and order_data.get("status") == "FILLED",
        f"{r.status_code}: {r.text}"
    )

    # 15. Check position appears in /api/trading/positions
    r = client.get("/api/trading/positions")
    pos_data = r.json()
    assert_test(
        "GET /api/trading/positions (Contains SBIN)", 
        r.status_code == 200 and any(p["symbol"] == "SBIN" for p in pos_data),
        f"{r.status_code}: {r.text}"
    )

    # 16. Manual Close Position: SELL SBIN
    r = client.post("/api/trading/close/SBIN")
    close_data = r.json()
    assert_test(
        "POST /api/trading/close/SBIN (Close Position)", 
        r.status_code == 200 and close_data.get("status") == "CLOSED",
        f"{r.status_code}: {r.text}"
    )

    # 17. System Health
    r = client.get("/api/system/health")
    h = r.json()
    assert_test(
        "GET /api/system/health", 
        r.status_code == 200 and h.get("status") == "HEALTHY" and "memory_rss_mb" in h,
        f"{r.status_code}: {r.text}"
    )

    # 18. System Sync Status
    r = client.get("/api/system/sync/status")
    assert_test(
        "GET /api/system/sync/status", 
        r.status_code == 200 and "is_running" in r.json(),
        f"{r.status_code}: {r.text}"
    )

    # 19. WebSocket Live Endpoint Connection & Ping
    try:
        with client.websocket_connect("/ws/live") as ws:
            ack = ws.receive_json()
            assert_test(
                "WS /ws/live Connection ACK",
                ack.get("status") == "CONNECTED" and ack.get("channel") == "live",
                str(ack)
            )
            ws.send_json({"action": "ping"})
            pong = ws.receive_json()
            assert_test("WS /ws/live Ping/Pong", pong.get("type") == "pong", str(pong))
    except Exception as e:
        assert_test("WS /ws/live Test", False, str(e))

    # 20. WebSocket Trades Endpoint Connection
    try:
        with client.websocket_connect("/ws/trades") as ws:
            ack = ws.receive_json()
            assert_test(
                "WS /ws/trades Connection ACK",
                ack.get("status") == "CONNECTED" and ack.get("channel") == "trades",
                str(ack)
            )
    except Exception as e:
        assert_test("WS /ws/trades Test", False, str(e))

    logger.info("=" * 60)
    logger.info(f"API TEST RESULTS: {passed} PASSED | {failed} FAILED")
    logger.info("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
