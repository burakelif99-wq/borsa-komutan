"""
scheduler.py - Borsa Komutan v4.0
Basit zamanlayici - Her analiz sonrasi rapor kaydeder
"""

import os
import sys
import time
import schedule
from datetime import datetime

BASE_DIR = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi"
RAPOR_DIR = os.path.join(BASE_DIR, "rapor")
os.makedirs(RAPOR_DIR, exist_ok=True)

sys.path.insert(0, BASE_DIR)

# Modulleri import et
try:
    from hisse_analiz import tum_hisseleri_analiz_et, al_sat_listeleri_olustur, rapor_kaydet, HISSE_LISTESI, AI_MODEL
    from komutan_karar import KomutanKararMotoru
    from komutan_karari import send_telegram_message as telegram_gonder
    from eposta_rapor import gunluk_rapor_gonder
    KOMUTAN = KomutanKararMotoru()
    print("[INFO] Komutan Karar Motoru aktif")
except ImportError as e:
    print(f"[UYARI] Modul hatasi: {e}")
    KOMUTAN = None


# =============================================================================
# GOREVLER (Her biri rapor kaydeder)
# =============================================================================

def analiz_ve_rapor(gorev_adi, hisse_sayisi=50):
    """Analiz yap ve rapor kaydet."""
    print(f"\n{'='*70}")
    print(f"  {gorev_adi} - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")

    try:
        # Analiz
        print(f"  [INFO] {hisse_sayisi} hisse analiz ediliyor...")
        sonuclar = tum_hisseleri_analiz_et(HISSE_LISTESI[:hisse_sayisi], max_workers=3)

        # AL/SAT listeleri
        al, sat, notr = al_sat_listeleri_olustur(sonuclar)

        # RAPOR KAYDET
        print(f"  [INFO] Rapor kaydediliyor...")
        txt_path, json_path = rapor_kaydet(al, sat, notr)
        print(f"  [OK] Rapor: {os.path.basename(txt_path)}")

        # Komutan kararlari (varsa)
        if KOMUTAN:
            print(f"\n  KOMUTAN KARARLARI:")
            print(f"  {'-'*50}")
            for result in sonuclar:
                if not isinstance(result, dict):
                    continue
                ticker = result.get('ticker', '?')
                skor = result.get('skor', 0)
                fiyat = result.get('fiyat', 0)
                skorlar = result.get('skorlar', {})
                if skor and skor >= 0.6:
                    try:
                        karar = KOMUTAN.karar_ver(ticker, skorlar, fiyat)
                        print(f"  {ticker}: {karar['karar']} - {karar['neden'][:40]}")
                    except:
                        pass

        print(f"\n  [OK] {gorev_adi} tamamlandi.")
        print(f"  AL: {len(al)}, SAT: {len(sat)}, NOTR: {len(notr)}")

        # Telegram bildirimi
        try:
            mesaj = (
                f"[KIMI] {gorev_adi}\n"
                f"{datetime.now().strftime('%H:%M')}\n"
                f"AL: {len(al)} | SAT: {len(sat)} | NOTR: {len(notr)}\n"
            )
            if al:
                ilk_bes = [a[0] if isinstance(a, tuple) else str(a) for a in al[:5]]
                mesaj += f"Top AL: {', '.join(ilk_bes)}"
            telegram_gonder(mesaj)
            print(f"  [OK] Telegram gonderildi.")
        except Exception as e:
            print(f"  [UYARI] Telegram: {e}")

    except Exception as e:
        print(f"  [HATA] {gorev_adi}: {e}")


def premarket_scan():
    """08:30 - Pre-market."""
    print(f"\n{'='*70}")
    print(f"  PRE-MARKET SCAN - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    try:
        from premarket_scan import PremarketScan
        pm = PremarketScan()
        sonuc = pm.tara(['THYAO.IS', 'GARAN.IS', 'ASELS.IS', 'EREGL.IS', 'SASA.IS'])
        print(f"  Piyasa: {sonuc['piyasa_durumu']}")
        print(f"  Firsat: {len(sonuc.get('firsatlar', []))} hisse")
        print("  [OK] Pre-market tamamlandi.")
    except Exception as e:
        print(f"  [HATA] Pre-market: {e}")


def acilis_analizi():
    """09:00 - Acilis."""
    analiz_ve_rapor("ACILIS ANALIZI", 50)


def ogle_raporu():
    """12:00 - Ogle."""
    analiz_ve_rapor("OGLE RAPORU", 50)


def kapanis_oncesi():
    """15:00 - Kapanis oncesi."""
    analiz_ve_rapor("KAPANIS ONCESI", 50)


def gece_egitimi():
    """23:00 - AI model gece egitimi (580 hisse, 5 yil)."""
    print(f"\n{'='*70}")
    print(f"  GECE EGITIMI - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*70}")
    try:
        from ai_skorlayici import AIModel
        from hisse_listesi import HISSE_LISTESI
        model = AIModel()
        basari = model.egit(HISSE_LISTESI, period="5y", esik_al=0.02, esik_sat=-0.02)
        if basari:
            print(f"  [OK] 580 hisse x 5y egitimi basarili!")
            try:
                if AI_MODEL and hasattr(AI_MODEL, 'modeli_yenile'):
                    AI_MODEL.modeli_yenile(str(model.model_yolu))
                    print(f"  [OK] AI Motoru model yenilendi")
            except Exception as e:
                print(f"  [UYARI] Model yenileme: {e}")
        else:
            print(f"  [HATA] Egitim basarisiz!")
    except Exception as e:
        print(f"  [HATA] Gece egitimi: {e}")


def gun_sonu_raporu():
    """18:00 - Gun sonu + e-posta."""
    analiz_ve_rapor("GUN SONU RAPORU", 50)

    # E-posta gonder
    try:
        print(f"\n  [INFO] E-posta gonderiliyor...")
        sifre = "btokbnymhmlglroz"
        gunluk_rapor_gonder(RAPOR_DIR, sifre=sifre)
        print(f"  [OK] E-posta gonderildi!")
    except Exception as e:
        print(f"  [HATA] E-posta: {e}")

    # Ogrenme
    if KOMUTAN:
        try:
            print(f"\n  [INFO] Ogrenme guncelleniyor...")
            import yfinance as yf
            for karar in KOMUTAN.ogrenme.veriler['kararlar']:
                if karar['durum'] == 'BEKLIYOR':
                    try:
                        data = yf.download(karar['ticker'], period='1d', progress=False)
                        if data is not None and len(data) > 0:
                            fiyat = float(data['Close'].iloc[-1])
                            KOMUTAN.ogren(karar['id'], fiyat)
                    except:
                        pass
            print(f"  [OK] Ogrenme tamamlandi.")
        except Exception as e:
            print(f"  [HATA] Ogrenme: {e}")


# =============================================================================
# ZAMANLAYICI
# =============================================================================

def zamanlayici_baslat():
    """Zamanlayiciyi baslat."""
    print("\n" + "="*70)
    print("  BORSA KOMUTAN v4.0 - ZAMANLAYICI")
    print("="*70)
    print("\n  Program:")
    print("    08:30 - Pre-market Scan")
    print("    09:00 - Acilis Analizi")
    print("    12:00 - Ogle Raporu")
    print("    15:00 - Kapanis Oncesi")
    print("    18:00 - Gun Sonu + E-posta")
    print("    23:00 - AI Gece Egitimi (580 hisse, 5y)")
    print("\n  CTRL+C ile durdurabilirsiniz.")
    print("="*70 + "\n")

    schedule.every().day.at("08:30").do(premarket_scan)
    schedule.every().day.at("09:00").do(acilis_analizi)
    schedule.every().day.at("12:00").do(ogle_raporu)
    schedule.every().day.at("15:00").do(kapanis_oncesi)
    schedule.every().day.at("18:00").do(gun_sonu_raporu)
    schedule.every().day.at("23:00").do(gece_egitimi)

    while True:
        schedule.run_pending()
        time.sleep(60)


# =============================================================================
# CALISTIR
# =============================================================================

# YENI (normal mod)
if __name__ == "__main__":
    zamanlayici_baslat()

    # NORMAL MOD (Zamanlayici - yorum kaldirirsan aktif olur)
    # zamanlayici_baslat()