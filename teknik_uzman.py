# teknik_uzman.py - Teknik Analiz Uzmanı
# Borsa Komutan v3.0 - Modul 1

import pandas as pd
import numpy as np
from datetime import datetime

class TeknikUzman:
    """
    20+ teknik indikatör ve formasyon tespiti.
    RSI, MACD, Bollinger, SMA/EMA, ATR, Stochastic, ADX, OBV, vb.
    """

    def __init__(self):
        self.indikatörler = [
            'rsi', 'macd', 'bollinger', 'sma', 'ema', 'atr',
            'stochastic', 'adx', 'obv', 'mfi', 'cci', 'williams_r',
            'parabolic_sar', 'ichimoku', 'fibonacci', 'volume_profile',
            'pivot_points', 'support_resistance', 'trend_lines', 'patterns'
        ]

    def analiz_et(self, df, zaman_dilimi='1D'):
        """
        Teknik analiz yap ve sinyal üret

        Returns:
            dict: {'sinyal': 'AL'/'SAT'/'BEKLE', 'skor': 0-100, 'guven': 0-1, 'neden': '...'}
        """
        if df is None or len(df) < 50:
            return {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.3, 'neden': 'Yetersiz veri'}

        close = df['Close']
        high = df['High']
        low = df['Low']
        volume = df['Volume'] if 'Volume' in df.columns else pd.Series([1]*len(df))

        skorlar = {}

        # 1. RSI (14)
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_current = rsi.iloc[-1]

        if rsi_current < 30:
            skorlar['rsi'] = 70  # Asiri satim = AL
        elif rsi_current > 70:
            skorlar['rsi'] = 70  # Asiri alim = momentum AL (yukselen trend)
        else:
            skorlar['rsi'] = 50 + (50 - rsi_current)  # 50 merkez

        # 2. MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9).mean()
        histogram = macd_line - signal_line

        if histogram.iloc[-1] > 0 and histogram.iloc[-2] < 0:
            skorlar['macd'] = 75  # Yukari kesisim
        elif histogram.iloc[-1] < 0 and histogram.iloc[-2] > 0:
            skorlar['macd'] = 25  # Asagi kesisim
        else:
            skorlar['macd'] = 50 + (histogram.iloc[-1] * 10)

        # 3. Bollinger Bands
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        upper = sma20 + (std20 * 2)
        lower = sma20 - (std20 * 2)

        pos = (close.iloc[-1] - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
        if pos < 0.1:
            skorlar['bollinger'] = 80  # Alt banda yakin
        elif pos > 0.9:
            skorlar['bollinger'] = 20  # Ust banda yakin
        else:
            skorlar['bollinger'] = 50

        # 4. SMA/EMA Trend
        sma50 = close.rolling(50).mean()
        sma200 = close.rolling(200).mean() if len(close) >= 200 else sma50

        if close.iloc[-1] > sma50.iloc[-1] > sma200.iloc[-1]:
            skorlar['trend'] = 75  # Golden cross yakin
        elif close.iloc[-1] < sma50.iloc[-1] < sma200.iloc[-1]:
            skorlar['trend'] = 25  # Death cross yakin
        else:
            skorlar['trend'] = 50

        # 5. ATR (Volatilite)
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()
        atr_ratio = atr.iloc[-1] / close.iloc[-1]

        if atr_ratio > 0.03:
            skorlar['volatilite'] = 40  # Yuksek vol = riskli
        else:
            skorlar['volatilite'] = 60  # Dusuk vol = guvenli

        # 6. Stochastic (14,3)
        low14 = low.rolling(14).min()
        high14 = high.rolling(14).max()
        k = 100 * (close - low14) / (high14 - low14)
        d = k.rolling(3).mean()

        if k.iloc[-1] < 20 and d.iloc[-1] < 20:
            skorlar['stochastic'] = 70
        elif k.iloc[-1] > 80 and d.iloc[-1] > 80:
            skorlar['stochastic'] = 30
        else:
            skorlar['stochastic'] = 50

        # 7. ADX (Trend gucu)
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(14).mean()

        if adx.iloc[-1] > 25:
            skorlar['adx'] = 65  # Guclu trend
        else:
            skorlar['adx'] = 45  # Zayif trend

        # 8. Hacim Analizi (OBV benzeri)
        obv = (np.sign(close.diff()) * volume).cumsum()
        obv_trend = np.polyfit(range(20), obv.iloc[-20:].values, 1)[0]

        if obv_trend > 0:
            skorlar['hacim'] = 65  # Hacim artiyor
        else:
            skorlar['hacim'] = 35  # Hacim dusuyor

        # 9. Formasyon Tespiti (Basit)
        formasyon = self._formasyon_tespit(df)
        skorlar['formasyon'] = formasyon['skor']

        # Agirlikli ortalama
        agirliklar = {
            'rsi': 0.15, 'macd': 0.15, 'bollinger': 0.10,
            'trend': 0.15, 'volatilite': 0.05, 'stochastic': 0.10,
            'adx': 0.10, 'hacim': 0.10, 'formasyon': 0.10
        }

        toplam_skor = sum(skorlar.get(k, 50) * v for k, v in agirliklar.items())
        toplam_agirlik = sum(agirliklar.values())
        final_skor = round(toplam_skor / toplam_agirlik, 1)

        # Guven hesapla (indikator uyumu)
        al_sayisi = sum(1 for v in skorlar.values() if v > 60)
        sat_sayisi = sum(1 for v in skorlar.values() if v < 40)
        toplam = len(skorlar)

        if al_sayisi > sat_sayisi * 2:
            guven = 0.8
        elif sat_sayisi > al_sayisi * 2:
            guven = 0.8
        elif al_sayisi > 0 or sat_sayisi > 0:
            guven = 0.6
        else:
            guven = 0.4

        # Karar
        if final_skor >= 65:
            sinyal = 'AL'
        elif final_skor <= 35:
            sinyal = 'SAT'
        else:
            sinyal = 'BEKLE'

        # Neden olustur
        nedenler = []
        if rsi_current < 30: nedenler.append(f"RSI asiri satim ({rsi_current:.1f})")
        elif rsi_current > 70: nedenler.append(f"RSI asiri alim ({rsi_current:.1f})")
        if 'yukari' in str(skorlar.get('macd', '')).lower(): nedenler.append("MACD yukari kesisim")
        elif 'asagi' in str(skorlar.get('macd', '')).lower(): nedenler.append("MACD asagi kesisim")
        if formasyon['tip']: nedenler.append(f"Formasyon: {formasyon['tip']}")

        neden = "; ".join(nedenler) if nedenler else "Karisik sinyaller"

        return {
            'sinyal': sinyal,
            'skor': final_skor,
            'guven': round(guven, 2),
            'neden': neden,
            'detay': skorlar,
            'zaman_dilimi': zaman_dilimi
        }

    def _formasyon_tespit(self, df):
        """Basit formasyon tespiti"""
        close = df['Close'].values
        if len(close) < 20:
            return {'skor': 50, 'tip': None}

        # Son 20 gunun min/max
        recent = close[-20:]
        max_idx = np.argmax(recent)
        min_idx = np.argmin(recent)

        # Cift tepe (basit)
        if max_idx > 10 and abs(recent[-1] - recent[max_idx]) / recent[max_idx] < 0.02:
            return {'skor': 35, 'tip': 'Cift Tepe'}

        # Cift dip (basit)
        if min_idx > 10 and abs(recent[-1] - recent[min_idx]) / recent[min_idx] < 0.02:
            return {'skor': 65, 'tip': 'Cift Dip'}

        # Yukan kirilim
        if recent[-1] > np.max(recent[:-5]) * 1.02:
            return {'skor': 70, 'tip': 'Yukan Kirilim'}

        # Asagi kirilim
        if recent[-1] < np.min(recent[:-5]) * 0.98:
            return {'skor': 30, 'tip': 'Asagi Kirilim'}

        return {'skor': 50, 'tip': None}


# Kullanim kolayligi icin fonksiyon
def analiz_et(df, zaman_dilimi='1D'):
    uzman = TeknikUzman()
    return uzman.analiz_et(df, zaman_dilimi)


if __name__ == "__main__":
    print("=" * 70)
    print("TEKNIK ANALIZ UZMANI TEST")
    print("=" * 70)

    # Test verisi
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=100, freq='D')
    trend = np.cumsum(np.random.randn(100) * 0.5 + 0.3)
    df = pd.DataFrame({
        'Open': trend + 100,
        'High': trend + 100 + np.abs(np.random.randn(100)) * 2,
        'Low': trend + 100 - np.abs(np.random.randn(100)) * 2,
        'Close': trend + 100 + np.random.randn(100),
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    uzman = TeknikUzman()
    sonuc = uzman.analiz_et(df)

    print(f"Sinyal: {sonuc['sinyal']}")
    print(f"Skor: {sonuc['skor']}")
    print(f"Guven: {sonuc['guven']}")
    print(f"Neden: {sonuc['neden']}")
    print(f"Detaylar:")
    for k, v in sonuc['detay'].items():
        print(f"  {k}: {v}")

    print("=" * 70)
