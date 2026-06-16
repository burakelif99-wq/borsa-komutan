# grok_al.py - ENSEMBLE MODÜLÜ (düzeltilmiş)

from teknik_al import calculate_technical_indicators
from makro_al import get_macro_data
from medya_al import get_media_sentiment
from kimi_al import calculate_risk_metrics


def calculate_ensemble(df=None, teknik=None, risk=None, makro=None, medya=None):
    """
    Tüm modül skorlarını ağırlıklı birleştirir
    """
    # Gerçek verileri çek (eğer df varsa)
    if df is not None:
        teknik_data = calculate_technical_indicators(df)
        risk_data = calculate_risk_metrics(df)
        makro_data = get_macro_data()
        medya_data = get_media_sentiment()
    else:
        # Demo mod veya manuel veri
        teknik_data = teknik or {'status': 'OK', 'score': 65, 'weight': 0.40}
        risk_data = risk or {'status': 'OK', 'score': 52.1, 'level': 'YUKSEK_RISK', 'weight': 0.25}
        makro_data = makro or {'status': 'OK', 'score': 58, 'weight': 0.20}
        medya_data = medya or {'status': 'OK', 'score': 55, 'weight': 0.15}

    # Eğer manuel sadece score/weight gönderildiyse, tam format oluştur
    if 'status' not in teknik_data:
        teknik_data = {
            'status': 'OK',
            'score': teknik_data.get('score', 65),
            'weight': teknik_data.get('weight', 0.40)
        }
    if 'status' not in risk_data:
        risk_data = {
            'status': 'OK',
            'score': risk_data.get('score', 52.1),
            'level': risk_data.get('level', 'ORTA_RISK'),
            'weight': risk_data.get('weight', 0.25)
        }
    if 'status' not in makro_data:
        makro_data = {
            'status': 'OK',
            'score': makro_data.get('score', 58),
            'weight': makro_data.get('weight', 0.20)
        }
    if 'status' not in medya_data:
        medya_data = {
            'status': 'OK',
            'score': medya_data.get('score', 55),
            'weight': medya_data.get('weight', 0.15)
        }

    # Modülleri birleştir
    modules = {
        'teknik': {
            'status': teknik_data['status'],
            'score': teknik_data['score'],
            'weight': teknik_data['weight']
        },
        'risk': {
            'status': 'OK',
            'score': risk_data['score'] if 'risk_skor' not in risk_data else risk_data['risk_skor'],
            'level': risk_data.get('risk_level', 'ORTA_RISK') if 'risk_level' in risk_data else risk_data.get('level',
                                                                                                              'ORTA_RISK'),
            'weight': risk_data.get('ensemble_weight', 0.25) if 'ensemble_weight' in risk_data else risk_data.get(
                'weight', 0.25)
        },
        'makro': {
            'status': makro_data['status'],
            'score': makro_data['score'],
            'weight': makro_data['weight']
        },
        'medya': {
            'status': medya_data['status'],
            'score': medya_data['score'],
            'weight': medya_data['weight']
        }
    }

    # Ağırlıklı skor
    total_weight = 0
    weighted_sum = 0

    for name, mod in modules.items():
        if mod['status'] == 'OK':
            weighted_sum += mod['score'] * mod['weight']
            total_weight += mod['weight']

    final_score = weighted_sum / total_weight if total_weight > 0 else 50

    # Karar
    if final_score >= 70:
        decision = 'AL'
    elif final_score <= 30:
        decision = 'SAT'
    else:
        decision = 'BEKLE'

    confidence = abs(final_score - 50) * 2
    confidence = min(confidence, 95)

    # Risk veto
    if modules['risk']['level'] in ['COK_YUKSEK_RISK', 'YUKSEK_RISK'] and decision == 'AL':
        if confidence < 75:
            decision = 'BEKLE'

    return {
        'status': 'OK',
        'ensemble': {
            'final_score': round(final_score, 1),
            'decision': decision,
            'confidence': round(confidence, 1),
            'module_breakdown': {
                name: {
                    'score': mod['score'],
                    'weight': mod['weight'],
                    'contribution': round(mod['score'] * mod['weight'] / total_weight, 2)
                }
                for name, mod in modules.items() if mod['status'] == 'OK'
            }
        },
        'details': {
            'teknik': teknik_data,
            'risk': risk_data,
            'makro': makro_data,
            'medya': medya_data
        }
    }


def format_telegram_message(ensemble_result, risk_metrics=None):
    """Telegram mesajı formatı"""
    if ensemble_result['status'] != 'OK':
        return "HATA: Ensemble hesaplanamadı"

    e = ensemble_result['ensemble']
    msg = f"""
🎯 BORSA KOMUTAN KARARI

Karar: {e['decision']}
Güven: %{e['confidence']}
Skor: {e['final_score']}/100

📊 Modül Skorları:
"""
    for name, data in e['module_breakdown'].items():
        msg += f"  • {name.upper()}: {data['score']} (ağırlık %{data['weight'] * 100:.0f})\n"

    if risk_metrics:
        msg += f"\n⚠️ Risk: {risk_metrics.get('risk_level', 'N/A')}"
        msg += f"\n📉 VaR(95%): {risk_metrics.get('metrics', {}).get('var_95_percent', 'N/A')}%"

    msg += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return msg


if __name__ == "__main__":
    from veri_al import get_bist100

    result = get_bist100()
    if result['status'] == 'OK':
        ensemble = calculate_ensemble(df=result['data'])

        print(f"\n{'=' * 50}")
        print(f"ENSEMBLE (Gerçek Modüller)")
        print(f"{'=' * 50}")
        print(f"Nihai Skor: {ensemble['ensemble']['final_score']}")
        print(f"Karar: {ensemble['ensemble']['decision']}")
        print(f"Güven: %{ensemble['ensemble']['confidence']}")
        print(f"\nModüller:")
        for name, data in ensemble['ensemble']['module_breakdown'].items():
            print(f"  {name}: {data['score']} x {data['weight']} = {data['contribution']}")
        print(f"{'=' * 50}")