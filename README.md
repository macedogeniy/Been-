# 🎯 Торговая система "Охота за ликвидностью"

Профессиональная торговая система для бэк-тестов, реализующая стратегию "Охота за ликвидностью" для пары BTC/USDT.

## 🔥 Особенности

- **Многотаймфреймовый анализ**: Иерархическая система анализа от D1 до M1
- **Детекция ликвидности**: Поиск BSL/SSL пулов на основе свинг-точек
- **Структурный анализ**: Определение HH/HL и LL/LH паттернов
- **Человекоподобное мышление**: Адаптивная логика принятия решений
- **Реалтайм данные**: Подключение к биржам через CCXT
- **Асинхронная архитектура**: Высокая производительность
- **Профессиональный код**: Типизация, тесты, логирование

## 🏗️ Архитектура

```
liquidity_hunting_system/
├── core/                    # Базовые классы и интерфейсы
│   ├── data_types.py       # Типы данных (OHLCV, Signal, Trade и др.)
│   ├── interfaces.py       # Интерфейсы компонентов
│   └── exceptions.py       # Исключения системы
├── data/                   # Модули работы с данными
│   └── data_provider.py    # Провайдер данных с бирж
├── analysis/               # Модули анализа рынка
│   ├── market_structure.py # Анализ структуры рынка
│   └── liquidity_detector.py # Детектор ликвидности
├── config.py              # Конфигурация системы
├── main.py               # Главный файл
└── requirements.txt      # Зависимости
```

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Конфигурация

Создайте файл `.env`:

```env
# Настройки биржи
EXCHANGE_NAME=binance
EXCHANGE_SANDBOX=true
EXCHANGE_API_KEY=your_api_key
EXCHANGE_SECRET=your_secret

# Торговые настройки
TRADING_SYMBOL=BTC/USDT
TRADING_MAX_RISK_PER_TRADE=0.02

# Настройки данных
DATA_CACHE_TTL=300
DATA_ENABLE_CACHE=true
```

### 3. Запуск анализа

```bash
python main.py
```

## 📊 Стратегия "Охота за ликвидностью"

### Концепция

Стратегия основана на понимании того, как маркет-мейкеры используют ликвидность розничных трейдеров:

1. **Манипуляция**: ММ снимают ликвидность (SSL/BSL)
2. **Ловушка**: Розничные трейдеры попадают в противоположную позицию
3. **Экспансия**: Истинное движение в направлении ММ

### Иерархия таймфреймов

- **D1/H4** (Стратегические): Глобальная структура и ключевые пулы ликвидности
- **H1/M30** (Промежуточные): Подтверждение манипуляции и уточнение зон
- **M15/M5** (Тактические): Слом структуры и определение точек входа
- **M1** (Снайперский): Ювелирное уточнение входа

### Ключевые элементы

```python
# Структура рынка
class MarketStructure(Enum):
    BULLISH = "bullish"    # HH + HL
    BEARISH = "bearish"    # LL + LH
    RANGING = "ranging"    # Боковик
    UNDEFINED = "undefined"

# Типы ликвидности
class LiquidityType(Enum):
    BSL = "buy_side_liquidity"   # Над свинг-хаями
    SSL = "sell_side_liquidity"  # Под свинг-лоу

# Зоны интереса
class POIType(Enum):
    ORDER_BLOCK = "order_block"      # Последняя противоположная свеча
    IMBALANCE = "imbalance"          # Fair Value Gap
    SUPPORT = "support"              # Уровень поддержки
    RESISTANCE = "resistance"        # Уровень сопротивления
```

## 🔧 Использование компонентов

### Анализ структуры рынка

```python
from analysis.market_structure import MarketStructureAnalyzer
import pandas as pd

analyzer = MarketStructureAnalyzer()

# Анализ структуры
structure = analyzer.analyze_structure(data)
print(f"Структура: {structure.value}")

# Детекция свингов
swing_highs, swing_lows = analyzer.detect_swings(data)
print(f"Свинги: {len(swing_highs)}H / {len(swing_lows)}L")

# Сила тренда
strength = analyzer.calculate_trend_strength(data)
print(f"Сила тренда: {strength:.2f}")
```

### Детекция ликвидности

```python
from analysis.liquidity_detector import LiquidityDetector

detector = LiquidityDetector()

# Поиск пулов ликвидности
all_swings = swing_highs + swing_lows
pools = detector.detect_liquidity_pools(data, all_swings)

for pool in pools:
    print(f"{pool.liquidity_type.value} @ {pool.price:.2f} "
          f"(сила: {pool.strength:.2f})")

# Проверка снятия ликвидности
current_price = data['close'].iloc[-1]
swept_pools = detector.check_liquidity_sweep(current_price, pools)
```

### Получение данных

```python
from data.data_provider import ExchangeDataProvider
from core.data_types import TimeFrame
from datetime import datetime, timedelta

async def get_market_data():
    async with ExchangeDataProvider("binance") as provider:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        data = await provider.get_historical_data(
            "BTC/USDT", 
            TimeFrame.H4, 
            start_date, 
            end_date
        )
        
        return data
```

## ⚙️ Конфигурация

Система использует Pydantic для валидации конфигурации:

```python
from config import get_config

config = get_config()

# Настройки стратегии
print(f"Чувствительность ликвидности: {config.strategy.liquidity_sensitivity}")
print(f"Минимальный возраст: {config.strategy.min_liquidity_age}")

# Настройки таймфреймов
print(f"Стратегические ТФ: {config.trading.strategic_timeframes}")
print(f"Тактические ТФ: {config.trading.tactical_timeframes}")
```

## 📈 Человекоподобное мышление

Система реализует адаптивную логику:

```python
# Эмоциональные факторы
context.fear_factor = 0.1    # Страх после убытков
context.greed_factor = 0.05  # Жадность после прибыли

# Адаптация параметров
if recent_win_rate < 0.4:
    # Снижаем агрессивность после серии потерь
    confluence_threshold *= 1.2
    position_size *= 0.8

# Учет контекста
if market_regime == "high_volatility":
    # В волатильности увеличиваем стопы
    stop_multiplier *= 1.5
```

## 🛡️ Риск-менеджмент

- **Максимальный риск на сделку**: 2% (настраивается)
- **Максимум открытых позиций**: 3
- **Минимальный R:R**: 2:1
- **Корреляционные фильтры**: Проверка связанных позиций

## 🧪 Тестирование

```bash
# Запуск тестов
pytest tests/ -v

# Покрытие кода
pytest --cov=. tests/

# Тесты производительности
pytest tests/test_performance.py -v
```

## 📊 Логирование

Система ведет подробные логи:

```
2024-01-15 10:30:00 | INFO | market_structure:analyze_structure:45 | Анализ структуры завершен: bullish
2024-01-15 10:30:01 | INFO | liquidity_detector:detect_liquidity_pools:67 | Обнаружено 5 пулов ликвидности
2024-01-15 10:30:02 | INFO | liquidity_detector:check_liquidity_sweep:95 | Снята ликвидность SSL @ 42,350.00
```

## 🔮 Дальнейшее развитие

- [ ] Веб-интерфейс для мониторинга
- [ ] ML-модели для улучшения детекции
- [ ] Интеграция с TradingView
- [ ] Мобильные уведомления
- [ ] Портфельный анализ

## ⚠️ Дисклеймер

Эта система предназначена только для образовательных целей и бэк-тестинга. Торговля криптовалютами сопряжена с высокими рисками. Автор не несет ответственности за любые финансовые потери.

## 📄 Лицензия

MIT License - см. файл LICENSE для деталей.

---

*Создано с 💛 для профессиональных трейдеров*