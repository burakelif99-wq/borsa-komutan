# makro_uzman.py - Sentiment & Makro Uzmanı
# Borsa Komutan v3.0 - Modul 5

import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class MakroUzman:
    """
    Haber analizi, USD/TRY, faiz oranlari, enflasyon,
    sektor sentimenti, makro trendler.
    """

    def __init__(self):
        self.makro_kayit = {}  # Cache
        self.usd_esik = 0.02  # %2 degisim
        self.faiz_esik = 0.005  # 50bp

    def analiz_et(self, ticker=None, df=None, zaman_dilimi='1D',
                  haber_skor=None, usdtry_df=None, faiz=None, enflasyon=None):
        """
        Makro analiz yap

        Args:
            ticker: Hisse kodu (opsiyonel)
            df: Hisse DataFrame (opsiyonel)
            haber_skor: -1 (negatif) ile 1 (pozitif) arasi
            usdtry_df: USD/TRY DataFrame
            faiz: Mevcut faiz orani (ornegin 0.50 = %50)
            enflasyon: Mevcut enflasyon orani (ornegin 0.65 = %65)

        Returns:
            dict: {'sinyal': 'AL'/'SAT'/'BEKLE', 'skor': 0-100, 'guven': 0-1, 'neden': '...'}
        """
        skorlar = {}
        nedenler = []
        guven_faktorleri = []

        # 1. USD/TRY Analizi
        if usdtry_df is not None and len(usdtry_df) > 20:
            usd_close = usdtry_df['Close']
            usd_change_1w = (usd_close.iloc[-1] - usd_close.iloc[-5]) / usd_close.iloc[-5] if len(usd_close) >= 5 else 0
            usd_change_1m = (usd_close.iloc[-1] - usd_close.iloc[-20]) / usd_close.iloc[-20] if len(usd_close) >= 20 else 0

            # USD yukseliyor = BIST icin genelde negatif (ozellikle ithalatci sirketler)
            if usd_change_1w > self.usd_esik:
                skorlar['usd'] = 35  # USD hizli yukseliyor = riskli
                nedenler.append(f"USD yukseliyor (+{usd_change_1w:.1%} 1H)")
            elif usd_change_1w < -self.usd_esik:
                skorlar['usd'] = 65  # USD dusuyor = pozitif
                nedenler.append(f"USD dusuyor ({usd_change_1w:.1%} 1H)")
            else:
                skorlar['usd'] = 50  # Stabil

            guven_faktorleri.append(0.8)
        else:
            skorlar['usd'] = 50
            guven_faktorleri.append(0.3)

        # 2. Faiz Orani Analizi
        if faiz is not None:
            # TCMB faiz orani (ornegin %50 = 0.50)
            if faiz > 0.50:  # Yuksek faiz = negatif
                skorlar['faiz'] = 40
                nedenler.append(f"Faiz cok yuksek ({faiz:.1%})")
            elif faiz > 0.30:
                skorlar['faiz'] = 45
                nedenler.append(f"Faiz yuksek ({faiz:.1%})")
            elif faiz < 0.15:  # Dusuk faiz = pozitif
                skorlar['faiz'] = 65
                nedenler.append(f"Faiz dusuk ({faiz:.1%})")
            else:
                skorlar['faiz'] = 55

            guven_faktorleri.append(0.9)
        else:
            skorlar['faiz'] = 50
            guven_faktorleri.append(0.2)

        # 3. Enflasyon Analizi
        if enflasyon is not None:
            # Enflasyon orani (ornegin %65 = 0.65)
            if enflasyon > 0.60:  # Hyper enflasyon = cok riskli
                skorlar['enflasyon'] = 30
                nedenler.append(f"Enflasyon cok yuksek ({enflasyon:.1%})")
            elif enflasyon > 0.40:
                skorlar['enflasyon'] = 40
                nedenler.append(f"Enflasyon yuksek ({enflasyon:.1%})")
            elif enflasyon < 0.10:  # Dusuk enflasyon = pozitif
                skorlar['enflasyon'] = 70
                nedenler.append(f"Enflasyon dusuk ({enflasyon:.1%})")
            else:
                skorlar['enflasyon'] = 55

            guven_faktorleri.append(0.9)
        else:
            skorlar['enflasyon'] = 50
            guven_faktorleri.append(0.2)

        # 4. Haber/Sentiment Analizi
        if haber_skor is not None:
            # haber_skor: -1 (cok negatif) ile 1 (cok pozitif)
            haber_skor_100 = (haber_skor + 1) * 50  # 0-100 arasina cevir
            skorlar['haber'] = haber_skor_100

            if haber_skor > 0.3:
                nedenler.append(f"Haberler pozitif (skor: {haber_skor:.2f})")
            elif haber_skor < -0.3:
                nedenler.append(f"Haberler negatif (skor: {haber_skor:.2f})")

            guven_faktorleri.append(0.7)
        else:
            skorlar['haber'] = 50
            guven_faktorleri.append(0.2)

        # 5. Sektor Makro Etkisi (eger ticker verilmisse)
        if ticker:
            sektor_skor = self._sektor_makro_etkisi(ticker, skorlar)
            skorlar['sektor'] = sektor_skor
            guven_faktorleri.append(0.6)
        else:
            skorlar['sektor'] = 50

        # 6. Trend Analizi (BIST100 trendi)
        if df is not None and len(df) > 50:
            close = df['Close']
            sma50 = close.rolling(50).mean().iloc[-1]
            sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else sma50

            if close.iloc[-1] > sma50 > sma200:
                skorlar['trend'] = 65
                nedenler.append("BIST trend yukari")
            elif close.iloc[-1] < sma50 < sma200:
                skorlar['trend'] = 35
                nedenler.append("BIST trend asagi")
            else:
                skorlar['trend'] = 50

            guven_faktorleri.append(0.8)
        else:
            skorlar['trend'] = 50
            guven_faktorleri.append(0.3)

        # Agirlikli ortalama
        agirliklar = {
            'usd': 0.20, 'faiz': 0.20, 'enflasyon': 0.20,
            'haber': 0.15, 'sektor': 0.10, 'trend': 0.15
        }

        toplam = sum(skorlar.get(k, 50) * v for k, v in agirliklar.items())
        final_skor = round(toplam / sum(agirliklar.values()), 1)

        # Guven (veri kalitesi)
        if guven_faktorleri:
            guven = sum(guven_faktorleri) / len(guven_faktorleri)
        else:
            guven = 0.3

        guven = round(min(0.9, guven), 2)

        # Karar (Makro skoru yuksek = AL, dusuk = SAT)
        if final_skor >= 60:
            sinyal = 'AL'
        elif final_skor <= 40:
            sinyal = 'SAT'
        else:
            sinyal = 'BEKLE'

        neden = "; ".join(nedenler) if nedenler else "Makro gostergeler notr"

        return {
            'sinyal': sinyal,
            'skor': final_skor,
            'guven': guven,
            'neden': neden,
            'detay': skorlar,
            'meta': {
                'ticker': ticker,
                'usd_change': round(usd_change_1w, 4) if 'usd_change_1w' in dir() else None,
                'faiz': faiz,
                'enflasyon': enflasyon,
                'haber_skor': haber_skor,
                'zaman_dilimi': zaman_dilimi
            }
        }

    def _sektor_makro_etkisi(self, ticker, makro_skorlar):
        """
        Sektore gore makro etkisi degisir.
        Ornegin: USD yukselince ihracatci sirketler kazanir.
        """
        # Basit sektor haritasi
        sektor_map = {
            'THYAO': 'Havacilik', 'PGSUS': 'Havacilik',
            'GARAN': 'Banka', 'AKBNK': 'Banka', 'ISCTR': 'Banka', 'YKBNK': 'Banka',
            'ASELS': 'Savunma', 'KONTR': 'Savunma',
            'EREGL': 'Celik', 'KRDMD': 'Celik',
            'TUPRS': 'Enerji', 'ASTOR': 'Enerji',
            'BIMAS': 'Perakende', 'SOKM': 'Perakende',
            'FROTO': 'Otomotiv', 'TOASO': 'Otomotiv'
        }

        kod = ticker.replace('.IS', '')
        sektor = sektor_map.get(kod, 'Diger')

        usd_skor = makro_skorlar.get('usd', 50)
        faiz_skor = makro_skorlar.get('faiz', 50)

        # Ihracatci sirketler USD yukselince pozitif etkilenir
        ihracatci = ['Havacilik', 'Celik', 'Otomotiv', 'Savunma', 'Tekstil']
        ithalatci = ['Enerji', 'Perakende', 'Banka']

        if sektor in ihracatci:
            # USD yukseliyorsa (skor dusuk) bu sirketler icin iyi
            if usd_skor < 45:
                return 65  # Pozitif etki
            elif usd_skor > 55:
                return 45  # Negatif etki
        elif sektor in ithalatci:
            # USD yukseliyorsa (skor dusuk) bu sirketler icin kotu
            if usd_skor < 45:
                return 40  # Negatif etki
            elif usd_skor > 55:
                return 60  # Pozitif etki

        return 50  # Notr

    def get_usdtry(self, period="3mo"):
        """USD/TRY verisini al"""
        try:
            usd = yf.Ticker("USDTRY=X")
            df = usd.history(period=period)
            return df
        except:
            return None

    def get_faiz_tahmin(self):
        """Basit faiz tahmini (gercek veri yerine)"""
        # Gercek implementasyonda TCMB API'si kullanilir
        return 0.50  # %50 (ornek)

    def get_enflasyon_tahmin(self):
        """Basit enflasyon tahmini"""
        # Gercek implementasyonda TUIK API'si kullanilir
        return 0.65  # %65 (ornek)


def analiz_et(ticker=None, df=None, zaman_dilimi='1D',
              haber_skor=None, usdtry_df=None, faiz=None, enflasyon=None):
    uzman = MakroUzman()
    return uzman.analiz_et(ticker, df, zaman_dilimi, haber_skor, usdtry_df, faiz, enflasyon)


if __name__ == "__main__":
    print("=" * 70)
    print("MAKRO UZMANI TEST")
    print("=" * 70)

    uzman = MakroUzman()

    # Test verisi
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=60, freq='D')
    usd = 35 + np.cumsum(np.random.randn(60) * 0.1)
    usd_df = pd.DataFrame({'Close': usd}, index=dates)

    # Test 1: Olumlu makro
    print("1. OLUMLU MAKRO SENARYOSU")
    print("-" * 70)

    sonuc = uzman.analiz_et(        ticker='THYAO.IS',
        haber_skor=0.5,  # Pozitif haber
        usdtry_df=usd_df,
        faiz=0.15,  # Dusuk faiz
        enflasyon=0.08  # Dusuk enflasyon
    )

    print(f"Sinyal: {sonuc['sinyal']}")
    print(f"Skor: {sonuc['skor']}")
    print(f"Guven: {sonuc['guven']}")
    print(f"Neden: {sonuc['neden']}")
    print(f"Detaylar:")
    for k, v in sonuc.get('detay', {}).items():
        print(f"  {k}: {v}")

    # Test 2: Olumsuz makro
    print("2. OLUMSUZ MAKRO SENARYOSU")
    print("-" * 70)

    usd_olumsuz = 35 + np.cumsum(np.random.randn(60) * 0.1 + 0.05)  # Yukari trend
    usd_df_olumsuz = pd.DataFrame({'Close': usd_olumsuz}, index=dates)

    sonuc2 = uzman.analiz_et(
        ticker='GARAN.IS',
        haber_skor=-0.4,  # Negatif haber
        usdtry_df=usd_df_olumsuz,
        faiz=0.50,  # Yuksek faiz
        enflasyon=0.65  # Yuksek enflasyon
    )

    print(f"Sinyal: {sonuc2['sinyal']}")
    print(f"Skor: {sonuc2['skor']}")
    print(f"Guven: {sonuc2['guven']}")
    print(f"Neden: {sonuc2['neden']}")

    print("=" * 70)
