# hisse_al.py - TEK HİSSE ANALİZ MODÜLÜ

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


def hisse_analiz(sembol, period="3mo"):
    """
    Tek hisse senedi analizi
    Girdi: THYAO.IS, GARAN.IS, vb.
    Çıktı: AL/SAT/BEKLE kararı + güven skoru
    """
    try:
        # Veri çek
        ticker = yf.Ticker(f"{sembol}.IS")
        df = ticker.history(period=period)

        if df.empty or len(df) < 20:
            return {
                'status': 'ERROR',
                'message': f'{sembol} için yetersiz veri'
            }

        # Son fiyat
        son_fiyat = df['Close'].iloc[-1]
        onceki_fiyat = df['Close'].iloc[-2]
        degisim = (son_fiyat - onceki_fiyat) / onceki_fiyat * 100

        # Teknik göstergeler
        rsi = calculate_rsi(df['Close'])
        ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
        ema50 = df['Close'].ewm(span=50).mean().iloc[-1]

        # Hacim analizi
        hacim_ort = df['Volume'].rolling(20).mean().iloc[-1]
        son_hacim = df['Volume'].iloc[-1]
        hacim_yuksek = son_hacim > hacim_ort * 1.5

        # Skor hesaplama (0-100)
        teknik_skor = 0

        # RSI
        if rsi < 30:  # Aşırı satım
            teknik_skor += 30
        elif rsi < 50:
            teknik_skor += 20
        elif rsi < 70:
            teknik_skor += 10

        # EMA
        if son_fiyat > ema20 > ema50:  # Yükseliş trendi
            teknik_skor += 40
        elif son_fiyat > ema20:
            teknik_skor += 25
        elif son_fiyat > ema50:
            teknik_skor += 15

        # Hacim
        if hacim_yuksek:
            teknik_skor += 30

        # Karar
        if teknik_skor >= 75:
            karar = "AL"
            guven = min(teknik_skor, 95)
        elif teknik_skor >= 60:
            karar = "AL"
            guven = teknik_skor * 0.8
        elif teknik_skor <= 25:
            karar = "SAT"
            guven = (100 - teknik_skor) * 0.6
        else:
            karar = "BEKLE"
            guven = 50

        # Potansiyel hedef
        hedef = son_fiyat * (1 + guven / 100 * 0.1)
        stop_loss = son_fiyat * (1 - 0.05)

        return {
            'status': 'OK',
            'sembol': sembol,
            'son_fiyat': round(son_fiyat, 2),
            'degisim': round(degisim, 2),
            'rsi': round(rsi, 2),
            'ema20': round(ema20, 2),
            'ema50': round(ema50, 2),
            'hacim_yuksek': hacim_yuksek,
            'teknik_skor': teknik_skor,
            'karar': karar,
            'guven': round(guven, 1),
            'hedef': round(hedef, 2),
            'stop_loss': round(stop_loss, 2),
            'trend': 'YUKARI' if son_fiyat > ema20 else 'YANA' if son_fiyat > ema50 else 'ASAGI'
        }

    except Exception as e:
        return {
            'status': 'ERROR',
            'message': str(e)
        }


def calculate_rsi(prices, period=14):
    """RSI hesapla"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]


def coklu_hisse_analiz(hisseler):
    """
    Birden fazla hisse analiz et
    """
    sonuclar = []

    for sembol in hisseler:
        print(f"Analiz: {sembol}...")
        sonuc = hisse_analiz(sembol)
        sonuclar.append(sonuc)

    # AL olanları sırala
    al_hisseler = [s for s in sonuclar if s['status'] == 'OK' and s['karar'] == 'AL']
    al_hisseler.sort(key=lambda x: x['guven'], reverse=True)

    return {
        'status': 'OK',
        'toplam': len(hisseler),
        'al_hisseler': al_hisseler,
        'bekle_hisseler': [s for s in sonuclar if s['status'] == 'OK' and s['karar'] == 'BEKLE'],
        'sat_hisseler': [s for s in sonuclar if s['status'] == 'OK' and s['karar'] == 'SAT'],
        'hatalar': [s for s in sonuclar if s['status'] == 'ERROR']
    }


if __name__ == "__main__":
    # Test - Senin verdiğin hisseler
    test_hisseler = [
        'SANEL', 'HATSN', 'YAYLA', 'CELHA', 'BIGTK',
        'KONTR', 'AYEN', 'BANVT', 'SELEC',
        'THYAO', 'GARAN', 'ASELS', 'EREGL', 'SASA'
    ]

    sonuc = coklu_hisse_analiz(test_hisseler)

    print(f"\n{'=' * 60}")
    print(f"ÇOKLU HİSSE ANALİZİ")
    print(f"{'=' * 60}")
    print(f"Toplam: {sonuc['toplam']}")
    print(f"AL: {len(sonuc['al_hisseler'])}")
    print(f"BEKLE: {len(sonuc['bekle_hisseler'])}")
    print(f"SAT: {len(sonuc['sat_hisseler'])}")

    if sonuc['al_hisseler']:
        print(f"\n{'=' * 60}")
        print(f"🟢 AL VEREN HİSSELER (Güven sıralaması)")
        print(f"{'=' * 60}")
        for i, h in enumerate(sonuc['al_hisseler'][:10], 1):
            print(f"{i}. {h['sembol']}: {h['son_fiyat']} TL")
            print(f"   Güven: %{h['guven']} | Hedef: {h['hedef']} | Stop: {h['stop_loss']}")
            print(f"   Değişim: %{h['degisim']} | Trend: {h['trend']}")
            print()

    if sonuc['hatalar']:
        print(f"\nHatalar: {len(sonuc['hatalar'])}")
