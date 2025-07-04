"""
Главный файл торговой системы "Охота за ликвидностью"
"""

import asyncio
import sys
from datetime import datetime, timedelta
from loguru import logger

from config import get_config
from data.data_provider import ExchangeDataProvider
from analysis.market_structure import MarketStructureAnalyzer
from analysis.liquidity_detector import LiquidityDetector
from core.data_types import TimeFrame, MarketState


class LiquidityHuntingBot:
    """Основной класс торгового бота"""
    
    def __init__(self):
        self.config = get_config()
        self.data_provider = None
        self.market_analyzer = MarketStructureAnalyzer()
        self.liquidity_detector = LiquidityDetector()
        
        # Настройка логирования
        logger.add(
            self.config.logging.log_path / "trading_system.log",
            level=self.config.logging.level,
            format=self.config.logging.format,
            rotation=self.config.logging.max_size,
            retention=self.config.logging.retention
        )
    
    async def initialize(self):
        """Инициализация системы"""
        logger.info("Инициализация торговой системы...")
        
        # Инициализация провайдера данных
        self.data_provider = ExchangeDataProvider()
        await self.data_provider.connect()
        
        logger.info("Торговая система инициализирована")
    
    async def run_analysis(self):
        """Запуск анализа рынка"""
        try:
            symbol = self.config.trading.symbol
            
            # Получаем данные по всем таймфреймам
            timeframes = [
                *self.config.trading.strategic_timeframes,
                *self.config.trading.intermediate_timeframes,
                *self.config.trading.tactical_timeframes
            ]
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            for tf_str in timeframes:
                timeframe = TimeFrame.from_string(tf_str)
                
                # Получаем исторические данные
                data = await self.data_provider.get_historical_data(
                    symbol, timeframe, start_date, end_date
                )
                
                logger.info(f"Загружено {len(data)} свечей для {symbol} {tf_str}")
                
                # Анализируем структуру рынка
                structure = self.market_analyzer.analyze_structure(data)
                trend_strength = self.market_analyzer.calculate_trend_strength(data)
                
                # Получаем свинг-точки
                swing_points = self.market_analyzer.get_current_swing_points(data)
                
                # Детектируем ликвидность
                liquidity_pools = self.liquidity_detector.detect_liquidity_pools(
                    data, swing_points['highs'] + swing_points['lows']
                )
                
                logger.info(
                    f"{tf_str}: Структура={structure.value}, "
                    f"Сила тренда={trend_strength:.2f}, "
                    f"Свинги={len(swing_points['highs'])}H/{len(swing_points['lows'])}L, "
                    f"Ликвидность={len(liquidity_pools)} пулов"
                )
                
                # Показываем топ-3 пула ликвидности
                top_pools = sorted(liquidity_pools, key=lambda p: p.strength, reverse=True)[:3]
                for i, pool in enumerate(top_pools, 1):
                    logger.info(
                        f"  Пул #{i}: {pool.liquidity_type.value} "
                        f"@ {pool.price:.2f} (сила: {pool.strength:.2f})"
                    )
        
        except Exception as e:
            logger.error(f"Ошибка анализа: {e}")
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.data_provider:
            await self.data_provider.close()
        logger.info("Ресурсы системы освобождены")


async def main():
    """Главная функция"""
    bot = LiquidityHuntingBot()
    
    try:
        await bot.initialize()
        await bot.run_analysis()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await bot.cleanup()


if __name__ == "__main__":
    print("🚀 Запуск торговой системы 'Охота за ликвидностью'")
    print(f"📊 Символ: {get_config().trading.symbol}")
    print("📈 Анализ многотаймфреймовой структуры рынка...")
    
    asyncio.run(main())