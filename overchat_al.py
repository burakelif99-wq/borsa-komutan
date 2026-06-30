# overchat_al.py - GÜNCELLENMİŞ RAPOR MODÜLÜ

import os
import sqlite3
import json
from datetime import datetime

DB_PATH = 'borsa_komutan.db'
RAPOR_KLASOR = 'rapor'


def init_rapor_klasor():
    """Rapor klasörü oluştur"""
    if not os.path.exists(RAPOR_KLASOR):
        os.makedirs(RAPOR_KLASOR)
        print(f"✅ {RAPOR_KLASOR}/ klasörü oluşturuldu")


def tahmin_gucu_hesapla(ensemble_score, risk_skor, confidence):
    """
    Tahmin gücünü hesapla:
    - Güçlü AL: Skor > 75, Risk < 40, Güven > 80
    - AL: Skor > 60, Risk < 50, Güven > 60
    - BEKLE: Diğer durumlar
    - SAT: Skor < 40, Risk > 60
    - Güçlü SAT: Skor < 25, Risk > 75
    """
    if ensemble_score > 75 and risk_skor < 40 and confidence > 80:
        return "GÜÇLÜ AL", "Yüksek potansiyel, düşük risk"
    elif ensemble_score > 60 and risk_skor < 50 and confidence > 60:
        return "AL", "Pozitif momentum"
    elif ensemble_score < 25 and risk_skor > 75:
        return "GÜÇLÜ SAT", "Kritik risk, kaçın"
    elif ensemble_score < 40 and risk_skor > 60:
        return "SAT", "Negatif trend"
    else:
        return "BEKLE", "Belirsizlik yüksek"


def generate_report(data, risk, ensemble, final):
    """
    Güçlü tahmin içeren rapor oluştur
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rapor_saati = datetime.now().strftime('%H:%M')
    tarih = datetime.now().strftime('%Y%m%d')

    # Tahmin gücünü hesapla
    ensemble_score = ensemble['ensemble']['final_score']
    risk_skor = risk['risk_skor']
    confidence = final['confidence']

    tahmin, aciklama = tahmin_gucu_hesapla(ensemble_score, risk_skor, confidence)

    # Rapor metni
    report = f"""
{'=' * 70}
🔥 BORSA KOMUTAN - GÜÇLÜ TAHMİN RAPORU 🔥
{'=' * 70}
📅 Tarih: {timestamp.split(' ')[0]}
⏰ Saat:  {rapor_saati}
{'=' * 70}

🎯 TAHMİN GÜCÜ: {tahmin}
📊 Açıklama: {aciklama}

{'=' * 70}
📈 PAZAR DURUMU
{'=' * 70}
BIST 100 (XU100): {risk['last_price']}
Son Güncelleme: {timestamp}

{'=' * 70}
📊 MODÜL ANALİZİ
{'=' * 70}
Teknik Skor:    {data['teknik']['score']}/100  (RSI: {data['teknik']['indicators']['rsi']})
Risk Skoru:     {risk['risk_skor']}/100        (Volatilite: {risk['metrics']['volatility_yearly']}%)
Makro Skor:     {data['makro']['score']}/100    (USD/TRY: {data['makro']['data']['usd_try']})
Medya Skoru:    {data['medya']['score']}/100    (Sentiment: {data['medya']['data']['sentiment_label']})

{'=' * 70}
⚠️ RİSK METRİKLERİ
{'=' * 70}
Yıllık Volatilite:  {risk['metrics']['volatility_yearly']}%
Sharpe Ratio:       {risk['metrics']['sharpe_ratio']}
VaR (95%):          {risk['metrics']['var_95_percent']}%
Max Drawdown:       {risk['metrics']['max_drawdown_percent']}%
ATR:                {risk['metrics']['atr_percent']}%

{'=' * 70}
🎯 ENSEMBLE KARARI
{'=' * 70}
Nihai Skor: {ensemble['ensemble']['final_score']}/100
Karar:      {final['decision']}
Güven:      %{final['confidence']}
Tahmin:     {tahmin}

Modül Katkıları:
"""
    for name, mod in ensemble['ensemble']['module_breakdown'].items():
        report += f"  • {name.upper()}: {mod['score']}/100 (ağırlık %{mod['weight'] * 100:.0f})\n"

    report += f"""
{'=' * 70}
💡 YORUM ve STRATEJİ
{'=' * 70}
"""

    # Strateji önerisi
    if "AL" in tahmin:
        report += f"""
✅ ALIM STRATEJİSİ ÖNERİLİR
• Pozisyon açmayı düşünün
• Stop-loss: %{risk['metrics']['var_95_percent']:.1f} altında
• Hedef: +{ensemble['ensemble']['final_score'] * 0.5:.1f}% potansiyel
"""
    elif "SAT" in tahmin:
        report += f"""
🔴 SATIŞ STRATEJİSİ ÖNERİLİR
• Pozisyon kapatmayı düşünün
• Risk sınırı aşıldı: {risk['risk_level']}
• Alternatif: Hedge pozisyonu
"""
    else:
        report += f"""
⏳ BEKLEME STRATEJİSİ
• Piyasa belirsizliği yüksek
• Yeni sinyal bekleyin
• Risk toleransı: {risk['risk_level']}
"""

    report += f"""
{'=' * 70}
⚠️ UYARI
{'=' * 70}
Bu rapor otomatik oluşturulmuştur.
Yatırım tavsiyesi değildir.
Kararlar kendi sorumluluğunuzdadır.

⏰ {timestamp}
{'=' * 70}
"""

    return report, tahmin


def save_report(report, tahmin):
    """
    Raporu rapor/ klasörüne kaydet
    """
    init_rapor_klasor()

    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    tarih = datetime.now().strftime('%Y%m%d')

    # Dosya adı: rapor_20260617_1110_GÜÇLÜ_AL.txt
    tahmin_kisa = tahmin.replace(" ", "_")
    filename = f"{RAPOR_KLASOR}/rapor_{timestamp}_{tahmin_kisa}.txt"

    # Dosyaya yaz
    # ESKİ (bozuk)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)

    # YENİ (BOM ekleyerek)
    with open(filename, 'w', encoding='utf-8-sig') as f:
        f.write(report)

    # Veritabanına kaydet
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT INTO raporlar (rapor_saati, timestamp, karar, guven, risk_skor, mesaj)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime('%H:%M'),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        tahmin,
        0,  # güven
        0,  # risk_skor
        report
    ))

    conn.commit()
    conn.close()

    return filename


if __name__ == "__main__":
    # Test
    print("Rapor modülü test")
    init_rapor_klasor()
