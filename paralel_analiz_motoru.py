#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Borsa Komutan v4.0 - RAPOR DIZINI Duzeltilmis
Raporlar: C:\\Users\\Administrator\\PycharmProjects\\PythonProject\\Kimi\\rapor
"""

import concurrent.futures
import threading
import time
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import warnings
import sys
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# === RAPOR DIZINI ===
RAPOR_DIZINI = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\rapor"
# Rapor dizini yoksa olustur
os.makedirs(RAPOR_DIZINI, exist_ok=True)

# LOG AYARI - Rapor dizinine kaydet
LOG_DOSYASI = os.path.join(RAPOR_DIZINI, f"analiz_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")

for logger_name in ['urllib3', 'requests']:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
    logging.getLogger(logger_name).propagate = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DOSYASI, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Rapor dizini: {RAPOR_DIZINI}")

try:
    from hisse_listesi import hisse_listesi
except ImportError:
    logger.warning("hisse_listesi.py bulunamadi!")
    hisse_listesi = []

# =============================================================================
# VERI KONTROLU (Duzeltilmis - Datetime hatasi giderildi)
# =============================================================================

class VeriKontrolu:
    @staticmethod
    def veri_guncel_mi(hist_df, max_gun=5):
        """Veri guncel mi? - Datetime hatasi giderildi"""
        if hist_df is None or hist_df.empty:
            return False

        try:
            son_tarih = hist_df.index[-1]

            # pd.Timestamp -> datetime
            if isinstance(son_tarih, pd.Timestamp):
                son_tarih = son_tarih.to_pydatetime()
            elif not isinstance(son_tarih, datetime):
                son_tarih = pd.to_datetime(son_tarih).to_pydatetime()

            # Timezone kaldır (naive yap)
            if son_tarih.tzinfo is not None:
                son_tarih = son_tarih.replace(tzinfo=None)

            # Bugun (naive)
            bugun = datetime.now().replace(tzinfo=None)

            # Tarih farki
            fark = (bugun - son_tarih).days

            if fark > max_gun:
                logger.warning(f"Veri eski! Son tarih: {son_tarih.date()}, {fark} gun once")
                return False

            return True

        except Exception as e:
            logger.warning(f"Tarih kontrolu hatasi: {e}")
            # Hata durumunda veriyi kullan (esnek)
            return True

    @staticmethod
    def gunluk_degisim(hist_df):
        if hist_df is None or len(hist_df) < 2:
            return 0
        close = hist_df['Close'].dropna()
        if len(close) < 2:
            return 0
        son = float(close.iloc[-1])
        onceki = float(close.iloc[-2])
        if onceki == 0:
            return 0
        return ((son - onceki) / onceki) * 100

# =============================================================================
# CACHE SISTEMI - Rapor dizinine
# =============================================================================

class CacheSistemi:
    def __init__(self, cache_dosyasi=None):
        if cache_dosyasi is None:
            cache_dosyasi = os.path.join(RAPOR_DIZINI, 'rapor/hisse_cache.json')
        self.cache_dosyasi = cache_dosyasi
        self.cache = {}
        self.lock = threading.Lock()
        self._yukle()

    def _yukle(self):
        if os.path.exists(self.cache_dosyasi):
            try:
                with open(self.cache_dosyasi, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                logger.info(f"Cache yuklendi: {len(self.cache)} hisse")
            except:
                self.cache = {}

    def kaydet(self, hisse_kodu, veri):
        with self.lock:
            if isinstance(veri, dict) and 'hist' in veri:
                try:
                    hist_dict = veri['hist'].to_dict() if isinstance(veri['hist'], pd.DataFrame) else veri['hist']
                    info_dict = veri['info'] if isinstance(veri['info'], dict) else {}
                    self.cache[hisse_kodu] = {
                        'hist': hist_dict,
                        'info': info_dict,
                        'kaynak': veri.get('kaynak', 'yfinance'),
                        'zaman': datetime.now().isoformat()
                    }
                except Exception as e:
                    logger.debug(f"Cache kayit hatasi {hisse_kodu}: {e}")

    def getir(self, hisse_kodu, max_yas_saat=24):
        with self.lock:
            if hisse_kodu in self.cache:
                kayit = self.cache[hisse_kodu]
                try:
                    kayit_zaman = datetime.fromisoformat(kayit['zaman'])
                    gecen = (datetime.now() - kayit_zaman).total_seconds() / 3600
                    if gecen < max_yas_saat:
                        if 'hist' in kayit and isinstance(kayit['hist'], dict):
                            hist_df = pd.DataFrame.from_dict(kayit['hist'])
                            if not hist_df.empty:
                                return {
                                    'hist': hist_df,
                                    'info': kayit.get('info', {}),
                                    'kaynak': kayit.get('kaynak', 'cache')
                                }
                except Exception as e:
                    logger.debug(f"Cache okuma hatasi {hisse_kodu}: {e}")
            return None

    def diske_kaydet(self):
        with self.lock:
            try:
                with open(self.cache_dosyasi, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, ensure_ascii=False, default=str)
                logger.info(f"Cache kaydedildi: {self.cache_dosyasi}")
            except Exception as e:
                logger.warning(f"Cache diske kayit hatasi: {e}")

# =============================================================================
# VERI CEKICI
# =============================================================================

class VeriCekici:
    def __init__(self, cache=None):
        self.rate_lock = threading.Lock()
        self.son_istek = 0
        self.min_bekleme = 2.0
        self.cache = cache or CacheSistemi()
        self.basarili_sayisi = 0
        self.hata_sayisi = 0

    def _rate_limit(self):
        with self.rate_lock:
            gecen = time.time() - self.son_istek
            if gecen < self.min_bekleme:
                time.sleep(self.min_bekleme - gecen)
            self.son_istek = time.time()

    def veri_cek(self, hisse_kodu: str, max_retry=3):
        import yfinance as yf

        for deneme in range(max_retry):
            try:
                self._rate_limit()

                ticker = yf.Ticker(f"{hisse_kodu}.IS")
                hist = ticker.history(period="10d", interval="1d")
                info = ticker.info

                if hist is None or hist.empty:
                    logger.debug(f"{hisse_kodu}: hist bos (deneme {deneme+1})")
                    if deneme < max_retry - 1:
                        time.sleep(2 * (deneme + 1))
                        continue
                    return None

                if len(hist) < 5:
                    logger.debug(f"{hisse_kodu}: hist yetersiz ({len(hist)})")
                    if deneme < max_retry - 1:
                        time.sleep(2 * (deneme + 1))
                        continue
                    return None

                # Veri guncel mi? (HATA GIDERILDI)
                try:
                    if not VeriKontrolu.veri_guncel_mi(hist, max_gun=5):
                        logger.warning(f"{hisse_kodu}: Veri eski")
                        if deneme < max_retry - 1:
                            time.sleep(3 * (deneme + 1))
                            continue
                except Exception as e:
                    logger.debug(f"{hisse_kodu}: Tarih kontrolu hatasi, devam: {e}")

                if info is None or not isinstance(info, dict):
                    info = {}

                if not isinstance(hist, pd.DataFrame):
                    logger.debug(f"{hisse_kodu}: hist DataFrame degil")
                    if deneme < max_retry - 1:
                        time.sleep(2 * (deneme + 1))
                        continue
                    return None

                veri = {'hist': hist, 'info': info, 'kaynak': 'yfinance'}
                self.cache.kaydet(hisse_kodu, veri)
                self.basarili_sayisi += 1
                return veri

            except Exception as e:
                logger.debug(f"{hisse_kodu} deneme {deneme+1}: {str(e)[:100]}")
                if deneme < max_retry - 1:
                    time.sleep(3 * (deneme + 1))
                else:
                    logger.warning(f"{hisse_kodu}: yfinance veri alinamadi - {str(e)[:100]}")

        self.hata_sayisi += 1
        return None

# =============================================================================
# TEKNIK ANALIZ
# =============================================================================

class TeknikAnaliz:
    def analiz_et(self, hisse_kodu, veri):
        try:
            if not isinstance(veri, dict) or 'hist' not in veri:
                return self._dummy(hisse_kodu, "Veri yok")

            hist = veri['hist']
            if not isinstance(hist, pd.DataFrame) or hist.empty:
                return self._dummy(hisse_kodu, "DataFrame bos")

            if 'Close' not in hist.columns or 'Volume' not in hist.columns:
                return self._dummy(hisse_kodu, "Close/Volume yok")

            # Veri guncel mi? (HATA GIDERILDI - try/except)
            try:
                if not VeriKontrolu.veri_guncel_mi(hist, max_gun=5):
                    return self._dummy(hisse_kodu, "Veri eski")
            except Exception as e:
                logger.debug(f"{hisse_kodu}: Tarih kontrolu hatasi, devam: {e}")

            kapanis = hist['Close'].dropna().values
            hacim = hist['Volume'].dropna().values

            if len(kapanis) < 5:
                return self._dummy(hisse_kodu, f"Yetersiz veri ({len(kapanis)})")

            son_fiyat = float(kapanis[-1])
            fiyat_5_gun_once = float(kapanis[-5]) if len(kapanis) >= 5 else son_fiyat

            momentum_5 = ((son_fiyat - fiyat_5_gun_once) / fiyat_5_gun_once) * 100 if fiyat_5_gun_once > 0 else 0
            gunluk_degisim = VeriKontrolu.gunluk_degisim(hist)

            sma_5 = float(np.mean(kapanis[-5:]))
            sma_20 = float(np.mean(kapanis[-20:])) if len(kapanis) >= 20 else sma_5

            kisa_trend = 'YUKARI' if sma_5 > sma_20 else 'ASAGI'

            hacim_5 = float(np.mean(hacim[-5:])) if len(hacim) >= 5 else 0
            hacim_20 = float(np.mean(hacim[-20:])) if len(hacim) >= 20 else hacim_5
            hacim_trendi = 'ARTAN' if hacim_5 > hacim_20 * 1.2 else 'AZALAN' if hacim_5 < hacim_20 * 0.8 else 'STABIL'

            if gunluk_degisim > 0 and hacim_trendi == 'ARTAN':
                hacim_fiyat_uyumu = 'GUC_YUKARI'
            elif gunluk_degisim > 0 and hacim_trendi == 'AZALAN':
                hacim_fiyat_uyumu = 'ZAYIF_YUKARI'
            elif gunluk_degisim < 0 and hacim_trendi == 'ARTAN':
                hacim_fiyat_uyumu = 'GUC_DUSUS'
            elif gunluk_degisim < 0 and hacim_trendi == 'AZALAN':
                hacim_fiyat_uyumu = 'ZAYIF_DUSUS'
            else:
                hacim_fiyat_uyumu = 'NOTR'

            rsi = 50
            if len(kapanis) >= 15:
                deltas = np.diff(kapanis)
                gains = deltas[deltas > 0]
                losses = -deltas[deltas < 0]
                avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else (np.mean(gains) if len(gains) > 0 else 0)
                avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else (np.mean(losses) if len(losses) > 0 else 1)
                if avg_loss == 0: avg_loss = 1
                rsi = 100 - (100 / (1 + avg_gain/avg_loss))

            skor = 50

            if momentum_5 > 5: skor += 20
            elif momentum_5 > 2: skor += 15
            elif momentum_5 > 0: skor += 10
            elif momentum_5 < -5: skor -= 20
            elif momentum_5 < -2: skor -= 15
            elif momentum_5 < 0: skor -= 10

            if gunluk_degisim > 3: skor += 10
            elif gunluk_degisim > 1: skor += 5
            elif gunluk_degisim < -3: skor -= 10
            elif gunluk_degisim < -1: skor -= 5

            if hacim_fiyat_uyumu == 'GUC_YUKARI': skor += 15
            elif hacim_fiyat_uyumu == 'ZAYIF_YUKARI': skor += 5
            elif hacim_fiyat_uyumu == 'GUC_DUSUS': skor -= 15
            elif hacim_fiyat_uyumu == 'ZAYIF_DUSUS': skor -= 5

            if kisa_trend == 'YUKARI': skor += 5
            elif kisa_trend == 'ASAGI': skor -= 5

            if 40 < rsi < 60: skor += 3
            elif rsi > 70: skor -= 5
            elif rsi < 30: skor += 5

            skor = min(100, max(0, skor))

            if skor >= 80: sinyal = 'GUC_AL'
            elif skor >= 65: sinyal = 'AL'
            elif skor >= 50: sinyal = 'IZLE'
            elif skor >= 35: sinyal = 'SAT'
            else: sinyal = 'GUC_SAT'

            return {
                'son_fiyat': round(son_fiyat, 2),
                'momentum_5': round(momentum_5, 2),
                'gunluk_degisim': round(gunluk_degisim, 2),
                'sma_5': round(sma_5, 2),
                'sma_20': round(sma_20, 2),
                'kisa_trend': kisa_trend,
                'rsi': round(float(rsi), 2),
                'hacim_trendi': hacim_trendi,
                'hacim_fiyat_uyumu': hacim_fiyat_uyumu,
                'skor': skor,
                'sinyal': sinyal
            }

        except Exception as e:
            logger.error(f"{hisse_kodu} teknik analiz HATA: {e}")
            return self._dummy(hisse_kodu, str(e))

    def _dummy(self, hisse_kodu, hata=""):
        return {
            'son_fiyat': 0, 'momentum_5': 0, 'gunluk_degisim': 0,
            'sma_5': 0, 'sma_20': 0, 'kisa_trend': 'BELIRSIZ',
            'rsi': 50, 'hacim_trendi': 'NORMAL', 'hacim_fiyat_uyumu': 'NOTR',
            'skor': 50, 'sinyal': 'IZLE', 'hata': hata
        }

# =============================================================================
# TEMEL ANALIZ
# =============================================================================

class TemelAnaliz:
    def analiz_et(self, hisse_kodu, veri):
        try:
            if not isinstance(veri, dict) or 'info' not in veri:
                return {'skor': 50, 'sinyal': 'IZLE'}

            info = veri['info']
            if not isinstance(info, dict):
                return {'skor': 50, 'sinyal': 'IZLE'}

            f_k = info.get('trailingPE') or info.get('forwardPE') or 0
            pd_dd = info.get('priceToBook') or 0
            roe = info.get('returnOnEquity') or 0
            kar_marji = info.get('profitMargins') or 0

            skor = 50
            if roe and roe > 0.20: skor += 20
            elif roe and roe > 0.15: skor += 15
            elif roe and roe > 0.10: skor += 10
            elif roe and roe < 0: skor -= 15

            if kar_marji and kar_marji > 0.30: skor += 15
            elif kar_marji and kar_marji > 0.20: skor += 10
            elif kar_marji and kar_marji > 0.10: skor += 5
            elif kar_marji and kar_marji < 0: skor -= 15

            if f_k and 5 < f_k < 15: skor += 10
            elif f_k and 15 < f_k < 25: skor += 5
            elif f_k and f_k > 50: skor -= 10
            elif f_k and f_k < 3: skor -= 10

            if pd_dd and 0.5 < pd_dd < 2: skor += 10
            elif pd_dd and pd_dd > 5: skor -= 10
            elif pd_dd and pd_dd < 0.3: skor -= 10

            skor = min(100, max(0, skor))

            if skor >= 80: sinyal = 'GUC_AL'
            elif skor >= 65: sinyal = 'AL'
            elif skor >= 50: sinyal = 'IZLE'
            elif skor >= 35: sinyal = 'SAT'
            else: sinyal = 'GUC_SAT'

            return {
                'f_k_orani': round(float(f_k), 2) if f_k else 0,
                'pd_dd': round(float(pd_dd), 2) if pd_dd else 0,
                'roe': round(float(roe) * 100, 2) if roe else 0,
                'kar_marji': round(float(kar_marji) * 100, 2) if kar_marji else 0,
                'skor': skor,
                'sinyal': sinyal
            }
        except Exception as e:
            logger.error(f"{hisse_kodu} temel analiz HATA: {e}")
            return {'skor': 50, 'sinyal': 'IZLE'}

# =============================================================================
# YATIRIMCI ANALIZI
# =============================================================================

class YatirimciAnalizi:
    def analiz_et(self, hisse_kodu, veri):
        try:
            if not isinstance(veri, dict) or 'hist' not in veri:
                return {'skor': 50, 'sinyal': 'IZLE'}

            hist = veri['hist']
            if not isinstance(hist, pd.DataFrame) or hist.empty:
                return {'skor': 50, 'sinyal': 'IZLE'}

            if 'Volume' not in hist.columns or 'Close' not in hist.columns:
                return {'skor': 50, 'sinyal': 'IZLE'}

            hacim = hist['Volume'].dropna().values
            fiyat = hist['Close'].dropna().values

            if len(hacim) < 5 or len(fiyat) < 5:
                return {'skor': 50, 'sinyal': 'IZLE'}

            hacim_5 = float(np.mean(hacim[-5:]))
            hacim_20 = float(np.mean(hacim[-20:])) if len(hacim) >= 20 else hacim_5
            hacim_trendi = 'ARTAN' if hacim_5 > hacim_20 * 1.2 else 'AZALAN' if hacim_5 < hacim_20 * 0.8 else 'STABIL'

            fiyat_yonu = 'YUKSELIS' if fiyat[-1] > fiyat[-5] else 'DUSUS'

            if fiyat_yonu == 'YUKSELIS' and hacim_trendi == 'ARTAN':
                uyum = 'GUC_YUKARI'; skor = 85
            elif fiyat_yonu == 'YUKSELIS' and hacim_trendi == 'STABIL':
                uyum = 'YUKARI'; skor = 70
            elif fiyat_yonu == 'DUSUS' and hacim_trendi == 'ARTAN':
                uyum = 'GUC_DUSUS'; skor = 25
            elif fiyat_yonu == 'DUSUS' and hacim_trendi == 'STABIL':
                uyum = 'DUSUS'; skor = 35
            else:
                uyum = 'NOTR'; skor = 50

            if skor >= 80: sinyal = 'GUC_AL'
            elif skor >= 65: sinyal = 'AL'
            elif skor >= 50: sinyal = 'IZLE'
            elif skor >= 35: sinyal = 'SAT'
            else: sinyal = 'GUC_SAT'

            return {
                'hacim_trendi': hacim_trendi,
                'fiyat_yonu': fiyat_yonu,
                'hacim_fiyat_uyumu': uyum,
                'skor': skor,
                'sinyal': sinyal
            }
        except Exception as e:
            logger.error(f"{hisse_kodu} yatirimci analiz HATA: {e}")
            return {'skor': 50, 'sinyal': 'IZLE'}

# =============================================================================
# RISK ANALIZI
# =============================================================================

class RiskAnalizi:
    def analiz_et(self, hisse_kodu, veri):
        try:
            if not isinstance(veri, dict) or 'hist' not in veri:
                return {'skor': 50, 'sinyal': 'IZLE'}

            hist = veri['hist']
            if not isinstance(hist, pd.DataFrame) or hist.empty:
                return {'skor': 50, 'sinyal': 'IZLE'}

            if 'Close' not in hist.columns:
                return {'skor': 50, 'sinyal': 'IZLE'}

            fiyat = hist['Close'].dropna().values
            if len(fiyat) < 20:
                return {'skor': 50, 'sinyal': 'IZLE'}

            getiriler = np.diff(fiyat) / fiyat[:-1]
            volatilite = float(np.std(getiriler) * np.sqrt(252) * 100)

            zirve = float(np.max(fiyat[-60:])) if len(fiyat) >= 60 else float(np.max(fiyat))
            simdiki = float(fiyat[-1])
            max_dusus = ((zirve - simdiki) / zirve) * 100 if zirve > 0 else 0

            skor = 50
            if 20 < volatilite < 40: skor += 15
            elif 40 < volatilite < 60: skor += 5
            elif volatilite > 80: skor -= 20
            elif volatilite < 10: skor -= 10

            if max_dusus > 30: skor += 15
            elif max_dusus > 20: skor += 10
            elif max_dusus < 5: skor -= 15

            skor = min(100, max(0, skor))

            if skor >= 80: sinyal = 'GUC_AL'
            elif skor >= 65: sinyal = 'AL'
            elif skor >= 50: sinyal = 'IZLE'
            elif skor >= 35: sinyal = 'SAT'
            else: sinyal = 'GUC_SAT'

            return {
                'volatilite_yillik': round(volatilite, 2),
                'max_dusus_60gun': round(max_dusus, 2),
                'skor': skor,
                'sinyal': sinyal
            }
        except Exception as e:
            logger.error(f"{hisse_kodu} risk analiz HATA: {e}")
            return {'skor': 50, 'sinyal': 'IZLE'}

# =============================================================================
# MAKRO ANALIZ
# =============================================================================

class MakroAnaliz:
    def analiz_et(self, hisse_kodu, veri):
        try:
            if not isinstance(veri, dict) or 'info' not in veri:
                return {'skor': 50, 'sinyal': 'IZLE'}

            info = veri['info']
            if not isinstance(info, dict):
                return {'skor': 50, 'sinyal': 'IZLE'}

            sektor = info.get('sector', '')
            guclu = ['Technology', 'Financial Services', 'Healthcare', 'Consumer Cyclical']
            zayif = ['Utilities', 'Real Estate', 'Energy']

            skor = 50
            if sektor in guclu: skor += 15
            elif sektor in zayif: skor -= 10

            skor = min(100, max(0, skor))

            if skor >= 65: sinyal = 'AL'
            elif skor >= 50: sinyal = 'IZLE'
            else: sinyal = 'SAT'

            return {'sektor': sektor, 'skor': skor, 'sinyal': sinyal}
        except Exception as e:
            logger.error(f"{hisse_kodu} makro analiz HATA: {e}")
            return {'skor': 50, 'sinyal': 'IZLE'}

# =============================================================================
# ENSEMBLE MOTOR
# =============================================================================

class EnsembleMotor:
    def __init__(self):
        self.agirliklar = {
            'teknik': 0.40,
            'yatirimci': 0.25,
            'temel': 0.15,
            'risk': 0.15,
            'makro': 0.05
        }

    def hesapla(self, teknik, temel, yatirimci, risk, makro):
        sinyal_puan = {'GUC_AL': 100, 'AL': 80, 'IZLE': 50, 'SAT': 30, 'GUC_SAT': 10}

        teknik_puan = sinyal_puan.get(teknik.get('sinyal', 'IZLE'), 50)
        yatirimci_puan = sinyal_puan.get(yatirimci.get('sinyal', 'IZLE'), 50)
        temel_puan = sinyal_puan.get(temel.get('sinyal', 'IZLE'), 50)
        risk_puan = sinyal_puan.get(risk.get('sinyal', 'IZLE'), 50)
        makro_puan = sinyal_puan.get(makro.get('sinyal', 'IZLE'), 50)

        skor = (
            teknik_puan * self.agirliklar['teknik'] +
            yatirimci_puan * self.agirliklar['yatirimci'] +
            temel_puan * self.agirliklar['temel'] +
            risk_puan * self.agirliklar['risk'] +
            makro_puan * self.agirliklar['makro']
        )

        skor = round(skor, 2)

        if teknik.get('sinyal') in ['SAT', 'GUC_SAT']:
            skor = min(skor, 40)

        if teknik.get('sinyal') == 'GUC_AL':
            skor = max(skor, 75)

        if yatirimci.get('sinyal') in ['SAT', 'GUC_SAT']:
            skor = min(skor, 45)

        if skor >= 85: sinyal = 'GUC_AL'
        elif skor >= 70: sinyal = 'AL'
        elif skor >= 50: sinyal = 'IZLE'
        elif skor >= 30: sinyal = 'SAT'
        else: sinyal = 'GUC_SAT'

        return skor, sinyal

# =============================================================================
# PARALEL MOTOR - Rapor dizini destegi
# =============================================================================

class ParalelAnalizMotoru:
    def __init__(self, worker_sayisi=1, timeout=60):
        self.worker_sayisi = worker_sayisi
        self.timeout = timeout
        self.baslangic = None

        self.cache = CacheSistemi()
        self.veri_cekici = VeriCekici(cache=self.cache)
        self.teknik = TeknikAnaliz()
        self.temel = TemelAnaliz()
        self.yatirimci = YatirimciAnalizi()
        self.risk = RiskAnalizi()
        self.makro = MakroAnaliz()
        self.ensemble = EnsembleMotor()

        self.sonuc_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.analiz_sonuclari = {}
        self.hata_listesi = []
        self.islenen = 0

    def _progress(self, hisse_kodu, durum="OK"):
        with self.progress_lock:
            self.islenen += 1
            kalan = len(hisse_listesi) - self.islenen
            yuzde = (self.islenen / len(hisse_listesi)) * 100
            gecen = time.time() - self.baslangic

            tahmini = gecen / (self.islenen / len(hisse_listesi)) if self.islenen > 0 else 0
            kalan_sure = tahmini - gecen

            logger.info(
                f"[{self.islenen:3d}/{len(hisse_listesi)}] %{yuzde:5.1f} | "
                f"{hisse_kodu:6s} {durum} | Kalan: {kalan:3d} | "
                f"Tahmini: {kalan_sure/60:4.1f} dk"
            )

    def hisse_analiz_et(self, hisse_kodu):
        try:
            veri = self.veri_cekici.veri_cek(hisse_kodu)
            if veri is None:
                # Dummy degerler ile devam et
                teknik = self.teknik._dummy(hisse_kodu, "Veri cekilemedi")
                temel = {'skor': 50, 'sinyal': 'IZLE'}
                yatirimci = {'skor': 50, 'sinyal': 'IZLE'}
                risk = {'skor': 50, 'sinyal': 'IZLE'}
                makro = {'skor': 50, 'sinyal': 'IZLE'}

                ensemble_skor, ensemble_sinyal = self.ensemble.hesapla(teknik, temel, yatirimci, risk, makro)

                sonuc = {
                    'hisse_kodu': hisse_kodu,
                    'zaman_damgasi': datetime.now().isoformat(),
                    'teknik': teknik,
                    'temel': temel,
                    'yatirimci': yatirimci,
                    'risk': risk,
                    'makro': makro,
                    'ensemble_skor': ensemble_skor,
                    'ensemble_sinyal': ensemble_sinyal,
                    'status': 'VERI_YOK',
                    'kaynak': 'dummy'
                }

                with self.sonuc_lock:
                    self.analiz_sonuclari[hisse_kodu] = sonuc

                self._progress(hisse_kodu, "VERI_YOK")
                return sonuc

            teknik = self.teknik.analiz_et(hisse_kodu, veri)
            temel = self.temel.analiz_et(hisse_kodu, veri)
            yatirimci = self.yatirimci.analiz_et(hisse_kodu, veri)
            risk = self.risk.analiz_et(hisse_kodu, veri)
            makro = self.makro.analiz_et(hisse_kodu, veri)

            ensemble_skor, ensemble_sinyal = self.ensemble.hesapla(teknik, temel, yatirimci, risk, makro)

            sonuc = {
                'hisse_kodu': hisse_kodu,
                'zaman_damgasi': datetime.now().isoformat(),
                'teknik': teknik,
                'temel': temel,
                'yatirimci': yatirimci,
                'risk': risk,
                'makro': makro,
                'ensemble_skor': ensemble_skor,
                'ensemble_sinyal': ensemble_sinyal,
                'status': 'OK',
                'kaynak': veri.get('kaynak', 'yfinance')
            }

            with self.sonuc_lock:
                self.analiz_sonuclari[hisse_kodu] = sonuc

            self._progress(hisse_kodu, f"OK [{ensemble_sinyal}]")
            return sonuc

        except Exception as e:
            logger.warning(f"{hisse_kodu}: HATA - {str(e)[:50]}")
            with self.sonuc_lock:
                self.hata_listesi.append(hisse_kodu)
                self.analiz_sonuclari[hisse_kodu] = {
                    'hisse_kodu': hisse_kodu, 'status': 'HATA', 'hata_mesaji': str(e)
                }
            self._progress(hisse_kodu, "HATA")
            return self.analiz_sonuclari[hisse_kodu]

    def tum_hisseleri_analiz_et(self):
        self.baslangic = time.time()
        logger.info("=" * 70)
        logger.info(f"RAPOR DIZINI: {RAPOR_DIZINI}")
        logger.info(f"ANALIZ BASLADI | Worker: {self.worker_sayisi} | Hedef: {len(hisse_listesi)} hisse")
        logger.info("=" * 70)

        for hisse in hisse_listesi:
            self.hisse_analiz_et(hisse)

        self.cache.diske_kaydet()

        return self._rapor(time.time() - self.baslangic)

    def _rapor(self, sure):
        basarili = sum(1 for s in self.analiz_sonuclari.values() if s.get('status') == 'OK')
        veri_yok = sum(1 for s in self.analiz_sonuclari.values() if s.get('status') == 'VERI_YOK')
        hatali = len(self.hata_listesi)

        al_sinyalleri = [s for s in self.analiz_sonuclari.values() if s.get('status') in ['OK', 'VERI_YOK'] and s.get('ensemble_sinyal') in ['AL', 'GUC_AL']]
        sat_sinyalleri = [s for s in self.analiz_sonuclari.values() if s.get('status') in ['OK', 'VERI_YOK'] and s.get('ensemble_sinyal') in ['SAT', 'GUC_SAT']]

        al_sirali = sorted(al_sinyalleri, key=lambda x: x['ensemble_skor'], reverse=True)
        sat_sirali = sorted(sat_sinyalleri, key=lambda x: x['ensemble_skor'])

        rapor = {
            'meta': {
                'tarih': datetime.now().isoformat(),
                'toplam_hisse': len(hisse_listesi),
                'basarili': basarili,
                'veri_yok': veri_yok,
                'hatali': hatali,
                'al_sinyali': len(al_sinyalleri),
                'sat_sinyali': len(sat_sinyalleri),
                'toplam_sure_dk': round(sure / 60, 2),
                'toplam_sure_sn': round(sure, 2),
                'ortalama_sure_sn': round(sure / len(hisse_listesi), 2) if len(hisse_listesi) > 0 else 0,
                'worker_sayisi': self.worker_sayisi,
                'veri_basarili': self.veri_cekici.basarili_sayisi,
                'veri_hata': self.veri_cekici.hata_sayisi
            },
            'al_listesi': al_sirali[:20],
            'sat_listesi': sat_sirali[:20],
            'hata_listesi': self.hata_listesi,
            'tum_sonuclar': self.analiz_sonuclari
        }

        # Rapor dizinine kaydet
        zaman_damgasi = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_dosya = os.path.join(RAPOR_DIZINI, f"analiz_raporu_{zaman_damgasi}.json")
        txt_dosya = os.path.join(RAPOR_DIZINI, f"analiz_raporu_{zaman_damgasi}.txt")

        # JSON kaydet
        with open(json_dosya, 'w', encoding='utf-8') as f:
            json.dump(rapor, f, ensure_ascii=False, indent=2, default=str)

        # TXT rapor kaydet
        with open(txt_dosya, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("BORSA KOMUTAN v4.0 - ANALIZ RAPORU\n")
            f.write("=" * 70 + "\n")
            f.write(f"Tarih: {datetime.now().isoformat()}\n")
            f.write(f"Rapor Dizini: {RAPOR_DIZINI}\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Toplam Sure:     {sure/60:6.1f} dk ({sure:.1f} sn)\n")
            f.write(f"Basarili:        {basarili:6d} hisse\n")
            f.write(f"Veri Yok:        {veri_yok:6d} hisse\n")
            f.write(f"Hatali:          {hatali:6d} hisse\n")
            f.write(f"Ortalama:        {sure/len(hisse_listesi):6.2f} sn/hisse\n")
            f.write(f"Worker:          {self.worker_sayisi:6d}\n")
            f.write(f"Veri Basarili:   {self.veri_cekici.basarili_sayisi}\n")
            f.write(f"Veri Hata:       {self.veri_cekici.hata_sayisi}\n")
            f.write("=" * 70 + "\n\n")

            f.write("AL SINYALLERI (Top 20)\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Sira':<5} {'Hisse':<8} {'Skor':<8} {'Sinyal':<10} {'Fiyat':<10} {'M5%':<8} {'Gun%':<8} {'HF':<12}\n")
            f.write("-" * 70 + "\n")

            for i, s in enumerate(al_sirali[:20], 1):
                t = s['teknik']
                f.write(f"{i:<5} {s['hisse_kodu']:<8} {s['ensemble_skor']:<8.1f} "
                       f"{s['ensemble_sinyal']:<10} {t.get('son_fiyat', 0):<10.2f} "
                       f"{t.get('momentum_5', 0):<8.2f} {t.get('gunluk_degisim', 0):<8.2f} "
                       f"{t.get('hacim_fiyat_uyumu', 'NOTR'):<12}\n")

            f.write("\nSAT SINYALLERI (Top 20)\n")
            f.write("-" * 70 + "\n")
            f.write(f"{'Sira':<5} {'Hisse':<8} {'Skor':<8} {'Sinyal':<10} {'Fiyat':<10} {'M5%':<8} {'Gun%':<8} {'HF':<12}\n")
            f.write("-" * 70 + "\n")

            for i, s in enumerate(sat_sirali[:20], 1):
                t = s['teknik']
                f.write(f"{i:<5} {s['hisse_kodu']:<8} {s['ensemble_skor']:<8.1f} "
                       f"{s['ensemble_sinyal']:<10} {t.get('son_fiyat', 0):<10.2f} "
                       f"{t.get('momentum_5', 0):<8.2f} {t.get('gunluk_degisim', 0):<8.2f} "
                       f"{t.get('hacim_fiyat_uyumu', 'NOTR'):<12}\n")

            f.write("=" * 70 + "\n")

            if hatali > 0:
                f.write(f"\nHATALI ({hatali}): {', '.join(self.hata_listesi[:10])}\n")
                if hatali > 10: f.write(f"... ve {hatali-10} diger\n")

        logger.info(f"Rapor kaydedildi: {json_dosya}")
        logger.info(f"Rapor kaydedildi: {txt_dosya}")

        self._ozet_yazdir(sure, basarili, veri_yok, hatali, al_sirali, sat_sirali, json_dosya)
        return rapor

    def _ozet_yazdir(self, sure, basarili, veri_yok, hatali, al_listesi, sat_listesi, dosya):
        print("\n" + "=" * 70)
        print("ANALIZ TAMAMLANDI")
        print("=" * 70)
        print(f"Rapor Dizini:    {RAPOR_DIZINI}")
        print(f"Toplam Sure:     {sure/60:6.1f} dk ({sure:.1f} sn)")
        print(f"Basarili:        {basarili:6d} hisse")
        print(f"Veri Yok:        {veri_yok:6d} hisse")
        print(f"Hatali:          {hatali:6d} hisse")
        print(f"Ortalama:        {sure/len(hisse_listesi):6.2f} sn/hisse")
        print(f"Worker:          {self.worker_sayisi:6d}")
        print(f"Veri Basarili:   {self.veri_cekici.basarili_sayisi}")
        print(f"Veri Hata:       {self.veri_cekici.hata_sayisi}")
        print(f"JSON Rapor:      {dosya}")
        print(f"TXT Rapor:       {dosya.replace('.json', '.txt')}")
        print("=" * 70)

        print("\n🟢 AL SINYALLERI (Top 20)")
        print("-" * 70)
        print(f"{'Sira':<5} {'Hisse':<8} {'Skor':<8} {'Sinyal':<10} {'Fiyat':<10} {'M5%':<8} {'Gun%':<8} {'HF':<12}")
        print("-" * 70)

        for i, s in enumerate(al_listesi[:20], 1):
            t = s['teknik']
            print(f"{i:<5} {s['hisse_kodu']:<8} {s['ensemble_skor']:<8.1f} "
                  f"{s['ensemble_sinyal']:<10} {t.get('son_fiyat', 0):<10.2f} "
                  f"{t.get('momentum_5', 0):<8.2f} {t.get('gunluk_degisim', 0):<8.2f} "
                  f"{t.get('hacim_fiyat_uyumu', 'NOTR'):<12}")

        print("\n🔴 SAT SINYALLERI (Top 20)")
        print("-" * 70)
        print(f"{'Sira':<5} {'Hisse':<8} {'Skor':<8} {'Sinyal':<10} {'Fiyat':<10} {'M5%':<8} {'Gun%':<8} {'HF':<12}")
        print("-" * 70)

        for i, s in enumerate(sat_listesi[:20], 1):
            t = s['teknik']
            print(f"{i:<5} {s['hisse_kodu']:<8} {s['ensemble_skor']:<8.1f} "
                  f"{s['ensemble_sinyal']:<10} {t.get('son_fiyat', 0):<10.2f} "
                  f"{t.get('momentum_5', 0):<8.2f} {t.get('gunluk_degisim', 0):<8.2f} "
                  f"{t.get('hacim_fiyat_uyumu', 'NOTR'):<12}")

        print("=" * 70)

        if hatali > 0:
            print(f"\nHATALI ({hatali}): {', '.join(self.hata_listesi[:10])}")
            if hatali > 10: print(f"... ve {hatali-10} diger")

if __name__ == "__main__":
    try:
        import yfinance, pandas, numpy
    except ImportError as e:
        print("pip install yfinance pandas numpy")
        sys.exit(1)

    motor = ParalelAnalizMotoru(worker_sayisi=1)
    sonuclar = motor.tum_hisseleri_analiz_et()