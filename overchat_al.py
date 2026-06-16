# overchat_al.py - RAPOR MODÜLÜ

import sqlite3
import json
from datetime import datetime
import os

DB_PATH = 'borsa_komutan.db'


def generate_report(data, risk, ensemble, final):
    """
    Özet rapor oluştur ve dosyaya yaz
    """
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    rapor_saati = datetime.now().strftime('%H:%M')

    report = f"""
{'=' * 70}
BORSA KOMUTAN SİSTEMİ - GÜNLÜK RAPOR
{'=' * 70}
Tarih: {timestamp.split(' ')[0]}
Saat:  {rapor_saati}
{'=' * 70}

📊 PAZAR DURUMU
BIST 100 (XU100): {risk['last_price']}
Son Güncelleme: {timestamp}

📈 TEKNİK ANALİZ
RSI (14): {data['teknik']['indicators']['rsi']}
MACD: {data['teknik']['indicators']['macd']}
Sinyal: {data['teknik']['indicators']['macd_signal']}
BB Pozisyon: %{data['teknik']['indicators']['bb_position'] * 100:.1f}
SMA50: {data['teknik']['indicators']['sma50']}
SMA200: {data['teknik']['indicators']['sma200']}
Teknik Skor: {data['teknik']['score']}/100

⚠️ RİSK METRİKLERİ
Yıllık Volatilite: {risk['metrics']['volatility_yearly']}%
Sharpe Ratio: {risk['metrics']['sharpe_ratio']}
VaR (95%): {risk['metrics']['var_95_percent']}%
Max Drawdown: {risk['metrics']['max_drawdown_percent']}%
ATR: {risk['metrics']['atr_percent']}%
Risk Skoru: {risk['risk_skor']}/100
Risk Seviyesi: {risk['risk_level']}

🌍 MAKRO VERİLER
USD/TRY: {data['makro']['data']['usd_try']}
USD Değişim: {data['makro']['data']['usd_change']}%
Faiz: %{data['makro']['data']['faiz']}
Enflasyon: %{data['makro']['data']['enflasyon']}
Makro Skor: {data['makro']['score']}/100

📰 MEDYA/SENTIMENT
Sentiment: {data['medya']['data']['sentiment_label']}
Skor: {data['medya']['score']}/100
KAP Bildirim: {data['medya']['data']['kap_bildirim']}

🎯 ENSEMBLE KARARI
Nihai Skor: {ensemble['ensemble']['final_score']}/100
Karar: {final['decision']}
Güven: %{final['confidence']}

Modül Katkıları:
"""
    for name, mod in ensemble['ensemble']['module_breakdown'].items():
        report += f"  • {name.upper()}: {mod['score']} x {mod['weight']} = {mod['contribution']:.1f}\n"

    report += f"""
{'=' * 70}
⚠️ UYARI: Bu rapor otomatik oluşturulmuştur.
Yatırım tavsiyesi değildir.
{'=' * 70}
"""

    return report


def save_report(report):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    filename = f"rapor_{timestamp}.txt"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''
        INSERT INTO raporlar (rapor_saati, timestamp, karar, guven, risk_skor, mesaj)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime('%H:%M'),
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'BEKLE',
        59,
        52.5,
        report
    ))

    conn.commit()
    conn.close()

    return filename


def read_last_report():
    """
    Son raporu oku
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('SELECT * FROM raporlar ORDER BY id DESC LIMIT 1')
    row = c.fetchone()

    conn.close()

    if row:
        return {
            'id': row[0],
            'rapor_saati': row[1],
            'timestamp': row[2],
            'karar': row[3],
            'guven': row[4],
            'risk_skor': row[5],
            'mesaj': row[6]
        }
    return None


if __name__ == "__main__":
    # Test için veri oluştur
    from veri_al import get_bist100
    from kimi_al import calculate_risk_metrics
    from grok_al import calculate_ensemble
    from komutan_karari import final_decision

    data = get_bist100()
    if data['status'] == 'OK':
        df = data['data']

        teknik = {'indicators': {'rsi': 62.4, 'macd': 0.045, 'macd_signal': 0.032, 'bb_position': 0.65, 'sma50': 14200,
                                 'sma200': 13800}, 'score': 65}
        risk = calculate_risk_metrics(df)
        makro = {'data': {'usd_try': 32.45, 'usd_change': 0.5, 'faiz': 50.0, 'enflasyon': 61.5}, 'score': 58}
        medya = {'data': {'sentiment_label': 'NÖTR', 'kap_bildirim': 3}, 'score': 55}

        ensemble = calculate_ensemble(teknik=teknik, risk=risk, makro=makro, medya=medya)
        final = final_decision(ensemble, risk, auto_send=False)

        # Rapor oluştur
        report_data = {
            'teknik': teknik,
            'makro': makro,
            'medya': medya
        }

        report = generate_report(report_data, risk, ensemble, final)
        filename = save_report(report)

        print(f"\n{'=' * 70}")
        print(f"RAPOR OLUŞTURULDU: {filename}")
        print(f"{'=' * 70}")
        print(report[:500] + "\n...")
        print(f"{'=' * 70}")