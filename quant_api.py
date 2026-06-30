from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), 'dashboard_data')

@app.route('/')
def dashboard():
    return send_from_directory('.', 'quant_dashboard_live.html')

@app.route('/api/metrics')
def get_metrics():
    try:
        with open(os.path.join(DATA_DIR, 'metrics.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/signals')
def get_signals():
    try:
        with open(os.path.join(DATA_DIR, 'signals.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/performance')
def get_performance():
    try:
        with open(os.path.join(DATA_DIR, 'performance.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/canary')
def get_canary():
    try:
        with open(os.path.join(DATA_DIR, 'canary.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/opportunities')
def get_opportunities():
    try:
        with open(os.path.join(DATA_DIR, 'opportunities.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/filtered')
def get_filtered():
    try:
        with open(os.path.join(DATA_DIR, 'filtered.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/equity')
def get_equity():
    try:
        with open(os.path.join(DATA_DIR, 'equity.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/confusion')
def get_confusion():
    try:
        with open(os.path.join(DATA_DIR, 'confusion.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/prf_trend')
def get_prf_trend():
    try:
        with open(os.path.join(DATA_DIR, 'prf_trend.json'), 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/all')
def get_all():
    try:
        result = {}
        for fname in ['metrics', 'signals', 'performance', 'canary', 'opportunities', 'filtered', 'equity', 'confusion', 'prf_trend']:
            with open(os.path.join(DATA_DIR, f'{fname}.json'), 'r', encoding='utf-8') as f:
                result[fname] = json.load(f)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

if __name__ == '__main__':
    print("Quant Dashboard API baslatiliyor...")
    print("Dashboard: http://localhost:5001")
    print("API Endpoints:")
    print("   GET /api/metrics")
    print("   GET /api/signals")
    print("   GET /api/performance")
    print("   GET /api/canary")
    print("   GET /api/opportunities")
    print("   GET /api/filtered")
    print("   GET /api/equity")
    print("   GET /api/confusion")
    print("   GET /api/prf_trend")
    print("   GET /api/all")
    print("   GET /api/health")
    app.run(host='0.0.0.0', port=5001, debug=False)