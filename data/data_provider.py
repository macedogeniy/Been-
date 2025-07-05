"""
Провайдер данных с биржи
"""

import asyncio
import ccxt.async_support as ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from loguru import logger
import time

from core.interfaces import IDataProvider
from core.data_types import TimeFrame, OHLCV
from core.exceptions import (
    DataProviderError, DataNotFoundError, ExchangeConnectionError, 
    RateLimitError, DataValidationError
)
from config import get_config


class ExchangeDataProvider(IDataProvider):
    """Провайдер данных с биржи через ccxt"""
    
    def __init__(self, exchange_name: Optional[str] = None):
        self.config = get_config()
        self.exchange_name = exchange_name or self.config.exchange.name
        self.exchange = None
        self.rate_limiter = asyncio.Semaphore(10)  # Лимит одновременных запросов
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Минимальный интервал между запросами
        
        # Кэш для данных
        self._cache: Dict[str, Dict] = {}
        self._cache_ttl = self.config.data.cache_ttl
        
        # Подписчики на обновления
        self._subscribers: Dict[str, List[Callable]] = {}
        
    async def __aenter__(self):
        """Асинхронный контекст-менеджер"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Закрытие соединения"""
        await self.close()
    
    async def connect(self) -> None:
        """Подключение к бирже"""
        try:
            exchange_class = getattr(ccxt, self.exchange_name)
            
            self.exchange = exchange_class({
                'apiKey': self.config.exchange.api_key,
                'secret': self.config.exchange.secret,
                'sandbox': self.config.exchange.sandbox,
                'timeout': self.config.exchange.timeout,
                'rateLimit': 60000 / self.config.exchange.rate_limit,  # мс между запросами
                'enableRateLimit': True,
            })
            
            await self.exchange.load_markets()
            logger.info(f"Подключение к бирже {self.exchange_name} успешно")
            
        except Exception as e:
            logger.error(f"Ошибка подключения к бирже {self.exchange_name}: {e}")
            raise ExchangeConnectionError(f"Не удалось подключиться к бирже: {e}")
    
    async def close(self) -> None:
        """Закрытие соединения"""
        if self.exchange:
            await self.exchange.close()
            logger.info(f"Соединение с биржей {self.exchange_name} закрыто")
    
    async def _rate_limit(self) -> None:
        """Контроль частоты запросов"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
    
    def _get_cache_key(self, symbol: str, timeframe: TimeFrame, **kwargs) -> str:
        """Генерация ключа кэша"""
        params = "_".join([f"{k}={v}" for k, v in sorted(kwargs.items())])
        return f"{symbol}_{timeframe.value}_{params}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Получение данных из кэша"""
        if not self.config.data.enable_cache:
            return None
            
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self._cache_ttl:
                logger.debug(f"Данные получены из кэша: {cache_key}")
                return cache_entry['data']
            else:
                # Удаляем устаревшие данные
                del self._cache[cache_key]
        
        return None
    
    def _store_in_cache(self, cache_key: str, data: pd.DataFrame) -> None:
        """Сохранение данных в кэш"""
        if not self.config.data.enable_cache:
            return
            
        self._cache[cache_key] = {
            'data': data.copy(),
            'timestamp': time.time()
        }
        
        # Очистка кэша при превышении размера
        if len(self._cache) > self.config.data.cache_size:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]
    
    def _validate_data(self, data: pd.DataFrame, symbol: str, timeframe: TimeFrame) -> None:
        """Валидация полученных данных"""
        if data.empty:
            raise DataNotFoundError(f"Нет данных для {symbol} {timeframe.value}")
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            raise DataValidationError(f"Отсутствуют колонки: {missing_columns}")
        
        # Проверка на NaN значения
        if data[required_columns].isna().any().any():
            logger.warning(f"Обнаружены NaN значения в данных {symbol} {timeframe.value}")
            data[required_columns] = data[required_columns].fillna(method='ffill')
        
        # Проверка корректности OHLC
        invalid_rows = (data['high'] < data['low']) | \
                      (data['high'] < data['open']) | \
                      (data['high'] < data['close']) | \
                      (data['low'] > data['open']) | \
                      (data['low'] > data['close'])
        
        if invalid_rows.any():
            logger.warning(f"Обнаружены некорректные OHLC данные в {symbol} {timeframe.value}")
            # Исправляем некорректные данные
            data.loc[invalid_rows, 'high'] = data.loc[invalid_rows, ['open', 'close']].max(axis=1)
            data.loc[invalid_rows, 'low'] = data.loc[invalid_rows, ['open', 'close']].min(axis=1)
    
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Получение исторических данных"""
        try:
            cache_key = self._get_cache_key(
                symbol, timeframe, 
                start=start_date.isoformat(), 
                end=end_date.isoformat()
            )
            
            # Проверяем кэш
            cached_data = self._get_from_cache(cache_key)
            if cached_data is not None:
                return cached_data
            
            # Подготовка параметров запроса
            since = int(start_date.timestamp() * 1000)
            end_timestamp = int(end_date.timestamp() * 1000)
            
            all_data = []
            current_since = since
            
            async with self.rate_limiter:
                while current_since < end_timestamp:
                    await self._rate_limit()
                    
                    try:
                        # Запрос данных с биржи
                        ohlcv = await self.exchange.fetch_ohlcv(
                            symbol=symbol,
                            timeframe=timeframe.value,
                            since=current_since,
                            limit=1000
                        )
                        
                        if not ohlcv:
                            break
                        
                        all_data.extend(ohlcv)
                        
                        # Обновляем позицию для следующего запроса
                        last_timestamp = ohlcv[-1][0]
                        if last_timestamp <= current_since:
                            break  # Избегаем бесконечного цикла
                        
                        current_since = last_timestamp + timeframe.to_seconds() * 1000
                        
                        # Логирование прогресса
                        if len(all_data) % 5000 == 0:
                            logger.info(f"Загружено {len(all_data)} свечей для {symbol} {timeframe.value}")
                    
                    except ccxt.RequestTimeout:
                        logger.warning("Таймаут запроса, повторная попытка через 1 секунду")
                        await asyncio.sleep(1)
                    except ccxt.RateLimitExceeded:
                        logger.warning("Превышен лимит запросов, ожидание 5 секунд")
                        await asyncio.sleep(5)
                        raise RateLimitError("Превышен лимит запросов к бирже")
            
            if not all_data:
                raise DataNotFoundError(f"Нет данных для {symbol} {timeframe.value} за период {start_date} - {end_date}")
            
            # Конвертация в DataFrame
            df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            
            # Фильтрация по датам
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # Валидация данных
            self._validate_data(df, symbol, timeframe)
            
            # Сохранение в кэш
            self._store_in_cache(cache_key, df)
            
            logger.info(f"Загружено {len(df)} свечей для {symbol} {timeframe.value}")
            return df
            
        except Exception as e:
            if isinstance(e, (DataProviderError, DataNotFoundError, RateLimitError)):
                raise
            logger.error(f"Ошибка получения исторических данных: {e}")
            raise DataProviderError(f"Ошибка получения данных: {e}")
    
    async def get_latest_candles(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        limit: int = 100
    ) -> pd.DataFrame:
        """Получение последних свечей"""
        try:
            cache_key = self._get_cache_key(symbol, timeframe, limit=limit, latest=True)
            
            # Для последних данных используем короткий TTL
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                short_ttl = min(30, self._cache_ttl)  # Максимум 30 секунд для актуальных данных
                if time.time() - cache_entry['timestamp'] < short_ttl:
                    return cache_entry['data']
            
            async with self.rate_limiter:
                await self._rate_limit()
                
                ohlcv = await self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe.value,
                    limit=limit
                )
            
            if not ohlcv:
                raise DataNotFoundError(f"Нет последних данных для {symbol} {timeframe.value}")
            
            # Конвертация в DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            df = df.astype(float)
            
            # Валидация данных
            self._validate_data(df, symbol, timeframe)
            
            # Сохранение в кэш
            self._store_in_cache(cache_key, df)
            
            logger.debug(f"Получено {len(df)} последних свечей для {symbol} {timeframe.value}")
            return df
            
        except Exception as e:
            if isinstance(e, (DataProviderError, DataNotFoundError, RateLimitError)):
                raise
            logger.error(f"Ошибка получения последних данных: {e}")
            raise DataProviderError(f"Ошибка получения данных: {e}")
    
    async def subscribe_to_updates(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        callback: Callable[[pd.DataFrame], None]
    ) -> None:
        """Подписка на обновления данных"""
        key = f"{symbol}_{timeframe.value}"
        
        if key not in self._subscribers:
            self._subscribers[key] = []
        
        self._subscribers[key].append(callback)
        logger.info(f"Добавлена подписка на обновления {symbol} {timeframe.value}")
        
        # Запуск задачи обновления для нового символа
        if len(self._subscribers[key]) == 1:
            asyncio.create_task(self._update_loop(symbol, timeframe))
    
    async def _update_loop(self, symbol: str, timeframe: TimeFrame) -> None:
        """Цикл обновления данных для подписчиков"""
        key = f"{symbol}_{timeframe.value}"
        update_interval = max(timeframe.to_seconds(), self.config.data.refresh_interval)
        
        logger.info(f"Запущен цикл обновления для {symbol} {timeframe.value}")
        
        while key in self._subscribers and self._subscribers[key]:
            try:
                # Получаем последние данные
                latest_data = await self.get_latest_candles(symbol, timeframe, limit=1)
                
                # Уведомляем всех подписчиков
                for callback in self._subscribers[key].copy():  # copy для безопасности
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(latest_data)
                        else:
                            callback(latest_data)
                    except Exception as e:
                        logger.error(f"Ошибка в callback для {symbol} {timeframe.value}: {e}")
                
                await asyncio.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в цикле обновления для {symbol} {timeframe.value}: {e}")
                await asyncio.sleep(60)  # Ожидание перед повторной попыткой
        
        logger.info(f"Цикл обновления для {symbol} {timeframe.value} остановлен")
    
    def unsubscribe_from_updates(
        self, 
        symbol: str, 
        timeframe: TimeFrame, 
        callback: Callable[[pd.DataFrame], None]
    ) -> None:
        """Отписка от обновлений данных"""
        key = f"{symbol}_{timeframe.value}"
        
        if key in self._subscribers and callback in self._subscribers[key]:
            self._subscribers[key].remove(callback)
            logger.info(f"Удалена подписка на обновления {symbol} {timeframe.value}")
            
            # Удаляем ключ если нет подписчиков
            if not self._subscribers[key]:
                del self._subscribers[key]
    
    async def get_ticker_info(self, symbol: str) -> Dict[str, Any]:
        """Получение информации о тикере"""
        try:
            async with self.rate_limiter:
                await self._rate_limit()
                ticker = await self.exchange.fetch_ticker(symbol)
            
            return {
                'symbol': ticker['symbol'],
                'last_price': ticker['last'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
                'volume': ticker['baseVolume'],
                'change_24h': ticker['change'],
                'change_percent_24h': ticker['percentage'],
                'timestamp': datetime.fromtimestamp(ticker['timestamp'] / 1000)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о тикере {symbol}: {e}")
            raise DataProviderError(f"Ошибка получения тикера: {e}")
    
    async def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """Получение стакана цен"""
        try:
            async with self.rate_limiter:
                await self._rate_limit()
                order_book = await self.exchange.fetch_order_book(symbol, limit)
            
            return {
                'symbol': symbol,
                'bids': order_book['bids'],
                'asks': order_book['asks'],
                'timestamp': datetime.fromtimestamp(order_book['timestamp'] / 1000)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения стакана для {symbol}: {e}")
            raise DataProviderError(f"Ошибка получения стакана: {e}")
    
    def get_supported_symbols(self) -> List[str]:
        """Получение списка поддерживаемых символов"""
        if not self.exchange:
            raise ExchangeConnectionError("Не подключен к бирже")
        
        return list(self.exchange.markets.keys())
    
    def get_supported_timeframes(self) -> List[str]:
        """Получение списка поддерживаемых таймфреймов"""
        if not self.exchange:
            raise ExchangeConnectionError("Не подключен к бирже")
        
        return list(self.exchange.timeframes.keys())
    
    def clear_cache(self) -> None:
        """Очистка кэша"""
        self._cache.clear()
        logger.info("Кэш данных очищен")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Статистика кэша"""
        total_size = sum(len(entry['data']) for entry in self._cache.values())
        return {
            'entries': len(self._cache),
            'total_rows': total_size,
            'memory_usage_mb': total_size * 8 * 6 / (1024 * 1024),  # Примерная оценка
            'cache_hit_ratio': getattr(self, '_cache_hits', 0) / getattr(self, '_cache_requests', 1)
        }


# Alias for compatibility
DataProvider = ExchangeDataProvider