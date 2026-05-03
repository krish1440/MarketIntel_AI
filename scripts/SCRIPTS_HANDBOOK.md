# 🛠️ MarketIntel AI: Production Scripts Handbook
**Layer: Utilities & Automation**

This directory contains standalone execution scripts designed for database administration, environment testing, and automated Kaggle exports. These files do not run the core application loop but are essential for maintenance and diagnostics.

---

## 🏗️ Utility Breakdown

### 1. Database Administration
*   **`create_tables.py`**: A safe, idempotent script that synchronizes the current SQLAlchemy models with the PostgreSQL database. Run this when setting up the environment on a new machine.

### 2. The Kaggle Export Engine
*   **`smart_export.py`**: Our proprietary "Additive Export" engine. 
    *   **Long Format**: Employs a 'tail-read' strategy on massive CSVs to append only new rows, saving gigabytes of disk I/O.
    *   **Wide Format**: Reconstructs the 2D time-series price matrix incrementally using Pandas.
    *   **Automation**: Includes a sub-process that pushes the newly compiled dataset directly to Kaggle via the Kaggle CLI API.
*   **`export_kaggle.py`**: The legacy full-export script, retained as a fallback.

### 3. Alert System Diagnostics
*   **`setup_test_watchlist.py`**: Injects a dummy watchlist into the database (targeting RELIANCE) with extreme thresholds, ensuring the next intelligence cycle triggers an event.
*   **`simulate_alert.py`**: Artificially injects massive price spikes and positive sentiment events directly into the `AlertManager` memory space without altering the database. Used to test push notifications.
*   **`view_alerts.py`**: A clean terminal interface that queries the DB for the 10 most recent generated alerts. Ideal for SSH server administration.

---
*Maintained by MarketIntel AI Engineering Group.*
