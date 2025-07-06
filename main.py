"""
Главный файл торговой системы "Охота за ликвидностью"
СТРОГО СЛЕДУЕТ ИЕРАРХИИ ТАЙМФРЕЙМОВ СТРАТЕГИИ
"""

import asyncio
import sys
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd

from config import get_config
from data.data_provider import ExchangeDataProvider
from analysis.market_structure import MarketStructureAnalyzer
from analysis.liquidity_detector import LiquidityDetector
from trading.signal_generator import LiquidityHuntSignalGenerator
from core.data_types import TimeFrame, MarketState, ContextState


class LiquidityHuntingBot:
    """
    Основной класс торгового бота
    СТРОГО СЛЕДУЕТ СТРАТЕГИИ "ОХОТА ЗА ЛИКВИДНОСТЬЮ"
    """
    
    def __init__(self):
        self.config = get_config()
        self.data_provider = None
        self.market_analyzer = MarketStructureAnalyzer()
        self.liquidity_detector = LiquidityDetector()
        self.signal_generator = LiquidityHuntSignalGenerator()
        
        # Контекст для человекоподобного мышления
        self.context = ContextState()
        
        # Настройка логирования
        logger.add(
            self.config.logging.log_path / "liquidity_hunt.log",
            level=self.config.logging.level,
            format=self.config.logging.format,
            rotation=self.config.logging.max_size,
            retention=self.config.logging.retention
        )
    
    async def initialize(self):
        """Инициализация системы"""
        logger.info("🚀 Инициализация системы 'Охота за ликвидностью'...")
        
        # Инициализация провайдера данных
        self.data_provider = ExchangeDataProvider()
        await self.data_provider.connect()
        
        logger.info("✅ Торговая система инициализирована")
    
    async def run_complete_analysis(self):
        """
        ПОЛНЫЙ АНАЛИЗ ПО СТРАТЕГИИ:
        1. HTF Analysis (D1/H4) - Определение bias и целей
        2. Intermediate (H1/M30) - Уточнение зон
        3. LTF (M15/M5) - Тактический анализ  
        4. Снайперский (M1) - Точный вход
        """
        try:
            symbol = self.config.trading.symbol
            end_date = datetime.now()
            start_date = end_date - timedelta(days=90)  # 3 месяца данных
            
            logger.info(f"📊 Запуск анализа для {symbol}")
            logger.info("=" * 60)
            
            # ЭТАП 1: HTF АНАЛИЗ (Стратегические таймфреймы)
            logger.info("🔍 ЭТАП 1: СТРАТЕГИЧЕСКИЙ АНАЛИЗ (HTF)")
            htf_analysis = await self._analyze_htf_timeframes(symbol, start_date, end_date)
            
            if not htf_analysis['has_bias']:
                logger.warning("❌ HTF bias не определен - анализ остановлен")
                return
            
            logger.info(f"✅ HTF Bias: {htf_analysis['bias'].value}")
            
            # ЭТАП 2: ПРОМЕЖУТОЧНЫЕ ТАЙМФРЕЙМЫ
            logger.info("\n🔍 ЭТАП 2: ПРОМЕЖУТОЧНЫЙ АНАЛИЗ")
            intermediate_analysis = await self._analyze_intermediate_timeframes(
                symbol, start_date, end_date, htf_analysis
            )
            
            # ЭТАП 3: LTF АНАЛИЗ (Тактические таймфреймы)  
            logger.info("\n🔍 ЭТАП 3: ТАКТИЧЕСКИЙ АНАЛИЗ (LTF)")
            ltf_signals = await self._analyze_ltf_timeframes(
                symbol, start_date, end_date, htf_analysis, intermediate_analysis
            )
            
            # ЭТАП 4: СНАЙПЕРСКИЙ АНАЛИЗ (если есть сигналы)
            if ltf_signals:
                logger.info("\n🎯 ЭТАП 4: СНАЙПЕРСКИЙ АНАЛИЗ")
                await self._analyze_sniper_timeframe(symbol, ltf_signals)
            
            # Итоговый отчет
            self._generate_summary_report(htf_analysis, intermediate_analysis, ltf_signals)
        
        except Exception as e:
            logger.error(f"❌ Ошибка анализа: {e}")
    
    async def _analyze_htf_timeframes(self, symbol: str, start_date: datetime, end_date: datetime) -> dict:
        """ЭТАП 1: Анализ стратегических таймфреймов (D1/H4)"""
        htf_analysis = {
            'bias': None,
            'has_bias': False,
            'target_pools': [],
            'trap_zones': [],
            'strength': 0.0
        }
        
        for tf_str in self.config.trading.strategic_timeframes:
            timeframe = TimeFrame.from_string(tf_str)
            
            logger.info(f"  📈 Анализ {tf_str}...")
            
            # Получаем данные
            data = await self.data_provider.get_historical_data(
                symbol, timeframe, start_date, end_date
            )
            
            if len(data) < 50:
                logger.warning(f"  ⚠️ Недостаточно данных для {tf_str}")
                continue
            
            # Анализируем структуру
            structure = self.market_analyzer.analyze_structure(data)
            trend_strength = self.market_analyzer.calculate_trend_strength(data)
            
            # Получаем свинги
            swing_points = self.market_analyzer.get_current_swing_points(data)
            swing_highs = swing_points['highs']
            swing_lows = swing_points['lows']
            
            # Детектируем ликвидность
            liquidity_pools = self.liquidity_detector.detect_liquidity_pools(
                data, swing_highs + swing_lows
            )
            
            logger.info(f"    Структура: {structure.value}")
            logger.info(f"    Сила тренда: {trend_strength:.2f}")
            logger.info(f"    Свинги: {len(swing_highs)}H/{len(swing_lows)}L")
            logger.info(f"    Пулы ликвидности: {len(liquidity_pools)}")
            
            # Определяем bias на старшем таймфрейме
            if structure in [structure.BULLISH, structure.BEARISH] and trend_strength > 0.3:
                htf_analysis['bias'] = structure
                htf_analysis['has_bias'] = True
                htf_analysis['strength'] = trend_strength
                htf_analysis['target_pools'] = liquidity_pools
                
                logger.info(f"    ✅ Bias установлен: {structure.value}")
                
                # Показываем топ-3 пула ликвидности
                top_pools = sorted(liquidity_pools, key=lambda p: p.strength, reverse=True)[:3]
                for i, pool in enumerate(top_pools, 1):
                    logger.info(f"      Цель #{i}: {pool.liquidity_type.value} @ {pool.price:.2f} (сила: {pool.strength:.2f})")
        
        return htf_analysis
    
    async def _analyze_intermediate_timeframes(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime, 
        htf_analysis: dict
    ) -> dict:
        """ЭТАП 2: Анализ промежуточных таймфреймов (H1/M30)"""
        intermediate_analysis = {
            'refined_zones': [],
            'confirmation_strength': 0.0
        }
        
        if not htf_analysis['has_bias']:
            return intermediate_analysis
        
        for tf_str in self.config.trading.intermediate_timeframes:
            timeframe = TimeFrame.from_string(tf_str)
            
            logger.info(f"  📊 Уточнение на {tf_str}...")
            
            # Получаем данные
            data = await self.data_provider.get_historical_data(
                symbol, timeframe, start_date, end_date
            )
            
            if len(data) < 30:
                logger.warning(f"  ⚠️ Недостаточно данных для {tf_str}")
                continue
            
            # Анализируем структуру
            structure = self.market_analyzer.analyze_structure(data)
            
            # Проверяем соответствие HTF bias
            bias_alignment = (structure == htf_analysis['bias'])
            
            logger.info(f"    Структура: {structure.value}")
            logger.info(f"    Соответствие HTF: {'✅' if bias_alignment else '❌'}")
            
            if bias_alignment:
                intermediate_analysis['confirmation_strength'] += 0.5
                logger.info(f"    ✅ Подтверждение HTF bias")
        
        return intermediate_analysis
    
    async def _analyze_ltf_timeframes(
        self, 
        symbol: str, 
        start_date: datetime, 
        end_date: datetime, 
        htf_analysis: dict,
        intermediate_analysis: dict
    ) -> list:
        """ЭТАП 3: Анализ тактических таймфреймов (M15/M5) - поиск сигналов"""
        ltf_signals = []
        
        if not htf_analysis['has_bias']:
            return ltf_signals
        
        for tf_str in self.config.trading.tactical_timeframes:
            timeframe = TimeFrame.from_string(tf_str)
            
            logger.info(f"  🎯 Тактический анализ {tf_str}...")
            
            # Получаем данные
            data = await self.data_provider.get_historical_data(
                symbol, timeframe, start_date, end_date
            )
            
            if len(data) < 20:
                logger.warning(f"  ⚠️ Недостаточно данных для {tf_str}")
                continue
            
            # Создаем состояние рынка
            market_state = await self._create_market_state(
                symbol, timeframe, data, htf_analysis
            )
            
            # Генерируем сигналы
            signals = self.signal_generator.generate_signals(market_state, self.context)
            
            logger.info(f"    Сигналов найдено: {len(signals)}")
            
            for signal in signals:
                logger.info(f"    🎯 {signal.signal_type.value.upper()}: "
                           f"вход {signal.entry_price:.2f}, "
                           f"R:R {signal.risk_reward_ratio:.1f}, "
                           f"конфлюенция {signal.confluence_score:.2f}")
                
                ltf_signals.append({
                    'signal': signal,
                    'timeframe': tf_str,
                    'market_state': market_state
                })
        
        return ltf_signals
    
    async def _analyze_sniper_timeframe(self, symbol: str, ltf_signals: list):
        """ЭТАП 4: Снайперский анализ (M1) для точного входа"""
        if not ltf_signals:
            return
        
        logger.info("  🎯 Снайперский вход на M1...")
        
        # Берем лучший LTF сигнал
        best_signal_data = max(ltf_signals, key=lambda x: x['signal'].confluence_score)
        signal = best_signal_data['signal']
        
        logger.info(f"    Лучший сигнал: {signal.signal_type.value.upper()} "
                   f"@ {signal.entry_price:.2f} (конфлюенция: {signal.confluence_score:.2f})")
        
        # Получаем M1 данные для уточнения входа
        timeframe = TimeFrame.M1
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=4)  # Последние 4 часа
        
        m1_data = await self.data_provider.get_historical_data(
            symbol, timeframe, start_date, end_date
        )
        
        if len(m1_data) > 0:
            current_price = m1_data['close'].iloc[-1]
            distance_to_entry = abs(current_price - signal.entry_price) / signal.entry_price * 100
            
            logger.info(f"    Текущая цена: {current_price:.2f}")
            logger.info(f"    Расстояние до входа: {distance_to_entry:.2f}%")
            
            if distance_to_entry <= 1.0:  # В пределах 1%
                logger.info("    🎯 ГОТОВ К СНАЙПЕРСКОМУ ВХОДУ!")
            else:
                logger.info(f"    ⏳ Ожидание подхода к зоне входа")
    
    async def _create_market_state(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        data: pd.DataFrame,
        htf_analysis: dict
    ) -> MarketState:
        """Создание состояния рынка для анализа"""
        # Анализируем структуру
        structure = self.market_analyzer.analyze_structure(data)
        trend_strength = self.market_analyzer.calculate_trend_strength(data)
        
        # Получаем свинги
        swing_points = self.market_analyzer.get_current_swing_points(data)
        swing_highs = swing_points['highs']
        swing_lows = swing_points['lows']
        
        # Детектируем ликвидность
        liquidity_pools = self.liquidity_detector.detect_liquidity_pools(
            data, swing_highs + swing_lows
        )
        
        # Создаем состояние рынка
        market_state = MarketState(
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            structure=structure,
            trend_strength=trend_strength,
            swing_highs=swing_highs,
            swing_lows=swing_lows,
            liquidity_pools=liquidity_pools,
            active_pois=[],  # Упрощенно для демо
            fibonacci_levels={},  # Упрощенно для демо
            volatility=0.0
        )
        
        return market_state
    
    def _generate_summary_report(self, htf_analysis: dict, intermediate_analysis: dict, ltf_signals: list):
        """Генерация итогового отчета"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 ИТОГОВЫЙ ОТЧЕТ АНАЛИЗА")
        logger.info("=" * 60)
        
        if htf_analysis['has_bias']:
            logger.info(f"🎯 HTF Bias: {htf_analysis['bias'].value} (сила: {htf_analysis['strength']:.2f})")
            logger.info(f"🎯 Целей найдено: {len(htf_analysis['target_pools'])}")
        else:
            logger.info("❌ HTF Bias не определен")
        
        logger.info(f"🔄 Подтверждение промежуточных ТФ: {intermediate_analysis['confirmation_strength']:.1f}")
        logger.info(f"🎯 LTF сигналов: {len(ltf_signals)}")
        
        if ltf_signals:
            best_signal = max(ltf_signals, key=lambda x: x['signal'].confluence_score)['signal']
            logger.info(f"🏆 Лучший сигнал: {best_signal.signal_type.value.upper()} "
                       f"@ {best_signal.entry_price:.2f} "
                       f"(R:R {best_signal.risk_reward_ratio:.1f}, "
                       f"конфлюенция {best_signal.confluence_score:.2f})")
        
        logger.info("=" * 60)
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.data_provider:
            await self.data_provider.close()
        logger.info("🔄 Ресурсы системы освобождены")


async def main():
    """Главная функция"""
    bot = LiquidityHuntingBot()
    
    try:
        await bot.initialize()
        await bot.run_complete_analysis()
    except KeyboardInterrupt:
        logger.info("⏹️ Получен сигнал остановки")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
    finally:
        await bot.cleanup()


if __name__ == "__main__":
    print("🎯 ТОРГОВАЯ СИСТЕМА 'ОХОТА ЗА ЛИКВИДНОСТЬЮ'")
    print("=" * 50)
    print(f"📊 Символ: {get_config().trading.symbol}")
    print("� Стратегические ТФ: D1, H4 (определение bias)")
    print("📋 Промежуточные ТФ: H1, M30 (уточнение зон)")  
    print("📋 Тактические ТФ: M15, M5 (поиск сигналов)")
    print("📋 Снайперский ТФ: M1 (точный вход)")
    print("=" * 50)
    
    asyncio.run(main())