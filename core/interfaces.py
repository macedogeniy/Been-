"""
Интерфейсы компонентов торговой системы
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
from datetime import datetime

from .data_types import (
    OHLCV, TimeFrame, Signal, Trade, MarketState, 
    SwingPoint, LiquidityPool, POI, BacktestResult,
    MarketStructure, ContextState
)


class IDataProvider(ABC):
    """Интерфейс провайдера данных"""
    
    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Получение исторических данных"""
        pass
    
    @abstractmethod
    async def get_latest_candles(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        limit: int = 100
    ) -> pd.DataFrame:
        """Получение последних свечей"""
        pass
    
    @abstractmethod
    async def subscribe_to_updates(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        callback
    ) -> None:
        """Подписка на обновления данных"""
        pass


class IMarketStructureAnalyzer(ABC):
    """Интерфейс анализатора структуры рынка"""
    
    @abstractmethod
    def analyze_structure(self, data: pd.DataFrame) -> MarketStructure:
        """Анализ структуры рынка"""
        pass
    
    @abstractmethod
    def detect_swings(self, data: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """Детекция свинг-точек (хаи, лоу)"""
        pass
    
    @abstractmethod
    def confirm_structure_break(
        self, 
        data: pd.DataFrame, 
        current_structure: MarketStructure
    ) -> bool:
        """Подтверждение слома структуры"""
        pass
    
    @abstractmethod
    def calculate_trend_strength(self, data: pd.DataFrame) -> float:
        """Расчет силы тренда"""
        pass


class ILiquidityDetector(ABC):
    """Интерфейс детектора ликвидности"""
    
    @abstractmethod
    def detect_liquidity_pools(
        self, 
        data: pd.DataFrame, 
        swing_points: List[SwingPoint]
    ) -> List[LiquidityPool]:
        """Детекция пулов ликвидности"""
        pass
    
    @abstractmethod
    def check_liquidity_sweep(
        self, 
        current_price: float, 
        liquidity_pools: List[LiquidityPool]
    ) -> List[LiquidityPool]:
        """Проверка снятия ликвидности"""
        pass
    
    @abstractmethod
    def calculate_liquidity_strength(
        self, 
        swing_point: SwingPoint, 
        volume_data: pd.Series
    ) -> float:
        """Расчет силы ликвидности"""
        pass


class IPOIIdentifier(ABC):
    """Интерфейс идентификатора зон интереса"""
    
    @abstractmethod
    def identify_order_blocks(self, data: pd.DataFrame) -> List[POI]:
        """Идентификация ордер-блоков"""
        pass
    
    @abstractmethod
    def identify_imbalances(self, data: pd.DataFrame) -> List[POI]:
        """Идентификация дисбалансов (FVG)"""
        pass
    
    @abstractmethod
    def identify_support_resistance(self, data: pd.DataFrame) -> List[POI]:
        """Идентификация уровней поддержки/сопротивления"""
        pass
    
    @abstractmethod
    def calculate_fibonacci_levels(
        self, 
        swing_high: SwingPoint, 
        swing_low: SwingPoint
    ) -> Dict[float, float]:
        """Расчет уровней Фибоначчи"""
        pass
    
    @abstractmethod
    def validate_poi_relevance(self, poi: POI, current_time: datetime) -> bool:
        """Валидация актуальности зоны интереса"""
        pass


class ISignalGenerator(ABC):
    """Интерфейс генератора сигналов"""
    
    @abstractmethod
    def generate_signals(
        self, 
        market_state: MarketState, 
        context: ContextState
    ) -> List[Signal]:
        """Генерация торговых сигналов"""
        pass
    
    @abstractmethod
    def calculate_confluence_score(
        self, 
        market_state: MarketState, 
        entry_price: float
    ) -> float:
        """Расчет скора конфлюенции"""
        pass
    
    @abstractmethod
    def determine_entry_levels(
        self, 
        market_state: MarketState, 
        signal_direction: str
    ) -> Tuple[float, float, float]:
        """Определение уровней входа, стопа и тейка"""
        pass
    
    @abstractmethod
    def filter_signals(
        self, 
        signals: List[Signal], 
        context: ContextState
    ) -> List[Signal]:
        """Фильтрация сигналов по качеству"""
        pass


class IRiskManager(ABC):
    """Интерфейс менеджера рисков"""
    
    @abstractmethod
    def calculate_position_size(
        self, 
        signal: Signal, 
        account_balance: float
    ) -> float:
        """Расчет размера позиции"""
        pass
    
    @abstractmethod
    def validate_risk_parameters(self, signal: Signal) -> bool:
        """Валидация риск-параметров сигнала"""
        pass
    
    @abstractmethod
    def check_correlation_risk(
        self, 
        new_signal: Signal, 
        open_positions: List[Trade]
    ) -> bool:
        """Проверка корреляционного риска"""
        pass
    
    @abstractmethod
    def update_stop_loss(
        self, 
        trade: Trade, 
        current_price: float, 
        market_state: MarketState
    ) -> Optional[float]:
        """Обновление стоп-лосса"""
        pass


class IBacktester(ABC):
    """Интерфейс бэк-тестера"""
    
    @abstractmethod
    def run_backtest(
        self, 
        start_date: datetime, 
        end_date: datetime, 
        initial_balance: float
    ) -> BacktestResult:
        """Запуск бэк-теста"""
        pass
    
    @abstractmethod
    def simulate_trade_execution(
        self, 
        signal: Signal, 
        market_data: pd.DataFrame, 
        current_balance: float
    ) -> Trade:
        """Симуляция исполнения сделки"""
        pass
    
    @abstractmethod
    def calculate_performance_metrics(self, trades: List[Trade]) -> Dict[str, float]:
        """Расчет метрик производительности"""
        pass
    
    @abstractmethod
    def generate_equity_curve(self, trades: List[Trade]) -> pd.Series:
        """Генерация кривой капитала"""
        pass


class IVisualizer(ABC):
    """Интерфейс визуализатора"""
    
    @abstractmethod
    def plot_price_chart(
        self, 
        data: pd.DataFrame, 
        market_state: MarketState, 
        signals: Optional[List[Signal]] = None
    ):
        """Построение ценового графика"""
        pass
    
    @abstractmethod
    def plot_backtest_results(self, result: BacktestResult):
        """Визуализация результатов бэк-теста"""
        pass
    
    @abstractmethod
    def plot_liquidity_analysis(
        self, 
        data: pd.DataFrame, 
        liquidity_pools: List[LiquidityPool]
    ):
        """Визуализация анализа ликвидности"""
        pass
    
    @abstractmethod
    def create_dashboard(self, results: Dict[str, Any]):
        """Создание интерактивного дашборда"""
        pass


class ILogger(ABC):
    """Интерфейс логгера"""
    
    @abstractmethod
    def log_signal(self, signal: Signal) -> None:
        """Логирование сигнала"""
        pass
    
    @abstractmethod
    def log_trade(self, trade: Trade) -> None:
        """Логирование сделки"""
        pass
    
    @abstractmethod
    def log_market_state(self, market_state: MarketState) -> None:
        """Логирование состояния рынка"""
        pass
    
    @abstractmethod
    def log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Логирование ошибки"""
        pass
    
    @abstractmethod
    def log_performance(self, metrics: Dict[str, float]) -> None:
        """Логирование метрик производительности"""
        pass


class IDataStorage(ABC):
    """Интерфейс хранилища данных"""
    
    @abstractmethod
    async def save_candles(self, symbol: str, timeframe: TimeFrame, data: pd.DataFrame) -> None:
        """Сохранение данных свечей"""
        pass
    
    @abstractmethod
    async def load_candles(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Загрузка данных свечей"""
        pass
    
    @abstractmethod
    async def save_signals(self, signals: List[Signal]) -> None:
        """Сохранение сигналов"""
        pass
    
    @abstractmethod
    async def save_trades(self, trades: List[Trade]) -> None:
        """Сохранение сделок"""
        pass
    
    @abstractmethod
    async def save_backtest_result(self, result: BacktestResult) -> None:
        """Сохранение результата бэк-теста"""
        pass


class IContextManager(ABC):
    """Интерфейс менеджера контекста для человекоподобного мышления"""
    
    @abstractmethod
    def update_context(
        self, 
        new_trade: Optional[Trade] = None, 
        new_signal: Optional[Signal] = None,
        market_event: Optional[Dict[str, Any]] = None
    ) -> None:
        """Обновление контекста"""
        pass
    
    @abstractmethod
    def get_current_context(self) -> ContextState:
        """Получение текущего контекста"""
        pass
    
    @abstractmethod
    def calculate_confidence_level(self, market_state: MarketState) -> float:
        """Расчет уровня уверенности"""
        pass
    
    @abstractmethod
    def adapt_strategy_parameters(
        self, 
        recent_performance: Dict[str, float]
    ) -> Dict[str, float]:
        """Адаптация параметров стратегии"""
        pass
    
    @abstractmethod
    def detect_market_regime_change(self, market_data: pd.DataFrame) -> str:
        """Детекция смены рыночного режима"""
        pass


class ITimeFrameSynchronizer(ABC):
    """Интерфейс синхронизатора таймфреймов"""
    
    @abstractmethod
    def synchronize_data(
        self, 
        multi_tf_data: Dict[TimeFrame, pd.DataFrame]
    ) -> Dict[TimeFrame, pd.DataFrame]:
        """Синхронизация данных по таймфреймам"""
        pass
    
    @abstractmethod
    def align_timestamps(
        self, 
        primary_tf: TimeFrame, 
        secondary_tf: TimeFrame, 
        primary_data: pd.DataFrame,
        secondary_data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Выравнивание временных меток"""
        pass
    
    @abstractmethod
    def propagate_analysis_results(
        self, 
        source_tf: TimeFrame, 
        target_tf: TimeFrame, 
        analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Пропагирование результатов анализа между таймфреймами"""
        pass


class IPerformanceMonitor(ABC):
    """Интерфейс монитора производительности"""
    
    @abstractmethod
    def start_monitoring(self) -> None:
        """Запуск мониторинга"""
        pass
    
    @abstractmethod
    def stop_monitoring(self) -> None:
        """Остановка мониторинга"""
        pass
    
    @abstractmethod
    def record_execution_time(self, function_name: str, execution_time: float) -> None:
        """Запись времени выполнения"""
        pass
    
    @abstractmethod
    def record_memory_usage(self, component_name: str, memory_mb: float) -> None:
        """Запись использования памяти"""
        pass
    
    @abstractmethod
    def get_performance_report(self) -> Dict[str, Any]:
        """Получение отчета о производительности"""
        pass


class IEventBus(ABC):
    """Интерфейс шины событий"""
    
    @abstractmethod
    def subscribe(self, event_type: str, callback) -> None:
        """Подписка на событие"""
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, callback) -> None:
        """Отписка от события"""
        pass
    
    @abstractmethod
    async def publish(self, event_type: str, data: Any) -> None:
        """Публикация события"""
        pass
    
    @abstractmethod
    def clear_subscribers(self, event_type: Optional[str] = None) -> None:
        """Очистка подписчиков"""
        pass