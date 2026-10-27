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
    # --- Core Majors (Top Liquidity) ---
    "BTC-SWAP-USDT", "ETH-SWAP-USDT", "SOL-SWAP-USDT", "XRP-SWAP-USDT", 
    "BNB-SWAP-USDT", "DOGE-SWAP-USDT", "ADA-SWAP-USDT", "TRX-SWAP-USDT",
    "AVAX-SWAP-USDT", "LINK-SWAP-USDT", "DOT-SWAP-USDT", "LTC-SWAP-USDT",
    "BCH-SWAP-USDT", "TON-SWAP-USDT", "SUI-SWAP-USDT", "NEAR-SWAP-USDT",
    "APT-SWAP-USDT", "ARB-SWAP-USDT", "OP-SWAP-USDT", "ATOM-SWAP-USDT",
    
    # --- High Volume / Popular Altcoins ---
    "UNI-SWAP-USDT", "AAVE-SWAP-USDT", "FIL-SWAP-USDT", "INJ-SWAP-USDT",
    "TIA-SWAP-USDT", "JUP-SWAP-USDT", "ENA-SWAP-USDT", "WIF-SWAP-USDT",
    "1000PEPE-SWAP-USDT", "1000SHIB-SWAP-USDT", "WLD-SWAP-USDT", "SEI-SWAP-USDT",
    "RUNE-SWAP-USDT", "LDO-SWAP-USDT", "STX-SWAP-USDT", "IMX-SWAP-USDT",
    "HBAR-SWAP-USDT", "ICP-SWAP-USDT", "ETC-SWAP-USDT", "XLM-SWAP-USDT",
    
    # --- DeFi & Layer 2 ---
    "CRV-SWAP-USDT", "SNX-SWAP-USDT",
    "COMP-SWAP-USDT", "SUSHI-SWAP-USDT", "1INCH-SWAP-USDT", "GRT-SWAP-USDT",
    "DYDX-SWAP-USDT", "GMX-SWAP-USDT", "PENDLE-SWAP-USDT", "ONDO-SWAP-USDT",
    "JTO-SWAP-USDT", "PYTH-SWAP-USDT", "STRK-SWAP-USDT", "MANTA-SWAP-USDT",
    
    # --- Meme & Community Coins ---
    "1000BONK-SWAP-USDT", "1000FLOKI-SWAP-USDT", "MEME-SWAP-USDT", "ORDI-SWAP-USDT",
    "1000SATS-SWAP-USDT", "1000RATS-SWAP-USDT", "POPCAT-SWAP-USDT",
    "BRETT-SWAP-USDT", "TURBO-SWAP-USDT", "1000000MOG-SWAP-USDT", "DOGS-SWAP-USDT",
    
    # --- AI, Gaming & Metaverse ---
    "FET-SWAP-USDT", "TAO-SWAP-USDT",
    "AKT-SWAP-USDT", "ILV-SWAP-USDT",
    "AXS-SWAP-USDT", "SAND-SWAP-USDT", "MANA-SWAP-USDT", "GALA-SWAP-USDT",
    
    # --- Infrastructure & Others ---
    "ALGO-SWAP-USDT", "VET-SWAP-USDT", "EGLD-SWAP-USDT", "FLOW-SWAP-USDT",
    "KAVA-SWAP-USDT", "ROSE-SWAP-USDT", "KAS-SWAP-USDT",
    "THETA-SWAP-USDT", "CHZ-SWAP-USDT", "ENJ-SWAP-USDT", "ZIL-SWAP-USDT",
    "ONE-SWAP-USDT", "QTUM-SWAP-USDT", "IOTA-SWAP-USDT", "NEO-SWAP-USDT"
]

HEARTBEAT_FILE = "server_messages_v10.json" 
SIGNALS_FILE = "last_signals_v10.json" 
MAX_HEARTBEATS = 4
MAX_SIGNALS_PER_CYCLE = 3

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

# --- مدیریت معاملات ---
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
                
                if direction == "LONG":
                    if current_price >= tp: result = "TP"
                    elif current_price <= sl: result = "SL"
                elif direction == "SHORT":
                    if current_price <= tp: result = "TP"
                    elif current_price >= sl: result = "SL"
                
                if result:
                    signals[symbol]['status'] = "CLOSED"
                    signals[symbol]['result'] = result
                    updated = True
                    emoji = "🎯" if result == "TP" else "🛑"
                    title = "حد سود (TP) لمس شد" if result == "TP" else "حد ضرر (SL) لمس شد"
                    print(f"{emoji} {symbol} {direction} hit {result} at {current_price}")
                    
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
    if updated: save_signals(signals)

# --- داده و تحلیل ---
def create_exchange():
    return ccxt.toobit({'apiKey': TOOBIT_API_KEY, 'secret': TOOBIT_SECRET, 'enableRateLimit': True})

def fetch_ohlcv(exchange, symbol, timeframe, limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    return pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

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

def get_btc_trend(exchange):
    try:
        df_btc_4h = fetch_ohlcv(exchange, "BTC-SWAP-USDT", '4h', 100)
        df_btc_4h = calculate_indicators(df_btc_4h)
        last_btc_4h = df_btc_4h.iloc[-1]
        
        if last_btc_4h['ema9'] > last_btc_4h['ema21']:
            trend_4h = "LONG"
        elif last_btc_4h['ema9'] < last_btc_4h['ema21']:
            trend_4h = "SHORT"
        else:
            trend_4h = "NONE"

        df_btc_1h = fetch_ohlcv(exchange, "BTC-SWAP-USDT", '1h', 100)
        df_btc_1h = calculate_indicators(df_btc_1h)
        last_btc_1h = df_btc_1h.iloc[-1]
        
        if last_btc_1h['ema9'] > last_btc_1h['ema21']:
            trend_1h = "LONG"
        elif last_btc_1h['ema9'] < last_btc_1h['ema21']:
            trend_1h = "SHORT"
        else:
            trend_1h = "NONE"
            
        return trend_4h, trend_1h
    except Exception as e:
        print(f"⚠️ خطا در دریافت روند بیت‌کوین: {e}")
        return "UNKNOWN", "UNKNOWN"

def analyze(symbol, exchange):
    # ۱. بررسی تایم 4 ساعته (کراس)
    df_4h = fetch_ohlcv(exchange, symbol, '4h', 100)
    df_4h = calculate_indicators(df_4h)
    last_4h = df_4h.iloc[-1]
    prev_4h = df_4h.iloc[-2]

    cross_long_4h = (prev_4h['ema9'] <= prev_4h['ema21']) and (last_4h['ema9'] > last_4h['ema21'])
    cross_short_4h = (prev_4h['ema9'] >= prev_4h['ema21']) and (last_4h['ema9'] < last_4h['ema21'])

    # ۲. بررسی تایم 1 ساعته (تایید روند)
    df_1h = fetch_ohlcv(exchange, symbol, '1h', 100)
    df_1h = calculate_indicators(df_1h)
    last_1h = df_1h.iloc[-1]

    trend_long_1h = last_1h['ema9'] > last_1h['ema21']
    trend_short_1h = last_1h['ema9'] < last_1h['ema21']

    # ۳. بررسی تایم 15 دقیقه (مومنتوم و نقطه ورود)
    df_15m = fetch_ohlcv(exchange, symbol, '15m', 100)
    df_15m = calculate_indicators(df_15m)
    last_15m = df_15m.iloc[-1]

    entry_price = last_15m['close']
    atr = last_15m['atr']
    rsi_15m = last_15m['rsi']

    # ۴. فیلتر حجم (شل‌تر: ۵۰٪ میانگین)
    avg_volume = df_15m['volume'].rolling(window=20).mean().iloc[-1]
    current_volume = df_15m['volume'].iloc[-1]
    volume_condition = current_volume > avg_volume * 0.5  # شرط شل‌تر

    print(f"  [DEBUG 4H] Cross LONG: {cross_long_4h} | Cross SHORT: {cross_short_4h}")
    print(f"  [DEBUG 1H] Trend LONG: {trend_long_1h} | Trend SHORT: {trend_short_1h}")
    print(f"  [DEBUG 15m] RSI: {rsi_15m:.2f} | Vol: {current_volume:.2f} | AvgVol: {avg_volume:.2f} | VolOK(50%): {volume_condition}")

    signal = None
    sl = tp = None

    # شرط LONG (با فیلتر حجم شل‌تر)
    if cross_long_4h and trend_long_1h and rsi_15m > 50 and volume_condition:
        signal = "LONG"
        sl = entry_price - (atr * 1.5)
        tp = entry_price + (atr * 3.0)

    # شرط SHORT (با فیلتر حجم شل‌تر)
    elif cross_short_4h and trend_short_1h and rsi_15m < 50 and volume_condition:
        signal = "SHORT"
        sl = entry_price + (atr * 1.5)
        tp = entry_price - (atr * 3.0)

    return signal, entry_price, sl, tp, rsi_15m, atr, volume_condition

def format_number(value):
    if value >= 1000: return f"{value:.2f}"
    elif value >= 1: return f"{value:.4f}"
    else: return f"{value:.6f}"

# --- اجرای اصلی ---
if __name__ == "__main__":
    print("=" * 50)
    print("Starting V10 bot cycle (Cross + Confirm + BTC Filter + Soft Volume)...")

    send_heartbeat()
    print("✅ V10 Heartbeat sent.")

    exchange = create_exchange()
    date_gregorian, date_jalali, time_str = get_iran_time()

    update_open_trades(exchange)
    signals_data = load_signals()

    btc_trend_4h, btc_trend_1h = get_btc_trend(exchange)
    print(f"🌍 BTC 4H Trend: {btc_trend_4h} | BTC 1H Trend: {btc_trend_1h}")

    signals_sent_this_cycle = 0

    for symbol in SYMBOLS:
        try:
            print(f"--- Checking {symbol} ---")
            
            if symbol in signals_data and signals_data[symbol].get("status") == "OPEN":
                print(f"⏳ {symbol} has an OPEN trade. Skipping.")
                continue

            signal, entry, sl, tp, rsi, atr, vol_ok = analyze(symbol, exchange)

            if signal is None:
                print(f"{symbol} | Price: {entry} | No valid setup or low volume.")
                continue

            # فیلتر بیت‌کوین
            if btc_trend_4h != "UNKNOWN" and btc_trend_4h != "NONE" and signal != btc_trend_4h:
                print(f"🚫 {symbol} signal {signal} rejected. BTC 4H trend is {btc_trend_4h}.")
                continue
            if btc_trend_1h != "UNKNOWN" and btc_trend_1h != "NONE" and signal != btc_trend_1h:
                print(f"🚫 {symbol} signal {signal} rejected. BTC 1H trend is {btc_trend_1h}.")
                continue

            if signals_sent_this_cycle >= MAX_SIGNALS_PER_CYCLE:
                print(f"🛑 Reached max signals per cycle ({MAX_SIGNALS_PER_CYCLE}). Skipping {symbol}.")
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
📊 Volume: {current_volume:.2f} (Avg: {avg_volume:.2f})
━━━━━━━━━━━━━━━━━
📅 تاریخ شمسی: {date_jalali}
📅 تاریخ میلادی: {date_gregorian}
⏰ ساعت: {time_str}
━━━━━━━━━━━━━━━━━"""

            send_telegram(msg)
            
            signals_data[symbol] = {
                "direction": signal,
                "entry": entry,
                "tp": tp,
                "sl": sl,
                "status": "OPEN",
                "time": datetime.now().isoformat()
            }
            save_signals(signals_data)
            signals_sent_this_cycle += 1
            print(f"✅ {signal} signal for {symbol} sent! ({signals_sent_this_cycle}/{MAX_SIGNALS_PER_CYCLE})")

        except Exception as e:
            print(f"⚠️ خطا در {symbol}: {e}")
            continue

    print("V10 Analysis complete.")
    print("=" * 50)