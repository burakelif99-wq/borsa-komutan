# app.py - FLASK SUNUCU (gerçek modüllerle)

import sys
import os
import traceback
from datetime import datetime
from flask import Flask, jsonify, make_response
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from veri_al import get_bist100, get_ohlcv_json
    from kimi_al import calculate_risk_metrics
    from grok_al import calculate_ensemble
    from komutan_karari import final_decision
    from teknik_al import calculate_technical_indicators
    from makro_al import get_macro_data
    from medya_al import get_media_sentiment

    MODULES_OK = True
except ImportError as e:
    print(f"⚠️ Modül import hatası: {e}")
    MODULES_OK = False

app = Flask(__name__, template_folder='.', static_folder='.')
CORS(app, resources={
    r"/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/')
def dashboard():
    return app.send_static_file('bist-dashboard.html')


@app.route('/api/data')
def get_data():
    if not MODULES_OK:
        return jsonify({'status': 'ERROR', 'message': 'Modüller yüklenemedi'})

    try:
        data_result = get_bist100()
        if data_result['status'] != 'OK':
            return jsonify(
                {'status': 'ERROR', 'message': f"Veri çekilemedi: {data_result.get('message', 'Bilinmeyen hata')}"})

        df = data_result['data']
        ohlcv = get_ohlcv_json(df)

        # Gerçek modüller
        teknik = calculate_technical_indicators(df)
        risk = calculate_risk_metrics(df)
        makro = get_macro_data()
        medya = get_media_sentiment()

        # Ensemble
        ensemble = calculate_ensemble(
            teknik=teknik,
            risk=risk,
            makro=makro,
            medya=medya
        )

        final = final_decision(ensemble, risk, auto_send=False)

        response_data = {
            'status': 'OK',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ohlcv': ohlcv,
            'risk': risk,
            'teknik': teknik,
            'makro': makro,
            'medya': medya,
            'ensemble': ensemble['ensemble'],
            'decision': {
                'karar': final['decision'],
                'guven': final['confidence'],
                'mesaj': final['message']
            },
            'modules': {
                'veri': {'status': 'OK', 'last_update': data_result['last_update']},
                'teknik': {'status': teknik['status'], 'score': teknik['score']},
                'kimi': {'status': 'OK', 'risk_skor': risk['risk_skor']},
                'makro': {'status': makro['status'], 'score': makro['score']},
                'medya': {'status': medya['status'], 'score': medya['score']},
                'grok': {'status': 'OK', 'final_score': ensemble['ensemble']['final_score']},
                'komutan': {'status': 'READY', 'decision': final['decision']}
            }
        }

        return make_response(jsonify(response_data))

    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ HATA: {e}\n{error_trace}")
        return jsonify({'status': 'ERROR', 'message': str(e), 'trace': error_trace})


@app.route('/api/refresh')
def refresh():
    return get_data()


@app.route('/api/health')
def health_check():
    return jsonify(
        {'status': 'OK', 'modules_loaded': MODULES_OK, 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})


if __name__ == '__main__':
    print("=" * 60)
    print(" BIST KOMUTAN SUNUCU BAŞLATILIYOR")
    print("=" * 60)
    print(f" Modüller: {'✅ Yüklendi' if MODULES_OK else '❌ Hatalı'}")
    print("-" * 60)
    print(" Dashboard: http://localhost:5001")
    print(" API:      http://localhost:5001/api/data")
    print(" Health:   http://localhost:5001/api/health")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)