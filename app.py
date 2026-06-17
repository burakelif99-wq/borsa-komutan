# app.py - BIST KOMUTAN FLASK SUNUCU (Render için optimize)

import sys
import os
import traceback
import math
from datetime import datetime
from flask import Flask, jsonify, make_response, request
from flask_cors import CORS

# Kimi klasörünü path'e ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Modülleri import et
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

# CORS - Tüm originlere izin ver (Render için kritik)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


@app.route('/')
def dashboard():
    """Ana dashboard sayfası"""
    return app.send_static_file('bist-dashboard.html')


@app.route('/api/data')
def get_data():
    """Tüm modül verilerini JSON olarak döndür"""
    if not MODULES_OK:
        return jsonify({
            'status': 'ERROR',
            'message': 'Modüller yüklenemedi'
        })

    try:
        # 1. Veri çek
        data_result = get_bist100()
        if data_result['status'] != 'OK':
            return jsonify({
                'status': 'ERROR',
                'message': 'Veri çekilemedi'
            })

        df = data_result['data']

        # 2. OHLCV JSON
        ohlcv = get_ohlcv_json(df)

        # 3. Modülleri çalıştır
        teknik = calculate_technical_indicators(df)
        risk = calculate_risk_metrics(df)
        makro = get_macro_data()
        medya = get_media_sentiment()

        # 4. Ensemble
        ensemble = calculate_ensemble(
            teknik={'score': teknik['score'], 'weight': 0.4},
            risk={'score': risk['risk_skor'], 'level': risk['risk_level'], 'weight': 0.25},
            makro={'score': makro['score'], 'weight': 0.2},
            medya={'score': medya['score'], 'weight': 0.15}
        )

        # 5. Komutan kararı
        final = final_decision(ensemble, risk, auto_send=False)

        # NaN temizleme
        def clean_nan(obj):
            if isinstance(obj, float) and math.isnan(obj):
                return None
            if isinstance(obj, dict):
                return {k: clean_nan(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [clean_nan(v) for v in obj]
            return obj

        response_data = {
            'status': 'OK',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'ohlcv': ohlcv,
            'risk': risk,
            'teknik': clean_nan(teknik),
            'makro': makro,
            'medya': medya,
            'ensemble': clean_nan(ensemble['ensemble']),
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
        return jsonify({
            'status': 'ERROR',
            'message': str(e),
            'trace': error_trace
        })


@app.route('/api/refresh')
def refresh():
    """Manuel yenileme"""
    return get_data()


@app.route('/api/health')
def health_check():
    """Sağlık kontrolü"""
    return jsonify({
        'status': 'OK',
        'modules_loaded': MODULES_OK,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })


if __name__ == '__main__':
    print("=" * 60)
    print(" BIST KOMUTAN SUNUCU BAŞLATILIYOR")
    print("=" * 60)
    print(f" Modüller: {'✅ Yüklendi' if MODULES_OK else '❌ Hatalı'}")
    print("-" * 60)
    print(" Dashboard: http://localhost:5000")
    print(" API:      http://localhost:5000/api/data")
    print(" Health:   http://localhost:5000/api/health")
    print("=" * 60)

    # Render için PORT ortam değişkenini kullan
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port, threaded=True)