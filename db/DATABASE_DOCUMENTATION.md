# 🗄️ Database Documentation: MarketIntel AI

This document provides a comprehensive technical overview of the persistence layer for **MarketIntel AI**. The database is designed to handle high-frequency live market data, multi-year historical time-series, and AI-derived sentiment metadata.

---

## 🏗️ Infrastructure Architecture

MarketIntel AI utilizes **PostgreSQL 16 (Alpine)** as its primary relational engine, orchestrated via Docker.

### 🐳 Docker Configuration
- **Image**: `postgres:16-alpine`
- **Internal Port**: `5432`
- **External Mapping**: `5433` (Avoids conflicts with default local Postgres)
- **Data Persistence**: Volumes are mapped to `./pgdata` in the project root to ensure data survives container restarts.
- **Auto-Initialization**: The `./db/init.sql` script is mounted to `/docker-entrypoint-initdb.d/init.sql`, ensuring the schema and seed data are applied on the first run.

---

## 📊 Schema Blueprint

The schema is optimized for relational integrity while supporting high-density time-series data.

### 1. `stocks` Table
The registry for all tracked equity assets.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL | PRIMARY KEY | Unique internal identifier. |
| `ticker` | VARCHAR(20) | UNIQUE, NOT NULL | Base ticker (e.g., `RELIANCE`). |
| `name` | VARCHAR(100) | - | Legal name of the company. |
| `nse_symbol` | VARCHAR(20) | - | Yahoo Finance / Exchange symbol for NSE (e.g., `RELIANCE.NS`). |
| `bse_symbol` | VARCHAR(20) | - | Yahoo Finance / Exchange symbol for BSE (e.g., `RELIANCE.BO`). |

### 2. `live_quotes` Table
Captures real-time price snapshots for the dashboard.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL | PRIMARY KEY | Unique identifier. |
| `stock_id` | INTEGER | FK (stocks.id) | Reference to the core stock asset. |
| `exchange` | VARCHAR(10) | - | Source exchange (`NSE` or `BSE`). |
| `price` | DECIMAL(15,2)| NOT NULL | Current market price. |
| `change_percent`| DECIMAL(10,4)| - | Intraday percentage change. |
| `volume` | BIGINT | - | Traded volume in the current session. |
| `timestamp` | TIMESTAMP | DEFAULT NOW() | Record creation time (UTC). |

### 3. `historical_prices` Table
Stores high-density historical OHLCV data for backtesting and AI training.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL | PRIMARY KEY | Unique identifier. |
| `stock_id` | INTEGER | FK (stocks.id) | Reference to the core stock asset. |
| `exchange` | VARCHAR(10) | - | Exchange source. |
| `date` | DATE | NOT NULL | Trading day date. |
| `open` | DECIMAL(15,2)| - | Opening price. |
| `high` | DECIMAL(15,2)| - | Daily high. |
| `low` | DECIMAL(15,2)| - | Daily low. |
| `close` | DECIMAL(15,2)| - | Closing price. |
| `volume` | BIGINT | - | Total daily volume. |

> [!NOTE]
> **Unique Constraint**: `UNIQUE (stock_id, exchange, date)` prevents duplicate historical records, ensuring data integrity during "Delta Sync" operations.

### 4. `news_articles` Table
Stores news headlines and AI-generated sentiment scores.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL | PRIMARY KEY | Unique identifier. |
| `stock_id` | INTEGER | FK (stocks.id) | Related stock for the news. |
| `title` | TEXT | NOT NULL | Article headline. |
| `summary` | TEXT | - | Brief summary of the article. |
| `url` | TEXT | UNIQUE, NOT NULL | Source link (serves as idempotency key). |
| `published_at` | TIMESTAMP | - | Publication time. |
| `sentiment_score`| DECIMAL(10,4)| - | **Neural Score**: -1.0 (Bearish) to 1.0 (Bullish). |

---

## 🐍 ORM Implementation (SQLAlchemy)

The `db/schema.py` file provides a Pythonic interface to the database using SQLAlchemy.

### Core Models
- `Stock`: Maps to `stocks`.
- `LiveQuote`: Maps to `live_quotes`.
- `HistoricalPrice`: Maps to `historical_prices`.
- `NewsArticle`: Maps to `news_articles`.

### Session Management
The implementation provides two critical utility functions:
- `get_engine()`: Configures the connection string using `pg8000` driver.
- `get_session()`: Returns a scoped session factory for database operations.

```python
from db.schema import get_session, Stock

# Example: Fetching a stock by ticker
session = get_session()
reliance = session.query(Stock).filter_by(ticker="RELIANCE").first()
print(f"Tracking: {reliance.name}")
session.close()
```

---

## 🚀 Data Lifecycle & Seeding

### 1. Initial Seeding
Upon first deployment, `init.sql` automatically populates the `stocks` table with top-tier Indian equities (RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK). This ensures the system is immediately functional.

### 2. Delta Sync Logic
The `historical_prices` table is populated via the `ingestion/delta_update.py` service. It uses the `UNIQUE` constraint to perform **Upserts** (Insert or Update on Conflict), allowing the system to fill "gaps" in data without creating duplicates.

### 3. Real-Time Updates
The `live_quotes` table acts as a high-speed buffer, frequently updated by `ingestion/poll_prices.py` to drive the frontend dashboard.

---

## 🛠️ Advanced Maintenance

### Performance Scaling
With over **4.5M+ records** (as noted in the Kaggle dataset), the database is optimized for:
- **Index Efficiency**: Automatic indexing on Primary Keys and Unique constraints.
- **Volume Handling**: `BIGINT` types for volume to prevent overflow on high-cap stocks.
- **Precision**: `DECIMAL` types ensure financial accuracy compared to `FLOAT`.

### Manual Schema Updates
If the schema needs to be reset:
1. Stop containers: `docker-compose down`
2. Clear data: `Remove-Item -Recurse -Force ./pgdata`
3. Restart: `python run_app.py` (which triggers fresh initialization)
