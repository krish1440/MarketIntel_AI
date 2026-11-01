import logging
import polars as pl
from pathlib import Path
from typing import Optional
from src.config.settings import settings
import src.features.polars_indicators as ind

logger = logging.getLogger(__name__)

class Model0FeatureEngineer:
    """
    Computes the 28 strictly orthogonal, dimensionless features for Model 0
    (Pre-Market Screener & LambdaMART Cross-Sectional Ranker).
    Reads Silver Lakehouse tables and writes to Gold Layer.
    """

    def __init__(self):
        self.silver_ohlcv_dir = settings.SILVER_DIR / "ohlcv_1d"
        self.silver_macro_dir = settings.SILVER_DIR / "macro"
        self.silver_global_dir = settings.SILVER_DIR / "macro" / "global"
        self.silver_master_dir = settings.SILVER_DIR / "master"
        self.silver_corp_dir = settings.SILVER_DIR / "corporate"
        
        self.gold_output_dir = settings.GOLD_DIR / "features_screener_ranking"
        self.gold_output_dir.mkdir(parents=True, exist_ok=True)

        self._load_shared_context()

    def _load_shared_context(self):
        """Loads Macro Indices, Global Correlators, Sector Mappings and FII Flows once into memory."""
        logger.info("Loading shared macro, sector, and global context for Model 0...")
        
        # 1. Stock to Sector Mapper
        mapper_path = self.silver_master_dir / "stock_sector_mapping.parquet"
        self.stock_sector_map = pl.read_parquet(mapper_path) if mapper_path.exists() else None

        # Build Master Macro Context DataFrame joined by date_key
        context_df = None

        # 2. Global Correlators (SP500, Nasdaq, Crude, USDINR, 10Y Yield)
        asset_map = {
            "SP500": ("sp500_overnight_ret", 1),
            "NASDAQ100": ("nasdaq_overnight_ret", 1),
            "CRUDE_OIL": ("crude_oil_ret_3d", 3),
            "USD_INR": ("usdinr_ret_1d", 1),
            "US10Y_YIELD": ("us_10y_yield_delta", 1)
        }

        for asset, (col_alias, shift_k) in asset_map.items():
            p = self.silver_global_dir / f"ticker={asset}" / "data.parquet"
            if p.exists():
                gdf = pl.read_parquet(p)
                col_t = "date" if "date" in gdf.columns else "timestamp"
                gdf = gdf.sort(col_t).with_columns([
                    pl.col(col_t).cast(pl.Date).alias("date_key"),
                    ((pl.col("close") / pl.col("close").shift(shift_k)).log() if asset != "US10Y_YIELD" else (pl.col("close") - pl.col("close").shift(1))).alias(col_alias)
                ]).select(["date_key", col_alias])

                if context_df is None:
                    context_df = gdf
                else:
                    context_df = context_df.join(gdf, on="date_key", how="outer_coalesce")

        # 3. India VIX & Nifty 50
        vix_path = self.silver_macro_dir / "index=INDIA_VIX" / "data.parquet"
        if vix_path.exists():
            vdf = pl.read_parquet(vix_path)
            col_t = "date" if "date" in vdf.columns else "timestamp"
            vdf = vdf.sort(col_t).with_columns([
                pl.col(col_t).cast(pl.Date).alias("date_key"),
                ((pl.col("close") - pl.col("close").rolling_mean(20)) / (pl.col("close").rolling_std(20) + 1e-8)).alias("india_vix_zscore_20d")
            ]).select(["date_key", "india_vix_zscore_20d"])
            if context_df is not None:
                context_df = context_df.join(vdf, on="date_key", how="outer_coalesce")

        nifty_path = self.silver_macro_dir / "index=NIFTY_50" / "data.parquet"
        if nifty_path.exists():
            ndf = pl.read_parquet(nifty_path)
            col_t = "date" if "date" in ndf.columns else "timestamp"
            ndf = ndf.sort(col_t).with_columns([
                pl.col(col_t).cast(pl.Date).alias("date_key"),
                (pl.col("close") / pl.col("close").shift(5)).log().alias("nifty_ret_5d")
            ]).select(["date_key", "nifty_ret_5d"])
            if context_df is not None:
                context_df = context_df.join(ndf, on="date_key", how="outer_coalesce")

        # 4. FII Flows
        fii_path = self.silver_macro_dir / "fii_dii_flows.parquet"
        if fii_path.exists():
            fdf = pl.read_parquet(fii_path)
            col_t = "date" if "date" in fdf.columns else "timestamp"
            fdf = fdf.sort(col_t).with_columns([
                pl.col(col_t).cast(pl.Date).alias("date_key"),
                (pl.col("fii_net_crores").rolling_mean(5) / 1000.0).alias("fii_flow_5d_norm")
            ]).select(["date_key", "fii_flow_5d_norm"])
            if context_df is not None:
                context_df = context_df.join(fdf, on="date_key", how="outer_coalesce")

        if context_df is not None:
            # Sort by date and forward-fill weekend/holiday gaps
            self.macro_context_df = context_df.sort("date_key").fill_null(strategy="forward").fill_null(0.0)
        else:
            self.macro_context_df = None

    def compute_for_stock(self, symbol: str, df: Optional[pl.DataFrame] = None) -> Optional[pl.DataFrame]:
        """Computes Model 0's 28 feature matrix for a single stock."""
        if df is None:
            stock_file = self.silver_ohlcv_dir / "exchange=NSE" / f"symbol={symbol}" / "data.parquet"
            if not stock_file.exists():
                return None
            try:
                df = pl.read_parquet(stock_file)
            except Exception:
                return None

        try:
            if len(df) < 252:
                return None

            date_col = "date" if "date" in df.columns else "timestamp"
            df = df.sort(date_col).with_columns(pl.col(date_col).cast(pl.Date).alias("date_key"))

            # --- Category A: Momentum & Trend Structure ---
            ret_exprs = ind.calc_log_returns("close", [1, 3, 5, 21])
            ema20 = ind.calc_ema("close", 20)
            ema200 = ind.calc_ema("close", 200)
            atr14 = ind.calc_atr("high", "low", "close", 14)
            atr5 = ind.calc_atr("high", "low", "close", 5)
            atr20 = ind.calc_atr("high", "low", "close", 20)
            rsi14 = ind.calc_rsi("close", 14)
            adx14 = ind.calc_adx("high", "low", "close", 14)

            df = df.with_columns(ret_exprs + [ema20, ema200, atr14, atr5, atr20, rsi14, adx14])

            # Normalized EMA distances & Volatility ratios
            dist_ema20 = ind.calc_distance_to_ema_atr("close", "ema_20", "atr_14", "dist_ema20_atr")
            dist_ema200 = ind.calc_distance_to_ema_atr("close", "ema_200", "atr_14", "dist_ema200_atr")
            atr_ratio = (pl.col("atr_5") / (pl.col("atr_20") + 1e-8)).alias("atr_ratio_5_20")

            # --- Category B: Volatility Compression & Breakout ---
            bb_exprs = ind.calc_bollinger_bands("close", 20, 2.0)
            parkinson = ind.calc_parkinson_volatility("high", "low", 10)
            dist_52w_high = ((pl.col("close") - pl.col("high").rolling_max(252)) / (pl.col("high").rolling_max(252) + 1e-8)).alias("dist_52w_high_pct")

            # --- Category C: Volume & Institutional Accumulation ---
            rvol20 = ind.calc_rvol("volume", 20)
            vol_trend = (pl.col("volume").rolling_mean(5) / (pl.col("volume").rolling_mean(20) + 1e-8)).alias("volume_trend_5_20")

            df = df.with_columns([dist_ema20, dist_ema200, atr_ratio, parkinson, dist_52w_high, rvol20, vol_trend] + bb_exprs)

            # Liquidity Turnover Metric for gatekeeping
            df = df.with_columns(
                (pl.col("close") * pl.col("volume")).rolling_mean(20).alias("turnover_20d_avg")
            )

            # --- Category D, E, F: Join Macro Context ---
            if self.macro_context_df is not None:
                df = df.join(self.macro_context_df, on="date_key", how="left").fill_null(strategy="forward").fill_null(0.0)
                # Compute Relative Strength vs Nifty 50
                if "nifty_ret_5d" in df.columns:
                    df = df.with_columns((pl.col("ret_5d") - pl.col("nifty_ret_5d")).alias("rs_vs_nifty_5d"))

            # Add symbol column
            if "symbol" not in df.columns:
                df = df.with_columns(pl.lit(symbol).alias("symbol"))

            return df

        except Exception as e:
            logger.warning(f"Error computing Model 0 features for {symbol}: {e}")
            return None
