"""
hisse_analiz.py - Borsa Komutan v4.0
Ana analiz motoru: 8 uzman modulu + EnsembleMotor + RegimeEngine
"""

import os
import sys
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import yfinance as yf
import pandas as pd
import numpy as np

# Proje dizini
BASE_DIR = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi"
RAPOR_DIR = os.path.join(BASE_DIR, "rapor")
os.makedirs(RAPOR_DIR, exist_ok=True)

# Uzman modulleri import et
try:
    from teknik import TeknikUzman
except ImportError:
    TeknikUzman = None
    print("[UYARI] teknik.py bulunamadi")

try:
    from temel import TemelUzman
except ImportError:
    TemelUzman = None
    print("[UYARI] temel.py bulunamadi")

try:
    from yatirimci import YatirimciUzman
except ImportError:
    YatirimciUzman = None
    print("[UYARI] yatirimci.py bulunamadi")

try:
    from risk import RiskUzman
except ImportError:
    RiskUzman = None
    print("[UYARI] risk.py bulunamadi")

try:
    from risk_tolerance import RiskTolerance
except ImportError:
    RiskTolerance = None
    print("[UYARI] risk_tolerance.py bulunamadi")

try:
    from makro import MakroUzman
except ImportError:
    MakroUzman = None
    print("[UYARI] makro.py bulunamadi")

try:
    from mikro import MikroUzman
except ImportError:
    MikroUzman = None
    print("[UYARI] mikro.py bulunamadi")

try:
    from max_drawdown import MaxDrawdownUzman
except ImportError:
    MaxDrawdownUzman = None
    print("[UYARI] max_drawdown.py bulunamadi")

try:
    from grok_al import EnsembleMotor
except ImportError:
    EnsembleMotor = None
    print("[UYARI] grok_al.py bulunamadi")

try:
    from regime_engine import RegimeEngine
except ImportError:
    RegimeEngine = None
    print("[UYARI] regime_engine.py bulunamadi")

try:
    from hisse_listesi import HISSE_LISTESI
except ImportError:
    HISSE_LISTESI = []
    print("[UYARI] hisse_listesi.py bulunamadi")


# =============================================================================
# GUVENLI VERI CEKIM FONKSIYONLARI (yfinance MultiIndex/Series cozumleri)
# =============================================================================

def _safe_scalar(val):
    """
    Series/DataFrame/Scalar degerini guvenli sekilde float scalar yapar.
    yfinance yeni surumde MultiIndex DataFrame dondurebilir.
    """
    try:
        # Eger pandas Series ise
        if hasattr(val, 'item') and callable(getattr(val, 'item')):
            # Tek elemanli mi kontrol et
            if hasattr(val, 'shape') and val.shape == (1,):
                return float(val.item())
            # DataFrame ise (MultiIndex)
            if hasattr(val, 'values'):
                flat = val.values.flatten()
                if len(flat) > 0:
                    return float(flat[0])
                return None
            return float(val.item())
        # Eger numpy array ise
        if hasattr(val, 'ndim') and val.ndim > 0:
            flat = val.flatten()
            if len(flat) > 0:
                return float(flat[0])
            return None
        # Direkt float
        return float(val)
    except Exception:
        return None


def _get_close_series(data):
    """
    DataFrame'den Close kolonunu guvenli sekilde alir.
    yfinance yeni surumde MultiIndex kolon dondurebilir.
    """
    try:
        if 'Close' in data.columns:
            close = data['Close']
            # Eger MultiIndex kolon ise, duzlestir
            if isinstance(close, pd.DataFrame):
                # Tek seviyeli kolon adi al
                close = close.iloc[:, 0] if close.shape[1] > 0 else None
            return close
        return None
    except Exception:
        return None


def safe_download(ticker, period="60d", interval="1d", max_retries=3):
    """
    Guvenli veri cekim. yfinance yeni surumde MultiIndex DataFrame dondurebilir.
    """
    for attempt in range(max_retries):
        try:
            data = yf.download(ticker, period=period, interval=interval, progress=False)
            if data is None:
                time.sleep(1)
                continue

            # DataFrame mi kontrol et
            if not isinstance(data, pd.DataFrame):
                time.sleep(1)
                continue

            # Yeterli veri var mi
            if len(data) < 5:
                time.sleep(1)
                continue

            # Close kolonu var mi
            close_series = _get_close_series(data)
            if close_series is None:
                time.sleep(1)
                continue

            # Bos veya tamamen NaN mi
            # Series icin .isna() kullan, DataFrame degil
            valid_count = close_series.dropna().shape[0]
            if valid_count < 5:
                time.sleep(1)
                continue

            return data

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"[HATA] {ticker} veri cekilemedi: {str(e)[:100]}")
                return None
    return None


def safe_get_close(data, index=-1):
    """
    Guvenli kapanis fiyati alimi.
    """
    try:
        close_series = _get_close_series(data)
        if close_series is None:
            return None
        val = close_series.iloc[index]
        return _safe_scalar(val)
    except Exception:
        return None


def safe_get_change(data):
    """
    Guvenli gunluk degisim hesaplama.
    """
    try:
        if len(data) < 2:
            return None
        son = safe_get_close(data, -1)
        onceki = safe_get_close(data, -2)
        if son is None or onceki is None or onceki == 0:
            return None
        return ((son - onceki) / onceki) * 100
    except Exception:
        return None


# =============================================================================
# UZMAN SKOR HESAPLAMA
# =============================================================================

def uzman_skor_hesapla(ticker, data):
    """
    Tum uzman modullerinden skor alir.
    Eger modul yoksa veya hata verirse 0.5 (notr) dondurur.
    """
    skorlar = {}

    # Teknik Uzman
    if TeknikUzman is not None:
        try:
            skorlar['teknik'] = TeknikUzman.analiz(data)
        except Exception as e:
            skorlar['teknik'] = 0.5
            print(f"[TEKNIK HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['teknik'] = 0.5

    # Temel Uzman
    if TemelUzman is not None:
        try:
            skorlar['temel'] = TemelUzman.analiz(ticker, data)
        except Exception as e:
            skorlar['temel'] = 0.5
            print(f"[TEMEL HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['temel'] = 0.5

    # Yatirimci Uzman
    if YatirimciUzman is not None:
        try:
            skorlar['yatirimci'] = YatirimciUzman.analiz(data)
        except Exception as e:
            skorlar['yatirimci'] = 0.5
            print(f"[YATIRIMCI HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['yatirimci'] = 0.5

    # Risk Uzman
    if RiskUzman is not None:
        try:
            skorlar['risk'] = RiskUzman.analiz(data)
        except Exception as e:
            skorlar['risk'] = 0.5
            print(f"[RISK HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['risk'] = 0.5

    # Risk Tolerance
    if RiskTolerance is not None:
        try:
            skorlar['risk_tolerance'] = RiskTolerance.analiz(data)
        except Exception as e:
            skorlar['risk_tolerance'] = 0.5
            print(f"[RISK_TOL HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['risk_tolerance'] = 0.5

    # Makro Uzman
    if MakroUzman is not None:
        try:
            skorlar['makro'] = MakroUzman.analiz()
        except Exception as e:
            skorlar['makro'] = 0.5
            print(f"[MAKRO HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['makro'] = 0.5

    # Mikro Uzman
    if MikroUzman is not None:
        try:
            skorlar['mikro'] = MikroUzman.analiz(ticker)
        except Exception as e:
            skorlar['mikro'] = 0.5
            print(f"[MIKRO HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['mikro'] = 0.5

    # Max Drawdown Uzman
    if MaxDrawdownUzman is not None:
        try:
            skorlar['max_drawdown'] = MaxDrawdownUzman.analiz(data)
        except Exception as e:
            skorlar['max_drawdown'] = 0.5
            print(f"[MAX_DD HATA] {ticker}: {str(e)[:60]}")
    else:
        skorlar['max_drawdown'] = 0.5

    return skorlar


# =============================================================================
# ENSEMBLE SKOR HESAPLAMA
# =============================================================================

def ensemble_skor_hesapla(ticker, skorlar=None, data=None):
    """
    Ensemble skor hesaplar.
    Eger EnsembleMotor varsa onu kullanir, yoksa basit agirlikli ortalama.
    """
    if data is None:
        data = safe_download(ticker)
        if data is None:
            return None, None, None, None

    if skorlar is None:
        skorlar = uzman_skor_hesapla(ticker, data)

    # Degisim bilgisi
    degisim = safe_get_change(data)
    son_fiyat = safe_get_close(data, -1)

    # EnsembleMotor varsa kullan
    if EnsembleMotor is not None:
        try:
            ensemble_skor = EnsembleMotor.hesapla(skorlar, data)
            return ensemble_skor, son_fiyat, degisim, skorlar
        except Exception as e:
            print(f"[ENSEMBLE HATA] {ticker}: {str(e)[:80]}")

    # Basit agirlikli ortalama (fallback)
    agirliklar = {
        'teknik': 0.15,
        'temel': 0.15,
        'yatirimci': 0.15,
        'risk': 0.10,
        'risk_tolerance': 0.10,
        'makro': 0.10,
        'mikro': 0.10,
        'max_drawdown': 0.15
    }

    if RegimeEngine is not None:
        try:
            rejim = RegimeEngine.tespit(data)
            agirliklar = RegimeEngine.agirlik_ayarla(rejim, agirliklar)
        except Exception:
            pass

    # Agirlikli ortalama
    toplam_agirlik = 0
    toplam_skor = 0
    for key, deger in skorlar.items():
        if key in agirliklar:
            toplam_skor += deger * agirliklar[key]
            toplam_agirlik += agirliklar[key]

    if toplam_agirlik > 0:
        ensemble_skor = toplam_skor / toplam_agirlik
    else:
        ensemble_skor = 0.5

    # Normalize et (0-1 arasi)
    ensemble_skor = max(0.0, min(1.0, ensemble_skor))

    return ensemble_skor, son_fiyat, degisim, skorlar


# =============================================================================
# TEK HISSE ANALIZI
# =============================================================================

def hisse_analiz_et(ticker):
    """
    Tek bir hisseyi analiz eder.
    Donus: (ticker, ensemble_skor, son_fiyat, degisim, skorlar, hata)
    """
    try:
        data = safe_download(ticker)
        if data is None:
            return (ticker, None, None, None, None, "Veri cekilemedi")

        skorlar = uzman_skor_hesapla(ticker, data)
        result = ensemble_skor_hesapla(ticker, skorlar, data)

        if result[0] is None:
            return (ticker, None, None, None, None, "Skor hesaplanamadi")

        ensemble_skor, son_fiyat, degisim, skorlar = result
        return (ticker, ensemble_skor, son_fiyat, degisim, skorlar, None)

    except Exception as e:
        return (ticker, None, None, None, None, str(e)[:100])


# =============================================================================
# TOPLU ANALIZ (TUM HISSeler)
# =============================================================================

def tum_hisseleri_analiz_et(hisse_listesi=None, max_workers=5):
    """
    Tum hisseleri paralel analiz eder.
    Donus: list of (ticker, skor, fiyat, degisim, skorlar, hata)
    """
    if hisse_listesi is None:
        hisse_listesi = HISSE_LISTESI

    if not hisse_listesi:
        print("[HATA] Hisse listesi bos!")
        return []

    print(f"[INFO] {len(hisse_listesi)} hisse analiz ediliyor...")
    print(f"[INFO] Paralel worker: {max_workers}")

    sonuclar = []
    basari = 0
    hata = 0

    # Paralel analiz
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(hisse_analiz_et, ticker): ticker
            for ticker in hisse_listesi
        }

        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                result = future.result(timeout=30)
                sonuclar.append(result)
                if result[1] is not None:
                    basari += 1
                else:
                    hata += 1
                    print(f"[HATA] {ticker}: {result[5]}")
            except Exception as e:
                sonuclar.append((ticker, None, None, None, None, str(e)[:100]))
                hata += 1
                print(f"[HATA] {ticker}: {str(e)[:80]}")

            # Rate limit korumasi
            time.sleep(0.3)

    print(f"[INFO] Analiz tamamlandi: {basari} basarili, {hata} hatali")
    return sonuclar


# =============================================================================
# AL/SAT LISTESI OLUSTURMA
# =============================================================================

def al_sat_listeleri_olustur(sonuclar, al_esik=0.6, sat_esik=0.4, top_n=20):
    """
    Analiz sonuclarindan AL/SAT listeleri olusturur.
    """
    gecerli_sonuclar = [s for s in sonuclar if s[1] is not None]

    if not gecerli_sonuclar:
        print("[HATA] Gecerli analiz sonucu yok!")
        return [], [], []

    # Sirala (skor yuksekten dusuge)
    gecerli_sonuclar.sort(key=lambda x: x[1], reverse=True)

    al_listesi = []
    sat_listesi = []
    notr_listesi = []

    for ticker, skor, fiyat, degisim, skorlar, hata in gecerli_sonuclar:
        hisse_bilgi = {
            'ticker': ticker,
            'skor': round(skor, 4),
            'fiyat': round(fiyat, 2) if fiyat else None,
            'degisim': round(degisim, 2) if degisim else None,
            'skorlar': {k: round(v, 4) for k, v in skorlar.items()} if skorlar else {}
        }

        if skor >= al_esik:
            al_listesi.append(hisse_bilgi)
        elif skor <= sat_esik:
            sat_listesi.append(hisse_bilgi)
        else:
            notr_listesi.append(hisse_bilgi)

    # Top N AL listesi
    al_top20 = al_listesi[:top_n]

    print(f"[INFO] AL listesi: {len(al_listesi)} hisse (Top {top_n} gosteriliyor)")
    print(f"[INFO] SAT listesi: {len(sat_listesi)} hisse")
    print(f"[INFO] NOTR listesi: {len(notr_listesi)} hisse")

    return al_top20, sat_listesi, notr_listesi


# =============================================================================
# RAPOR KAYDETME
# =============================================================================

def rapor_kaydet(al_listesi, sat_listesi, notr_listesi, tarih=None):
    """
    Analiz raporlarini rapor klasorune kaydeder.
    """
    if tarih is None:
        tarih = datetime.now().strftime("%Y-%m-%d_%H-%M")

    # TXT rapor
    txt_path = os.path.join(RAPOR_DIR, f"analiz_raporu_{tarih}.txt")
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("  BORSA KOMUTAN v4.0 - AL/SAT ANALIZ RAPORU\n")
        f.write(f"  Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        # AL Listesi (Top 20)
        f.write(f"AL SINYALLERI (Top {len(al_listesi)})\n")
        f.write("-" * 50 + "\n")
        f.write(f"{'Sira':<6}{'Hisse':<12}{'Skor':<10}{'Fiyat':<12}{'Degisim%':<10}\n")
        f.write("-" * 50 + "\n")
        for i, h in enumerate(al_listesi, 1):
            f.write(f"{i:<6}{h['ticker']:<12}{h['skor']:<10.4f}{h['fiyat'] or '-':<12}{h['degisim'] or '-':<10}\n")
        f.write("\n")

        # SAT Listesi
        f.write(f"SAT SINYALLERI ({len(sat_listesi)})\n")
        f.write("-" * 50 + "\n")
        for i, h in enumerate(sat_listesi, 1):
            f.write(f"{i:<6}{h['ticker']:<12}{h['skor']:<10.4f}{h['fiyat'] or '-':<12}{h['degisim'] or '-':<10}\n")
        f.write("\n")

        # NOTR Listesi
        f.write(f"NOTR ({len(notr_listesi)})\n")
        f.write("-" * 50 + "\n")
        for i, h in enumerate(notr_listesi, 1):
            f.write(f"{i:<6}{h['ticker']:<12}{h['skor']:<10.4f}{h['fiyat'] or '-':<12}{h['degisim'] or '-':<10}\n")

    print(f"[INFO] TXT rapor kaydedildi: {txt_path}")

    # JSON rapor
    json_path = os.path.join(RAPOR_DIR, f"analiz_raporu_{tarih}.json")
    rapor_data = {
        'tarih': datetime.now().isoformat(),
        'al_listesi': al_listesi,
        'sat_listesi': sat_listesi,
        'notr_listesi': notr_listesi
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rapor_data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] JSON rapor kaydedildi: {json_path}")

    return txt_path, json_path


# =============================================================================
# ANA FONKSIYON
# =============================================================================

def main(al_esik=0.6, sat_esik=0.4, top_n=20, max_workers=5):
    """
    Ana calistirma fonksiyonu.
    """
    print("\n" + "=" * 70)
    print("  BORSA KOMUTAN v4.0 - ANALIZ BASLIYOR")
    print("=" * 70 + "\n")

    # 1. Tum hisseleri analiz et
    sonuclar = tum_hisseleri_analiz_et(max_workers=max_workers)

    if not sonuclar:
        print("[HATA] Analiz sonucu bos!")
        return None

    # 2. AL/SAT listeleri olustur
    al_listesi, sat_listesi, notr_listesi = al_sat_listeleri_olustur(
        sonuclar, al_esik=al_esik, sat_esik=sat_esik, top_n=top_n
    )

    # 3. Rapor kaydet
    txt_path, json_path = rapor_kaydet(al_listesi, sat_listesi, notr_listesi)

    # 4. Ozet yazdir
    print("\n" + "=" * 70)
    print("  OZET")
    print("=" * 70)
    print(f"  AL Sinyali (Top {top_n}):")
    for i, h in enumerate(al_listesi[:5], 1):
        degisim_str = f"%{h['degisim']:.2f}" if h['degisim'] else "N/A"
        print(f"    {i}. {h['ticker']} - Skor: {h['skor']:.4f} - {degisim_str}")
    print(f"  ... ve {len(al_listesi)-5} hisse daha")
    print(f"\n  SAT Sinyali: {len(sat_listesi)} hisse")
    print(f"  NOTR: {len(notr_listesi)} hisse")
    print("=" * 70)

    return {
        'al_listesi': al_listesi,
        'sat_listesi': sat_listesi,
        'notr_listesi': notr_listesi,
        'txt_path': txt_path,
        'json_path': json_path
    }


# =============================================================================
# TEST BLOKU
# =============================================================================

if __name__ == "__main__":
    # Test: Tavan hisseler
    test_hisseler = ["CELHA.IS", "BIGCH.IS", "DGGYO.IS", "BAKAB.IS",
                     "BORLS.IS", "TRILC.IS", "KORDS.IS", "SANEL.IS",
                     "MTRYO.IS", "ATLAS.IS"]

    print("[TEST] Tavan hisseler analiz ediliyor...\n")
    for ticker in test_hisseler:
        result = hisse_analiz_et(ticker)
        ticker, skor, fiyat, degisim, skorlar, hata = result
        if skor is not None:
            degisim_str = f"%{degisim:.2f}" if degisim else "N/A"
            print(f"{ticker}: Skor={skor:.4f}, Fiyat={fiyat:.2f}, Degisim={degisim_str}")
            if skorlar:
                print(f"  Skorlar: {', '.join([f'{k}={v:.2f}' for k,v in skorlar.items()])}")
        else:
            print(f"{ticker}: HATA - {hata}")

    print("\n" + "=" * 70)
    print("[TEST] Tam analiz baslatiliyor...")
    print("=" * 70 + "\n")

    # Tam analiz
    # main(al_esik=0.6, sat_esik=0.4, top_n=20, max_workers=5)