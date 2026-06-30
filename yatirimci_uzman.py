# yatirimci_uzman.py - Ünlü Yatırımcı Stratejileri Uzmanı
# Borsa Komutan v3.0 - Modul 3

import yfinance as yf
import numpy as np
from datetime import datetime

class YatirimciUzman:
    """
    Warren Buffett, Benjamin Graham, Peter Lynch, Jesse Livermore
    stratejilerini uygular ve oy kullanır.
    """

    def __init__(self):
        self.stratejiler = {
            'buffett': self._buffett_analiz,
            'graham': self._graham_analiz,
            'lynch': self._lynch_analiz,
            'livermore': self._livermore_analiz
        }

    def analiz_et(self, ticker, df=None, zaman_dilimi='1D'):
        """
        4 ünlü yatırımcının stratejilerini uygula

        Returns:
            dict: {'sinyal': 'AL'/'SAT'/'BEKLE', 'skor': 0-100, 'guven': 0-1, 'neden': '...'}
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info:
                return {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.3, 'neden': 'Veri alinamadi'}

            skorlar = {}
            nedenler = []

            # 1. BUFFETT - Değer yatırımı + Moat
            skorlar['buffett'] = self._buffett_analiz(info)
            if skorlar['buffett'] > 60:
                nedenler.append("Buffett: Guclu deger sirketi")
            elif skorlar['buffett'] < 40:
                nedenler.append("Buffett: Zayif deger sirketi")

            # 2. GRAHAM - Margin of Safety + Net-Net
            skorlar['graham'] = self._graham_analiz(info)
            if skorlar['graham'] > 60:
                nedenler.append("Graham: Margin of safety var")
            elif skorlar['graham'] < 40:
                nedenler.append("Graham: Guvenlik marji yok")

            # 3. LYNCH - Growth at Reasonable Price (GARP)
            skorlar['lynch'] = self._lynch_analiz(info)
            if skorlar['lynch'] > 60:
                nedenler.append("Lynch: GARP firsati")
            elif skorlar['lynch'] < 40:
                nedenler.append("Lynch: Buyume pahali")

            # 4. LIVERMORE - Trend takip + Pivot noktaları
            skorlar['livermore'] = self._livermore_analiz(ticker, df)
            if skorlar['livermore'] > 60:
                nedenler.append("Livermore: Trend guclu")
            elif skorlar['livermore'] < 40:
                nedenler.append("Livermore: Trend zayif")

            # Agirlikli ortalama (her strateji esit agirlikli)
            agirliklar = {'buffett': 0.25, 'graham': 0.25, 'lynch': 0.25, 'livermore': 0.25}
            toplam = sum(skorlar.get(k, 50) * v for k, v in agirliklar.items())
            final_skor = round(toplam / sum(agirliklar.values()), 1)

            # Guven (stratejiler arasi uyum)
            al_sayisi = sum(1 for v in skorlar.values() if v > 60)
            sat_sayisi = sum(1 for v in skorlar.values() if v < 40)

            if al_sayisi >= 3 or sat_sayisi >= 3:
                guven = 0.85  # Guclu fikir birligi
            elif al_sayisi >= 2 or sat_sayisi >= 2:
                guven = 0.70  # Cogunluk var
            else:
                guven = 0.50  # Bolunmus

            # Karar
            if final_skor >= 65:
                sinyal = 'AL'
            elif final_skor <= 35:
                sinyal = 'SAT'
            else:
                sinyal = 'BEKLE'

            neden = "; ".join(nedenler) if nedenler else "Stratejiler karisik"

            return {
                'sinyal': sinyal,
                'skor': final_skor,
                'guven': round(guven, 2),
                'neden': neden,
                'detay': skorlar,
                'meta': {'ticker': ticker, 'zaman_dilimi': zaman_dilimi}
            }

        except Exception as e:
            return {
                'sinyal': 'BEKLE',
                'skor': 50,
                'guven': 0.2,
                'neden': f'Hata: {str(e)}',
                'detay': {},
                'meta': {'ticker': ticker, 'hata': str(e)}
            }

    def _buffett_analiz(self, info):
        """Warren Buffett kriterleri"""
        skor = 50

        # ROE > 15%
        roe = info.get('returnOnEquity', 0)
        if roe and roe > 0.15:
            skor += 15
        elif roe and roe > 0.10:
            skor += 5
        else:
            skor -= 10

        # Kar marji > 20%
        margin = info.get('profitMargins', 0)
        if margin and margin > 0.20:
            skor += 10
        elif margin and margin > 0.10:
            skor += 5
        else:
            skor -= 5

        # Borc/Ozkaynak < 0.5
        debt_equity = info.get('debtToEquity', 100)
        if debt_equity and debt_equity < 50:
            skor += 10
        elif debt_equity and debt_equity < 100:
            skor += 5
        else:
            skor -= 5

        # P/E < 15 (ucuz)
        pe = info.get('trailingPE', 25)
        if pe and pe < 15:
            skor += 10
        elif pe and pe < 25:
            skor += 5
        else:
            skor -= 5

        # Buyuk ve stabil sirket (market cap > 10B)
        market_cap = info.get('marketCap', 0)
        if market_cap > 10e9:
            skor += 5

        return max(0, min(100, skor))

    def _graham_analiz(self, info):
        """Benjamin Graham - Margin of Safety + Net-Net"""
        skor = 50

        # P/E < 15 (Graham kriteri)
        pe = info.get('trailingPE', 25)
        if pe and pe < 15:
            skor += 20
        elif pe and pe < 20:
            skor += 10
        else:
            skor -= 10

        # PD/DD < 1.5
        pb = info.get('priceToBook', 2)
        if pb and pb < 1.5:
            skor += 15
        elif pb and pb < 2.5:
            skor += 5
        else:
            skor -= 10

        # Borc/Ozkaynak < 1.0
        debt_equity = info.get('debtToEquity', 100)
        if debt_equity and debt_equity < 100:
            skor += 10
        else:
            skor -= 5

        # Current Ratio > 1.5 (aktif/pasif)
        current_ratio = info.get('currentRatio', 1)
        if current_ratio and current_ratio > 1.5:
            skor += 10
        elif current_ratio and current_ratio > 1.0:
            skor += 5
        else:
            skor -= 5

        # Temettu var mi?
        dividend = info.get('dividendYield', 0)
        if dividend and dividend > 0:
            skor += 5

        return max(0, min(100, skor))

    def _lynch_analiz(self, info):
        """Peter Lynch - GARP (Growth at Reasonable Price)"""
        skor = 50

        # PEG Ratio < 1.0 (mukemmel)
        peg = info.get('pegRatio', 2)
        if peg and peg < 1.0:
            skor += 25
        elif peg and peg < 2.0:
            skor += 15
        else:
            skor -= 10

        # Buyume orani > 15%
        growth = info.get('earningsGrowth', 0)
        if growth and growth > 0.20:
            skor += 15
        elif growth and growth > 0.10:
            skor += 10
        elif growth and growth > 0:
            skor += 5
        else:
            skor -= 10

        # P/E < buyume orani (Lynch kurali)
        pe = info.get('trailingPE', 25)
        if pe and growth and pe < growth * 100:
            skor += 10

        # Sektör bilgisi (Lynch favorileri)
        sector = info.get('sector', '')
        lynch_favorites = ['Consumer Cyclical', 'Consumer Defensive', 'Healthcare']
        if any(fav in sector for fav in lynch_favorites):
            skor += 5

        return max(0, min(100, skor))

    def _livermore_analiz(self, ticker, df):
        """Jesse Livermore - Trend takip + Pivot noktalari"""
        if df is None or len(df) < 50:
            return 50  # Yetersiz veri

        skor = 50
        close = df['Close']

        # Trend yonu
        sma50 = close.rolling(50).mean().iloc[-1]
        sma20 = close.rolling(20).mean().iloc[-1]
        current = close.iloc[-1]

        if current > sma20 > sma50:
            skor += 20  # Guclu yukari trend
        elif current > sma20:
            skor += 10  # Kisa vadeli yukari
        elif current < sma20 < sma50:
            skor -= 20  # Guclu asagi trend
        elif current < sma20:
            skor -= 10  # Kisa vadeli asagi

        # Pivot noktasi (son 20 gunun high/low)
        recent = df.iloc[-20:]
        high_20 = recent['High'].max()
        low_20 = recent['Low'].min()
        pivot = (high_20 + low_20 + close.iloc[-1]) / 3

        # Fiyat pivot uzerinde mi?
        if current > pivot * 1.02:
            skor += 10  # Pivot uzeri = guclu
        elif current < pivot * 0.98:
            skor -= 10  # Pivot alti = zayif

        # Hacim trendi
        if 'Volume' in df.columns:
            vol_avg = df['Volume'].iloc[-20:].mean()
            vol_current = df['Volume'].iloc[-1]
            if vol_current > vol_avg * 1.5 and current > close.iloc[-2]:
                skor += 10  # Yukari hacimli kirilim
            elif vol_current > vol_avg * 1.5 and current < close.iloc[-2]:
                skor -= 10  # Asagi hacimli kirilim

        return max(0, min(100, skor))


def analiz_et(ticker, df=None, zaman_dilimi='1D'):
    uzman = YatirimciUzman()
    return uzman.analiz_et(ticker, df, zaman_dilimi)


if __name__ == "__main__":
    print("=" * 70)
    print("YATIRIMCI UZMANI TEST")
    print("=" * 70)
    print("Ornek: GARAN.IS")
    print("-" * 70)

    uzman = YatirimciUzman()
    sonuc = uzman.analiz_et('GARAN.IS')

    print(f"Sinyal: {sonuc['sinyal']}")
    print(f"Skor: {sonuc['skor']}")
    print(f"Guven: {sonuc['guven']}")
    print(f"Neden: {sonuc['neden']}")
    print(f"Detaylar:")
    for k, v in sonuc.get('detay', {}).items():
        print(f"  {k}: {v}")

    print("=" * 70)
