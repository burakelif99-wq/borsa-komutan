#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YFINANCE TEST - Calisiyor mu?
"""

import yfinance as yf
import pandas as pd

print("=" * 60)
print("YFINANCE TEST")
print("=" * 60)

# Test 1: THYAO.IS
print("1. THYAO.IS test:")
try:
    t = yf.Ticker("THYAO.IS")
    hist = t.history(period="5d", interval="1d")
    print(f"   Veri sayisi: {len(hist)}")
    print(f"   Son tarih: {hist.index[-1] if not hist.empty else 'YOK'}")
    print(f"   Son fiyat: {hist['Close'].iloc[-1] if not hist.empty else 'YOK'}")
    print(f"   Info type: {type(t.info)}")
    if isinstance(t.info, dict):
        print(f"   Info keys: {list(t.info.keys())[:5]}")
    else:
        print(f"   Info value: {t.info}")
except Exception as e:
    print(f"   HATA: {e}")

# Test 2: GARAN.IS
print("2. GARAN.IS test:")
try:
    t = yf.Ticker("GARAN.IS")
    hist = t.history(period="5d", interval="1d")
    print(f"   Veri sayisi: {len(hist)}")
    print(f"   Son tarih: {hist.index[-1] if not hist.empty else 'YOK'}")
except Exception as e:
    print(f"   HATA: {e}")

# Test 3: ACSEL.IS
print("3. ACSEL.IS test:")
try:
    t = yf.Ticker("ACSEL.IS")
    hist = t.history(period="5d", interval="1d")
    print(f"   Veri sayisi: {len(hist)}")
    print(f"   Son tarih: {hist.index[-1] if not hist.empty else 'YOK'}")
except Exception as e:
    print(f"   HATA: {e}")

# Test 4: yfinance versiyon
print("4. yfinance versiyon:")
try:
    import yfinance
    print(f"   Versiyon: {yfinance.__version__}")
except:
    print("   Versiyon bilgisi yok")

# Test 5: Requests ile dogrudan Yahoo
print("5. Dogrudan Yahoo API test:")
import requests
url = "https://query1.finance.yahoo.com/v8/finance/chart/THYAO.IS"
params = {"interval": "1d", "range": "5d"}
try:
    resp = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    print(f"   Status: {resp.status_code}")
    print(f"   Content length: {len(resp.text)}")
    if resp.status_code == 200:
        data = resp.json()
        chart = data.get("chart", {})
        result = chart.get("result", [{}])[0]
        if result:
            timestamps = result.get("timestamp", [])
            print(f"   Timestamps: {len(timestamps)}")
            if timestamps:
                print(f"   Son tarih: {pd.to_datetime(timestamps[-1], unit='s')}")
except Exception as e:
    print(f"   HATA: {e}")

print("" + "=" * 60)