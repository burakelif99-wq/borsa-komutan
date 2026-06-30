"""
karar_pipeline.py - v2.0 Role-Based Decision Pipeline

AI aday gosterir, risk katmani filtreler. Weighted score fusion yerine
role-based decision architecture.
"""

import numpy as np
from datetime import datetime


class DecisionPipeline:
    def __init__(self, model, logger=None):
        self.model = model
        self.logger = logger

    def karar_ver(self, ticker, data):
        detay = {}

        # --- Step 1: GB Candidate ---
        gb_result = self._gb_candidate(data, detay)
        if not gb_result:
            return self._sonuc('BEKLE', detay, 'GB_LOW', ticker)

        # --- Step 2: Risk Validation ---
        risk = self._risk_validasyon(data, detay)
        if not risk['pass']:
            return self._sonuc('BEKLE', detay, risk['reason'], ticker)

        # --- Step 3: AL ---
        return self._sonuc('AL', detay, 'GB_PASS', ticker)

    def _gb_candidate(self, data, detay):
        """GB modelinden AL adayi kontrolu"""
        from ai_egit import TeknikIndikatorler

        oz = TeknikIndikatorler.tum_ozellikler(data)
        if oz is None or len(oz) == 0:
            return False

        row = oz.iloc[[-1]].copy()
        for col in self.model.ozellik_isimleri:
            if col not in row.columns:
                row[col] = 0.0
        X = row[self.model.ozellik_isimleri].fillna(0).replace([np.inf, -np.inf], 0).values

        if self.model.scaler:
            X = self.model.scaler.transform(X)
        if self.model.secici:
            X = self.model.secici.transform(X)

        modeller = self.model.paket.get('modeller', {})
        gb = modeller.get('gradient_boosting')
        if gb is None:
            return False

        gb_p = gb.predict_proba(X)[0]
        gb_remap = self._remap_proba(gb_p, gb.classes_)
        gb_al = gb_remap[2]

        detay['gb_al'] = round(float(gb_al), 4)
        detay['gb_remap'] = gb_remap

        return gb_al >= self.model.al_esik

    def _risk_validasyon(self, data, detay):
        """Risk Validation Layer — her check bagimsiz, binary pass/fail"""
        checks = {}

        # 1. Likidite kontrolu
        checks['likidite'] = self._check_likidite(data)
        if not checks['likidite']:
            return {'pass': False, 'reason': 'LIKIDITE', 'checks': checks}

        # 2. Bear guard (rejim bazli RF filter)
        regime = getattr(self.model, '_regime_cache', 'sideways')
        detay['rejim'] = regime
        if regime == 'bear':
            checks['bear_guard'] = self._check_bear_guard(data)
            if not checks['bear_guard']:
                return {'pass': False, 'reason': 'RF_GUARD', 'checks': checks}

        # 3. ATR (volatilite siniri)
        checks['atr'] = self._check_atr(data)
        if not checks['atr']:
            return {'pass': False, 'reason': 'ATR_LIMIT', 'checks': checks}

        # 4. Veri kalitesi
        checks['veri'] = self._check_veri_kalitesi(data)
        if not checks['veri']:
            return {'pass': False, 'reason': 'VERI_KALITESI', 'checks': checks}

        detay['risk_checks'] = checks
        return {'pass': True, 'reason': None, 'checks': checks}

    def _check_likidite(self, data):
        volume = data['Volume']
        if len(volume) < 20:
            return False
        son_hacim = float(volume.iloc[-1])
        ortalama = float(volume.tail(20).mean())
        if ortalama <= 0:
            return False
        # Hacim ortalamanin en az %20'si kadar olmali
        return son_hacim >= ortalama * 0.20

    def _check_bear_guard(self, data):
        rf = self.model.paket.get('modeller', {}).get('random_forest')
        if rf is None:
            return True
        from ai_egit import TeknikIndikatorler
        oz = TeknikIndikatorler.tum_ozellikler(data)
        if oz is None:
            return True
        row = oz.iloc[[-1]].copy()
        for col in self.model.ozellik_isimleri:
            if col not in row.columns:
                row[col] = 0.0
        X = row[self.model.ozellik_isimleri].fillna(0).replace([np.inf, -np.inf], 0).values
        if self.model.scaler:
            X = self.model.scaler.transform(X)
        if self.model.secici:
            X = self.model.secici.transform(X)
        rf_p = rf.predict_proba(X)[0]
        rf_remap = self._remap_proba(rf_p, rf.classes_)
        rf_al = rf_remap[2]
        return rf_al >= 0.35

    def _check_atr(self, data):
        if len(data) < 14:
            return True
        high = data['High'].values.astype(float)
        low = data['Low'].values.astype(float)
        close = data['Close'].values.astype(float)
        tr = np.maximum(high[1:] - low[1:],
                        np.abs(high[1:] - close[:-1]),
                        np.abs(low[1:] - close[:-1]))
        atr = np.mean(tr[-14:])
        son_fiyat = float(close[-1])
        if son_fiyat <= 0:
            return True
        atr_orani = atr / son_fiyat
        # ATR fiyatin %10'undan fazlaysa cok volatil
        return atr_orani < 0.10

    def _check_veri_kalitesi(self, data):
        if len(data) < 30:
            return False
        # Son 5 barda NaN kontrolu
        if data[['Close', 'Volume']].tail(5).isna().any().any():
            return False
        # Gap kontrolu: gun ici %20'den fazla acilis farki
        if len(data) > 1:
            son_acilis = float(data['Open'].iloc[-1])
            onceki_kapanis = float(data['Close'].iloc[-2])
            if onceki_kapanis > 0:
                gap = abs(son_acilis / onceki_kapanis - 1)
                if gap > 0.20:
                    return False
        return True

    def _remap_proba(self, proba, classes):
        has_neg1 = -1 in classes or -1.0 in classes
        remapped = np.zeros(3)
        for i, c in enumerate(classes):
            if c in (-1.0, -1):
                remapped[0] = proba[i]
            elif c in (0.0, 0):
                remapped[1] = proba[i] if has_neg1 else remapped[0]
                remapped[0] = proba[i] if not has_neg1 else remapped[0]
            elif c in (1.0, 1):
                remapped[2] = proba[i]
            elif c in (2.0, 2):
                remapped[2] = proba[i]
        return remapped

    def _sonuc(self, etiket, detay, reason, ticker):
        return {
            'etiket': etiket,
            'guven': round(detay.get('gb_al', 0), 4),
            'detay': detay,
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
        }
