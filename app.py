# app.py - Borsa Komutan Dashboard v3.0 (DÜZELTİLMİŞ)

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import json
from arsiv import Arsiv
from grok_al import calculate_ensemble
from hisse_analiz import analyze_hisse, analyze_top50, get_top_picks
from veri_al import get_bist100, get_usdtry
from hisse_listesi import BIST_HISSE_LISTESI, get_sector, SEKTOR_MAP
from max_drawdown import MaxDrawdown
app = Flask(__name__)
arsiv = Arsiv()
dd_trackers = {}

# HTML TEMPLATE (Basit dashboard)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Borsa Komutan v3.0</title>
    <style>
        body { font-family: Arial; background: #1a1a2e; color: #eee; padding: 20px; }
        h1 { color: #00d4ff; }
        .card { background: #16213e; padding: 15px; margin: 10px 0; border-radius: 8px; }
        a { color: #00d4ff; }
    </style>
</head>
<body>
    <h1>🚀 BORSA KOMUTAN v3.0</h1>
    <div class="card">
        <h3>API Endpoint'leri:</h3>
        <ul>
            <li><a href="/api/ensemble">/api/ensemble</a> - Ensemble analiz (XU100)</li>
            <li><a href="/api/usdtry">/api/usdtry</a> - USD/TRY kuru</li>
            <li><a href="/api/hisse_listesi">/api/hisse_listesi</a> - Hisse listesi</li>
            <li><a href="/api/top50">/api/top50</a> - Top 50 analiz</li>
            <li><a href="/api/all100">/api/all100</a> - Tüm BIST100 analiz</li>
            <li><a href="/api/top_picks">/api/top_picks</a> - En iyi öneriler</li>
            <li>/api/hisse/&lt;ticker&gt; - Tek hisse analiz</li>
            <li>/api/drawdown/&lt;ticker&gt; - Drawdown takibi</li>
            <li>/api/arsiv/&lt;hisse&gt; - Arşiv kayıtları</li>
            <li>/api/arsiv/istatistik/&lt;hisse&gt; - Arşiv istatistikleri</li>
            <li>/api/arsiv/trend/&lt;hisse&gt; - Trend analizi</li>
        </ul>
    </div>
</body>
</html>
"""

# ROUTE'LAR
@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/ensemble')
def api_ensemble():
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    result = get_bist100()

    if result['status'] == 'OK':
        ensemble = calculate_ensemble(df=result['data'], zaman_dilimi=zaman_dilimi)

        # ARŞİVE KAYDET (XU100)
        try:
            arsiv.kaydet_analiz('XU100', ensemble, zaman_dilimi)
        except:
            pass

        return jsonify(ensemble)

    return jsonify(result)

@app.route('/api/usdtry')
def api_usdtry():
    return jsonify(get_usdtry())

@app.route('/api/hisse/<ticker>')
def api_hisse(ticker):
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    result = analyze_hisse(ticker, zaman_dilimi=zaman_dilimi)

    # ARŞİVE KAYDET
    if result['status'] == 'OK':
        try:
            arsiv.kaydet_analiz(
                ticker,
                result,
                zaman_dilimi,
                fiyat=result.get('last_price'),
                degisim=result.get('change_pct'),
                sektor=result.get('sector')
            )
        except:
            pass

    return jsonify(result)

@app.route('/api/top50')
def api_top50():
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    result = analyze_top50_fast(zaman_dilimi=zaman_dilimi)
    return jsonify(result)

@app.route('/api/all100')
def api_all100():
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    result = analyze_top50_fast(zaman_dilimi=zaman_dilimi)
    return jsonify(result)

@app.route('/api/top_picks')
def api_top_picks():
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    n = int(request.args.get('n', 10))
    result = get_top_picks(zaman_dilimi=zaman_dilimi, n=n)
    return jsonify(result)

@app.route('/api/hisse_listesi')
def api_hisse_listesi():
    return jsonify({
        'status': 'OK',
        'total': len(BIST_HISSE_LISTESI),
        'hisseler': BIST_HISSE_LISTESI,
        'sectors': sorted(list(set(SEKTOR_MAP.values())))
    })

@app.route('/api/drawdown/<ticker>')
def api_drawdown(ticker):
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo")
        if df.empty:
            return jsonify({'status': 'HATA', 'message': 'Veri bulunamadı'})

        if ticker not in dd_trackers:
            dd_trackers[ticker] = MaxDrawdown(esik=-0.20, hisse_adi=ticker)

        current_price = float(df['Close'].iloc[-1])
        dd_result = dd_trackers[ticker].guncelle(current_price)

        return jsonify({'status': 'OK', 'ticker': ticker, 'drawdown': dd_result})
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

@app.route('/api/arsiv/<hisse>')
def api_arsiv(hisse):
    try:
        limit = int(request.args.get('limit', 30))
        veri = arsiv.getir(hisse, limit=limit)
        return jsonify({'status': 'OK', 'hisse': hisse, 'kayitlar': veri})
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

@app.route('/api/arsiv/istatistik/<hisse>')
def api_arsiv_istatistik(hisse):
    try:
        gun = int(request.args.get('gun', 30))
        stats = arsiv.istatistik(hisse, gun=gun)
        return jsonify({'status': 'OK', 'istatistik': stats})
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

@app.route('/api/arsiv/trend/<hisse>')
def api_arsiv_trend(hisse):
    try:
        gun = int(request.args.get('gun', 30))
        trend = arsiv.trend_analizi(hisse, gun=gun)
        return jsonify({'status': 'OK', 'trend': trend})
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

if __name__ == "__main__":
    print("=" * 60)
    print("BORSA KOMUTAN v3.0 BASLATILIYOR")
    print("=" * 60)
    print("http://localhost:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
