# risk_uzman.py - Risk Yönetimi Uzmanı
# Borsa Komutan v3.0 - Modul 4

import numpy as np
import pandas as pd
from datetime import datetime
from scipy import stats

class RiskUzman:
    """
    Kelly Kriteri, Value at Risk (VaR), Pozisyon Buyuklugu,
    Maksimum Drawdown, Sharpe Ratio, Beta analizi.
    """

    def __init__(self, risk_tolerance='moderate'):
        self.risk_tolerance = risk_tolerance
        self.kriterler = {
            'conservative': {'var_limit': 0.02, 'kelly_max': 0.10, 'max_dd': -0.10},
            'moderate': {'var_limit': 0.05, 'kelly_max': 0.20, 'max_dd': -0.15},
            'aggressive': {'var_limit': 0.10, 'kelly_max': 0.30, 'max_dd': -0.25}
        }

    def analiz_et(self, df, ticker="Portfoy", portfoy_df=None, zaman_dilimi='1D'):
        """
        Risk analizi yap

        Returns:
            dict: {'sinyal': 'AL'/'SAT'/'BEKLE', 'skor': 0-100, 'guven': 0-1, 'neden': '...'}
        """
        if df is None or len(df) < 30:
            return {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.3, 'neden': 'Yetersiz veri'}

        close = df['Close']
        returns = close.pct_change().dropna()

        if len(returns) < 20:
            return {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.3, 'neden': 'Yetersiz getiri verisi'}

        skorlar = {}
        nedenler = []
        esikler = self.kriterler.get(self.risk_tolerance, self.kriterler['moderate'])

        # 1. Kelly Kriteri (f* = (bp - q) / b)
        # Basitlestirilmis: Win rate ve avg win/avg loss
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.5
        avg_win = wins.mean() if len(wins) > 0 else 0.01
        avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.01

        if avg_loss > 0:
            kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_loss
            kelly = max(0, min(kelly, esikler['kelly_max']))  # Cap
        else:
            kelly = 0

        # Kelly skoru (0.10-0.20 ideal)
        if 0.10 <= kelly <= 0.20:
            skorlar['kelly'] = 70
            nedenler.append(f"Kelly ideal ({kelly:.2f})")
        elif kelly > 0.20:
            skorlar['kelly'] = 55  # Cok agresif
            nedenler.append(f"Kelly yuksek ({kelly:.2f}), dikkat")
        elif kelly > 0.05:
            skorlar['kelly'] = 50
        else:
            skorlar['kelly'] = 35  # Dusuk edge
            nedenler.append(f"Kelly dusuk ({kelly:.2f})")

        # 2. Value at Risk (VaR) - 95% confidence
        var_95 = np.percentile(returns, 5)
        var_limit = esikler['var_limit']

        if abs(var_95) < var_limit:
            skorlar['var'] = 70  # Risk kabul edilebilir
            nedenler.append(f"VaR dusuk ({var_95:.2%})")
        elif abs(var_95) < var_limit * 2:
            skorlar['var'] = 50  # Orta risk
            nedenler.append(f"VaR orta ({var_95:.2%})")
        else:
            skorlar['var'] = 30  # Yuksek risk
            nedenler.append(f"VaR yuksek ({var_95:.2%})")

        # 3. Maksimum Drawdown (Rolling)
        rolling_max = close.cummax()
        drawdown = (close - rolling_max) / rolling_max
        max_dd = drawdown.min()
        current_dd = drawdown.iloc[-1]

        max_dd_limit = esikler['max_dd']

        if current_dd > max_dd_limit * 0.5:  # Yari limiti gecmemis
            skorlar['drawdown'] = 65
        elif current_dd > max_dd_limit:  # Limit asilmis
            skorlar['drawdown'] = 25
            nedenler.append(f"Drawdown limit asildi ({current_dd:.1%})")
        else:
            skorlar['drawdown'] = 45
            nedenler.append(f"Drawdown yuksek ({current_dd:.1%})")

        # 4. Volatilite (Annualized)
        vol = returns.std() * np.sqrt(252)
        if vol < 0.20:
            skorlar['volatilite'] = 70  # Dusuk vol = guvenli
        elif vol < 0.35:
            skorlar['volatilite'] = 50  # Orta vol
        else:
            skorlar['volatilite'] = 30  # Yuksek vol = riskli
            nedenler.append(f"Volatilite yuksek ({vol:.1%})")

        # 5. Sharpe Ratio (Risk-free = 0)
        if returns.std() > 0:
            sharpe = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
        else:
            sharpe = 0

        if sharpe > 1.0:
            skorlar['sharpe'] = 75
            nedenler.append(f"Sharpe guclu ({sharpe:.2f})")
        elif sharpe > 0.5:
            skorlar['sharpe'] = 55
        elif sharpe > 0:
            skorlar['sharpe'] = 45
        else:
            skorlar['sharpe'] = 25
            nedenler.append(f"Sharpe negatif ({sharpe:.2f})")

        # 6. Beta (Piyasa korelasyonu) - eger portfoy verisi varsa
        if portfoy_df is not None and len(portfoy_df) == len(df):
            portfoy_returns = portfoy_df['Close'].pct_change().dropna()
            if len(portfoy_returns) == len(returns) and returns.std() > 0 and portfoy_returns.std() > 0:
                beta = np.cov(returns, portfoy_returns)[0][1] / np.var(portfoy_returns)

                if 0.8 < beta < 1.2:
                    skorlar['beta'] = 60  # Piyasa ile uyumlu
                elif beta < 0.8:
                    skorlar['beta'] = 55  # Dusuk korelasyon = diversifikasyon
                else:
                    skorlar['beta'] = 40  # Yuksek beta = daha riskli
            else:
                skorlar['beta'] = 50
        else:
            skorlar['beta'] = 50

        # 7. Pozisyon Buyuklugu (Kelly-based)
        position_size = min(kelly, 0.25)  # Max %25
        if position_size > 0.15:
            skorlar['pozisyon'] = 65
        elif position_size > 0.08:
            skorlar['pozisyon'] = 55
        else:
            skorlar['pozisyon'] = 40

        # Agirlikli ortalama
        agirliklar = {
            'kelly': 0.15, 'var': 0.20, 'drawdown': 0.20,
            'volatilite': 0.15, 'sharpe': 0.15, 'beta': 0.05, 'pozisyon': 0.10
        }

        toplam = sum(skorlar.get(k, 50) * v for k, v in agirliklar.items())
        final_skor = round(toplam / sum(agirliklar.values()), 1)

        # Guven (veri zenginligi)
        guven = 0.6 + (len(returns) / 252) * 0.3  # 0.6 - 0.9
        guven = min(0.9, guven)

        # Karar (Risk skoru dusukse = yuksek risk = SAT veya BEKLE)
        # NOT: Risk uzmani "guvenli" ise AL, "riskli" ise SAT
        if final_skor >= 60:
            sinyal = 'AL'  # Risk kabul edilebilir
        elif final_skor <= 40:
            sinyal = 'SAT'  # Risk cok yuksek
        else:
            sinyal = 'BEKLE'  # Risk orta

        neden = "; ".join(nedenler) if nedenler else "Risk metrikleri karisik"

        return {
            'sinyal': sinyal,
            'skor': final_skor,
            'guven': round(guven, 2),
            'neden': neden,
            'detay': skorlar,
            'meta': {
                'ticker': ticker,
                'kelly': round(kelly, 3),
                'var_95': round(var_95, 4),
                'max_dd': round(max_dd, 4),
                'current_dd': round(current_dd, 4),
                'volatilite': round(vol, 4),
                'sharpe': round(sharpe, 3),
                'position_size': round(position_size, 3),
                'zaman_dilimi': zaman_dilimi
            }
        }

    def pozisyon_hesapla(self, sermaye, risk_skor, kelly=None):
        """
        Pozisyon buyuklugu hesapla

        Args:
            sermaye: Toplam sermaye
            risk_skor: Risk uzmani skoru (0-100)
            kelly: Kelly kriteri degeri (opsiyonel)

        Returns:
            dict: Pozisyon bilgileri
        """
        if risk_skor >= 60:
            risk_multiplier = 1.0
        elif risk_skor >= 40:
            risk_multiplier = 0.5
        else:
            risk_multiplier = 0.0  # Pozisyon yok

        base_size = 0.10  # Base %10

        if kelly and kelly > 0:
            kelly_size = min(kelly, 0.25) * risk_multiplier
        else:
            kelly_size = base_size * risk_multiplier

        pozisyon = sermaye * kelly_size

        return {
            'sermaye': sermaye,
            'yuzde': round(kelly_size * 100, 1),
            'tutar': round(pozisyon, 2),
            'risk_multiplier': risk_multiplier,
            'kelly': kelly
        }


def analiz_et(df, ticker="Portfoy", portfoy_df=None, zaman_dilimi='1D'):
    uzman = RiskUzman()
    return uzman.analiz_et(df, ticker, portfoy_df, zaman_dilimi)


if __name__ == "__main__":
    print("=" * 70)
    print("RISK UZMANI TEST")
    print("=" * 70)

    # Test verisi
    np.random.seed(42)
    dates = pd.date_range('2026-01-01', periods=100, freq='D')
    returns = np.random.randn(100) * 0.02 + 0.001  # %0.1 gunluk ort, %2 vol
    close = 100 * np.cumprod(1 + returns)

    df = pd.DataFrame({
        'Open': close * 0.99,
        'High': close * 1.02,
        'Low': close * 0.98,
        'Close': close,
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    uzman = RiskUzman(risk_tolerance='moderate')
    sonuc = uzman.analiz_et(df, 'TEST.IS')

    print(f"Sinyal: {sonuc['sinyal']}")
    print(f"Skor: {sonuc['skor']}")
    print(f"Guven: {sonuc['guven']}")
    print(f"Neden: {sonuc['neden']}")
    print(f"Detaylar:")
    for k, v in sonuc.get('detay', {}).items():
        print(f"  {k}: {v}")

    print(f"Meta:")
    for k, v in sonuc.get('meta', {}).items():
        print(f"  {k}: {v}")

    # Pozisyon hesapla
    pozisyon = uzman.pozisyon_hesapla(100000, sonuc['skor'], sonuc['meta']['kelly'])
    print(f"Pozisyon Onerisi:")
    print(f"  Sermaye: {pozisyon['sermaye']:,.0f} TL")
    print(f"  Yuzde: %{pozisyon['yuzde']}")
    print(f"  Tutar: {pozisyon['tutar']:,.0f} TL")

    print("=" * 70)
