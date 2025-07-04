"""
Базовые типы данных торговой системы
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any
import pandas as pd
import numpy as np


class TimeFrame(Enum):
    """Таймфреймы"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    
    @classmethod
    def from_string(cls, timeframe: str) -> 'TimeFrame':
        """Создание таймфрейма из строки"""
        for tf in cls:
            if tf.value == timeframe:
                return tf
        raise ValueError(f"Неизвестный таймфрейм: {timeframe}")
    
    def to_seconds(self) -> int:
        """Конвертация в секунды"""
        mapping = {
            self.M1: 60,
            self.M5: 300,
            self.M15: 900,
            self.M30: 1800,
            self.H1: 3600,
            self.H4: 14400,
            self.D1: 86400
        }
        return mapping[self]


class MarketStructure(Enum):
    """Структура рынка"""
    BULLISH = "bullish"        # Бычья структура
    BEARISH = "bearish"        # Медвежья структура
    RANGING = "ranging"        # Боковик
    UNDEFINED = "undefined"    # Неопределенная


class SignalType(Enum):
    """Типы сигналов"""
    BUY = "buy"
    SELL = "sell"
    CLOSE_BUY = "close_buy"
    CLOSE_SELL = "close_sell"


class OrderType(Enum):
    """Типы ордеров"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class PositionStatus(Enum):
    """Статусы позиций"""
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class LiquidityType(Enum):
    """Типы ликвидности"""
    BSL = "buy_side_liquidity"    # Buy Side Liquidity
    SSL = "sell_side_liquidity"   # Sell Side Liquidity


class POIType(Enum):
    """Типы зон интереса (Points of Interest)"""
    ORDER_BLOCK = "order_block"        # Ордер блок
    IMBALANCE = "imbalance"            # Дисбаланс (FVG)
    SUPPORT = "support"                # Поддержка
    RESISTANCE = "resistance"          # Сопротивление
    FIBONACCI = "fibonacci"            # Фибоначчи уровень


@dataclass
class OHLCV:
    """Данные свечи"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    @property
    def body_size(self) -> float:
        """Размер тела свечи"""
        return abs(self.close - self.open)
    
    @property
    def upper_wick(self) -> float:
        """Верхняя тень"""
        return self.high - max(self.open, self.close)
    
    @property
    def lower_wick(self) -> float:
        """Нижняя тень"""
        return min(self.open, self.close) - self.low
    
    @property
    def is_bullish(self) -> bool:
        """Является ли свеча бычьей"""
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        """Является ли свеча медвежьей"""
        return self.close < self.open
    
    @property
    def body_ratio(self) -> float:
        """Отношение тела к общей высоте"""
        total_range = self.high - self.low
        return self.body_size / total_range if total_range > 0 else 0


@dataclass
class SwingPoint:
    """Свинг-точка"""
    timestamp: datetime
    price: float
    is_high: bool  # True для свинг-хая, False для свинг-лоу
    strength: float  # Сила свинга (0-1)
    confirmed: bool = False
    
    @property
    def swing_type(self) -> str:
        return "high" if self.is_high else "low"


@dataclass
class LiquidityPool:
    """Пул ликвидности"""
    price: float
    liquidity_type: LiquidityType
    strength: float  # Сила пула (0-1)
    volume: float   # Объем ликвидности
    created_at: datetime
    swept: bool = False  # Была ли снята ликвидность
    swept_at: Optional[datetime] = None
    
    @property
    def age(self) -> float:
        """Возраст пула в часах"""
        now = datetime.now()
        return (now - self.created_at).total_seconds() / 3600


@dataclass
class POI:
    """Зона интереса (Point of Interest)"""
    start_time: datetime
    end_time: datetime
    high_price: float
    low_price: float
    poi_type: POIType
    strength: float  # Сила зоны (0-1)
    tested: bool = False  # Была ли протестирована зона
    test_count: int = 0
    created_by_candle: Optional[OHLCV] = None
    
    @property
    def price_range(self) -> float:
        """Диапазон цен зоны"""
        return self.high_price - self.low_price
    
    @property
    def mid_price(self) -> float:
        """Средняя цена зоны"""
        return (self.high_price + self.low_price) / 2
    
    def contains_price(self, price: float) -> bool:
        """Проверка, содержит ли зона цену"""
        return self.low_price <= price <= self.high_price


@dataclass
class Signal:
    """Торговый сигнал"""
    timestamp: datetime
    signal_type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    confluence_score: float  # Скор конфлюенции (0-1)
    timeframe: TimeFrame
    
    # Контекст сигнала
    market_structure: MarketStructure
    liquidity_context: List[LiquidityPool] = field(default_factory=list)
    poi_context: List[POI] = field(default_factory=list)
    
    # Метаданные
    strategy_version: str = "1.0"
    notes: str = ""
    
    @property
    def risk_reward_ratio(self) -> float:
        """Соотношение риск/прибыль"""
        risk = abs(self.entry_price - self.stop_loss)
        reward = abs(self.take_profit - self.entry_price)
        return reward / risk if risk > 0 else 0
    
    @property
    def is_long(self) -> bool:
        """Является ли сигнал лонгом"""
        return self.signal_type == SignalType.BUY
    
    @property
    def is_short(self) -> bool:
        """Является ли сигнал шортом"""
        return self.signal_type == SignalType.SELL


@dataclass
class Trade:
    """Выполненная сделка"""
    trade_id: str
    signal: Signal
    entry_time: datetime
    entry_price: float
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    quantity: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    status: PositionStatus = PositionStatus.OPEN
    
    # Метрики сделки
    pnl: float = 0.0
    pnl_percentage: float = 0.0
    max_favorable_excursion: float = 0.0  # MFE
    max_adverse_excursion: float = 0.0    # MAE
    
    @property
    def duration(self) -> Optional[float]:
        """Продолжительность сделки в часах"""
        if self.exit_time:
            return (self.exit_time - self.entry_time).total_seconds() / 3600
        return None
    
    @property
    def is_winner(self) -> bool:
        """Является ли сделка прибыльной"""
        return self.pnl > 0
    
    @property
    def is_closed(self) -> bool:
        """Закрыта ли сделка"""
        return self.status == PositionStatus.CLOSED


@dataclass
class MarketState:
    """Состояние рынка"""
    timestamp: datetime
    symbol: str
    timeframe: TimeFrame
    
    # Структура рынка
    structure: MarketStructure
    trend_strength: float  # Сила тренда (0-1)
    
    # Свинги
    swing_highs: List[SwingPoint] = field(default_factory=list)
    swing_lows: List[SwingPoint] = field(default_factory=list)
    
    # Ликвидность
    liquidity_pools: List[LiquidityPool] = field(default_factory=list)
    
    # Зоны интереса
    active_pois: List[POI] = field(default_factory=list)
    
    # Уровни Фибоначчи
    fibonacci_levels: Dict[float, float] = field(default_factory=dict)
    
    # Дополнительные метрики
    volatility: float = 0.0
    volume_profile: Dict[float, float] = field(default_factory=dict)


@dataclass
class BacktestResult:
    """Результат бэк-теста"""
    start_date: datetime
    end_date: datetime
    initial_balance: float
    final_balance: float
    
    # Статистика сделок
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # Финансовые метрики
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Данные для графиков
    equity_curve: pd.Series = field(default_factory=pd.Series)
    drawdown_curve: pd.Series = field(default_factory=pd.Series)
    
    # Детализация сделок
    trades: List[Trade] = field(default_factory=list)
    
    @property
    def profit_factor(self) -> float:
        """Profit Factor"""
        gross_profit = sum(t.pnl for t in self.trades if t.pnl > 0)
        gross_loss = abs(sum(t.pnl for t in self.trades if t.pnl < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    @property
    def average_trade(self) -> float:
        """Средняя прибыль на сделку"""
        return sum(t.pnl for t in self.trades) / len(self.trades) if self.trades else 0


@dataclass 
class ContextState:
    """Контекстное состояние для человекоподобного мышления"""
    recent_trades: List[Trade] = field(default_factory=list)
    recent_signals: List[Signal] = field(default_factory=list)
    market_regime: str = "normal"  # normal, high_volatility, low_volatility
    confidence_level: float = 0.5  # Уровень уверенности (0-1)
    adaptation_factor: float = 0.1
    
    # Эмоциональные факторы
    fear_factor: float = 0.0  # Фактор страха (0-1)
    greed_factor: float = 0.0  # Фактор жадности (0-1)
    
    # Память о рыночных событиях
    significant_events: List[Dict[str, Any]] = field(default_factory=list)


# Вспомогательные функции
def ohlcv_from_dataframe(df: pd.DataFrame) -> List[OHLCV]:
    """Конвертация DataFrame в список OHLCV"""
    ohlcv_list = []
    for _, row in df.iterrows():
        ohlcv = OHLCV(
            timestamp=pd.to_datetime(row.name) if hasattr(row, 'name') else datetime.now(),
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            volume=float(row['volume']) if 'volume' in row else 0.0
        )
        ohlcv_list.append(ohlcv)
    return ohlcv_list


def dataframe_from_ohlcv(ohlcv_list: List[OHLCV]) -> pd.DataFrame:
    """Конвертация списка OHLCV в DataFrame"""
    data = []
    for candle in ohlcv_list:
        data.append({
            'timestamp': candle.timestamp,
            'open': candle.open,
            'high': candle.high,
            'low': candle.low,
            'close': candle.close,
            'volume': candle.volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df