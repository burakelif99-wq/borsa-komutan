import yfinance as yf
import pandas as pd
from datetime import datetime


def get_bist100(period="3mo", interval="1d"):
    try:
        ticker = yf.Ticker("XU100.IS")
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return None

        df['PM'] = calculate_pm_score(df)

        return {
            'symbol': 'XU100',
            'data': df,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'OK'
        }
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def calculate_pm_score(df):
    if len(df) < 20:
        return pd.Series([50] * len(df), index=df.index)

    # Gap
    gap = abs(df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1).replace(0, 1)

    # Hacim normalize
    vol_avg = df['Volume'].rolling(window=20, min_periods=1).mean()
    vol_score = (df['Volume'] / vol_avg.replace(0, 1) - 1) * 50

    # ATR normalize
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift(1))
    low_close = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=14, min_periods=1).mean()
    atr_score = (atr / df['Close']) * 100 * 50

    # Momentum
    momentum = ((df['Close'] - df['Close'].shift(10)) / df['Close'].shift(10).replace(0, 1)) * 50

    # Composite PM (0-100)
    pm_raw = gap * 20 + vol_score + atr_score + momentum

    # NaN düzeltme
    pm = pm_raw.ffill().bfill().fillna(50).clip(0, 100)

    return pm


def get_ohlcv_json(df):
    return {
        'dates': df.index.strftime('%Y-%m-%d').tolist(),
        'open': [round(x, 2) for x in df['Open'].tolist()],
        'high': [round(x, 2) for x in df['High'].tolist()],
        'low': [round(x, 2) for x in df['Low'].tolist()],
        'close': [round(x, 2) for x in df['Close'].tolist()],
        'volume': [int(x) for x in df['Volume'].tolist()],
        'pm': [round(x, 2) for x in df['PM'].tolist()]
    }


if __name__ == "__main__":
    result = get_bist100()
    if result['status'] == 'OK':
        df = result['data']
        print(f"Veri çekildi: {len(df)} satır")
        print(f"Son kapanış: {df['Close'].iloc[-1]:.2f}")
        print(f"PM Skoru: {df['PM'].iloc[-1]:.2f}")
        print(f"Son 5 PM: {df['PM'].tail().tolist()}")
    else:
        print(f"Hata: {result['message']}")


# veri_al.py - Hisse verisi ekle (en alta)

def get_hisse_fiyat(sembol):
    """
    Tek hisse fiyatı çek
    """
    try:
        ticker = yf.Ticker(f"{sembol}.IS")
        data = ticker.history(period="2d")

        if len(data) >= 2:
            son = data['Close'].iloc[-1]
            onceki = data['Close'].iloc[-2]
            degisim = (son - onceki) / onceki * 100

            return {
                'status': 'OK',
                'fiyat': round(son, 2),
                'degisim': round(degisim, 2)
            }
        else:
            return {'status': 'ERROR', 'message': 'Yetersiz veri'}

    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def get_populer_hisseler():
    """
    Popüler hisselerin fiyatlarını çek
    """
    hisseler = ['THYAO', 'GARAN', 'ASELS', 'EREGL', 'SASA', 'KONTR']
    sonuclar = {}

    for hisse in hisseler:
        sonuc = get_hisse_fiyat(hisse)
        if sonuc['status'] == 'OK':
            sonuclar[hisse] = sonuc
        else:
            sonuclar[hisse] = {'fiyat': 0, 'degisim': 0}

    return sonuclar

# veri_al.py - SONUNA EKLE (mevcut fonksiyonların altına)

def get_usdtry():
    """USD/TRY kuru çek"""
    try:
        import yfinance as yf
        usd = yf.Ticker("USDTRY=X")
        df = usd.history(period="1d")
        if not df.empty:
            return {
                'status': 'OK',
                'rate': round(df['Close'].iloc[-1], 2),
                'change': round(df['Close'].iloc[-1] - df['Open'].iloc[-1], 2)
            }
        return {'status': 'HATA', 'message': 'USD/TRY verisi boş'}
    except Exception as e:
        return {'status': 'HATA', 'message': str(e)}
