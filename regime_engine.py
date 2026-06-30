# regime_engine.py - Piyasa Rejimi Tespit Motoru
# Borsa Komutan v3.0

import pandas as pd
import numpy as np

class RegimeEngine:
    """
    Piyasa rejimini tespit eder ve strateji önerir.
    Trend, volatilite ve momentum analizi yapar.
    """

    def __init__(self):
        self.rejim_tanimlari = {
            'yukari_trend': {'adx_esik': 25, 'fiyat_ustu': True},
            'asagi_trend': {'adx_esik': 25, 'fiyat_ustu': False},
            'yatay': {'adx_esik': 20, 'bb_sikisma': True},
            'yuksek_vol': {'atr_oran': 0.03},
            'dusuk_vol': {'atr_oran': 0.01}
        }

    def tespit_et(self, hisse_df, bist100_df=None, usdtry_df=None):
        """
        Piyasa rejimini tespit et

        Returns:
            dict: {'trend': 'Yukari/Asagi/Yatay', 'volatilite': 'Yuksek/Dusuk', 'genel': 'Bull/Bear/Neutral'}
        """
        if hisse_df is None or len(hisse_df) < 20:
            return {'trend': 'Bilinmiyor', 'volatilite': 'Bilinmiyor', 'genel': 'Neutral'}

        # Trend tespiti (SMA50 vs SMA200)
        sma50 = hisse_df['Close'].rolling(50).mean().iloc[-1]
        sma200 = hisse_df['Close'].rolling(200).mean().iloc[-1] if len(hisse_df) >= 200 else sma50
        fiyat = hisse_df['Close'].iloc[-1]

        if fiyat > sma50 > sma200:
            trend = 'Yukari'
        elif fiyat < sma50 < sma200:
            trend = 'Asagi'
        else:
            trend = 'Yatay'

        # Volatilite tespiti (ATR)
        high_low = hisse_df['High'] - hisse_df['Low']
        high_close = np.abs(hisse_df['High'] - hisse_df['Close'].shift())
        low_close = np.abs(hisse_df['Low'] - hisse_df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]

        vol_oran = atr / fiyat if fiyat > 0 else 0
        if vol_oran > 0.03:
            volatilite = 'Yuksek'
        elif vol_oran > 0.015:
            volatilite = 'Orta'
        else:
            volatilite = 'Dusuk'

        # Genel rejim
        if trend == 'Yukari' and volatilite in ['Orta', 'Dusuk']:
            genel = 'Bull'
        elif trend == 'Asagi' and volatilite in ['Orta', 'Yuksek']:
            genel = 'Bear'
        else:
            genel = 'Neutral'

        return {
            'trend': trend,
            'volatilite': volatilite,
            'genel': genel,
            'sma50': round(sma50, 2),
            'sma200': round(sma200, 2),
            'atr': round(atr, 4),
            'vol_oran': round(vol_oran, 4)
        }

    def strateji_ayarla(self, rejim):
        """
        Rejime göre strateji ve ağırlıklar ayarla

        Returns:
            dict: {'agirliklar': {...}, 'esikler': {...}, 'tavsiye': '...'}
        """
        genel = rejim.get('genel', 'Neutral') if isinstance(rejim, dict) else 'Neutral'

        if genel == 'Bull':
            return {
                'agirliklar': {'teknik': 0.30, 'temel': 0.25, 'yatirimci': 0.20, 'risk': 0.15, 'makro': 0.10},
                'esikler': {'AL': 50, 'SAT': 45},
                'tavsiye': 'Aggressive - Pozisyon artırılabilir',
                'max_pozisyon': 1.0
            }
        elif genel == 'Bear':
            return {
                'agirliklar': {'teknik': 0.20, 'temel': 0.20, 'yatirimci': 0.15, 'risk': 0.30, 'makro': 0.15},
                'esikler': {'AL': 65, 'SAT': 40},
                'tavsiye': 'Defensive - Risk azaltılmalı',
                'max_pozisyon': 0.5
            }
        else:  # Neutral
            return {
                'agirliklar': {'teknik': 0.25, 'temel': 0.25, 'yatirimci': 0.20, 'risk': 0.20, 'makro': 0.10},
                'esikler': {'AL': 50, 'SAT': 50},
                'tavsiye': 'Balanced - Seçici olunmalı',
                'max_pozisyon': 0.75
            }


if __name__ == "__main__":
    print("=" * 60)
    print("REGIME ENGINE TEST")
    print("=" * 60)

    import pandas as pd
    import numpy as np

    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=100, freq='D')
    trend = np.cumsum(np.random.randn(100) * 0.5 + 0.3)
    df = pd.DataFrame({
        'Open': trend + 100,
        'High': trend + 100 + np.abs(np.random.randn(100)) * 2,
        'Low': trend + 100 - np.abs(np.random.randn(100)) * 2,
        'Close': trend + 100 + np.random.randn(100)
    }, index=dates)

    engine = RegimeEngine()
    rejim = engine.tespit_et(df)
    strateji = engine.strateji_ayarla(rejim)

    print(f"Trend: {rejim['trend']}")
    print(f"Volatilite: {rejim['volatilite']}")
    print(f"Genel: {rejim['genel']}")
    print(f"Tavsiye: {strateji['tavsiye']}")
    print(f"Eşikler: AL>{strateji['esikler']['AL']}, SAT<{strateji['esikler']['SAT']}")

    print("=" * 60)
    print("TEST TAMAMLANDI")
