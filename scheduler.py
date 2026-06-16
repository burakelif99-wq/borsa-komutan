# scheduler.py - Zamanlanmış veri çekme ve raporlama

import schedule
import time
import json
import sqlite3
from datetime import datetime

from veri_al import get_bist100
from kimi_al import calculate_risk_metrics
from grok_al import calculate_ensemble
from komutan_karari import final_decision
from teknik_al import calculate_technical_indicators
from makro_al import get_macro_data
from medya_al import get_media_sentiment

from overchat_al import generate_report, save_report

DB_PATH = 'borsa_komutan.db'


def init_db():
    """SQLite veritabanı oluştur"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS veriler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            symbol TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            pm REAL,
            risk_skor REAL,
            decision TEXT,
            confidence REAL,
            json_data TEXT
        )
    ''')

    # Eski raporlar tablosunu sil ve yeniden oluştur (veri_id ekle)
    c.execute('DROP TABLE IF EXISTS raporlar')

    c.execute('''
        CREATE TABLE IF NOT EXISTS raporlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rapor_saati TEXT,
            timestamp TEXT,
            karar TEXT,
            guven REAL,
            risk_skor REAL,
            mesaj TEXT,
            veri_id INTEGER
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Veritabanı hazır")


def kaydet_veri(data_result, risk, ensemble, final):
    """Veriyi SQLite'a kaydet"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    df = data_result['data']
    last = len(df) - 1

    c.execute('''
        INSERT INTO veriler 
        (timestamp, symbol, open, high, low, close, volume, pm, risk_skor, decision, confidence, json_data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'XU100',
        float(df['Open'].iloc[last]),
        float(df['High'].iloc[last]),
        float(df['Low'].iloc[last]),
        float(df['Close'].iloc[last]),
        int(df['Volume'].iloc[last]),
        float(df['PM'].iloc[last]) if 'PM' in df.columns else 0.0,
        risk['risk_skor'],
        final['decision'],
        final['confidence'],
        json.dumps({
            'ensemble': ensemble['ensemble'],
            'decision': final['decision']
        })
    ))

    conn.commit()
    conn.close()
    print("✅ Veri kaydedildi")


def saat_11_00():
    """Saat 11:00 veri çekme"""
    print(f"\n{'=' * 60}")
    print(f"📊 SAAT 11:00 VERİ ÇEKİMİ")
    print(f"{'=' * 60}")

    data_result = get_bist100()
    if data_result['status'] == 'OK':
        df = data_result['data']

        risk = calculate_risk_metrics(df)
        teknik = calculate_technical_indicators(df)
        makro = get_macro_data()
        medya = get_media_sentiment()

        ensemble = calculate_ensemble(
            teknik={'score': teknik['score'], 'weight': 0.4},
            risk={'score': risk['risk_skor'], 'level': risk['risk_level'], 'weight': 0.25},
            makro={'score': makro['score'], 'weight': 0.2},
            medya={'score': medya['score'], 'weight': 0.15}
        )
        final = final_decision(ensemble, risk, auto_send=False)

        kaydet_veri(data_result, risk, ensemble, final)

        print(f"✅ Fiyat: {risk['last_price']}")
        print(f"✅ Karar: {final['decision']} | Güven: %{final['confidence']}")
        print(f"✅ Risk: {risk['risk_skor']}/100")
        print(f"{'=' * 60}")

        return True
    else:
        print(f"❌ Hata: {data_result['message']}")
        return False


def saat_15_00():
    """Saat 15:00 veri çekme"""
    print(f"\n{'=' * 60}")
    print(f"📊 SAAT 15:00 VERİ ÇEKİMİ")
    print(f"{'=' * 60}")
    return saat_11_00()


def rapor_yaz():
    """Rapor oluştur ve kaydet"""
    print(f"\n{'=' * 60}")
    print(f"📝 RAPOR YAZILIYOR - {datetime.now().strftime('%H:%M')}")
    print(f"{'=' * 60}")

    data_result = get_bist100()
    if data_result['status'] == 'OK':
        df = data_result['data']

        risk = calculate_risk_metrics(df)
        teknik = calculate_technical_indicators(df)
        makro = get_macro_data()
        medya = get_media_sentiment()

        ensemble = calculate_ensemble(
            teknik={'score': teknik['score'], 'weight': 0.4},
            risk={'score': risk['risk_skor'], 'level': risk['risk_level'], 'weight': 0.25},
            makro={'score': makro['score'], 'weight': 0.2},
            medya={'score': medya['score'], 'weight': 0.15}
        )
        final = final_decision(ensemble, risk, auto_send=False)

        report_data = {
            'teknik': teknik,
            'makro': makro,
            'medya': medya
        }

        report = generate_report(report_data, risk, ensemble, final)
        filename = save_report(report)

        print(f"✅ Rapor kaydedildi: {filename}")
        print(f"{'=' * 60}")

        return True
    else:
        print(f"❌ Hata: {data_result['message']}")
        return False


# Zamanlayıcı
schedule.every().day.at("11:00").do(saat_11_00)
schedule.every().day.at("15:00").do(saat_15_00)
schedule.every().day.at("11:10").do(rapor_yaz)
schedule.every().day.at("19:10").do(rapor_yaz)

print("=" * 60)
print(" BORSA KOMUTAN ZAMANLAYICI BAŞLATILDI")
print("=" * 60)
print(" Görevler:")
print("  • 11:00 - Veri çekme")
print("  • 15:00 - Veri çekme")
print("  • 11:10 - Rapor yazma")
print("  • 19:10 - Rapor yazma")
print("=" * 60)
print(" Çıkmak için Ctrl+C")
print("=" * 60)

init_db()

# Test modu
print("\n🧪 TEST MODU - Hemen çalıştırılıyor...")
saat_11_00()
rapor_yaz()
print("✅ Test tamamlandı\n")

while True:
    schedule.run_pending()
    time.sleep(60)