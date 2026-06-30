"""
shadow_runner.py — Shadow Mode Calistirici

v1.0 (production) ve v2.0 (shadow) ayni anda calisir.
Her iki pipeline da ayni log dosyasina pipeline alaniyla ayrisarak yazilir.
"""

import warnings
warnings.filterwarnings('ignore')

import time
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, r'C:\Users\Administrator\PycharmProjects\PythonProject\Kimi')
from hisse_analiz import AI_MODEL, veri_cek
from hisse_listesi import HISSE_LISTESI
from signal_logger import get_logger


def _v1_karar(ticker, data):
    """v1.0: existing weighted score fusion (ai_skor_hesapla)"""
    try:
        from hisse_analiz import ai_skor_hesapla
        skor, etiket, guven, detay = ai_skor_hesapla(ticker, data)
        return {
            'etiket': etiket,
            'guven': guven,
            'detay': detay,
            'reason': detay.get('reason', '?'),
        }
    except Exception as e:
        return {'etiket': 'BEKLE', 'guven': 0, 'detay': {}, 'reason': f'ERR:{str(e)[:30]}'}


def _v2_karar(ticker, data):
    """v2.0: role-based decision pipeline (karar_pipeline)"""
    try:
        from karar_pipeline import DecisionPipeline
        pipe = DecisionPipeline(AI_MODEL)

        # Force regime sync
        AI_MODEL._get_regime()

        sonuc = pipe.karar_ver(ticker, data)
        detay = sonuc.get('detay', {})
        return {
            'etiket': sonuc['etiket'],
            'guven': sonuc.get('guven', 0),
            'detay': detay,
            'reason': sonuc.get('reason', '?'),
        }
    except Exception as e:
        return {'etiket': 'BEKLE', 'guven': 0, 'detay': {}, 'reason': f'ERR:{str(e)[:30]}'}


def _hisse_islem(ticker):
    """Tek hisse icin v1.0 + v2.0 kararlari"""
    data = veri_cek(ticker, period='200d')
    if data is None or len(data) < 50:
        return None

    v1 = _v1_karar(ticker, data)
    v2 = _v2_karar(ticker, data)

    # v1.0 log hisse_analiz icinden yapiliyor (double loglama yok)
    # sadece v2.0 logla (v2.0 pipeline kendi loglamiyor)
    d1 = v1['detay']
    d2 = v2['detay']
    fiyat = float(data['Close'].iloc[-1])
    regime = d1.get('rejim', AI_MODEL._regime_cache if hasattr(AI_MODEL, '_regime_cache') else '?')

    get_logger().log(
        pipeline='v2.0',
        ticker=ticker,
        regime=d2.get('rejim', regime),
        esik=d2.get('esik', d1.get('esik', getattr(AI_MODEL, 'al_esik', 0.45))),
        gb_proba=d2.get('gb_al', d1.get('gb_al', 0)),
        rf_proba=d2.get('rf_al'),
        rf_guard_active=d2.get('rf_guard_aktif', False),
        signal=v2['etiket'],
        reason=v2['reason'],
        fiyat=fiyat,
    )

    return {
        'ticker': ticker,
        'v1': v1['etiket'],
        'v2': v2['etiket'],
        'v1_reason': v1['reason'],
        'v2_reason': v2['reason'],
        'gb': d1.get('gb_al', d2.get('gb_al', 0)),
        'fiyat': fiyat,
    }


def run(hisse_listesi=None, max_workers=10):
    """Shadow mode run: v1.0 + v2.0 parallel on all tickers"""
    if hisse_listesi is None:
        hisse_listesi = HISSE_LISTESI

    print(f"\n{'='*60}")
    print(f"  SHADOW MODE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Hisseler: {len(hisse_listesi)}")
    print(f"{'='*60}\n")

    sonuclar = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {ex.submit(_hisse_islem, t): t for t in hisse_listesi}
        for future in as_completed(future_map):
            ticker = future_map[future]
            try:
                r = future.result(timeout=120)
                if r:
                    sonuclar.append(r)
                    fark = '!' if r['v1'] != r['v2'] else ' '
                    if r['v2'] == 'AL':
                        print(f"  {fark} {ticker:>7} | v1={r['v1']:>5} | v2={r['v2']:>5} | gb={r['gb']:.3f} | {r['v2_reason']}")
            except Exception as e:
                print(f"  x {ticker}: {str(e)[:40]}")

    # Ozet
    v1_al = sum(1 for r in sonuclar if r['v1'] == 'AL')
    v2_al = sum(1 for r in sonuclar if r['v2'] == 'AL')
    farkli = sum(1 for r in sonuclar if r['v1'] != r['v2'])
    sadece_v2 = [r for r in sonuclar if r['v1'] == 'BEKLE' and r['v2'] == 'AL']
    sadece_v1 = [r for r in sonuclar if r['v1'] == 'AL' and r['v2'] == 'BEKLE']

    print(f"\n{'='*60}")
    print(f"  SHADOW SUMMARY")
    print(f"{'='*60}")
    print(f"  Toplam hisse:     {len(sonuclar)}")
    print(f"  v1.0 AL:          {v1_al}")
    print(f"  v2.0 AL:          {v2_al}")
    print(f"  Farkli karar:     {farkli} ({farkli/len(sonuclar)*100:.1f}%)")
    print(f"  Sadece v2.0 AL:   {len(sadece_v2)} ({','.join(r['ticker'] for r in sadece_v2[:10])})")
    print(f"  Sadece v1.0 AL:   {len(sadece_v1)} ({','.join(r['ticker'] for r in sadece_v1[:10])})")
    print(f"{'='*60}\n")

    return sonuclar


if __name__ == '__main__':
    run()
