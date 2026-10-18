import os
import json
import requests
import pandas as pd
import ccxt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import jdatetime

# --- تنظیمات ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TOOBIT_API_KEY = os.environ.get("TOOBIT_API_KEY")
TOOBIT_SECRET = os.environ.get("TOOBIT_SECRET")

SYMBOLS = [
    "BTC-SWAP-USDT", "ETH-SWAP-USDT", "SOL-SWAP-USDT", "XRP-SWAP-USDT",
    "ADA-SWAP-USDT", "DOGE-SWAP-USDT", "BNB-SWAP-USDT", "AVAX-SWAP-USDT",
    "LINK-SWAP-USDT", "DOT-SWAP-USDT", "LTC-SWAP-USDT", "TON-SWAP-USDT",
    "UNI-SWAP-USDT", "AAVE-SWAP-USDT", "NEAR-SWAP-USDT", "SUI-SWAP-USDT",
    "APT-SWAP-USDT", "ARB-SWAP-USDT", "ATOM-SWAP-USDT", "FIL-SWAP-USDT",
    "TIA-SWAP-USDT", "JUP-SWAP-USDT", "ENA-SWAP-USDT", "WIF-SWAP-USDT",
    "INJ-SWAP-USDT"
]

HEARTBEAT_FILE = "server_messages_v10.json" 
SIGNALS_FILE = "last_signals_v10.json" 
MAX_HEARTBEATS = 4

# --- ابزارهای عمومی ---
def get_iran_time():
    now = datetime.now(ZoneInfo("Asia/Tehran"))
    date_gregorian = now.strftime("%Y-%m-%d")
    now_jalali = jdatetime.datetime.fromgregorian(datetime=now)
    date_jalali = now_jalali.strftime("%Y/%m/%d")
    time_str = now.strftime("%H:%M:%S")
    return date_gregorian, date_jalali, time_str

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=10)
        if r.status_code == 200:
            return r.json().get("result", {}).get("message_id")
    except Exception as e:
        print(f"⚠️ خطا در ارسال تلگرام: {e}")
    return None

def delete_telegram(message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "message_id": message_id}, timeout=10)
    except Exception as e:
        print(f"⚠️ خطا در حذف پیام: {e}")

# --- Heartbeat ---
def load_heartbeat_ids():
    try:
        with open(HEARTBEAT_FILE, "r") as f:
            return json.load(f).get("message_ids", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_heartbeat_ids(ids):
    with open(HEARTBEAT_FILE, "w") as f:
        json.dump({"message_ids": ids}, f)

def send_heartbeat():
    date_gregorian, date_jalali, time_str = get_iran_time()
    msg = f"""🖥️ [V10] سرور آنلاین
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""

    ids = load_heartbeat_ids()
    new_id = send_telegram(msg)

    if new_id:
        ids.append(new_id)
        while len(ids) > MAX_HEARTBEATS:
            old_id = ids.pop(0)
            delete_telegram(old_id)
        save_heartbeat_ids(ids)

# --- مدیریت معاملات باز و بسته ---
def load_signals():
    try:
        with open(SIGNALS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_signals(data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(data, f)

def update_open_trades(exchange):
    """بررسی می‌کند آیا معاملات باز به TP یا SL رسیده‌اند یا نه و پیام تلگرام می‌فرستد"""
    signals = load_signals()
    updated = False
    date_gregorian, date_jalali, time_str = get_iran_time()
    
    for symbol, data in list(signals.items()):
        if data.get("status") == "OPEN":
            try:
                ticker = exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                entry = data['entry']
                tp = data['tp']
                sl = data['sl']
                direction = data['direction']
                
                result = None
                
                # بررسی برخورد با TP یا SL
                if direction == "LONG":
                    if current_price >= tp:
                        result = "TP"
                    elif current_price <= sl:
                        result = "SL"
                elif direction == "SHORT":
                    if current_price <= tp:
                        result = "TP"
                    elif current_price >= sl:
                        result = "SL"
                
                if result:
                    signals[symbol]['status'] = "CLOSED"
                    signals[symbol]['result'] = result
                    updated = True
                    
                    if result == "TP":
                        emoji = "🎯"
                        title = "حد سود (TP) لمس شد"
                    else:
                        emoji = "🛑"
                        title = "حد ضرر (SL) لمس شد"

                    print(f"{emoji} {symbol} {direction} hit {result} at {current_price}")
                    
                    # ارسال پیام بسته شدن به تلگرام
                    close_msg = f"""{emoji} [V10] بسته شدن معامله
━━━━━━━━━━━━━━━━━
📌 نماد: {symbol}
📊 جهت: {direction}
🏁 نتیجه: {title}
💰 قیمت بسته شدن: {format_number(current_price)}
🚪 قیمت ورود: {format_number(entry)}
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""
                    send_telegram(close_msg)

            except Exception as e:
                print(f"⚠️ خطا در بررسی {symbol}: {e}")
                continue
                
    if updated:
        save_signals(signals)

# --- داده و تحلیل ---
def create_exchange():
    return ccxt.toobit({
        'apiKey': TOOBIT_API_KEY,
        'secret': TOOBIT_SECRET,
        'enableRateLimit': True,
    })

def fetch_ohlcv(exchange, symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def calculate_indicators(df):
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()

    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()

    return df

def analyze(symbol, exchange):
    df_4h = fetch_ohlcv(exchange, symbol, '4h', 100)
    df_4h = calculate_indicators(df_4h)
    last_4h = df_4h.iloc[-1]

    df_15m = fetch_ohlcv(exchange, symbol, '15m', 100)
    df_15m = calculate_indicators(df_15m)
    last_15m = df_15m.iloc[-1]

    entry_price = last_15m['close']
    atr = last_15m['atr']
    rsi_15m = last_15m['rsi']

    trend_long_4h = last_4h['ema9'] > last_4h['ema21']
    trend_short_4h = last_4h['ema9'] < last_4h['ema21']
    trend_long_15m = last_15m['ema9'] > last_15m['ema21']
    trend_short_15m = last_15m['ema9'] < last_15m['ema21']

    print(f"  [DEBUG 4H] EMA9: {last_4h['ema9']:.4f} | EMA21: {last_4h['ema21']:.4f} | Trend: {'LONG' if trend_long_4h else 'SHORT' if trend_short_4h else 'NONE'}")
    print(f"  [DEBUG 15m] EMA9: {last_15m['ema9']:.4f} | EMA21: {last_15m['ema21']:.4f} | RSI: {rsi_15m:.2f}")
    
    signal = None
    sl = tp = None

    if trend_long_4h:
        if trend_long_15m and rsi_15m > 50:
            signal = "LONG"
            sl = entry_price - (atr * 1.5)
            tp = entry_price + (atr * 3.0)

    elif trend_short_4h:
        if trend_short_15m and rsi_15m < 50:
            signal = "SHORT"
            sl = entry_price + (atr * 1.5)
            tp = entry_price - (atr * 3.0)

    return signal, entry_price, sl, tp, rsi_15m, atr

def format_number(value):
    if value >= 1000:
        return f"{value:.2f}"
    elif value >= 1:
        return f"{value:.4f}"
    else:
        return f"{value:.6f}"

# --- اجرای اصلی ---
if __name__ == "__main__":
    print("=" * 50)
    print("Starting V10 bot cycle...")

    send_heartbeat()
    print("✅ V10 Heartbeat sent.")

    exchange = create_exchange()
    date_gregorian, date_jalali, time_str = get_iran_time()

    # ۱. اول بررسی می‌کنیم که آیا معاملات باز به TP/SL رسیده‌اند
    print("🔍 Checking open trades...")
    update_open_trades(exchange)
    signals_data = load_signals()

    for symbol in SYMBOLS:
        try:
            print(f"--- Checking {symbol} ---")
            
            # ۲. اگر برای این ارز معامله‌ای باز است، سیگنال جدید نده
            if symbol in signals_data and signals_data[symbol].get("status") == "OPEN":
                print(f"⏳ {symbol} has an OPEN trade. Skipping.")
                continue

            signal, entry, sl, tp, rsi, atr = analyze(symbol, exchange)

            if signal is None:
                print(f"{symbol} | Price: {entry} | RSI: {rsi:.2f} | No signal")
                continue

            if signal == "LONG":
                rr = (tp - entry) / (entry - sl)
                emoji = "🟢"
            else:
                rr = (entry - tp) / (sl - entry)
                emoji = "🔴"

            msg = f"""{emoji} [V10] سیگنال {signal}
━━━━━━━━━━━━━━━━━
📌 نماد: {symbol}
💰 قیمت ورود: {format_number(entry)}
🎯 حد سود (TP): {format_number(tp)}
🛑 حد ضرر (SL): {format_number(sl)}
📊 نسبت R:R: 1:{rr:.1f}
📈 RSI: {rsi:.2f}
📉 ATR: {format_number(atr)}
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""

            send_telegram(msg)
            
            # ۳. ذخیره سیگنال جدید به عنوان OPEN
            signals_data[symbol] = {
                "direction": signal,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "status": "OPEN",
                "time": datetime.now().isoformat()
            }
            save_signals(signals_data)
            print(f"✅ {signal} signal for {symbol} sent and recorded as OPEN!")

        except Exception as e:
            print(f"⚠️ خطا در {symbol}: {e}")
            continue

    print("V10 Analysis complete.")
    print("=" * 50)