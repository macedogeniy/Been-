"""
Конфигурация торговой системы "Охота за ликвидностью"
"""

from typing import Dict, List, Optional, Union
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from pathlib import Path
import os


class ExchangeConfig(BaseSettings):
    """Настройки биржи"""
    name: str = "binance"
    sandbox: bool = True
    api_key: Optional[str] = None
    secret: Optional[str] = None
    passphrase: Optional[str] = None
    rate_limit: int = 1200  # requests per minute
    timeout: int = 30000  # milliseconds
    
    class Config:
        env_prefix = "EXCHANGE_"


class TradingConfig(BaseSettings):
    """Настройки торговой стратегии"""
    symbol: str = "BTC/USDT"
    base_currency: str = "USDT"
    
    # СТРОГАЯ ИЕРАРХИЯ ТАЙМФРЕЙМОВ СОГЛАСНО СТРАТЕГИИ
    # HTF: Стратегические таймфреймы - "Карта Генерала"
    strategic_timeframes: List[str] = ["1d", "4h"]
    
    # Промежуточные таймфреймы - "Карта Командира"  
    intermediate_timeframes: List[str] = ["1h", "30m"]
    
    # LTF: Тактические таймфреймы - "Компас Солдата"
    tactical_timeframes: List[str] = ["15m", "5m"]
    
    # Снайперский таймфрейм - "Оптический Прицел"
    sniper_timeframes: List[str] = ["1m"]
    
    # Настройки риск-менеджмента
    max_risk_per_trade: float = Field(0.02, ge=0.001, le=0.1)  # 2% риска на сделку
    max_open_positions: int = Field(3, ge=1, le=10)
    min_rr_ratio: float = Field(2.0, ge=1.0, le=10.0)  # минимальное соотношение риск/прибыль
    min_confluence_score: float = Field(0.7, ge=0.5, le=1.0)  # минимальный скор конфлюенции
    
    # Настройки детекции свингов
    swing_detection_lookback: int = Field(5, ge=3, le=20)  # N-bar lookback для свингов
    
    class Config:
        env_prefix = "TRADING_"


class StrategyConfig(BaseSettings):
    """Настройки стратегии 'Охота за ликвидностью'"""
    
    # Настройки детекции ликвидности (строго по стратегии)
    liquidity_sensitivity: float = Field(0.8, ge=0.1, le=1.0)
    min_liquidity_age: int = Field(5, ge=1, le=50)  # минимальный возраст свинга в барах
    max_liquidity_distance: float = Field(0.02, ge=0.001, le=0.1)  # максимальное расстояние до цены
    
    # Настройки Order Blocks (POI)
    ob_validity_period: int = Field(50, ge=10, le=200)  # валидность OB в барах
    ob_min_body_ratio: float = Field(0.6, ge=0.3, le=0.9)  # минимальный размер тела свечи
    
    # Настройки Fair Value Gaps (Imbalances)
    fvg_min_size: float = Field(0.001, ge=0.0001, le=0.01)  # минимальный размер FVG
    fvg_validity_period: int = Field(30, ge=5, le=100)
    
    # Настройки структуры рынка и Change of Character
    structure_confirmation_bars: int = Field(3, ge=1, le=10)  # подтверждение ChoCh
    trend_min_swings: int = Field(3, ge=2, le=10)
    
    # Premium/Discount зоны (СТРОГО ПО СТРАТЕГИИ)
    premium_discount_threshold: float = Field(0.5, ge=0.3, le=0.7)  # граница premium/discount на Фибо 0.5
    
    # ПРАВИЛЬНЫЕ ВЕСА КОНФЛЮЕНЦИИ СОГЛАСНО СТРАТЕГИИ
    confluence_weights: Dict[str, float] = {
        "market_structure": 0.20,  # Соответствие глобальному тренду
        "liquidity": 0.25,         # Близость к пулам ликвидности
        "poi": 0.25,              # Совпадение с POI (OB, FVG, S/R)
        "swing_structure": 0.15,   # Уважение ключевых уровней
        "fibonacci": 0.10,         # Совпадение с Фибо уровнями
        "time": 0.05              # Активные торговые сессии
    }
    
    # Настройки манипуляции (ключевой элемент стратегии)
    manipulation_detection_hours: int = Field(24, ge=1, le=72)  # окно для детекции манипуляции
    min_manipulation_distance: float = Field(0.005, ge=0.001, le=0.02)  # минимальное расстояние пробоя
    
    # Настройки человекоподобного мышления
    adaptation_factor: float = Field(0.1, ge=0.01, le=0.5)
    emotion_weight: float = Field(0.05, ge=0.0, le=0.2)
    context_memory_length: int = Field(20, ge=5, le=100)
    
    @validator('confluence_weights')
    def validate_weights_sum(cls, v):
        total = sum(v.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Веса конфлюенции должны в сумме давать 1.0, получено: {total}")
        return v
    
    class Config:
        env_prefix = "STRATEGY_"


class BacktestConfig(BaseSettings):
    """Настройки бэк-тестинга"""
    start_date: str = "2023-01-01"
    end_date: str = "2024-01-01"
    initial_balance: float = Field(10000.0, ge=1000.0)
    commission: float = Field(0.001, ge=0.0, le=0.01)  # 0.1% комиссия
    slippage: float = Field(0.0005, ge=0.0, le=0.01)  # 0.05% проскальзывание
    
    class Config:
        env_prefix = "BACKTEST_"


class DataConfig(BaseSettings):
    """Настройки данных"""
    data_path: Path = Path("data")
    cache_size: int = Field(1000, ge=100, le=10000)
    refresh_interval: int = Field(60, ge=10, le=3600)  # секунды
    
    # Настройки кэширования
    enable_cache: bool = True
    cache_ttl: int = Field(300, ge=60, le=3600)  # TTL кэша в секундах
    
    class Config:
        env_prefix = "DATA_"


class LoggingConfig(BaseSettings):
    """Настройки логирования"""
    level: str = "INFO"
    format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
    log_path: Path = Path("logs")
    max_size: str = "100 MB"
    retention: str = "30 days"
    
    class Config:
        env_prefix = "LOGGING_"


class SystemConfig(BaseSettings):
    """Основная конфигурация системы"""
    
    # Подконфигурации
    exchange: ExchangeConfig = ExchangeConfig()
    trading: TradingConfig = TradingConfig()
    strategy: StrategyConfig = StrategyConfig()
    backtest: BacktestConfig = BacktestConfig()
    data: DataConfig = DataConfig()
    logging: LoggingConfig = LoggingConfig()
    
    # Общие настройки системы
    debug_mode: bool = False
    enable_profiling: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    def __post_init__(self):
        """Создание необходимых директорий"""
        self.data.data_path.mkdir(exist_ok=True)
        self.logging.log_path.mkdir(exist_ok=True)


# Глобальный экземпляр конфигурации
config = SystemConfig()

# Alias for compatibility
Config = SystemConfig

# Функции для удобного доступа к конфигурации
def get_config() -> SystemConfig:
    """Получение глобальной конфигурации"""
    return config

def update_config(**kwargs) -> None:
    """Обновление глобальной конфигурации"""
    global config
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

def reset_config() -> None:
    """Сброс конфигурации к значениям по умолчанию"""
    global config
    config = SystemConfig()