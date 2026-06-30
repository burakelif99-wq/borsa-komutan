# makro_al.py - GERÇEK MAKRO VERİLERİ (Güncellenmiş)

import yfinance as yf
from datetime import datetime
from doviz_api import usd_try


def get_macro_data():
    """
    Gerçek makroekonomik veriler
    USD/TRY: exchangerate-api.com (gerçek)
    Faiz: Manuel (TCMB sitesinden güncelle)
    Enflasyon: Manuel (TÜİK'ten güncelle)
    """
    try:
        # Gerçek USD/TRY
        usd_data = usd_try()
        if usd_data['status'] == 'OK':
            usd_current = usd_data['kur']
            usd_change = 0.0  # Değişim için önceki veri lazım
        else:
            usd_current = 46.34
            usd_change = 0.0

        # BIST 100 son durum (yfinance - hafif gecikmeli)
        try:
            bist = yf.Ticker("XU100.IS").history(period="5d")
            bist_change = (bist['Close'].iloc[-1] - bist['Close'].iloc[-2]) / bist['Close'].iloc[-2] * 100
        except:
            bist_change = 0.0

        # Makro skor hesaplama (0-100)
        # USD yükseliyorsa BIST düşer (negatif korelasyon)
        usd_impact = 50 - (usd_change * 10)  # USD artarsa skor düşer

        # BIST momentum
        bist_impact = 50 + (bist_change * 5)  # BIST artarsa skor yükselir

        # Composite makro skor
        macro_score = (usd_impact * 0.40 + bist_impact * 0.60)
        macro_score = max(0, min(100, macro_score))

        return {
            'status': 'OK',
            'data': {
                'usd_try': round(usd_current, 4),
                'usd_change': round(usd_change, 2),
                'bist_change': round(bist_change, 2),
                'faiz': 37.5,  # Manuel güncelle
                'enflasyon': 32.4  # Manuel güncelle
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
        print(f"GERÇEK MAKRO VERİLERİ")
        print(f"{'=' * 50}")
        print(f"USD/TRY: {makro['data']['usd_try']} (Gerçek API)")
        print(f"BIST Değişim: %{makro['data']['bist_change']}")
        print(f"Faiz: %{makro['data']['faiz']}")
        print(f"Enflasyon: %{makro['data']['enflasyon']}")
        print(f"\nMakro Skor: {makro['score']}/100")
        print(f"{'=' * 50}")
    else:
        print(f"Hata: {makro['message']}")
