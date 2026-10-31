import math
import polars as pl
import numpy as np
from typing import List, Union

"""
High-Performance Vectorized Polars Technical Indicator Engine
Executes in pure Rust backend with multi-threaded parallel computation.
Zero pandas / numpy bottleneck on millions of bars.
"""

def calc_log_returns(close_col: str = "close", periods: List[int] = [1, 3, 5, 21, 63, 126]) -> List[pl.Expr]:
    """Generates stationary log returns across multiple lookback periods."""
    exprs = []
    for p in periods:
        exprs.append(
            (pl.col(close_col) / pl.col(close_col).shift(p)).log().alias(f"ret_{p}d")
        )
    return exprs

def calc_ema(col: str = "close", span: int = 20) -> pl.Expr:
    """Vectorized Exponential Moving Average using Polars ewm_mean."""
    return pl.col(col).ewm_mean(span=span, adjust=False).alias(f"ema_{span}")

def calc_sma(col: str = "close", window: int = 20) -> pl.Expr:
    """Vectorized Simple Moving Average."""
    return pl.col(col).rolling_mean(window_size=window).alias(f"sma_{window}")

def calc_true_range(high_col: str = "high", low_col: str = "low", close_col: str = "close") -> pl.Expr:
    """Computes True Range (TR) across bars."""
    prev_close = pl.col(close_col).shift(1)
    hl = pl.col(high_col) - pl.col(low_col)
    hc = (pl.col(high_col) - prev_close).abs()
    lc = (pl.col(low_col) - prev_close).abs()
    return pl.max_horizontal(hl, hc, lc).alias("true_range")

def calc_atr(high_col: str = "high", low_col: str = "low", close_col: str = "close", period: int = 14) -> pl.Expr:
    """Average True Range (Wilder's Smoothing)."""
    tr = calc_true_range(high_col, low_col, close_col)
    return tr.ewm_mean(alpha=1.0 / period, adjust=False).alias(f"atr_{period}")

def calc_bollinger_bands(close_col: str = "close", period: int = 20, num_std: float = 2.0) -> List[pl.Expr]:
    """Bollinger Bands and Bandwidth Squeeze ratio."""
    sma = pl.col(close_col).rolling_mean(window_size=period)
    std = pl.col(close_col).rolling_std(window_size=period)
    upper = (sma + (std * num_std)).alias("bb_upper")
    lower = (sma - (std * num_std)).alias("bb_lower")
    squeeze = ((upper - lower) / (sma + 1e-8)).alias("bb_squeeze_pct")
    return [upper, sma.alias("bb_middle"), lower, squeeze]

def calc_rsi(close_col: str = "close", period: int = 14) -> pl.Expr:
    """Vectorized Wilder's Relative Strength Index (RSI)."""
    diff = pl.col(close_col).diff()
    gain = pl.when(diff > 0).then(diff).otherwise(0.0)
    loss = pl.when(diff < 0).then(-diff).otherwise(0.0)
    
    avg_gain = gain.ewm_mean(alpha=1.0 / period, adjust=False)
    avg_loss = loss.ewm_mean(alpha=1.0 / period, adjust=False)
    
    rs = avg_gain / (avg_loss + 1e-8)
    rsi = (100.0 - (100.0 / (1.0 + rs))).alias(f"rsi_{period}")
    return rsi

def calc_parkinson_volatility(high_col: str = "high", low_col: str = "low", window: int = 20) -> pl.Expr:
    """
    Parkinson Volatility estimator: 5x more efficient than Close-to-Close.
    Uses continuous intra-period High/Low ranges.
    """
    factor = 1.0 / (4.0 * math.log(2.0))
    hl_sq = ((pl.col(high_col) / (pl.col(low_col) + 1e-8)).log()).pow(2)
    rolling_sum = hl_sq.rolling_sum(window_size=window)
    parkinson = ((rolling_sum / window) * factor).sqrt() * math.sqrt(252.0)
    return parkinson.alias(f"parkinson_vol_{window}d")

def calc_garman_klass_volatility(
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    window: int = 20
) -> pl.Expr:
    """
    Garman-Klass Volatility: 8x more statistically efficient than standard deviations.
    Ingests Open, High, Low, and Close.
    """
    hl = 0.5 * ((pl.col(high_col) / (pl.col(low_col) + 1e-8)).log()).pow(2)
    co = (2.0 * math.log(2.0) - 1.0) * ((pl.col(close_col) / (pl.col(open_col) + 1e-8)).log()).pow(2)
    term = hl - co
    gk = ((term.rolling_sum(window_size=window) / window)).sqrt() * math.sqrt(252.0)
    return gk.alias(f"garman_klass_vol_{window}d")

def calc_rvol(volume_col: str = "volume", window: int = 20) -> pl.Expr:
    """Relative Volume (RVOL) surge factor."""
    sma_vol = pl.col(volume_col).rolling_mean(window_size=window)
    return (pl.col(volume_col) / (sma_vol + 1e-8)).alias(f"rvol_{window}")

def calc_candle_anatomy(
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close"
) -> List[pl.Expr]:
    """
    Candle price action geometry (body ratio, upper rejection wick, lower absorption wick).
    Stationary metrics bounded between 0.0 and 1.0.
    """
    range_hl = pl.col(high_col) - pl.col(low_col) + 1e-8
    body = (pl.col(close_col) - pl.col(open_col)).abs()
    upper_wick = pl.col(high_col) - pl.max_horizontal(pl.col(open_col), pl.col(close_col))
    lower_wick = pl.min_horizontal(pl.col(open_col), pl.col(close_col)) - pl.col(low_col)
    
    return [
        (body / range_hl).alias("candle_body_ratio"),
        (upper_wick / range_hl).alias("candle_upper_wick_ratio"),
        (lower_wick / range_hl).alias("candle_lower_wick_ratio"),
    ]

def calc_distance_to_ema_atr(
    close_col: str = "close",
    ema_col: str = "ema_20",
    atr_col: str = "atr_14",
    alias: str = "dist_ema20_atr"
) -> pl.Expr:
    """Normalized dimensionless distance from EMA divided by ATR."""
    return ((pl.col(close_col) - pl.col(ema_col)) / (pl.col(atr_col) + 1e-8)).alias(alias)
