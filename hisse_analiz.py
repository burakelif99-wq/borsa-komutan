# =============================================================================
# hisse_analiz.py - Borsa Komutan v4.3 (AI Entegre)
# =============================================================================

import os
import json
import time
import schedule
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from hisse_listesi import HISSE_LISTESI
import yfinance as yf
import pandas as pd
import numpy as np

# =============================================================================
# AI ENTEGRASYONU
# =============================================================================

try:
    from ai_skorlayici import AIModel
    import os

    # En son modeli otomatik bul (once v431, sonra v43)
    model_dir = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\modeller"
    modeller = [
        f for f in os.listdir(model_dir) 
        if (f.startswith('ai_model_v43_') or f.startswith('ai_model_v431_')) 
        and f.endswith('.joblib') and not f.endswith('.bak')
    ]

    if modeller:
        modeller.sort(reverse=True)
        model_yolu = os.path.join(model_dir, modeller[0])
        print(f"[OK] En son model: {modeller[0]}")
    else:
        model_yolu = None
        print("[UYARI] v4.3 model bulunamadi, varsayilan kullanilacak")

    AI_MODEL = AIModel(model_yolu)
    AI_AKTIF = True
    print("[OK] AI Model yuklendi")
except Exception as e:
    print(f"[UYARI] AI Model yuklenemedi: {e}")
    AI_AKTIF = False


# =============================================================================
# AI SKORLAMA FONKSIYONLARI
# =============================================================================

# hisse_analiz.py - AI ENTEGRASYONU bölümüne ekle:

def ai_skor_hesapla(ticker, data):
    """Tek hisse için AI skoru hesapla"""
    if not AI_AKTIF or data is None:
        return 50, "BEKLE", 0.0, None

    try:
        sonuc = AI_MODEL.tahmin_et(data)
        detay = sonuc.get('detay', {})
        
        # Monitor log
        try:
            from signal_logger import get_logger
            fiyat = float(data['Close'].iloc[-1]) if data is not None and 'Close' in data else None
            get_logger().log(
                ticker=ticker,
                regime=detay.get('rejim', '?'),
                esik=detay.get('esik', '?'),
                gb_proba=detay.get('gb_al', 0),
                rf_proba=detay.get('rf_al'),
                rf_guard_active=detay.get('rf_guard_aktif', False),
                signal=sonuc.get('etiket', 'BEKLE'),
                reason=detay.get('reason', '?'),
                fiyat=fiyat,
                pipeline='v1.0',
            )
        except Exception:
            pass  # logger hatasi sistemi etkilemesin

        return (
            sonuc.get('ai_skor', 50),
            sonuc.get('etiket', 'BEKLE'),
            sonuc.get('guven', 0.0),
            detay
        )
    except Exception as e:
        print(f"    ⚠️ AI tahmin hatası: {e}")
        return 50, "BEKLE", 0.0, None
def ai_entegre_skor(teknik_skor, temel_skor, risk_skor, yatirimci_skor, makro_skor, ai_skor):
    """AI + uzman skorlarını birleştir"""
    return (
            teknik_skor * 0.15 +
            temel_skor * 0.15 +
            risk_skor * 0.10 +
            yatirimci_skor * 0.10 +
            makro_skor * 0.10 +
            ai_skor * 0.25 +
            0.15
    )


def ai_uyum_kontrol(teknik_skor, ai_tahmin):
    """AI ve teknik uzman uyumunu kontrol et"""
    if ai_tahmin == "AL" and teknik_skor > 60:
        return "UYUMLU"
    elif ai_tahmin == "SAT" and teknik_skor < 40:
        return "UYUMLU"
    elif ai_tahmin == "BEKLE" and 40 <= teknik_skor <= 60:
        return "UYUMLU"
    else:
        return "UYUMSUZ"


def ai_oneri_olustur(final_skor, ai_tahmin, ai_guven):
    """AI + final skora göre öneri"""
    if final_skor >= 75 and ai_tahmin == "AL" and ai_guven > 0.6:
        return "GÜÇLÜ AL"
    elif final_skor >= 60 and ai_tahmin == "AL":
        return "AL"
    elif final_skor <= 25 and ai_tahmin == "SAT" and ai_guven > 0.6:
        return "GÜÇLÜ SAT"
    elif final_skor <= 40 and ai_tahmin == "SAT":
        return "SAT"
    else:
        return "BEKLE"

# hisse_analiz.py - AI ENTEGRASYONU bölümüne ekle (ai_skor_hesapla'dan sonra):

def _pipeline_predictor_olustur(al_esik=0.0):
    """Pipeline RF model factory. al_esik: AL icin min AL olasiligi (0=devre disi)."""
    PIPELINE_KOK = r"C:\Users\Administrator\.local\share\opencode\worktree\ca751c77d3f8b0bcb92c6ff8149f6fa07240f66f\kind-knight"

    def _tahmin_et(df):
        try:
            sys.path.insert(0, PIPELINE_KOK)
            from komutan.ai_skorlayici import ai_skor_hesapla
            sonuc = ai_skor_hesapla(df)
            sinyal = sonuc.get('ai_sinyal', 'BEKLE')
            al_prob = sonuc.get('al_olasilik', 0.0)
            if sinyal == 'AL' and al_esik > 0 and al_prob < al_esik:
                sinyal = 'BEKLE'
            return {
                'etiket': sinyal,
                'guven': sonuc.get('ai_guven', 0.0),
                'tahmin': {'AL': 1, 'BEKLE': 0, 'SAT': -1}.get(sinyal, 0),
                'al_olasilik': al_prob,
            }
        except Exception as e:
            return {'etiket': 'BEKLE', 'guven': 0.0, 'hata': str(e)[:80]}

    return _tahmin_et

_pipeline_tahmin_et = _pipeline_predictor_olustur(al_esik=0.0)

def _model_adi(predictor):
    if predictor is None or predictor == AI_MODEL.tahmin_et:
        return "Kimi AIModel(v4.3)"
    if hasattr(predictor, '__closure__') and predictor.__closure__:
        for c in predictor.__closure__:
            if isinstance(c.cell_contents, (int, float)):
                esik = c.cell_contents
                if esik > 0:
                    return f"Pipeline RF(esik={esik:.2f})"
    return "Pipeline RF"

def backtest_yap(hisse_listesi, gun_sayisi=180, predictor=None):
    """Son N gun icin AI backtest - basari oranini olc"""
    if predictor is None:
        predictor = AI_MODEL.tahmin_et
    model_etiket = _model_adi(predictor)
    print(f"\n{'='*60}")
    print(f" {model_etiket} - Son {gun_sayisi} gun")
    print(f"{'='*60}")

    dogru = 0
    toplam = 0
    detaylar = []

    for ticker in hisse_listesi[:20]:
        try:
            print(f"  {ticker} backtest...")

            data = veri_cek(ticker, period=f"{gun_sayisi + 150}d")
            if data is None or len(data) < gun_sayisi + 5:
                continue

            for i in range(-gun_sayisi, -1):
                if i + 1 >= 0:
                    break

                gecmis_data = data.iloc[:i]
                tahmin_gunu = data.index[i]
                bugun_kapanis = data['Close'].iloc[i]
                yarin_kapanis = data['Close'].iloc[i + 1]
                getiri = (yarin_kapanis - bugun_kapanis) / bugun_kapanis

                sonuc = predictor(gecmis_data)
                tahmin = sonuc.get('etiket', 'BEKLE')
                guven = sonuc.get('guven', 0)

                basarili = False
                if tahmin == 'AL' and getiri > 0.01:
                    basarili = True
                elif tahmin == 'SAT' and getiri < -0.01:
                    basarili = True
                elif tahmin == 'BEKLE' and abs(getiri) <= 0.01:
                    basarili = True

                if basarili:
                    dogru += 1
                toplam += 1

                detaylar.append({
                    'ticker': ticker,
                    'tarih': tahmin_gunu.strftime('%Y-%m-%d'),
                    'tahmin': tahmin,
                    'guven': guven,
                    'getiri': getiri * 100,
                    'basari': basarili
                })

        except Exception as e:
            print(f"  X {ticker} hatasi: {str(e)[:80]}")
            continue

    basari_orani = (dogru / toplam * 100) if toplam > 0 else 0

    print(f"\n{'='*60}")
    print(f" BACKTEST SONUCLARI")
    print(f"{'='*60}")
    print(f"   Toplam tahmin: {toplam}")
    print(f"   Dogru tahmin: {dogru}")
    print(f"   Basari orani: %{basari_orani:.2f}")
    print(f"{'='*60}")

    if detaylar:
        import numpy as np
        al_getiriler = [d['getiri'] for d in detaylar if d['tahmin'] == 'AL']
        sat_getiriler = [d['getiri'] for d in detaylar if d['tahmin'] == 'SAT']
        bekle_getiriler = [d['getiri'] for d in detaylar if d['tahmin'] == 'BEKLE']

        al_dogru = sum(1 for d in detaylar if d['tahmin'] == 'AL' and d['basari'])
        al_toplam = len(al_getiriler)
        sat_dogru = sum(1 for d in detaylar if d['tahmin'] == 'SAT' and d['basari'])
        sat_toplam = len(sat_getiriler)
        bekle_dogru = sum(1 for d in detaylar if d['tahmin'] == 'BEKLE' and d['basari'])
        bekle_toplam = len(bekle_getiriler)

        print(f"\n   AL tahminleri: {al_dogru}/{al_toplam} dogru (%{al_dogru/max(al_toplam,1)*100:.1f})")
        if al_getiriler:
            al_arr = np.array(al_getiriler)
            print(f"   AL Getiri: ort={np.mean(al_arr):+.2f}% medyan={np.median(al_arr):+.2f}%"
                  f" en_iyi={np.max(al_arr):+.2f}% en_kotu={np.min(al_arr):+.2f}%")
            print(f"   AL Kazanan: {np.sum(al_arr>0)}/{al_toplam} (%{np.sum(al_arr>0)/al_toplam*100:.0f})"
                  f" ortalama kazanc={np.mean(al_arr[al_arr>0]):+.2f}%"
                  f" ortalama kayip={np.mean(al_arr[al_arr<=0]):+.2f}%")

        print(f"   SAT tahminleri: {sat_dogru}/{sat_toplam} dogru (%{sat_dogru/max(sat_toplam,1)*100:.1f})")
        if sat_getiriler:
            sat_arr = np.array(sat_getiriler)
            print(f"   SAT Getiri: ort={np.mean(sat_arr):+.2f}% medyan={np.median(sat_arr):+.2f}%")

        print(f"   BEKLE tahminleri: {bekle_dogru}/{bekle_toplam} dogru (%{bekle_dogru/max(bekle_toplam,1)*100:.1f})")

        # Net P&L (esit pozisyon buyuklugu varsayimi)
        print(f"\n   NET P&L (esit agirlik):")
        if al_getiriler:
            al_pl = np.sum(al_arr)
            print(f"     AL: %{al_pl:+.2f}")
        if sat_getiriler:
            sat_pl = np.sum(np.array(sat_getiriler))
            print(f"     SAT: %{sat_pl:+.2f}")

    return basari_orani, detaylar
# =============================================================================
# AYARLAR
# =============================================================================

RAPOR_DIR = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\rapor"
os.makedirs(RAPOR_DIR, exist_ok=True)

AL_ESIK = 0.6
SAT_ESIK = 0.4
TOP_N = 20
MAX_WORKERS = 2
TIMEOUT = 10
HATA_LIMITI = 30


# =============================================================================
# YARDIMCI FONKSIYONLAR
# =============================================================================

def format_ticker(ticker):
    """Ticker'a .IS ekler."""
    if not isinstance(ticker, str):
        return None
    ticker = ticker.strip().replace('$', '')
    return ticker if ticker.endswith('.IS') else ticker + '.IS'


def safe_scalar(val):
    """Series/DataFrame/Scalar -> float."""
    if val is None:
        return 0.0
    if isinstance(val, (pd.Series, pd.DataFrame)):
        if len(val) == 0:
            return 0.0
        val = val.iloc[0] if isinstance(val, pd.Series) else val.iloc[0, 0]
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def get_close(data, idx=-1):
    """Kapanis fiyatini al."""
    try:
        if data is None or 'Close' not in data.columns:
            return 0.0
        return safe_scalar(data['Close'].iloc[idx])
    except Exception:
        return 0.0


def get_change(data):
    """Gunluk degisimi hesapla."""
    try:
        if data is None or len(data) < 2:
            return 0.0
        close = data['Close']
        return (close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100
    except Exception:
        return 0.0


def veri_cek(ticker, period="60d", retries=2):
    """Yahoo Finance'den veri cek. Period 'Xd' formatinda ise gun bazina cevir."""
    ticker_is = format_ticker(ticker)
    if not ticker_is:
        return None

    for attempt in range(retries):
        try:
            if period.endswith('d') and period[:-1].isdigit():
                gun = int(period[:-1])
                bas = datetime.now() - pd.Timedelta(days=gun + 30)
                bit = datetime.now()
                data = yf.download(ticker_is, start=bas.strftime('%Y-%m-%d'),
                                   end=bit.strftime('%Y-%m-%d'), progress=False, auto_adjust=True)
            else:
                data = yf.download(ticker_is, period=period, progress=False, auto_adjust=True)
            if data is not None and len(data) > 20:
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.droplevel(1)
                return data
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                print(f"[UYARI] {ticker}: {str(e)[:60]}")
    return None


# =============================================================================
# UZMAN ANALIZLERI
# =============================================================================

def teknik_skor(data):
    """Teknik analiz skoru."""
    try:
        close = data['Close']
        high = data['High']
        low = data['Low']

        # RSI benzeri momentum
        returns = close.pct_change(fill_method=None).dropna()
        if len(returns) < 10:
            return 50.0

        momentum = returns.rolling(10).mean().iloc[-1] * 100
        volatility = returns.rolling(20).std().iloc[-1] * 100

        # Trend
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1]

        skor = 50.0
        if close.iloc[-1] > sma_20 > sma_50:
            skor += 20
        elif close.iloc[-1] < sma_20 < sma_50:
            skor -= 20

        # Momentum ekle
        skor += momentum * 2

        # Volatilite cezasi
        if volatility > 5:
            skor -= 10

        return max(0, min(100, skor))
    except Exception:
        return 50.0


def temel_skor(ticker):
    """Temel analiz skoru (simule)."""
    return 50.0


def yatirimci_skor(data):
    """Yatirimci davranisi skoru."""
    try:
        volume = data['Volume']
        close = data['Close']

        if len(volume) < 20:
            return 50.0

        vol_avg = volume.rolling(20).mean().iloc[-1]
        vol_current = volume.iloc[-1]

        # Hacim artisi
        if vol_current > vol_avg * 1.5:
            return 65.0
        elif vol_current < vol_avg * 0.5:
            return 35.0
        return 50.0
    except Exception:
        return 50.0


def risk_skor(data):
    """Risk analiz skoru."""
    try:
        close = data['Close']
        returns = close.pct_change(fill_method=None).dropna()

        if len(returns) < 20:
            return 50.0

        volatility = returns.rolling(20).std().iloc[-1] * 100

        # Dusuk volatilite = dusuk risk = yuksek skor
        skor = 100 - volatility * 5
        return max(0, min(100, skor))
    except Exception:
        return 50.0


def makro_skor():
    """Makro ekonomi skoru (simule)."""
    return 50.0


def max_drawdown_skor(data):
    """Max drawdown skoru."""
    try:
        close = data['Close']
        rolling_max = close.expanding().max()
        drawdown = (close - rolling_max) / rolling_max
        max_dd = drawdown.min()

        # Dusuk drawdown = iyi
        skor = 100 + max_dd * 100  # max_dd negatif
        return max(0, min(100, skor))
    except Exception:
        return 50.0


def ensemble_skor_hesapla(ticker, data):
    """Tum uzman skorlarini birlestir."""
    teknik = teknik_skor(data)
    temel = temel_skor(ticker)
    yatirimci = yatirimci_skor(data)
    risk = risk_skor(data)
    makro = makro_skor()
    drawdown = max_drawdown_skor(data)

    # Agirlikli ortalama
    skor = (
            teknik * 0.20 +
            temel * 0.15 +
            yatirimci * 0.15 +
            risk * 0.20 +
            makro * 0.15 +
            drawdown * 0.15
    )

    skorlar = {
        'teknik': teknik,
        'temel': temel,
        'yatirimci': yatirimci,
        'risk': risk,
        'makro': makro,
        'drawdown': drawdown
    }

    return skor, skorlar


# =============================================================================
# TEK HISSE ANALIZ
# =============================================================================

def hisse_analiz_et(ticker):
    """Tek hisse analizi (AI entegre)."""
    try:
        data = veri_cek(ticker)
        if data is None:
            return ticker, None, None, None, None, "Veri yok"

        # Mevcut uzman skorlari
        skor, skorlar = ensemble_skor_hesapla(ticker, data)

        # AI Skoru hesapla
        ai_skor, ai_tahmin, ai_guven, _ = ai_skor_hesapla(ticker, data)

        # Yeni entegre skor (AI + uzmanlar)
        if skorlar and AI_AKTIF:
            teknik = skorlar.get('teknik', 50)
            temel = skorlar.get('temel', 50)
            risk = skorlar.get('risk', 50)
            yatirimci = skorlar.get('yatirimci', 50)
            makro = skorlar.get('makro', 50)

            yeni_skor = ai_entegre_skor(teknik, temel, risk, yatirimci, makro, ai_skor)

            # AI bilgilerini skorlar'a ekle
            skorlar['ai_skor'] = ai_skor
            skorlar['ai_tahmin'] = ai_tahmin
            skorlar['ai_guven'] = ai_guven
            skorlar['uyum'] = ai_uyum_kontrol(teknik, ai_tahmin)
            skorlar['oneri'] = ai_oneri_olustur(yeni_skor, ai_tahmin, ai_guven)

            skor = yeni_skor
        else:
            skorlar['ai_skor'] = ai_skor
            skorlar['ai_tahmin'] = ai_tahmin
            skorlar['ai_guven'] = ai_guven

        fiyat = get_close(data)
        degisim = get_change(data)

        return ticker, skor, fiyat, degisim, skorlar, None
    except Exception as e:
        return ticker, None, None, None, None, str(e)[:80]


def tum_hisseleri_analiz_et(hisse_listesi, max_workers=MAX_WORKERS):
    """Tum hisseleri paralel analiz et."""
    sonuclar = []
    hata_sayisi = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(hisse_analiz_et, ticker): ticker
            for ticker in hisse_listesi
        }

        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                ticker, skor, fiyat, degisim, skorlar, hata = future.result(timeout=TIMEOUT)

                if hata:
                    hata_sayisi += 1
                    if hata_sayisi >= HATA_LIMITI:
                        print(f"⛔ Hata limiti ({HATA_LIMITI}) asildi, durduruluyor.")
                        break
                    continue

                if skor is not None:
                    sonuclar.append({
                        'ticker': ticker,
                        'skor': skor,
                        'fiyat': fiyat,
                        'degisim': degisim,
                        'skorlar': skorlar
                    })

            except Exception as e:
                print(f"⚠️ {ticker} islem hatasi: {str(e)[:60]}")

    return sonuclar


def al_sat_listeleri_olustur(sonuclar, al_esik=AL_ESIK, sat_esik=SAT_ESIK, top_n=TOP_N):
    """AL/SAT/NOTR listeleri olustur."""
    al_listesi = [s for s in sonuclar if s['skor'] >= al_esik]
    sat_listesi = [s for s in sonuclar if s['skor'] <= sat_esik]
    notr_listesi = [s for s in sonuclar if sat_esik < s['skor'] < al_esik]

    # Sirala
    al_listesi.sort(key=lambda x: x['skor'], reverse=True)
    sat_listesi.sort(key=lambda x: x['skor'])
    notr_listesi.sort(key=lambda x: x['skor'], reverse=True)

    # TOP N
    al_listesi = al_listesi[:top_n]
    sat_listesi = sat_listesi[:top_n]
    notr_listesi = notr_listesi[:top_n]

    return al_listesi, sat_listesi, notr_listesi


def rapor_kaydet(al_listesi, sat_listesi, notr_listesi):
    """Raporlari kaydet."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON rapor
    rapor = {
        'tarih': datetime.now().isoformat(),
        'al': al_listesi,
        'sat': sat_listesi,
        'notr': notr_listesi
    }

    json_yolu = os.path.join(RAPOR_DIR, f"rapor_{timestamp}.json")
    with open(json_yolu, 'w', encoding='utf-8') as f:
        json.dump(rapor, f, indent=2, ensure_ascii=False)

    # TXT rapor
    txt_yolu = os.path.join(RAPOR_DIR, f"rapor_{timestamp}.txt")
    with open(txt_yolu, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("  BORSA KOMUTAN - ANALIZ RAPORU\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"📅 Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")

        f.write("🟢 AL SINYALLERI (Top 20):\n")
        f.write("-" * 70 + "\n")
        for i, h in enumerate(al_listesi, 1):
            f.write(f"{i:2}. {h['ticker']:<12} Skor: {h['skor']:.4f}  "
                    f"Fiyat: {h['fiyat']:.2f}  Degisim: %{h['degisim']:.2f}\n")

        f.write("\n🔴 SAT SINYALLERI (Top 20):\n")
        f.write("-" * 70 + "\n")
        for i, h in enumerate(sat_listesi, 1):
            f.write(f"{i:2}. {h['ticker']:<12} Skor: {h['skor']:.4f}  "
                    f"Fiyat: {h['fiyat']:.2f}  Degisim: %{h['degisim']:.2f}\n")

        f.write("\n⚪ NOTR (Top 20):\n")
        f.write("-" * 70 + "\n")
        for i, h in enumerate(notr_listesi, 1):
            f.write(f"{i:2}. {h['ticker']:<12} Skor: {h['skor']:.4f}  "
                    f"Fiyat: {h['fiyat']:.2f}  Degisim: %{h['degisim']:.2f}\n")

    print(f"💾 Rapor kaydedildi: {txt_yolu}")
    return txt_yolu


# =============================================================================
# AKŞAM RAPORU
# =============================================================================

def aksam_raporu_gonder():
    """Akşam 21:00 raporu: Yarın için AL/SAT/BEKLE tahmini"""
    print(f"\n{'=' * 60}")
    print(f"🌙 AKŞAM RAPORU - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 60}")
    print("🎯 Yarın için tahminler hazırlanıyor...")

    # İlk 20 hisse
    hisseler = HISSE_LISTESI[:TOP_N]

    tahminler = []
    for ticker in hisseler:
        try:
            print(f"  📊 {ticker} analiz ediliyor...")
            data = veri_cek(ticker)
            if data is None:
                print(f"    ⚠️ {ticker}: Veri yok")
                continue

            print(f"    ✅ {ticker}: Veri alındı, AI tahmin yapılıyor...")

            # AI Skoru
            ai_skor, ai_tahmin, ai_guven, _ = ai_skor_hesapla(ticker, data)
            print(f"    ✅ {ticker}: AI tahmin = {ai_tahmin}, Güven = {ai_guven:.2f}")

            # Uzman skorları
            teknik = teknik_skor(data)
            temel = temel_skor(ticker)
            risk = risk_skor(data)

            # Final skor
            final_skor = ai_entegre_skor(teknik, temel, risk, 50, 50, ai_skor)

            # Öneri
            oneri = ai_oneri_olustur(final_skor, ai_tahmin, ai_guven)

            tahminler.append({
                'hisse': ticker,
                'tahmin': ai_tahmin,
                'guven': ai_guven,
                'final_skor': final_skor,
                'oneri': oneri,
                'fiyat': get_close(data)
            })

        except Exception as e:
            print(f"    ❌ {ticker} hatası: {e}")
            continue

    print(f"\n📊 Toplam tahmin: {len(tahminler)} hisse")

    if not tahminler:
        print("⛔ Hiç tahmin üretilemedi!")
        return []

    # Sırala: AL önce
    tahminler.sort(key=lambda x: (
        0 if x['tahmin'] == 'AL' else (1 if x['tahmin'] == 'BEKLE' else 2),
        -x['guven']
    ))

    # Rapor
    rapor = []
    rapor.append(f"\n{'=' * 60}")
    rapor.append(f"📊 YARIN İÇİN TAHMİNLER - {datetime.now().strftime('%Y-%m-%d')}")
    rapor.append(f"{'=' * 60}")
    rapor.append(f"{'Hisse':<10} {'Tahmin':<8} {'Güven':<8} {'Skor':<6} {'Öneri':<12}")
    rapor.append(f"{'-' * 60}")

    for t in tahminler:
        rapor.append(f"{t['hisse']:<10} {t['tahmin']:<8} {t['guven']:<8.2f} {t['final_skor']:<6.1f} {t['oneri']:<12}")

    rapor.append(f"{'=' * 60}")

    print("\n".join(rapor))

    # Kaydet
    rapor_yolu = os.path.join(RAPOR_DIR, f"aksam_raporu_{datetime.now().strftime('%Y%m%d')}.txt")
    with open(rapor_yolu, 'w', encoding='utf-8') as f:
        f.write("\n".join(rapor))

    print(f"\n💾 Rapor: {rapor_yolu}")
    print(f"⏰ Sonraki rapor: Yarın 21:00")

    return tahminler


# =============================================================================
# WRAPPER FUNCTIONS FOR Flask Dashboard (app_v4)
# =============================================================================

def analyze_hisse(ticker, zaman_dilimi="1D", bist100_df=None, usdtry_df=None):
    """Wrapper: app_v4 API uyumu"""
    sonuc = {"status": "OK", "ticker": ticker, "zaman_dilimi": zaman_dilimi}
    try:
        ticker_id, skor, fiyat, degisim, skorlar, hata = hisse_analiz_et(ticker)
        if hata:
            return {"status": "HATA", "message": hata}
        sonuc["ensemble_skor"] = skor
        sonuc["last_price"] = fiyat
        sonuc["change_pct"] = degisim
        sonuc["skorlar"] = skorlar
        return sonuc
    except Exception as e:
        return {"status": "HATA", "message": str(e)[:100]}

def analyze_top50(zaman_dilimi="1D"):
    """Wrapper: Top 50 hisse analizi"""
    try:
        liste = HISSE_LISTESI[:50]
        sonuclar = tum_hisseleri_analiz_et(liste)
        al, sat, notr = al_sat_listeleri_olustur(sonuclar)
        return {
            "status": "OK",
            "toplam": len(sonuclar),
            "al_sayisi": len(al),
            "sat_sayisi": len(sat),
            "notr_sayisi": len(notr),
            "al_listesi": al,
            "sat_listesi": sat,
            "notr_listesi": notr
        }
    except Exception as e:
        return {"status": "HATA", "message": str(e)[:100]}

def analyze_all100(zaman_dilimi="1D"):
    """Wrapper: Tum hisseleri analiz et"""
    try:
        sonuclar = tum_hisseleri_analiz_et(HISSE_LISTESI)
        al, sat, notr = al_sat_listeleri_olustur(sonuclar)
        return {
            "status": "OK",
            "toplam": len(sonuclar),
            "al_sayisi": len(al),
            "sat_sayisi": len(sat),
            "notr_sayisi": len(notr),
            "al_listesi": al,
            "sat_listesi": sat,
            "notr_listesi": notr
        }
    except Exception as e:
        return {"status": "HATA", "message": str(e)[:100]}

def get_top_picks(zaman_dilimi="1D", n=10):
    """Wrapper: En iyi AL onerileri"""
    try:
        sonuclar = tum_hisseleri_analiz_et(HISSE_LISTESI)
        al, sat, notr = al_sat_listeleri_olustur(sonuclar, top_n=n)
        return {
            "status": "OK",
            "top_n": n,
            "al_listesi": al,
            "sat_listesi": sat,
            "notr_listesi": notr
        }
    except Exception as e:
        return {"status": "HATA", "message": str(e)[:100]}

# =============================================================================
# MAIN
# =============================================================================

def main():
    """Ana calistirma - Akşam Rapor Modu."""
    print("\n" + "=" * 70)
    print("  BORSA KOMUTAN v4.3 - AKŞAM RAPOR MODU")
    print("=" * 70)
    print("  ⏰ Sadece 21:00'da çalışır")
    print("  🎯 Yarın tahminleri: AL / SAT / BEKLE")
    print("=" * 70 + "\n")

    schedule.every().day.at("21:00").do(aksam_raporu_gonder)

    print("✅ Scheduler başlatıldı. 21:00'ı bekliyor...")
    print("   Çıkmak için Ctrl+C\n")

    while True:
        schedule.run_pending()
        time.sleep(60)


# =============================================================================
# EN ALT
# =============================================================================

if __name__ == "__main__":
    import sys
    parser = __import__('argparse').ArgumentParser(description="BIST AI Backtest")
    parser.add_argument("--gun", type=int, default=0,
                        help="Gun sayisi (0=hepsi: 180/365/1825)")
    parser.add_argument("--model", type=str, default="hepsi",
                        help="Model: kimi, pipeline, hepsi (default: hepsi)")
    parser.add_argument("--esik-sweep", action="store_true",
                        help="Pipeline RF AL esik taramasi (0.4-0.9)")
    # YENİ ARGÜMANLAR EKLE:
    parser.add_argument("--ticker", type=str, default="AEFES",
                        help="Hisse sembolu (default: AEFES)")
    parser.add_argument("--karsilastir", action="store_true",
                        help="Karsilastirmali backtest modu")
    parser.add_argument("--coklu", action="store_true",
                        help="Coklu donem karsilastirma (6A/1Y/5Y)")
    args = parser.parse_args()
    # hisse_analiz.py'deki mevcut parser'a ekle:
    parser.add_argument('--karsilastir', action='store_true', help='Karsilastirma modu')
    parser.add_argument('--coklu', action='store_true', help='Coklu donem modu')
    parser.add_argument('--ticker', type=str, default='AEFES', help='Hisse sembolu')
 # YENİ KARŞILAŞTIRMA KONTROLLERİ EKLE:
    if args.karsilastir:
        backtest_karsilastir(args.ticker, gun_sayisi=args.gun if args.gun > 0 else 30, model_mod=args.model)
        sys.exit(0)
    
    if args.coklu:
        coklu_donem_karsilastir(args.ticker, model_mod=args.model)
        sys.exit(0)
    
    # MEVCUT KOD (esik-sweep veya normal backtest):
    if args.esik_sweep:
        esik_taramasi(args.gun)
    else:
        backtest_modeller(args.gun, model_mod=args.model)
    from hisse_listesi import HISSE_LISTESI

    if args.esik_sweep:
        esikler = [0.0, 0.4, 0.5, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9]
        gun = args.gun if args.gun else 30
        print("\n" + "="*80)
        print(f"  PIPELINE RF AL ESIK TARAMASI - {gun} gun")
        print("="*80)
        print(f"  {'Esik':<8} {'Basari':>8} {'AL Sayi':>9} {'Kazanan%':>9} {'Ort Getiri':>11} {'Net P&L':>10} {'MaxDD':>8}")
        print(f"  {'-'*65}")
        for esik in esikler:
            pred = _pipeline_predictor_olustur(al_esik=esik)
            basari, detaylar = backtest_yap(HISSE_LISTESI[:20], gun_sayisi=gun, predictor=pred)
            import numpy as np
            al_getiri = [d['getiri'] for d in detaylar if d['tahmin'] == 'AL']
            al_arr = np.array(al_getiri) if al_getiri else np.array([0.0])
            kazanan = np.sum(al_arr > 0) / max(len(al_arr), 1) * 100
            ort = np.mean(al_arr) if len(al_arr) > 0 else 0
            net_pl = np.sum(al_arr) if len(al_arr) > 0 else 0
            max_dd = min(al_arr) if len(al_arr) > 0 else 0
            etik = f"{esik:.2f}" if esik > 0 else "0(ham)"
            print(f"  {etik:<8} %{basari:>6.2f} {len(al_getiri):>9} %{kazanan:>7.1f} %{ort:>+8.2f} %{net_pl:>+7.2f} %{max_dd:>+6.2f}")
        print("="*80)
        sys.exit(0)

    modeller = []
    if args.model == "kimi":
        modeller = [("Kimi AIModel", AI_MODEL.tahmin_et)]
    elif args.model == "pipeline":
        modeller = [("Pipeline RF", _pipeline_tahmin_et)]
    else:
        modeller = [("Kimi AIModel", AI_MODEL.tahmin_et), ("Pipeline RF", _pipeline_tahmin_et)]

    donemler = [("6 AY", 180), ("1 YIL", 365), ("5 YIL", 1825)]

    if args.gun:
        donemler = [(f"{args.gun} gun", args.gun)]

    print("\n" + "="*70)
    print("  BORSA KOMUTAN v4.3 - ADIL KARSILASTIRMALI BACKTEST")
    print("="*70)

    sonuclar = {}
    for model_et, predictor in modeller:
        for donem_et, gun in donemler:
            anahtar = f"{model_et}_{gun}"
            basari, detaylar = backtest_yap(HISSE_LISTESI[:20], gun_sayisi=gun, predictor=predictor)
            sonuclar[anahtar] = (basari, detaylar, model_et, donem_et)

    print("\n" + "="*80)
    print("  ADIL KARSILASTIRMA TABLOSU (Ayni Veri Setinde)")
    print("="*80)
    print(f"  {'Model':<20} {'Donem':<8} {'Basari':>8} {'AL Sayi':>9} {'Net P&L':>10}")
    print(f"  {'-'*55}")
    for anahtar, (basari, detaylar, model_et, donem_et) in sonuclar.items():
        import numpy as np
        al_getiri = [d['getiri'] for d in detaylar if d['tahmin'] == 'AL']
        net_pl = np.sum(al_getiri) if al_getiri else 0
        print(f"  {model_et:<20} {donem_et:<8} %{basari:>6.2f} {len(al_getiri):>9} %{net_pl:>+7.2f}")
    print("="*80)