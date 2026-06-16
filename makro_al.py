# makro_al.py - MAKROEKONOMİK MODÜL

import yfinance as yf
from datetime import datetime


def get_macro_data():
    """
    Makroekonomik verileri çeker
    USD/TRY, faiz, enflasyon etkisi
    """
    try:
        # USD/TRY
        usd_try = yf.Ticker("USDTRY=X").history(period="5d")
        usd_current = usd_try['Close'].iloc[-1]
        usd_change = (usd_try['Close'].iloc[-1] - usd_try['Close'].iloc[-2]) / usd_try['Close'].iloc[-2] * 100

        # BIST 100 son durum
        bist = yf.Ticker("XU100.IS").history(period="5d")
        bist_change = (bist['Close'].iloc[-1] - bist['Close'].iloc[-2]) / bist['Close'].iloc[-2] * 100

        # Makro skor hesaplama (0-100)
        usd_impact = 50 - (usd_change * 10)
        bist_impact = 50 + (bist_change * 5)

        macro_score = (usd_impact * 0.40 + bist_impact * 0.60)
        macro_score = max(0, min(100, macro_score))

        return {
            'status': 'OK',
            'data': {
                'usd_try': round(usd_current, 4),
                'usd_change': round(usd_change, 2),
                'bist_change': round(bist_change, 2),
                'faiz': 50.0,
                'enflasyon': 61.5
            },
            'score': round(macro_score, 1),
            'weight': 0.20,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': str(e),
            'score': 50,
            'weight': 0.20
        }


if __name__ == "__main__":
    makro = get_macro_data()
    if makro['status'] == 'OK':
        print(f"\n{'=' * 50}")
        print(f"MAKRO VERİLER")
        print(f"{'=' * 50}")
        print(f"USD/TRY: {makro['data']['usd_try']} (%{makro['data']['usd_change']})")
        print(f"BIST Değişim: %{makro['data']['bist_change']}")
        print(f"Faiz: %{makro['data']['faiz']}")
        print(f"Enflasyon: %{makro['data']['enflasyon']}")
        print(f"\nMakro Skor: {makro['score']}/100")
        print(f"{'=' * 50}")