"""Service layer: the application brain that turns data sources + analytics into API responses."""
from .market_service import MarketService

__all__ = ["MarketService"]
