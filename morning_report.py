"""
morning_report.py — Shadow Mode Gunluk Karsilastirma Raporu

v1.0 (production) ve v2.0 (shadow) kararlarini karsilastirir,
anlasmazliklari kategorize eder, RALYH ozel takibi yapar,
Shadow Score ve kumulatif istatistikleri gosterir.
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


def _pipe_set(rows, pipe):
    return {r['ticker']: r for r in rows if r.get('pipeline') == pipe}


def read_gunluk(tarih=None):
    if tarih is None:
        tarih = date.today()
    path = os.path.join(LOG_DIR, f'sinyaller_{tarih.isoformat()}.csv')
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def tum_loglar():
    rows = []
    for fn in sorted(glob.glob(os.path.join(LOG_DIR, 'sinyaller_*.csv'))):
        with open(fn, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows.extend(reader)
    return rows


def pipeline_stats(rows, pipe):
    v = _pipe_set(rows, pipe)
    if not v:
        return {'AL': 0, 'count': 0, 'al_list': [], 'gb_ort': 0, 'rf_guard': 0}
    vals = list(v.values())
    al = [r for r in vals if r['signal'] == 'AL']
    gb_vals = [_safe_float(r['gb_proba']) for r in vals if _safe_float(r['gb_proba']) > 0]
    rf_guard = sum(1 for r in vals if r.get('rf_guard_active', '').lower() == 'true')
    return {
        'AL': len(al),
        'count': len(vals),
        'al_list': [r['ticker'] for r in al],
        'gb_ort': round(sum(gb_vals)/len(gb_vals), 4) if gb_vals else 0,
        'rf_guard': rf_guard,
    }


def rejim_dagilim(rows):
    d = defaultdict(int)
    for r in rows:
        d[r.get('regime', '?')] += 1
    return dict(d)


def generate(tarih=None):
    rows = read_gunluk(tarih)
    if not rows:
        print("[RAPOR] Bugun log bulunamadi.")
        return

    s1 = pipeline_stats(rows, 'v1.0')
    s2 = pipeline_stats(rows, 'v2.0')
    toplam = s1['count'] if s1['count'] > 0 else s2['count']
    if toplam == 0:
        print("[RAPOR] Bugun v1.0 veya v2.0 log bulunamadi.")
        return

    # Anlasmazlik
    v1_set = set(s1['al_list'])
    v2_set = set(s2['al_list'])
    only_v2 = sorted(v2_set - v1_set)
    only_v1 = sorted(v1_set - v2_set)
    both = sorted(v1_set & v2_set)

    # v1.0=BEKLE, v2.0=AL (yeni firsat)
    # v1.0=AL, v2.0=BEKLE (risk reddi)
    v2_ok = _pipe_set(rows, 'v2.0')
    yeni_firsat = []
    risk_reddi = []
    both_bekle = []
    for t in only_v2:
        r = v2_ok.get(t, {})
        yeni_firsat.append((t, _safe_float(r.get('gb_proba', 0)), r.get('reason', '?')))
    for t in only_v1:
        r = v2_ok.get(t, {})
        risk_reddi.append((t, _safe_float(r.get('gb_proba', 0)), r.get('reason', '?')))
    # Ortak BEKLE: hisse hem v1 hem v2'de var ama ikisi de AL degil
    v1_set_all = set(r['ticker'] for r in rows if r.get('pipeline') == 'v1.0')
    v2_set_all = set(r['ticker'] for r in rows if r.get('pipeline') == 'v2.0')
    ortak_tum = v1_set_all & v2_set_all
    both_bekle = sorted(ortak_tum - v1_set - v2_set)

    # Rejim
    regime_counts = rejim_dagilim(rows)
    dominant_regime = max(regime_counts, key=regime_counts.get) if regime_counts else '?'

    # --- SHADOW SCORE (bugun) ---
    false_bekle_40_45 = 0
    for r in rows:
        if r.get('pipeline') == 'v2.0' and r.get('signal') == 'BEKLE':
            p = _safe_float(r.get('gb_proba', 0))
            if 0.40 <= p <= 0.45:
                false_bekle_40_45 += 1
    bekle_all = sum(1 for r in rows if r.get('pipeline') == 'v2.0' and r.get('signal') == 'BEKLE')
    false_bekle_orani = round(false_bekle_40_45 / bekle_all * 100, 1) if bekle_all else 0

    # --- RISK RED DIYE AYRISTIR (nedene gore) ---
    def _risk_grubu(risk_list):
        """risk_reddi listesini {'neden': [(ticker, gb, gap, reason)]} seklinde grupla"""
        gruplar = defaultdict(list)
        for t, gb, reason in risk_list:
            # GB gap = gb - esik (ilk v2.0 satirdan esik bul)
            esik = _safe_float(
                next((r.get('esik', 0) for r in rows
                      if r.get('pipeline') == 'v2.0' and r.get('ticker') == t), 0.4)
            )
            gap = gb - esik
            gruplar[reason].append((t, gb, gap, reason))
        return dict(gruplar)

    risk_gruplari = _risk_grubu(risk_reddi) if risk_reddi else {}

    # --- SPECIAL WATCHLIST ---
    WATCH_TICKERS = ['RALYH', 'AKCNS', 'AKFIS']
    watch = {}
    for wt in WATCH_TICKERS:
        v1r = next((r for r in rows if r.get('pipeline') == 'v1.0' and r.get('ticker') == wt), None)
        v2r = next((r for r in rows if r.get('pipeline') == 'v2.0' and r.get('ticker') == wt), None)
        watch[wt] = (v1r, v2r)

    # PRINT
    print()
    print("=" * 62)
    print("  SHADOW MODE  ".center(62, '═'))
    print(f"  {date.today().isoformat()}  |  Hisse: {toplam}")
    print()

    # --- Pipeline karsilastirma ---
    print(f"  v1.0  AL={s1['AL']:>3}  GB_ort={s1['gb_ort']:.3f}  RF_Guard={s1['rf_guard']}")
    print(f"  v2.0  AL={s2['AL']:>3}  GB_ort={s2['gb_ort']:.3f}  RF_Guard={s2['rf_guard']}")
    print(f"  Fark  {s2['AL']-s1['AL']:+>3} AL  GB_fark={s2['gb_ort']-s1['gb_ort']:+.3f}")
    print()

    # --- SHADOW SCORE ---
    anlasma_orani = round((1 - (len(only_v1)+len(only_v2))/toplam) * 100, 1)
    print("  SHADOW SCORE")
    print(f"    Yeni firsat (v2 AL, v1 degil)  : {len(yeni_firsat):>3}")
    print(f"    Risk reddi (v1 AL, v2 degil)   : {len(risk_reddi):>3}")
    print(f"    Anlasmazlik orani               : %{100-anlasma_orani:.1f}")
    print(f"    Anlasma orani                   : %{anlasma_orani:.1f}")
    print(f"    False BEKLE (0.40-0.45)         : {false_bekle_40_45}/{bekle_all} (%{false_bekle_orani})")
    print(f"    Rejim                           : {dominant_regime}")
    print()

    # --- ANLASMAZLIK ANALIZI ---
    print("  ANLASMAZLIK ANALIZI")
    print(f"  {'─'*62}")
    print(f"  {'Grup':<20} {'Sayi':>5}  {'GB_ort':>6}  {'Bilesen':<30}")
    print(f"  {'─'*62}")
    print(f"  {'Ortak AL':<20} {len(both):>5}  {s1['gb_ort']:.3f}  {'v1=v2=AL':<30}")
    print(f"  {'Ortak BEKLE':<20} {len(both_bekle):>5}  {'':>6}  {'v1=v2≠AL':<30}")
    if yeni_firsat:
        gb_yf = sum(t[1] for t in yeni_firsat) / len(yeni_firsat)
        reasons = ','.join(sorted(set(t[2] for t in yeni_firsat)))
        print(f"  {'Yeni firsat (v2=AL, v1≠AL)':<20} {len(yeni_firsat):>5}  {gb_yf:.3f}  {reasons:<30}")
    if risk_reddi:
        gb_rr = sum(t[1] for t in risk_reddi) / len(risk_reddi)
        reasons = ','.join(sorted(set(t[2] for t in risk_reddi)))
        print(f"  {'Risk reddi (v1=AL, v2≠AL)':<20} {len(risk_reddi):>5}  {gb_rr:.3f}  {reasons:<30}")
    print()

    # --- YENI FIRSAT DETAYI ---
    if yeni_firsat:
        print("  YENI FIRSAT (v2.0 goruyor, v1.0 kaciriyor)")
        print(f"  {'Ticker':>7}  GB     Sebep")
        print(f"  {'─'*28}")
        for t, gb, reason in sorted(yeni_firsat, key=lambda x: -x[1]):
            print(f"  {t:>7}  {gb:.3f}  {reason}")
        print()

    # --- RISK REDDI DETAYI (nedene gore gruplanmis) ---
    if risk_gruplari:
        print("  RISK RED DIYE AYRISTIR")
        print(f"  {'Neden':<15} {'Sayi':>5}  {'GB_ort':>6}  {'GB_gap_ort':>10}  {'Dusuk_gap':>9}  {'Yuksek_gap':>11}")
        print(f"  {'─'*60}")
        for neden in ['ATR_LIMIT', 'LIKIDITE', '?']:
            grp = risk_gruplari.get(neden, [])
            if not grp:
                continue
            gb_vals = [t[1] for t in grp]
            gaps = [t[2] for t in grp]
            print(f"  {neden:<15} {len(grp):>5}  {sum(gb_vals)/len(gb_vals):.3f}  {sum(gaps)/len(gaps):+.3f}  {min(gaps):+.3f}  {max(gaps):+.3f}")
        # Geri kalanlar (diger nedenler)
        diger = [v for k, v in risk_gruplari.items() if k not in ('ATR_LIMIT', 'LIKIDITE', '?')]
        if diger:
            tum = [item for sublist in diger for item in sublist]
            gb_vals = [t[1] for t in tum]
            gaps = [t[2] for t in tum]
            print(f"  {'DIGER':<15} {len(tum):>5}  {sum(gb_vals)/len(gb_vals):.3f}  {sum(gaps)/len(gaps):+.3f}  {min(gaps):+.3f}  {max(gaps):+.3f}")
        print()

        # Her neden icin detay
        for neden in sorted(risk_gruplari):
            grp = risk_gruplari[neden]
            print(f"  {neden} ({len(grp)} hisse)")
            print(f"    {'Ticker':>6}  {'GB':>5}  {'Gap':>6}")
            for t, gb, gap, _ in sorted(grp, key=lambda x: -x[1]):
                print(f"    {t:>6}  {gb:.3f}  {gap:+.3f}")
        print()

    # --- YENI FIRSAT DETAYI ---
    if yeni_firsat:
        print("  YENI FIRSAT (v2.0 goruyor, v1.0 kaciriyor)")
        print(f"  {'Ticker':>7}  GB     Sebep")
        print(f"  {'─'*28}")
        for t, gb, reason in sorted(yeni_firsat, key=lambda x: -x[1]):
            print(f"  {t:>7}  {gb:.3f}  {reason}")
        print()

    # --- SPECIAL WATCHLIST ---
    print("  SPECIAL WATCHLIST")
    print(f"  {'Ticker':>7}  v1.0     v2.0     GB    Gap   Fiyat   Durum")
    print(f"  {'─'*54}")
    for wt in WATCH_TICKERS:
        v1r, v2r = watch.get(wt, (None, None))
        if not v1r and not v2r:
            continue
        sig1 = v1r.get('signal', '?') if v1r else '-'
        sig2 = v2r.get('signal', '?') if v2r else '-'
        gb = _safe_float((v2r or v1r).get('gb_proba', 0))
        esik = _safe_float((v2r or v1r).get('esik', 0.4))
        gap = gb - esik
        fiyat = _safe_float((v1r or v2r).get('fiyat', 0))
        durum = 'WATCH' if sig1 != sig2 else 'OK'
        print(f"  {wt:>7}  {sig1:>5}   {sig2:>5}   {gb:.3f}  {gap:+.3f}  {fiyat:>6.1f}  {durum}")

    # --- KUMULATIF (gecmis loglardan) ---
    tum = tum_loglar()
    onceki = [r for r in tum if r.get('timestamp','')[:10] < date.today().isoformat()]
    if onceki:
        # Sadece pipeline ayrismali satirlardan
        onceki_v1 = [r for r in onceki if r.get('pipeline') == 'v1.0']
        onceki_v2 = [r for r in onceki if r.get('pipeline') == 'v2.0']
        print("  KUMULATIF (gecmis gunler)")
        if onceki_v1:
            al_v1 = sum(1 for r in onceki_v1 if r['signal'] == 'AL')
            print(f"    v1.0 AL: {al_v1}/{len(onceki_v1)} (%{al_v1/len(onceki_v1)*100:.1f})")
        if onceki_v2:
            al_v2 = sum(1 for r in onceki_v2 if r['signal'] == 'AL')
            print(f"    v2.0 AL: {al_v2}/{len(onceki_v2)} (%{al_v2/len(onceki_v2)*100:.1f})")
        # Outcome olan varsa
        completed = [r for r in onceki if r.get('getiri_1g','') != '']
        if completed:
            v1_ret = [float(r['getiri_1g']) for r in completed if r.get('pipeline') == 'v1.0' and r['signal'] == 'AL']
            v2_ret = [float(r['getiri_1g']) for r in completed if r.get('pipeline') == 'v2.0' and r['signal'] == 'AL']
            if v1_ret:
                print(f"    v1.0 ortalama 1g getiri: {sum(v1_ret)/len(v1_ret)*100:+.2f}% ({len(v1_ret)} trade)")
            if v2_ret:
                print(f"    v2.0 ortalama 1g getiri: {sum(v2_ret)/len(v2_ret)*100:+.2f}% ({len(v2_ret)} trade)")
        son_tarih = max(r.get('timestamp','')[:10] for r in onceki)
        print(f"    Son veri: {son_tarih}")
        print()

    # --- KANIT TABLOSU (deney baslangici) ---
    print("  KANIT TABLOSU (2 hafta sonu dolacak)")
    print(f"  {'─'*62}")
    print(f"  {'Soru':<45} {'Durum':<15}")
    print(f"  {'─'*62}")
    print("  v2 Alpha v1.dan yuksek mi?                          Bekliyor...")
    print("  Sharpe daha iyi mi?                                 Bekliyor...")
    print("  MaxDD kotulesmedi mi?                               Bekliyor...")
    print("  Risk RED grubu gercekten yukseldi mi?               Bekliyor...")
    print("  Yeni firsat grubu firsat miydi?                     Bekliyor...")
    print("  ATR gereksiz filtre miydi?                          Bekliyor...")
    print()

    # --- DRIFT CHECK ---
    print("  DRIFT CHECK")
    al_orani_v2 = s2['AL'] / s2['count'] * 100 if s2['count'] else 0
    alarms = []
    if s2['gb_ort'] < 0.50:
        alarms.append(f"GB_ort dusuk: {s2['gb_ort']:.3f} (<0.50)")
    if s2['rf_guard'] > s2['count'] * 0.35:
        alarms.append(f"RF_guard yuksek: {s2['rf_guard']} (%{s2['rf_guard']/s2['count']*100:.0f})")
    if al_orani_v2 < 5 or al_orani_v2 > 50:
        alarms.append(f"AL_orani anormal: %{al_orani_v2:.1f}")
    if false_bekle_orani > 15:
        alarms.append(f"False_BEKLE yuksek: %{false_bekle_orani}")
    if alarms:
        for a in alarms:
            print(f"    [!] {a}")
    else:
        print("    Normal")
    print()

    print("=" * 62)
    print()

    ralyh_rec = watch.get('RALYH', (None, None))
    return {
        's1': s1, 's2': s2,
        'only_v2': only_v2, 'only_v1': only_v1, 'both': both,
        'yeni_firsat': yeni_firsat, 'risk_reddi': risk_reddi,
        'regime': dominant_regime,
        'false_bekle_orani': false_bekle_orani,
        'ralyh_v1': ralyh_rec[0], 'ralyh_v2': ralyh_rec[1],
        'alarms': alarms,
    }


if __name__ == '__main__':
    generate()
