# app.py - Borsa Komutan Dashboard v4.0 (FULL INTEGRATION)

from flask import Flask, render_template_string, jsonify, request
from datetime import datetime
import json

# Uzman modülleri
from teknik_uzman import TeknikUzman
from temel_uzman import TemelUzman
from yatirimci_uzman import YatirimciUzman
from risk_uzman import RiskUzman
from makro_uzman import MakroUzman

# Motorlar
from grok_al import EnsembleMotor, calculate_ensemble
from regime_engine import RegimeEngine
from dynamic_ensemble import DynamicEnsemble

# Yardımcı modüller
from hisse_analiz import analyze_hisse, analyze_top50, analyze_all100, get_top_picks
from premarket_scan import PremarketScan
from max_drawdown import MaxDrawdown
from arsiv import Arsiv

# Veri ve listeler
from veri_al import get_bist100, get_usdtry
from hisse_listesi import BIST_HISSE_LISTESI, get_sector, SEKTOR_MAP

app = Flask(__name__)

# Global instances
arsiv = Arsiv()
dd_trackers = {}
premarket_scanner = PremarketScan()
dynamic_ensemble = DynamicEnsemble(use_regime=True, use_drawdown=True)

# HTML TEMPLATE (v4.0 - Modern Dashboard)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Borsa Komutan v4.0 - Uzman Sistem</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Arial, sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
            color: #eee; 
            min-height: 100vh;
            padding: 20px; 
        }
        h1 { color: #00d4ff; text-align: center; margin-bottom: 10px; }
        .subtitle { text-align: center; color: #888; margin-bottom: 30px; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { 
            background: rgba(255,255,255,0.05); 
            padding: 20px; 
            border-radius: 12px; 
            border: 1px solid rgba(255,255,255,0.1);
            backdrop-filter: blur(10px);
        }
        .card h3 { color: #00d4ff; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
        .card ul { list-style: none; }
        .card li { margin: 8px 0; }
        a { color: #00d4ff; text-decoration: none; transition: all 0.3s; }
        a:hover { color: #fff; text-shadow: 0 0 10px rgba(0,212,255,0.5); }
        .badge { 
            display: inline-block; 
            padding: 2px 8px; 
            border-radius: 4px; 
            font-size: 0.8em; 
            margin-left: 5px; 
        }
        .badge-green { background: rgba(0,255,0,0.2); color: #0f0; }
        .badge-yellow { background: rgba(255,255,0,0.2); color: #ff0; }
        .badge-red { background: rgba(255,0,0,0.2); color: #f00; }
        .footer { text-align: center; margin-top: 30px; color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <h1>🚀 BORSA KOMUTAN v4.0</h1>
    <p class="subtitle">5 Uzman Modül + Ensemble Motor + Karar Motoru</p>

    <div class="grid">
        <div class="card">
            <h3>📊 ANLIK ANALIZ</h3>
            <ul>
                <li><a href="/api/ensemble">/api/ensemble</a> <span class="badge badge-green">XU100</span></li>
                <li><a href="/api/usdtry">/api/usdtry</a> <span class="badge badge-yellow">Kur</span></li>
                <li><a href="/api/hisse_listesi">/api/hisse_listesi</a> <span class="badge badge-yellow">Liste</span></li>
            </ul>
        </div>

        <div class="card">
            <h3>🔍 HİSSE ANALIZI</h3>
            <ul>
                <li>/api/hisse/&lt;ticker&gt; <span class="badge badge-green">5 Uzman</span></li>
                <li><a href="/api/top50">/api/top50</a> <span class="badge badge-green">Top 50</span></li>
                <li><a href="/api/all100">/api/all100</a> <span class="badge badge-green">BIST100</span></li>
                <li><a href="/api/top_picks">/api/top_picks</a> <span class="badge badge-green">En İyi</span></li>
            </ul>
        </div>

        <div class="card">
            <h3>🌅 PREMARKET</h3>
            <ul>
                <li><a href="/api/premarket">/api/premarket</a> <span class="badge badge-yellow">Tarama</span></li>
                <li><a href="/api/premarket/telegram">/api/premarket/telegram</a> <span class="badge badge-yellow">Telegram</span></li>
            </ul>
        </div>

        <div class="card">
            <h3>📈 RISK & ARŞIV</h3>
            <ul>
                <li>/api/drawdown/&lt;ticker&gt; <span class="badge badge-red">DD</span></li>
                <li>/api/arsiv/&lt;hisse&gt; <span class="badge badge-yellow">Kayıtlar</span></li>
                <li>/api/arsiv/istatistik/&lt;hisse&gt; <span class="badge badge-yellow">İstatistik</span></li>
                <li>/api/arsiv/trend/&lt;hisse&gt; <span class="badge badge-yellow">Trend</span></li>
            </ul>
        </div>

        <div class="card">
            <h3>🤖 UZMAN MODULLER</h3>
            <ul>
                <li>1. Teknik Analiz (RSI/MACD/BB)</li>
                <li>2. Temel Analiz (P/E/ROE)</li>
                <li>3. Yatırımcı Stratejileri</li>
                <li>4. Risk Yönetimi (Kelly/VaR)</li>
                <li>5. Sentiment & Makro</li>
            </ul>
        </div>

        <div class="card">
            <h3>⚙️ MOTORLAR</h3>
            <ul>
                <li>Ensemble Motor (Ağırlıklı Birleştirme)</li>
                <li>Karar Motoru (AL/SAT/BEKLE)</li>
                <li>Risk Veto Sistemi</li>
                <li>Rejim Motoru (Bull/Bear/Neutral)</li>
                <li>Dynamic Ensemble</li>
            </ul>
        </div>
    </div>

    <div class="footer">
        <p>Borsa Komutan v4.0 | 5 Uzman + Ensemble AI | 2026</p>
    </div>
</body>
</html>
"""

# ==================== ROUTE'LAR ====================

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

# --- ANLIK ANALIZ ---

@app.route('/api/ensemble')
def api_ensemble():
    """XU100 Ensemble analizi"""
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    result = get_bist100()

    if result['status'] == 'OK':
        ensemble = calculate_ensemble(df=result['data'], zaman_dilimi=zaman_dilimi)

        # Arşive kaydet
        try:
            arsiv.kaydet_analiz('XU100', ensemble, zaman_dilimi)
        except:
            pass

        return jsonify(ensemble)

    return jsonify(result)

@app.route('/api/usdtry')
def api_usdtry():
    """USD/TRY kuru"""
    return jsonify(get_usdtry())

@app.route('/api/hisse_listesi')
def api_hisse_listesi():
    """Hisse listesi ve sektörler"""
    return jsonify({
        'status': 'OK',
        'total': len(BIST_HISSE_LISTESI),
        'hisseler': BIST_HISSE_LISTESI,
        'sectors': sorted(list(set(SEKTOR_MAP.values())))
    })

# --- HİSSE ANALIZI ---

@app.route('/api/hisse/<ticker>')
def api_hisse(ticker):
    """Tek hisse tam analiz (5 uzman + ensemble)"""
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')

    # Makro verileri al
    usdtry = get_usdtry()
    bist100 = get_bist100()

    usdtry_df = None
    bist100_df = None

    if usdtry['status'] == 'OK':
        usdtry_df = usdtry['data']
    if bist100['status'] == 'OK':
        bist100_df = bist100['data']

    # Analiz yap
    result = analyze_hisse(
        ticker,
        zaman_dilimi=zaman_dilimi,
        bist100_df=bist100_df,
        usdtry_df=usdtry_df
    )

    # Arşive kaydet
    if result['status'] == 'OK':
        try:
            arsiv.kaydet_analiz(
                ticker,
                result,
                zaman_dilimi,
                fiyat=result.get('last_price'),
                degisim=result.get('change_pct'),
                sektor=get_sector(ticker)
            )
        except:
            pass

    return jsonify(result)

@app.route('/api/top50')
def api_top50():
    """Top 50 analiz"""
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    result = analyze_top50(zaman_dilimi=zaman_dilimi)
    return jsonify(result)

@app.route('/api/all100')
def api_all100():
    """Tüm BIST100 analiz"""
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    result = analyze_all100(zaman_dilimi=zaman_dilimi)
    return jsonify(result)

@app.route('/api/top_picks')
def api_top_picks():
    """En iyi öneriler"""
    zaman_dilimi = request.args.get('zaman_dilimi', '1D')
    n = int(request.args.get('n', 10))
    result = get_top_picks(zaman_dilimi=zaman_dilimi, n=n)
    return jsonify(result)

# --- PREMARKET ---

@app.route('/api/premarket')
def api_premarket():
    """Premarket tarama"""
    from hisse_listesi import BIST_HISSE_LISTESI

    tickers = [t + '.IS' for t in BIST_HISSE_LISTESI[:50]]
    result = premarket_scanner.tara(tickers)
    return jsonify(result)

@app.route('/api/premarket/telegram')
def api_premarket_telegram():
    """Premarket Telegram formatı"""
    from hisse_listesi import BIST_HISSE_LISTESI

    tickers = [t + '.IS' for t in BIST_HISSE_LISTESI[:50]]
    result = premarket_scanner.tara(tickers)

    if result['status'] == 'OK':
        msg = premarket_scanner.format_telegram(result)
        return jsonify({'status': 'OK', 'telegram': msg})

    return jsonify(result)

# --- RISK & ARŞIV ---

@app.route('/api/drawdown/<ticker>')
def api_drawdown(ticker):
    """Drawdown takibi"""
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
    """Hisse arşivini getir"""
    try:
        limit = int(request.args.get('limit', 30))
        veri = arsiv.getir(hisse, limit=limit)
        return jsonify({'status': 'OK', 'hisse': hisse, 'kayitlar': veri})
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

@app.route('/api/arsiv/istatistik/<hisse>')
def api_arsiv_istatistik(hisse):
    """Hisse istatistiğini getir"""
    try:
        gun = int(request.args.get('gun', 30))
        stats = arsiv.istatistik(hisse, gun=gun)
        return jsonify({'status': 'OK', 'istatistik': stats})
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

@app.route('/api/arsiv/trend/<hisse>')
def api_arsiv_trend(hisse):
    """Hisse trend analizi"""
    try:
        gun = int(request.args.get('gun', 30))
        trend = arsiv.trend_analizi(hisse, gun=gun)
        return jsonify({'status': 'OK', 'trend': trend})
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

# --- DYNAMIC ENSEMBLE ---

@app.route('/api/dynamic/<ticker>')
def api_dynamic(ticker):
    """Dynamic Ensemble analizi (Rejim + DD)"""
    try:
        import yfinance as yf
        zaman_dilimi = request.args.get('zaman_dilimi', '1D')

        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo")

        if df.empty:
            return jsonify({'status': 'HATA', 'message': 'Veri bulunamadı'})

        # Makro veriler
        bist100 = get_bist100()
        usdtry = get_usdtry()

        bist100_df = bist100['data'] if bist100['status'] == 'OK' else None
        usdtry_df = usdtry['data'] if usdtry['status'] == 'OK' else None

        # Dynamic ensemble
        sonuc = dynamic_ensemble.calculate(
            df=df,
            hisse_adi=ticker,
            zaman_dilimi=zaman_dilimi,
            bist100_df=bist100_df,
            usdtry_df=usdtry_df
        )

        return jsonify(sonuc)

    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})

@app.route('/api/dynamic/portfoy', methods=['POST'])
def api_dynamic_portfoy():
    """Portföy dynamic analizi"""
    try:
        data = request.get_json()
        portfoy = data.get('portfoy', [])

        if not portfoy:
            return jsonify({'status': 'HATA', 'message': 'Portföy boş'})

        bist100 = get_bist100()
        usdtry = get_usdtry()

        bist100_df = bist100['data'] if bist100['status'] == 'OK' else None
        usdtry_df = usdtry['data'] if usdtry['status'] == 'OK' else None

        sonuc = dynamic_ensemble.portfoy_analiz(
            portfoy=portfoy,
            bist100_df=bist100_df,
            usdtry_df=usdtry_df
        )

        return jsonify(sonuc)

    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})


# =============================================================================
# KOMUTAN API ENDPOINT'LERI
# =============================================================================

try:
    from komutan_karar import KomutanKararMotoru

    komutan = KomutanKararMotoru()
    KOMUTAN_AKTIF = True
except ImportError:
    KOMUTAN_AKTIF = False


@app.route('/api/komutan/<ticker>')
def api_komutan(ticker):
    """Komutan karari - tek hisse."""
    if not KOMUTAN_AKTIF:
        return jsonify({'status': 'HATA', 'message': 'Komutan motoru aktif degil'})

    try:
        from hisse_analiz import hisse_analiz_et
        result = hisse_analiz_et(ticker)
        ticker, skor, fiyat, degisim, skorlar, hata = result

        if skor is None:
            return jsonify({'status': 'HATA', 'message': hata})

        karar = komutan.karar_ver(ticker, skorlar, fiyat)

        return jsonify({
            'status': 'OK',
            'ticker': ticker,
            'skor': skor,
            'fiyat': fiyat,
            'degisim': degisim,
            'komutan_karari': karar['karar'],
            'komutan_neden': karar['neden'],
            'beklenen_getiri': karar.get('beklenen_getiri', 0),
            'skorlar': skorlar
        })
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})


@app.route('/api/komutan/istatistik')
def api_komutan_istatistik():
    """Komutan istatistik raporu."""
    if not KOMUTAN_AKTIF:
        return jsonify({'status': 'HATA', 'message': 'Komutan motoru aktif degil'})

    try:
        rapor = komutan.istatistik_rapor()
        return jsonify({
            'status': 'OK',
            'rapor': rapor,
            'ozet': komutan.ogrenme.kar_zarar_ozet()
        })
    except Exception as e:
        return jsonify({'status': 'HATA', 'message': str(e)})
# ==================== MAIN ====================

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 BORSA KOMUTAN v4.0 BAŞLATILIYOR")
    print("=" * 70)
    print("📊 5 Uzman Modül Aktif")
    print("🤖 Ensemble Motor Aktif")
    print("⚡ Dynamic Ensemble Aktif")
    print("🌐 http://localhost:5000")
    print("=" * 70)
    app.run(host='0.0.0.0', port=5000, debug=True)
