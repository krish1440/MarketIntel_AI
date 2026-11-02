import logging
from typing import Optional
from pathlib import Path

from src.config.settings import settings
from src.master.security_master import SecurityMaster
from src.serving.chart_service import ChartService
from src.serving.redis_manager import RedisManager
from src.serving.streaming_aggregator import StreamingAggregator
from src.execution.portfolio_manager import VirtualPortfolioManager
from src.execution.strategy_runner import AIStrategyRunner
from src.crawler.gap_orchestrator import GapOrchestrator

logger = logging.getLogger("APIDependencies")

# Global singleton container
class ServiceContainer:
    _instance: Optional["ServiceContainer"] = None

    def __init__(self):
        logger.info("Initializing Backend Service Container...")
        self.security_master = SecurityMaster()
        self.redis_manager = RedisManager()
        self.streaming_aggregator = StreamingAggregator(redis_mgr=self.redis_manager)
        self.chart_service = ChartService(redis_mgr=self.redis_manager)
        self.portfolio_manager = VirtualPortfolioManager()
        self.strategy_runner = AIStrategyRunner(portfolio_manager=self.portfolio_manager)
        self.gap_orchestrator = GapOrchestrator()
        logger.info("Backend Service Container ready.")

    @classmethod
    def get_instance(cls) -> "ServiceContainer":
        if cls._instance is None:
            cls._instance = ServiceContainer()
        return cls._instance

def get_services() -> ServiceContainer:
    return ServiceContainer.get_instance()

