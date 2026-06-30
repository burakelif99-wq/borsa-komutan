"""
experiment_timeline.py — Deney Zaman Cizelgesi (Sadece okuma, deneye dokunmaz)

Her gunluk log'dan:
- Taranan hisse sayisi
- v1.0 vs v2.0 AL sayisi
- Anlasmazlik
- False BEKLE
- Major events (deb'i degisim, model guncellemesi, vs.)
"""

import os
import sys
import csv
import glob
from datetime import date
from collections import defaultdict

sys.path.insert(0, r'C:\Users\Administrator\PycharmProjects\PythonProject\Kimi')
LOG_DIR = r'C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\logs'


def _safe_float(v, default=0.0):
    try:
        return float(v) if v != '' else default
    except (ValueError, TypeError):
        return default


def _tum_gunler():
    """Returns sorted list of unique dates with log data"""
    dates = set()
    for fn in glob.glob(os.path.join(LOG_DIR, 'sinyaller_*.csv')):
        # Extract date from filename: sinyaller_2026-06-29.csv
        basename = os.path.basename(fn)
        tarih_str = basename.replace('sinyaller_', '').replace('.csv', '')
        try:
            dates.add(tarih_str)
        except ValueError:
            pass
    return sorted(dates)


def _gun_oku(tarih_str):
    path = os.path.join(LOG_DIR, f'sinyaller_{tarih_str}.csv')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def generate():
    gunler = _tum_gunler()

    print()
    print("=" * 62)
    print("  EXPERIMENT TIMELINE  ".center(62, '═'))
    print(f"  Toplam gun: {len(gunler)}")
    print()

    if not gunler:
        print("  Henuz log verisi yok.\n")
        return

    # Baslik
    print(f"  {'Tarih':<12} {'Hisse':>6} {'v1 AL':>6} {'v2 AL':>6} {'Fark':>5} {'Anlasmazlik':>6} {'FB':>6} {'Not':<20}")
    print(f"  {'─'*70}")

    toplam_hisse = 0
    toplam_v1 = 0
    toplam_v2 = 0
    toplam_dis = 0

    for t in gunler:
        rows = _gun_oku(t)
        if not rows:
            continue

        v1_top = sum(1 for r in rows if r.get('pipeline') == 'v1.0')
        v2_top = sum(1 for r in rows if r.get('pipeline') == 'v2.0')
        hisse_count = max(v1_top, v2_top)

        v1_al = sum(1 for r in rows if r.get('pipeline') == 'v1.0' and r['signal'] == 'AL')
        v2_al = sum(1 for r in rows if r.get('pipeline') == 'v2.0' and r['signal'] == 'AL')

        v1_set = {r['ticker'] for r in rows if r.get('pipeline') == 'v1.0' and r['signal'] == 'AL'}
        v2_set = {r['ticker'] for r in rows if r.get('pipeline') == 'v2.0' and r['signal'] == 'AL'}
        dis = len(v1_set.symmetric_difference(v2_set))

        # False BEKLE
        fb = 0
        for r in rows:
            if r.get('pipeline') != 'v2.0' or r['signal'] != 'BEKLE':
                continue
            p = _safe_float(r.get('gb_proba', 0))
            if 0.40 <= p <= 0.45:
                fb += 1

        # Ilk gun notu
        is_first = (t == gunler[0])
        note = 'ILK GUN (baslangic)' if is_first else ''

        print(f"  {t:<12} {hisse_count:>6} {v1_al:>6} {v2_al:>6} {v2_al-v1_al:+>4} {dis:>6} {fb:>6}  {note:<20}")

        toplam_hisse += hisse_count
        toplam_v1 += v1_al
        toplam_v2 += v2_al
        toplam_dis += dis

    # Ozet
    print(f"  {'─'*70}")
    gun_say = len(gunler)
    print(f"  {'TOPLAM':<12} {toplam_hisse:>6} {toplam_v1:>6} {toplam_v2:>6} {toplam_v2-toplam_v1:+>4} {toplam_dis:>6}")
    if gun_say:
        print(f"  {'Gunluk ort':<12} {toplam_hisse//gun_say:>6} {toplam_v1//gun_say:>6} {toplam_v2//gun_say:>6} {'':>5} {toplam_dis//gun_say:>6}")
    print()

    # Major Events section
    print("  MAJOR EVENTS")
    print(f"  {'─'*62}")
    print(f"  {gunler[0] if gunler else '?'}: Deney baslangici (Shadow Mode aktif)")
    print(f"  Hedef: 14 gun boyunca parametre degisimi YOK")
    print(f"  Karar: 14. gun Kanit Tablosu dolar, kazanan production'a")
    print()

    # RALYH summary across all logs
    print("  RALYH OZETI (tum gunler)")
    print(f"  {'Tarih':<12} {'v1':>5} {'v2':>5} {'GB':>5} {'Fiyat':>6}")
    print(f"  {'─'*36}")
    for t in gunler:
        rows = _gun_oku(t)
        v1r = next((r for r in rows if r.get('ticker') == 'RALYH' and r.get('pipeline') == 'v1.0'), None)
        v2r = next((r for r in rows if r.get('ticker') == 'RALYH' and r.get('pipeline') == 'v2.0'), None)
        if not v1r and not v2r:
            continue
        sig1 = v1r['signal'] if v1r else '-'
        sig2 = v2r['signal'] if v2r else '-'
        gb = _safe_float((v2r or v1r).get('gb_proba', 0))
        fiyat = _safe_float((v1r or v2r).get('fiyat', 0))
        print(f"  {t:<12} {sig1:>5} {sig2:>5} {gb:.3f} {fiyat:>6.1f}")
    print()

    print("=" * 62)
    print()

    return {
        'gunler': gunler,
        'toplam_hisse': toplam_hisse,
        'toplam_v1': toplam_v1,
        'toplam_v2': toplam_v2,
        'toplam_dis': toplam_dis,
    }


if __name__ == '__main__':
    generate()
