"""
veri_topla.py - Borsa Komutan v4.3
Geçmiş 5 yıl veri toplama (AI eğitimi için)
"""

import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import time

BASE_DIR = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi"
VERI_DIR = os.path.join(BASE_DIR, "veri")
os.makedirs(VERI_DIR, exist_ok=True)

from hisse_listesi import HISSE_LISTESI


def veri_topla(ticker, baslangic="2019-01-01", bitis="2024-12-31"):
    """5 yıllık veri çek."""
    try:
        data = yf.download(ticker, start=baslangic, end=bitis, progress=False)
        if data is not None and len(data) > 100:
            # Teknik göstergeler ekle
            data['RSI'] = hesapla_rsi(data['Close'])
            data['MACD'] = hesapla_macd(data['Close'])
            data['MA20'] = data['Close'].rolling(20).mean()
            data['Hacim_Ort'] = data['Volume'].rolling(20).mean()

            # Hedef: Ertesi gün getiri
            data['Ertesi_Getiri'] = data['Close'].shift(-1) / data['Close'] - 1

            # Temizle
            data = data.dropna()

            return data
    except Exception as e:
        print(f"[HATA] {ticker}: {e}")
    return None


def hesapla_rsi(close, period=14):
    """RSI hesapla."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def hesapla_macd(close):
    """MACD hesapla."""
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    return ema12 - ema26


# Toplu veri çek
def tum_verileri_topla():
    """Tüm hisseler için veri çek."""
    print("=" * 60)
    print("VERI TOPLAMA - AI Egitimi Icin")
    print("=" * 60)

    basarili = 0
    hatali = 0

    for i, ticker in enumerate(HISSE_LISTESI):
        ticker_is = ticker + '.IS'
        print(f"\n[{i + 1}/{len(HISSE_LISTESI)}] {ticker_is}...")

        data = veri_topla(ticker_is)
        if data is not None:
            # Kaydet
            dosya = os.path.join(VERI_DIR, f"{ticker}_5yil.csv")
            data.to_csv(dosya)
            print(f"  [OK] {len(data)} satır, {dosya}")
            basarili += 1
        else:
            hatali += 1

        time.sleep(0.5)  # Rate limit

    print(f"\n{'=' * 60}")
    print(f"Tamamlandi: {basarili} basarili, {hatali} hatali")
    print(f"Veri klasoru: {VERI_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    tum_verileri_topla()