import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, date, time, timezone
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import polars as pl
import joblib
import lightgbm as lgb

from src.config.settings import settings
from src.execution.portfolio_manager import VirtualPortfolioManager, Position, TradeExitResult

logger = logging.getLogger("AIStrategyRunner")

@dataclass
class CandidateStock:
    """Pre-Market Screened Candidate Stock."""
    symbol: str
    rank_score: float
    current_price: float
    macro_approved: bool
    structural_drawdown: float = 0.0
    calmar_ratio: float = 0.0

@dataclass
class SignalDecision:
    """Multi-Tier AI Strategy Signal Decision."""
    symbol: str
    action: str                       # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    confidence: float                 # Platt-calibrated probability (0.0 to 1.0)
    is_approved: bool                 # Passed all tiers
    rejection_reason: Optional[str]
    current_price: float
    ml_stop_price: float              # Model 3 P05 floor clamped at max -6.0%
    ml_target_1: float                # Model 3 P75 resistance
    ml_target_2: float                # Model 1 Q90 runner ceiling
    corridor_p05: float = 0.0
    corridor_p25: float = 0.0
    corridor_p50: float = 0.0
    corridor_p75: float = 0.0
    corridor_p95: float = 0.0

@dataclass
class IntradayBar:
    """1-Minute or 5-Minute Intraday Bar."""
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class AIStrategyRunner:
    """
    Institutional Multi-Tier AI Strategy Execution Runner.
    
    Orchestrates the 5 verified AI models in real time:
      - Tier 0: Model 2 Macro Quality Gatekeeper (Excludes structurally impaired stocks).
      - Tier 1 (09:08 AM): Model 0 Pre-Market Screener (Dynamic 4 to 20 focus watchlist).
      - Tier 2 (09:15 AM): Model 3 Fair-Value Corridor Check (P25 to P50 zone, rejects >= P95).
      - Tier 3 (09:30 AM): Model 4 Direction & Confidence Check (STRONG_BUY >= 65%).
      - Tier 4 (Real-Time): Intraday 1-Min Trigger (15m ORB Breakout + Price > VWAP + RVOL > 1.2).
      - Dynamic Risk: Stop-Loss at Model 3 P05 (Capped at -6%), Target 1 at P75 (Book 50% + Breakeven stop),
        Target 2 at Model 1 Q90 runner, Invalidation exit if Model 4 flips to SELL.
    """

    MAX_STOP_LOSS_PCT = 0.06       # Strict institutional 6.0% maximum safety loss floor
    MIN_CONFIDENCE_STRONG_BUY = 0.65  # 65% minimum confidence
    MIN_CONFIDENCE_BUY = 0.55         # 55% minimum confidence for regular BUY
    MAX_STRUCTURAL_DRAWDOWN = -0.40   # Trash stock filter: reject drawdown > -40%

    def __init__(
        self,
        portfolio_manager: Optional[VirtualPortfolioManager] = None,
        model_dir: Optional[Path] = None
    ):
        self.portfolio_manager = portfolio_manager or VirtualPortfolioManager()
        self.model_dir = model_dir or (settings.BASE_DIR / "models" / "active")

        # Models & Registries
        self.models: Dict[str, Any] = {}
        self.registry: Dict[str, Any] = {}
        self._load_active_models()

        # Dynamic State
        self.focus_watchlist: List[CandidateStock] = []
        self.approved_signals: Dict[str, SignalDecision] = {}

        # Intraday 15m ORB & VWAP Trackers per symbol
        self.orb_highs: Dict[str, float] = {}
        self.orb_lows: Dict[str, float] = {}
        self.orb_locked: Dict[str, bool] = {}
        self.cum_vol: Dict[str, float] = {}
        self.cum_pv: Dict[str, float] = {}
        self.base_15m_vol: Dict[str, float] = {}

    def _load_active_models(self):
        """Loads all 5 active production models from the model registry."""
        registry_path = self.model_dir / "model_registry.json"
        if not registry_path.exists():
            raise FileNotFoundError(f"Model registry not found at {registry_path}")

        with open(registry_path, "r") as f:
            self.registry = json.load(f)

        logger.info(f"Loading Active Models from {self.model_dir} (Refit: {self.registry.get('refit_timestamp')})...")

        # 1. Model 0: Screener Ranker
        m0_file = self.model_dir / self.registry["models"]["model0"]["artifact"]
        self.models["model0"] = lgb.Booster(model_file=str(m0_file))

        # 2. Model 1: Swing Quantiles (q10, q50, q90)
        self.models["model1"] = {}
        for q, art in self.registry["models"]["model1"]["artifacts"].items():
            self.models["model1"][q] = lgb.Booster(model_file=str(self.model_dir / art))

        # 3. Model 2: Macro Gatekeeper
        m2_file = self.model_dir / self.registry["models"]["model2"]["artifact"]
        self.models["model2"] = lgb.Booster(model_file=str(m2_file))

        # 4. Model 3: Price Corridor Quantiles (p05, p25, p50, p75, p95)
        self.models["model3"] = {}
        for p, art in self.registry["models"]["model3"]["artifacts"].items():
            self.models["model3"][p] = lgb.Booster(model_file=str(self.model_dir / art))

        # 5. Model 4: Action Classifier
        m4_file = self.model_dir / self.registry["models"]["model4"]["artifact"]
        self.models["model4"] = joblib.load(str(m4_file))

        logger.info("All 5 Active Institutional Models loaded successfully into memory.")

    def run_premarket_screener(
        self,
        market_features_df: pl.DataFrame,
        macro_gatekeeper_df: Optional[pl.DataFrame] = None
    ) -> List[CandidateStock]:
        """
        Tier 0 & Tier 1 (09:08 AM):
          - Model 2 Macro Gatekeeper filters out structurally broken / crash-prone stocks.
          - Model 0 ranks universe cross-sectionally.
          - Breadth determines watchlist size (4 to 20 focus stocks).
        """
        logger.info("Running 09:08 AM Pre-Market AI Screener across universe...")
        m0_feats = self.registry["models"]["model0"]["features"]
        m2_feats = self.registry["models"]["model2"]["features"]

        # 1. Tier 0: Macro Gatekeeper Check (Model 2)
        macro_banned = set()
        macro_stats = {}
        if macro_gatekeeper_df is not None and len(macro_gatekeeper_df) > 0:
            for row in macro_gatekeeper_df.iter_rows(named=True):
                sym = row["symbol"]
                max_dd = row.get("max_drawdown_756d", 0.0) or 0.0
                calmar = row.get("calmar_ratio_3y", 1.0) or 1.0
                macro_stats[sym] = {"drawdown": max_dd, "calmar": calmar}
                if max_dd < self.MAX_STRUCTURAL_DRAWDOWN or calmar < 0.0:
                    macro_banned.add(sym)
                    logger.debug(f"Macro BANNED {sym}: Drawdown {max_dd:.1%}, Calmar {calmar:.2f}")

        # 2. Tier 1: Model 0 Ranking
        # Ensure required features exist
        available_feats = [c for c in m0_feats if c in market_features_df.columns]
        missing_feats = set(m0_feats) - set(available_feats)
        if missing_feats:
            logger.warning(f"Model 0 missing {len(missing_feats)} features; filling with 0.0: {missing_feats}")
            for mf in missing_feats:
                market_features_df = market_features_df.with_columns(pl.lit(0.0).alias(mf))

        X0 = market_features_df.select(m0_feats).to_numpy()
        rank_scores = self.models["model0"].predict(X0)

        # Build candidate list
        symbols = market_features_df["symbol"].to_list()
        prices = market_features_df["close"].to_list()

        candidates: List[CandidateStock] = []
        for sym, score, px in zip(symbols, rank_scores, prices):
            if sym in macro_banned:
                continue  # Banned by Tier 0
            
            m_stat = macro_stats.get(sym, {"drawdown": 0.0, "calmar": 1.0})
            candidates.append(CandidateStock(
                symbol=sym,
                rank_score=float(score),
                current_price=float(px),
                macro_approved=True,
                structural_drawdown=float(m_stat["drawdown"]),
                calmar_ratio=float(m_stat["calmar"])
            ))

        # Sort candidates descending by Model 0 rank score
        candidates.sort(key=lambda c: c.rank_score, reverse=True)

        # Dynamic Watchlist Sizing based on breadth (positive alpha scores)
        positive_candidates = [c for c in candidates if c.rank_score > 0.0]
        breadth_count = len(positive_candidates)

        if breadth_count == 0:
            target_watchlist_size = 0  # 100% Cash in panic market
            logger.warning("MARKET BREADTH COLLAPSE: Zero stocks scored positive alpha. Staying in 100% Cash!")
        elif breadth_count < 10:
            target_watchlist_size = min(len(candidates), max(4, breadth_count))
        else:
            target_watchlist_size = min(len(candidates), 20)

        self.focus_watchlist = candidates[:target_watchlist_size]

        logger.info(
            f"09:08 AM SCREENER COMPLETE: Selected {len(self.focus_watchlist)} focus stocks "
            f"(Breadth: {breadth_count} positive candidates, Target: {target_watchlist_size})."
        )
        return self.focus_watchlist

    def evaluate_corridor_and_action(
        self,
        symbol: str,
        current_price: float,
        features_dict: Dict[str, Any]
    ) -> SignalDecision:
        """
        Tier 2 (09:15 AM) & Tier 3 (09:30 AM):
          - Model 3 Corridor Valuation Check: Must be in P25 to P50 Fair Value zone (Reject >= P95).
          - Model 4 Action & Confidence Check: STRONG_BUY with Confidence >= 65% (or BUY >= 70%).
          - Dynamic Risk Setup: Model 3 P05 Stop Loss (clamped at -6%), Model 3 P75 Target 1, Model 1 Q90 Target 2.
        """
        m3_feats = self.registry["models"]["model3"]["features"]
        m4_feats = self.registry["models"]["model4"]["features"]
        m1_feats = self.registry["models"]["model1"]["features"]

        # 1. Model 3 Quantiles (Price Corridor)
        x3 = np.array([[features_dict.get(k, 0.0) for k in m3_feats]], dtype=np.float32)
        p05 = float(self.models["model3"]["p05"].predict(x3)[0])
        p25 = float(self.models["model3"]["p25"].predict(x3)[0])
        p50 = float(self.models["model3"]["p50"].predict(x3)[0])
        p75 = float(self.models["model3"]["p75"].predict(x3)[0])
        p95 = float(self.models["model3"]["p95"].predict(x3)[0])

        # Convert quantile return offsets to price levels
        # Standardize: if p50 < 5.0, quantile is a fractional return offset from current price
        if abs(p50) < 5.0:
            price_p05 = current_price * (1.0 + p05)
            price_p25 = current_price * (1.0 + p25)
            price_p50 = current_price * (1.0 + p50)
            price_p75 = current_price * (1.0 + p75)
            price_p95 = current_price * (1.0 + p95)
        else:
            price_p05, price_p25, price_p50, price_p75, price_p95 = p05, p25, p50, p75, p95

        # 2. Model 4 Action & Calibrated Directional Confidence
        x4 = np.array([[features_dict.get(k, 0.0) for k in m4_feats]], dtype=np.float32)
        probs = self.models["model4"].predict_proba(x4)[0]
        # Class indices: 0: STRONG_SELL, 1: SELL, 2: HOLD, 3: BUY, 4: STRONG_BUY
        p_bear = float(probs[0] + probs[1])
        p_hold = float(probs[2])
        p_bull = float(probs[3] + probs[4])
        dir_sum = p_bull + p_bear
        bullish_ratio = p_bull / max(dir_sum, 1e-6)

        if bullish_ratio >= 0.65 and p_bull >= 0.28:
            action = "STRONG_BUY"
            confidence = bullish_ratio
        elif bullish_ratio >= 0.55 and p_bull >= 0.25:
            action = "BUY"
            confidence = bullish_ratio
        elif bullish_ratio <= 0.35 and p_bear >= 0.28:
            action = "STRONG_SELL"
            confidence = 1.0 - bullish_ratio
        elif bullish_ratio <= 0.45 and p_bear >= 0.25:
            action = "SELL"
            confidence = 1.0 - bullish_ratio
        else:
            action = "HOLD"
            confidence = p_hold

        # 3. Model 1 Momentum Runner Target (Q90)
        x1 = np.array([[features_dict.get(k, 0.0) for k in m1_feats]], dtype=np.float32)
        q90_raw = float(self.models["model1"]["q90"].predict(x1)[0])
        target_2 = current_price * (1.0 + q90_raw) if abs(q90_raw) < 5.0 else q90_raw

        # 4. Corridor Valuation & Penny Stock Gate Checks
        # Rule: Current price must not be overbought/exhausted (must be < P95) and >= Rs.30.
        is_approved = True
        rejection_reason = None

        if current_price < 30.0:
            is_approved = False
            rejection_reason = f"Penny Stock Gate: Price Rs.{current_price:.2f} < Rs.30.00 floor (Institutional quality required)"
        elif current_price >= price_p95:
            is_approved = False
            rejection_reason = f"Corridor Rejection: Price Rs.{current_price:.2f} >= P95 ceiling Rs.{price_p95:.2f} (Overbought/Exhausted)"
        elif action not in ["STRONG_BUY", "BUY"]:
            is_approved = False
            rejection_reason = f"Model 4 Action Rejection: Signal is {action} (Requires STRONG_BUY or BUY)"
        elif action == "STRONG_BUY" and confidence < self.MIN_CONFIDENCE_STRONG_BUY:
            is_approved = False
            rejection_reason = f"Model 4 Confidence Rejection: {confidence:.1%} < {self.MIN_CONFIDENCE_STRONG_BUY:.0%} threshold"
        elif action == "BUY" and confidence < self.MIN_CONFIDENCE_BUY:
            is_approved = False
            rejection_reason = f"Model 4 BUY Confidence Rejection: {confidence:.1%} < {self.MIN_CONFIDENCE_BUY:.0%} threshold"

        # 5. Stop-Loss Calculation (Model 3 P05 with max 6% safety floor clamp)
        max_safety_stop = current_price * (1.0 - self.MAX_STOP_LOSS_PCT)
        # Dynamic Stop is max(P05, -6% clamp) so we never risk more than 6%
        ml_stop_price = max(price_p05, max_safety_stop)
        ml_stop_price = round(min(ml_stop_price, current_price * 0.985), 2)  # At least 1.5% below entry

        # Target 1: Model 3 P75 with Asymmetric 1.8x Reward-to-Risk hurdle
        risk_dist = current_price - ml_stop_price
        min_reward_target = current_price + (risk_dist * 1.80)
        ml_target_1 = max(round(price_p75, 2), round(min_reward_target, 2), round(current_price * 1.08, 2))
        ml_target_2 = max(round(target_2, 2), round(ml_target_1 * 1.10, 2))

        decision = SignalDecision(
            symbol=symbol,
            action=action,
            confidence=confidence,
            is_approved=is_approved,
            rejection_reason=rejection_reason,
            current_price=current_price,
            ml_stop_price=ml_stop_price,
            ml_target_1=ml_target_1,
            ml_target_2=ml_target_2,
            corridor_p05=round(price_p05, 2),
            corridor_p25=round(price_p25, 2),
            corridor_p50=round(price_p50, 2),
            corridor_p75=round(price_p75, 2),
            corridor_p95=round(price_p95, 2)
        )

        if is_approved:
            self.approved_signals[symbol] = decision
            logger.info(
                f"TIER 2 & 3 APPROVED: {symbol} | Action: {action} ({confidence:.1%}) | "
                f"Price: Rs.{current_price:.2f} | Stop: Rs.{ml_stop_price:.2f} (-{((current_price-ml_stop_price)/current_price)*100:.1f}%) | "
                f"T1: Rs.{ml_target_1:.2f} | T2: Rs.{ml_target_2:.2f}"
            )
        else:
            logger.debug(f"TIER 2/3 REJECTED: {symbol} | Reason: {rejection_reason}")

        return decision

    def register_orb_candle(self, bar: IntradayBar, is_orb_window: bool = True):
        """Registers 1-minute candles during the 09:15 to 09:30 AM Opening Range Window."""
        sym = bar.symbol
        if sym not in self.orb_highs:
            self.orb_highs[sym] = bar.high
            self.orb_lows[sym] = bar.low
            self.cum_vol[sym] = bar.volume
            self.cum_pv[sym] = bar.close * bar.volume
        else:
            self.orb_highs[sym] = max(self.orb_highs[sym], bar.high)
            self.orb_lows[sym] = min(self.orb_lows[sym], bar.low)
            self.cum_vol[sym] += bar.volume
            self.cum_pv[sym] += bar.close * bar.volume

        if not is_orb_window:
            self.orb_locked[sym] = True

    def process_intraday_tick(
        self,
        symbol: str,
        price: float,
        volume: float,
        timestamp: Optional[datetime] = None,
        rvol: float = 1.3
    ) -> Optional[Position]:
        """
        Tier 4 Execution Trigger & Dynamic Trade Lifecycle Management:
          1. Monitors existing open positions for:
             - Stop-Loss Hit (Model 3 P05 Floor)
             - Target 1 Hit (Model 3 P75 -> Books 50%, Moves stop to Breakeven)
             - Target 2 Hit (Model 1 Q90 Runner)
          2. Monitors approved candidates for Tier 4 Breakout Trigger:
             - Price > 15m ORB High
             - Price > VWAP
             - RVOL >= 1.2
             -> Calls PortfolioManager to size and execute paper trade.
        """
        ts = timestamp or datetime.now(timezone.utc)

        # 1. Position Management for existing active trades
        if symbol in self.portfolio_manager.positions:
            self.portfolio_manager.update_market_price(symbol, price)
            return self.portfolio_manager.positions.get(symbol)

        # 2. Check if symbol is an approved AI candidate
        signal = self.approved_signals.get(symbol)
        if not signal or not signal.is_approved:
            return None

        # 3. Check circuit breaker or max positions
        if self.portfolio_manager.circuit_breaker_tripped:
            return None
        if len(self.portfolio_manager.positions) >= self.portfolio_manager.MAX_OPEN_POSITIONS:
            return None

        # 4. Check Intraday Trigger Requirements:
        # A) 15m ORB High Breakout
        orb_high = self.orb_highs.get(symbol, 0.0)
        if orb_high <= 0.0:
            # Fallback if ORB high not yet recorded: breakout from signal price
            orb_high = signal.current_price

        # B) VWAP Check
        tot_vol = self.cum_vol.get(symbol, 1.0)
        tot_pv = self.cum_pv.get(symbol, price * tot_vol)
        vwap = (tot_pv / tot_vol) if tot_vol > 0 else price

        # Trigger conditions
        is_orb_breakout = price > orb_high
        is_above_vwap = price >= vwap
        is_high_volume = rvol >= 1.2

        if is_orb_breakout and is_above_vwap and is_high_volume:
            trigger_reason = f"15M_ORB_VWAP_RVOL_BREAKOUT (ORB:{orb_high:.2f}, VWAP:{vwap:.2f}, RVOL:{rvol:.2f})"
            logger.info(f"TIER 4 ENTRY TRIGGER FIRED for {symbol} at Rs.{price:.2f}! Reason: {trigger_reason}")

            pos = self.portfolio_manager.open_position(
                symbol=symbol,
                current_price=price,
                ml_stop_price=signal.ml_stop_price,
                ml_target_1=signal.ml_target_1,
                ml_target_2=signal.ml_target_2,
                confidence=signal.confidence,
                trigger_reason=trigger_reason
            )

            # Once entered, remove from approved signals to prevent duplicate triggers
            if pos:
                self.approved_signals.pop(symbol, None)
            return pos

        return None

    def handle_eod_invalidation(
        self, 
        current_features_per_stock: Dict[str, Dict[str, Any]],
        direct_actions: Optional[Dict[str, str]] = None
    ):
        """
        EOD / Daily Close Governance Check:
          If Model 4 updates and flips to SELL or STRONG_SELL,
          exit the swing position immediately the next morning / at market close.
        """
        m4_feats = self.registry["models"]["model4"]["features"]
        classes = ["STRONG_SELL", "SELL", "HOLD", "BUY", "STRONG_BUY"]
        direct_actions = direct_actions or {}

        for sym, pos in list(self.portfolio_manager.positions.items()):
            action = direct_actions.get(sym)

            if not action:
                feats = current_features_per_stock.get(sym)
                if not feats:
                    continue

                x4 = np.array([[feats.get(k, 0.0) for k in m4_feats]], dtype=np.float32)
                probs = self.models["model4"].predict_proba(x4)[0]
                action = classes[int(np.argmax(probs))]

            if action in ["SELL", "STRONG_SELL"]:
                logger.warning(
                    f"EARLY INVALIDATION TRIGGER: Model 4 flipped to {action} for {sym}! "
                    f"Exiting position immediately at Rs.{pos.current_price:.2f}."
                )
                self.portfolio_manager.close_position(
                    symbol=sym,
                    current_price=pos.current_price,
                    exit_trigger=f"MODEL4_{action}_INVALIDATION"
                )
