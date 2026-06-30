# temel_uzman.py - Temel Analiz Uzmanı
# Borsa Komutan v3.0 - Modul 2

import yfinance as yf
import numpy as np
from datetime import datetime

class TemelUzman:
    """
    Bilanço, P/E, ROE, F/K, PD/DD, borc/ozkaynak,
    kar buyumesi, temettu verimi analizi.
    """

    def __init__(self):
        self.kriterler = {
            'pe_ideal': (5, 15),      # Ideal P/E araligi
            'roe_min': 0.15,           # Min ROE %15
            'kar_buyume_min': 0.10,    # Min yillik kar buyumesi %10
            'borc_oran_max': 2.0,      # Max borc/ozkaynak
            'pd_dd_ideal': (0.5, 2.0), # Ideal PD/DD
            'temettu_min': 0.02        # Min temettu verimi %2
        }

    def analiz_et(self, ticker, df=None, zaman_dilimi='1D'):
        """
        Temel analiz yap

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

            # 1. P/E Orani
            pe = info.get('trailingPE', info.get('forwardPE', None))
            if pe:
                if pe < self.kriterler['pe_ideal'][0]:
                    skorlar['pe'] = 75  # Cok ucuz
                    nedenler.append(f"P/E cok dusuk ({pe:.1f})")
                elif pe < self.kriterler['pe_ideal'][1]:
                    skorlar['pe'] = 65  # Ucuz
                    nedenler.append(f"P/E uygun ({pe:.1f})")
                elif pe < 25:
                    skorlar['pe'] = 45  # Pahali
                else:
                    skorlar['pe'] = 25  # Cok pahali
                    nedenler.append(f"P/E yuksek ({pe:.1f})")
            else:
                skorlar['pe'] = 50

            # 2. ROE
            roe = info.get('returnOnEquity', None)
            if roe:
                if roe > self.kriterler['roe_min']:
                    skorlar['roe'] = 70
                    nedenler.append(f"ROE guclu ({roe*100:.1f}%)")
                elif roe > 0.10:
                    skorlar['roe'] = 55
                else:
                    skorlar['roe'] = 35
                    nedenler.append(f"ROE zayif ({roe*100:.1f}%)")
            else:
                skorlar['roe'] = 50

            # 3. PD/DD (Price/Book)
            pb = info.get('priceToBook', None)
            if pb:
                low, high = self.kriterler['pd_dd_ideal']
                if low < pb < high:
                    skorlar['pd_dd'] = 65
                    nedenler.append(f"PD/DD uygun ({pb:.2f})")
                elif pb < low:
                    skorlar['pd_dd'] = 70  # Cok ucuz
                    nedenler.append(f"PD/DD cok dusuk ({pb:.2f})")
                else:
                    skorlar['pd_dd'] = 35
                    nedenler.append(f"PD/DD yuksek ({pb:.2f})")
            else:
                skorlar['pd_dd'] = 50

            # 4. Kar Buyumesi (Revenue Growth)
            rev_growth = info.get('revenueGrowth', None)
            earnings_growth = info.get('earningsGrowth', None)
            growth = earnings_growth or rev_growth

            if growth:
                if growth > self.kriterler['kar_buyume_min']:
                    skorlar['buyume'] = 70
                    nedenler.append(f"Kar buyumesi guclu ({growth*100:.1f}%)")
                elif growth > 0:
                    skorlar['buyume'] = 55
                else:
                    skorlar['buyume'] = 30
                    nedenler.append(f"Kar buyumesi negatif ({growth*100:.1f}%)")
            else:
                skorlar['buyume'] = 50

            # 5. Borc/Özkaynak (Debt/Equity)
            debt_equity = info.get('debtToEquity', None)
            if debt_equity:
                de_ratio = debt_equity / 100  # yfinance % olarak verir
                if de_ratio < self.kriterler['borc_oran_max']:
                    skorlar['borc'] = 65
                else:
                    skorlar['borc'] = 35
                    nedenler.append(f"Borc yuksek (D/E: {de_ratio:.1f})")
            else:
                skorlar['borc'] = 50

            # 6. Temettu Verimi
            dividend = info.get('dividendYield', None)
            if dividend:
                div_yield = dividend  # zaten oran olarak gelir
                if div_yield > self.kriterler['temettu_min']:
                    skorlar['temettu'] = 65
                    nedenler.append(f"Temettu verimi iyi ({div_yield*100:.1f}%)")
                else:
                    skorlar['temettu'] = 45
            else:
                skorlar['temettu'] = 50  # Temettu yok

            # 7. F/K (Fiyat/Kazanç) - P/E ile ayni ama farkli perspektif
            # Zaten P/E'de degerlendirildi

            # 8. Piyasa Degeri / Sektör Ortalaması (Basit karsilastirma)
            sector = info.get('sector', 'Unknown')
            market_cap = info.get('marketCap', 0)

            if market_cap > 10e9:  # 10B+ buyuk sirket
                skorlar['buyukluk'] = 60  # Daha stabil
            elif market_cap > 1e9:
                skorlar['buyukluk'] = 55
            else:
                skorlar['buyukluk'] = 50  # Kucuk sirket = daha riskli

            # Agirlikli ortalama
            agirliklar = {
                'pe': 0.20, 'roe': 0.20, 'pd_dd': 0.15,
                'buyume': 0.20, 'borc': 0.15, 'temettu': 0.05, 'buyukluk': 0.05
            }

            toplam = sum(skorlar.get(k, 50) * v for k, v in agirliklar.items())
            final_skor = round(toplam / sum(agirliklar.values()), 1)

            # Guven (veri kalitesi)
            dolu_veri = sum(1 for v in [pe, roe, pb, growth, debt_equity, dividend] if v is not None)
            guven = 0.4 + (dolu_veri / 6) * 0.5  # 0.4 - 0.9 arasi

            # Karar
            if final_skor >= 65:
                sinyal = 'AL'
            elif final_skor <= 35:
                sinyal = 'SAT'
            else:
                sinyal = 'BEKLE'

            neden = "; ".join(nedenler) if nedenler else "Karisik temel gostergeler"

            return {
                'sinyal': sinyal,
                'skor': final_skor,
                'guven': round(guven, 2),
                'neden': neden,
                'detay': skorlar,
                'meta': {
                    'ticker': ticker,
                    'sector': sector,
                    'market_cap': market_cap,
                    'zaman_dilimi': zaman_dilimi
                }
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


def analiz_et(ticker, df=None, zaman_dilimi='1D'):
    uzman = TemelUzman()
    return uzman.analiz_et(ticker, df, zaman_dilimi)


if __name__ == "__main__":
    print("=" * 70)
    print("TEMEL ANALIZ UZMANI TEST")
    print("=" * 70)
    print("Ornek: THYAO.IS")
    print("-" * 70)

    uzman = TemelUzman()
    sonuc = uzman.analiz_et('THYAO.IS')

    print(f"Sinyal: {sonuc['sinyal']}")
    print(f"Skor: {sonuc['skor']}")
    print(f"Guven: {sonuc['guven']}")
    print(f"Neden: {sonuc['neden']}")
    print(f"Detaylar:")
    for k, v in sonuc.get('detay', {}).items():
        print(f"  {k}: {v}")

    print("=" * 70)
