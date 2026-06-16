# komutan_karari.py - KOMUTAN KARARI + TELEGRAM

import os
import requests
from datetime import datetime

# Telegram Bot Token ve Chat ID (kendi bilgilerinle değiştir)
TELEGRAM_BOT_TOKEN = "SENIN_BOT_TOKEN"
TELEGRAM_CHAT_ID = "SENIN_CHAT_ID"


def send_telegram_message(message, token=None, chat_id=None):
    """
    Telegram'a mesaj gönderir
    """
    token = token or TELEGRAM_BOT_TOKEN
    chat_id = chat_id or TELEGRAM_CHAT_ID

    if token == "SENIN_BOT_TOKEN" or chat_id == "SENIN_CHAT_ID":
        print("⚠️ UYARI: Telegram token/chat_id ayarlanmamış!")
        print("Mesaj simülasyonu (gerçekte gönderilmedi):")
        print("-" * 50)
        print(message)
        print("-" * 50)
        return {
            'status': 'SIMULATION',
            'message': 'Token ayarlanmamış, mesaj konsola yazdırıldı'
        }

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return {
                'status': 'OK',
                'message_id': response.json()['result']['message_id'],
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            return {
                'status': 'ERROR',
                'code': response.status_code,
                'message': response.text
            }
    except Exception as e:
        return {
            'status': 'ERROR',
            'message': str(e)
        }


def final_decision(ensemble_result, risk_metrics=None, auto_send=False):
    """
    Nihai kararı al ve Telegram'a gönder
    """
    if ensemble_result['status'] != 'OK':
        return {
            'status': 'ERROR',
            'message': 'Ensemble sonucu hatalı'
        }

    e = ensemble_result['ensemble']
    decision = e['decision']
    confidence = e['confidence']
    score = e['final_score']

    # Karar güçlendirme (güven < 60 ise BEKLE'ye çek)
    if confidence < 60 and decision != 'BEKLE':
        decision = 'BEKLE'
        confidence = confidence * 0.8

    # Risk kontrolü
    if risk_metrics and risk_metrics.get('risk_level') in ['COK_YUKSEK_RISK', 'YUKSEK_RISK']:
        if decision == 'AL' and confidence < 75:
            decision = 'BEKLE'

    # Mesaj oluştur
    emoji = {'AL': '🟢', 'SAT': '🔴', 'BEKLE': '🟡'}

    message = f"""
{emoji[decision]} BORSA KOMUTAN KARARI {emoji[decision]}

Karar: {decision}
Güven: %{confidence}
Skor: {score}/100

Modül Skorları:
"""
    for name, data in e['module_breakdown'].items():
        message += f"  • {name.upper()}: {data['score']} (ağırlık %{data['weight'] * 100:.0f})\n"

    if risk_metrics:
        message += f"\nRisk: {risk_metrics.get('risk_level', 'N/A')}"
        message += f"\nVaR(95%): {risk_metrics.get('metrics', {}).get('var_95_percent', 'N/A')}%"
        message += f"\nVolatilite: {risk_metrics.get('metrics', {}).get('volatility_yearly', 'N/A')}%"

    message += f"\n\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    message += "\n\nBu bir yatırım tavsiyesi değildir."

    # Telegram'a gönder
    result = {
        'status': 'READY',
        'decision': decision,
        'confidence': confidence,
        'message': message,
        'telegram_sent': False
    }

    if auto_send:
        telegram_result = send_telegram_message(message)
        result['telegram_status'] = telegram_result
        result['telegram_sent'] = telegram_result['status'] == 'OK'

    return result


# Test
if __name__ == "__main__":
    try:
        from veri_al import get_bist100
        from kimi_al import calculate_risk_metrics
        from grok_al import calculate_ensemble

        # Veri çek
        data_result = get_bist100()
        if data_result['status'] == 'OK':
            # Risk hesapla
            risk = calculate_risk_metrics(data_result['data'])

            # Ensemble
            risk_input = {
                'status': 'OK',
                'score': risk['risk_skor'],
                'level': risk['risk_level'],
                'weight': risk['ensemble_weight']
            }
            ensemble = calculate_ensemble(risk=risk_input)

            # Komutan kararı
            final = final_decision(ensemble, risk, auto_send=False)

            print(f"\n{'=' * 50}")
            print(f"KOMUTAN KARARI (komutan_karari.py)")
            print(f"{'=' * 50}")
            print(f"Karar: {final['decision']}")
            print(f"Güven: %{final['confidence']}")
            print(f"\nTelegram Mesajı:")
            print(f"{'=' * 50}")
            print(final['message'])
            print(f"{'=' * 50}")

    except ImportError as e:
        print(f"Import hatası: {e}")