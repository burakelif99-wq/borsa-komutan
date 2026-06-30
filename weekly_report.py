"""
weekly_report.py — Haftalik Arastirma Ozeti (Sadece okuma, deneye dokunmaz)

Her Cuma calistirilir. Gecmis 7 gunluk loglardan:
- Shadow Accuracy (v1 vs v2 anlasma/disagreement trend)
- Alpha karsilastirmasi (backfill varsa)
- False BEKLE / False AL trendi
- Drift
- Haftalik sonuc
"""

import os
import sys
import csv
import glob
from datetime import date, timedelta
from collections import defaultdict

sys.path.insert(0, r'C:\Users\Administrator\PycharmProjects\PythonProject\Kimi')
LOG_DIR = r'C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\logs'


def _safe_float(v, default=0.0):
    try:
        return float(v) if v != '' else default
    except (ValueError, TypeError):
        return default


def _gunluk_oku(tarih_str):
    path = os.path.join(LOG_DIR, f'sinyaller_{tarih_str}.csv')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def generate(bitis_tarihi=None):
    if bitis_tarihi is None:
        bitis_tarihi = date.today()
    baslangic = bitis_tarihi - timedelta(days=6)

    print()
    print("=" * 62)
    print("  WEEKLY RESEARCH SUMMARY  ".center(62, '═'))
    print(f"  {baslangic.isoformat()}  →  {bitis_tarihi.isoformat()}")
    print("=" * 62)

    # Gun gun veri topla
    gunluk_veri = []
    for i in range(7):
        g = baslangic + timedelta(days=i)
        rows = _gunluk_oku(g.isoformat())
        if rows:
            gunluk_veri.append((g, rows))

    if not gunluk_veri:
        print("\n  Bu hafta hic log bulunamadi.\n")
        return

    print(f"\n  Aktif gun: {len(gunluk_veri)}/{7}")

    # Pipeline bazli gunluk istatistik
    gunler = []
    for g, rows in gunluk_veri:
        v1_al = sum(1 for r in rows if r.get('pipeline') == 'v1.0' and r['signal'] == 'AL')
        v2_al = sum(1 for r in rows if r.get('pipeline') == 'v2.0' and r['signal'] == 'AL')
        v1_top = sum(1 for r in rows if r.get('pipeline') == 'v1.0')
        v2_top = sum(1 for r in rows if r.get('pipeline') == 'v2.0')
        # Anlasmazlik
        v1_set = {r['ticker'] for r in rows if r.get('pipeline') == 'v1.0' and r['signal'] == 'AL'}
        v2_set = {r['ticker'] for r in rows if r.get('pipeline') == 'v2.0' and r['signal'] == 'AL'}
        dis = len(v1_set.symmetric_difference(v2_set))
        # Outcome
        completed = [r for r in rows if r.get('getiri_1g','') != '' and r['signal'] == 'AL']
        v1_ret = [_safe_float(r['getiri_1g']) for r in completed if r.get('pipeline') == 'v1.0']
        v2_ret = [_safe_float(r['getiri_1g']) for r in completed if r.get('pipeline') == 'v2.0']
        gunler.append({
            'tarih': g,
            'v1_al': v1_al, 'v1_top': v1_top,
            'v2_al': v2_al, 'v2_top': v2_top,
            'dis': dis,
            'v1_ret': v1_ret, 'v2_ret': v2_ret,
        })

    # Gunluk trend tablosu
    print(f"\n  {'Gun':<12} {'v1 AL':>6} {'v2 AL':>6} {'Fark':>6} {'Anlasmazlik':>12} {'v1 getiri':>10} {'v2 getiri':>10}")
    print(f"  {'─'*62}")
    toplam_v1_al = 0
    toplam_v2_al = 0
    toplam_dis = 0
    tum_v1_ret = []
    tum_v2_ret = []
    for g in gunler:
        v1_ret_ort = sum(g['v1_ret'])/len(g['v1_ret'])*100 if g['v1_ret'] else 0
        v2_ret_ort = sum(g['v2_ret'])/len(g['v2_ret'])*100 if g['v2_ret'] else 0
        print(f"  {g['tarih'].isoformat():<12} {g['v1_al']:>6} {g['v2_al']:>6} {g['v2_al']-g['v1_al']:+>5} {g['dis']:>6} (%{g['dis']/(g['v1_top'] or 1)*100:4.1f}) {v1_ret_ort:>+9.2f}% {v2_ret_ort:>+9.2f}%")
        toplam_v1_al += g['v1_al']
        toplam_v2_al += g['v2_al']
        toplam_dis += g['dis']
        tum_v1_ret.extend(g['v1_ret'])
        tum_v2_ret.extend(g['v2_ret'])

    # Haftalik ozet
    print(f"\n  HAFTALIK OZET")
    print(f"  {'─'*62}")
    print(f"  Toplam v1.0 AL        : {toplam_v1_al}")
    print(f"  Toplam v2.0 AL        : {toplam_v2_al}")
    print(f"  Toplam anlasmazlik    : {toplam_dis}")
    haftalik_top = sum(g['v1_top'] for g in gunler)
    dis_oran = toplam_dis / haftalik_top * 100 if haftalik_top else 0
    print(f"  Anlasmazlik orani     : %{dis_oran:.1f}")

    if tum_v1_ret:
        v1_ort = sum(tum_v1_ret)/len(tum_v1_ret)*100
        print(f"  v1.0 ortalama 1g getiri: %{v1_ort:+.2f} ({len(tum_v1_ret)} trade)")
    if tum_v2_ret:
        v2_ort = sum(tum_v2_ret)/len(tum_v2_ret)*100
        print(f"  v2.0 ortalama 1g getiri: %{v2_ort:+.2f} ({len(tum_v2_ret)} trade)")
    if tum_v1_ret and tum_v2_ret:
        print(f"  Fark                  : %{v2_ort - v1_ort:+.2f}")
    print()

    # False BEKLE trendi (gunluk)
    print("  FALSE BEKLE TRENDI (0.40-0.45 bandi)")
    print(f"  {'Gun':<12} {'False BEKLE':>12} {'Toplam BEKLE':>14} {'Oran':>8}")
    print(f"  {'─'*48}")
    total_fb = 0
    total_bk = 0
    for g in gunler:
        rows = _gunluk_oku(g['tarih'].isoformat())
        fb = 0
        bk = 0
        for r in rows:
            if r.get('pipeline') != 'v2.0':
                continue
            if r['signal'] == 'BEKLE':
                bk += 1
                p = _safe_float(r.get('gb_proba', 0))
                if 0.40 <= p <= 0.45:
                    fb += 1
        total_fb += fb
        total_bk += bk
        oran = fb / bk * 100 if bk else 0
        print(f"  {g['tarih'].isoformat():<12} {fb:>6} / {bk:<6} {oran:>7.1f}%")
    if total_bk:
        print(f"  {'─'*48}")
        print(f"  {'HAFTALIK':<12} {total_fb:>6} / {total_bk:<6} {total_fb/total_bk*100:>7.1f}%")
    print()

    # Sonuc
    print("  HAFTALIK SONUC")
    print(f"  {'─'*62}")
    if tum_v1_ret and tum_v2_ret:
        kazanan = 'v2.0' if v2_ort > v1_ort else 'v1.0'
        print(f"  Getiri lideri        : {kazanan} (%{v2_ort - v1_ort:+.2f})")
    if dis_oran < 10:
        print(f"  Anlasma seviyesi     : Yuksek (%{100-dis_oran:.1f})")
    elif dis_oran < 20:
        print(f"  Anlasma seviyesi     : Orta (%{100-dis_oran:.1f})")
    else:
        print(f"  Anlasma seviyesi     : Dusuk (%{100-dis_oran:.1f})")
    print(f"  False BEKLE tespiti  : {total_fb} kez ({total_fb/total_bk*100:.1f}%)" if total_bk else "  False BEKLE tespiti  : Yok")
    print()

    print("=" * 62)
    print()

    return {
        'gunler': gunler,
        'toplam_v1_al': toplam_v1_al,
        'toplam_v2_al': toplam_v2_al,
        'toplam_dis': toplam_dis,
        'dis_oran': dis_oran,
        'tum_v1_ret': tum_v1_ret,
        'tum_v2_ret': tum_v2_ret,
        'false_bekle': total_fb,
    }


if __name__ == '__main__':
    generate()
