"""
signal_logger.py - v1.0 Monitor Katmani
Her sinyali log'lar, outcome backfill destegi, analiz raporu.
"""

import os
import csv
import json
from datetime import datetime, date
from collections import defaultdict


class SignalLogger:
    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._buffer = []

    # --- columns ---
    COLUMNS = [
        'pipeline', 'timestamp', 'ticker', 'regime', 'esik',
        'gb_proba', 'rf_proba',
        'rf_guard_active', 'signal',
        'reason', 'fiyat',
        'getiri_1g', 'getiri_5g', 'pnl',
    ]

    @property
    def _gunluk_path(self):
        return os.path.join(self.log_dir, f'sinyaller_{date.today().isoformat()}.csv')

    def log(self, ticker, regime, esik, gb_proba, rf_proba,
            rf_guard_active, signal, reason, fiyat=None, pipeline='v1.0'):
        row = {
            'pipeline': pipeline,
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'regime': regime,
            'esik': esik,
            'gb_proba': round(gb_proba, 4),
            'rf_proba': round(rf_proba, 4) if rf_proba is not None else '',
            'rf_guard_active': rf_guard_active,
            'signal': signal,
            'reason': reason,
            'fiyat': round(fiyat, 2) if fiyat else '',
            'getiri_1g': '',
            'getiri_5g': '',
            'pnl': '',
        }
        path = self._gunluk_path
        yeni = not os.path.exists(path)
        with open(path, 'a', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=self.COLUMNS)
            if yeni:
                w.writeheader()
            w.writerow(row)

    def flush(self):
        pass  # direct write per log call, no buffer needed

    def backfill_outcome(self, ticker, tarih, getiri_1g=None, getiri_5g=None, pnl=None):
        rows = []
        path = None
        for fn in os.listdir(self.log_dir):
            if fn.endswith('.csv'):
                path = os.path.join(self.log_dir, fn)
                break
        if not path:
            return
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['ticker'] == ticker and row['timestamp'].startswith(tarih):
                    if getiri_1g is not None:
                        row['getiri_1g'] = round(getiri_1g, 4)
                    if getiri_5g is not None:
                        row['getiri_5g'] = round(getiri_5g, 4)
                    if pnl is not None:
                        row['pnl'] = round(pnl, 4)
                rows.append(row)
        if rows:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=self.COLUMNS)
                w.writeheader()
                w.writerows(rows)

    def analyze(self, gunluk=False):
        rows = []
        for fn in sorted(os.listdir(self.log_dir)):
            if not fn.endswith('.csv'):
                continue
            if not gunluk and not fn.startswith('sinyaller_'):
                continue
            with open(os.path.join(self.log_dir, fn), 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    rows.append(row)
        if not rows:
            return {}

        total = len(rows)
        al = sum(1 for r in rows if r['signal'] == 'AL')
        bekle = total - al
        reasons = defaultdict(int)
        for r in rows:
            reasons[r.get('reason', '?')] += 1
        by_regime = defaultdict(lambda: {'al': 0, 'total': 0})
        for r in rows:
            regime = r.get('regime', '?')
            by_regime[regime]['total'] += 1
            if r['signal'] == 'AL':
                by_regime[regime]['al'] += 1

        completed = [r for r in rows if r.get('getiri_1g') != '']
        if completed:
            rets_1g = [float(r['getiri_1g']) for r in completed]
            avg_ret_1g = sum(rets_1g) / len(rets_1g) * 100
        else:
            avg_ret_1g = None

        return {
            'toplam_sinyal': total,
            'al': al,
            'bekle': bekle,
            'al_orani': round(al / total * 100, 1) if total else 0,
            'neden_dagilimi': dict(reasons),
            'rejim_dagilimi': dict(by_regime),
            'tamamlanan_getiri_ort': round(avg_ret_1g, 2) if avg_ret_1g else None,
            'tamamlanan_adet': len(completed),
        }

    def light_report(self, son_n=100):
        """Light monitoring: en kritik 4 metrik, full drift oncesi"""
        rows = []
        for fn in sorted(os.listdir(self.log_dir)):
            if not fn.endswith('.csv'):
                continue
            with open(os.path.join(self.log_dir, fn), 'r', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    rows.append(row)
        if not rows:
            return {}

        recent = rows[-son_n:] if len(rows) > son_n else rows
        total = len(recent)

        # 1. AL rate
        al = sum(1 for r in recent if r['signal'] == 'AL')
        al_orani = round(al / total * 100, 1) if total else 0

        # 2. GB mean (rolling, AL sinyalleri)
        gb_vals = []
        for r in recent:
            try:
                v = float(r['gb_proba'])
                if v > 0:
                    gb_vals.append(v)
            except (ValueError, TypeError):
                pass
        gb_mean = round(sum(gb_vals) / len(gb_vals), 4) if gb_vals else None
        gb_al_vals = [float(r['gb_proba']) for r in recent if r['signal'] == 'AL'
                      and _safe_float(r['gb_proba'])]
        gb_al_mean = round(sum(gb_al_vals) / len(gb_al_vals), 4) if gb_al_vals else None

        # 3. False BEKLE proxy: BEKLE kararlarinda gb_proba'nin 0.40-0.45 bandindaki adedi
        bekle_40_45 = 0
        for r in recent:
            if r['signal'] != 'BEKLE':
                continue
            try:
                p = float(r['gb_proba'])
                if 0.40 <= p <= 0.45:
                    bekle_40_45 += 1
            except (ValueError, TypeError):
                pass
        false_bekle_orani = round(bekle_40_45 / total * 100, 1) if total else 0

        # 4. Regime breakdown
        by_regime = {}
        for r in recent:
            rg = r.get('regime', '?')
            if rg not in by_regime:
                by_regime[rg] = {'total': 0, 'al': 0}
            by_regime[rg]['total'] += 1
            if r['signal'] == 'AL':
                by_regime[rg]['al'] += 1

        return {
            'sinyal_sayisi': total,
            'al_orani': al_orani,
            'gb_ort': gb_mean,
            'gb_al_ort': gb_al_mean,
            'false_bekle_40_45': bekle_40_45,
            'false_bekle_orani': false_bekle_orani,
            'rejim_dagilimi': {
                rg: f"{d['al']}/{d['total']} (%{round(d['al']/d['total']*100,1) if d['total'] else 0})"
                for rg, d in sorted(by_regime.items())
            },
        }


def _safe_float(v):
    try:
        return float(v) > 0
    except (ValueError, TypeError):
        return False


# Tekil global instance
_logger = None


def get_logger():
    global _logger
    if _logger is None:
        _logger = SignalLogger()
    return _logger
