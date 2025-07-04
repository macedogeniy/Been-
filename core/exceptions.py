"""
Исключения торговой системы
"""


class TradingSystemError(Exception):
    """Базовое исключение торговой системы"""
    pass


class DataProviderError(TradingSystemError):
    """Ошибки провайдера данных"""
    pass


class DataNotFoundError(DataProviderError):
    """Данные не найдены"""
    pass


class DataValidationError(DataProviderError):
    """Ошибка валидации данных"""
    pass


class ExchangeConnectionError(DataProviderError):
    """Ошибка подключения к бирже"""
    pass


class RateLimitError(DataProviderError):
    """Превышен лимит запросов"""
    pass


class MarketAnalysisError(TradingSystemError):
    """Ошибки анализа рынка"""
    pass


class StructureAnalysisError(MarketAnalysisError):
    """Ошибка анализа структуры рынка"""
    pass


class LiquidityDetectionError(MarketAnalysisError):
    """Ошибка детекции ликвидности"""
    pass


class POIIdentificationError(MarketAnalysisError):
    """Ошибка идентификации зон интереса"""
    pass


class SignalGenerationError(TradingSystemError):
    """Ошибки генерации сигналов"""
    pass


class InvalidSignalError(SignalGenerationError):
    """Невалидный сигнал"""
    pass


class ConfluenceError(SignalGenerationError):
    """Ошибка расчета конфлюенции"""
    pass


class RiskManagementError(TradingSystemError):
    """Ошибки управления рисками"""
    pass


class PositionSizeError(RiskManagementError):
    """Ошибка расчета размера позиции"""
    pass


class RiskLimitExceededError(RiskManagementError):
    """Превышен лимит риска"""
    pass


class CorrelationRiskError(RiskManagementError):
    """Ошибка корреляционного риска"""
    pass


class BacktestError(TradingSystemError):
    """Ошибки бэк-тестинга"""
    pass


class TradeExecutionError(BacktestError):
    """Ошибка исполнения сделки"""
    pass


class MetricsCalculationError(BacktestError):
    """Ошибка расчета метрик"""
    pass


class ConfigurationError(TradingSystemError):
    """Ошибки конфигурации"""
    pass


class InvalidConfigError(ConfigurationError):
    """Невалидная конфигурация"""
    pass


class MissingConfigError(ConfigurationError):
    """Отсутствующая конфигурация"""
    pass


class StorageError(TradingSystemError):
    """Ошибки хранилища данных"""
    pass


class DatabaseError(StorageError):
    """Ошибка базы данных"""
    pass


class CacheError(StorageError):
    """Ошибка кэша"""
    pass


class VisualizationError(TradingSystemError):
    """Ошибки визуализации"""
    pass


class ChartError(VisualizationError):
    """Ошибка построения графика"""
    pass


class DashboardError(VisualizationError):
    """Ошибка дашборда"""
    pass


class ContextError(TradingSystemError):
    """Ошибки контекста"""
    pass


class ContextUpdateError(ContextError):
    """Ошибка обновления контекста"""
    pass


class AdaptationError(ContextError):
    """Ошибка адаптации"""
    pass


class SynchronizationError(TradingSystemError):
    """Ошибки синхронизации"""
    pass


class TimeFrameSyncError(SynchronizationError):
    """Ошибка синхронизации таймфреймов"""
    pass


class DataAlignmentError(SynchronizationError):
    """Ошибка выравнивания данных"""
    pass