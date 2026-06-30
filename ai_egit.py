#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BORSA KOMUTAN v4.3 — AI Modeli Eğitimi
=======================================
535 hisse için özellik mühendisliği + ML modeli eğitimi
Sınıflandırma: AL(1), BEKLE(0), SAT(-1)
Hedef: 5 gün sonraki getiri > %2 = AL, < -%2 = SAT, arası = BEKLE

Çalıştırma:
    python ai_egit.py
    python ai_egit.py --hisse AEFES  # Tek hisse için debug
    python ai_egit.py --tune         # Hiperparametre optimizasyonu
"""

import os
import sys
import glob
import argparse
import warnings
import joblib
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================
# KÜTÜPHANE KONTROLÜ VE IMPORT
# ============================================
KUTUPHANE_DURUM = {}


def kutuphane_kontrol():
    """Gerekli kütüphaneleri kontrol et, eksikse bilgilendir."""
    global KUTUPHANE_DURUM

    kutuphaneler = {
        'sklearn': ('scikit-learn', 'pip install scikit-learn'),
        'lightgbm': ('lightgbm', 'pip install lightgbm'),
        'xgboost': ('xgboost', 'pip install xgboost'),
    }

    for modul, (paket, kurulum) in kutuphaneler.items():
        try:
            __import__(modul)
            KUTUPHANE_DURUM[modul] = True
            print(f"  ✅ {paket} — Kurulu")
        except ImportError:
            KUTUPHANE_DURUM[modul] = False
            print(f"  ❌ {paket} — EKSİK! Kur: {kurulum}")

    if not any(KUTUPHANE_DURUM.values()):
        print("\n⛔ HATA: En az bir ML kütüphanesi gerekli!")
        print("   pip install scikit-learn lightgbm xgboost")
        sys.exit(1)

    return KUTUPHANE_DURUM


# Lazy import (kontrolden sonra)
def ml_importlari_yukle():
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit, cross_val_score
    from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
    from sklearn.feature_selection import SelectKBest, f_classif

    global RandomForestClassifier, GradientBoostingClassifier
    global StandardScaler, TimeSeriesSplit, cross_val_score
    global classification_report, confusion_matrix, accuracy_score
    global SelectKBest, f_classif

    if KUTUPHANE_DURUM.get('lightgbm'):
        import lightgbm as lgb
        global lgb

    if KUTUPHANE_DURUM.get('xgboost'):
        import xgboost as xgb
        global xgb


# ============================================
# YAPILANDIRMA
# ============================================
class Config:
    """Proje yapılandırması"""

    # Veri yolları
    VERI_KLASORU = Path(r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\veri")
    MODEL_KLASORU = Path(r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\modeller")
    RAPOR_KLASORU = Path(r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\rapor")

    # Hedef parametreler
    HEDEF_GUN = 5  # Kaç gün sonrası için tahmin
    AL_ESIK = 0.02  # %2 üstü = AL
    SAT_ESIK = -0.02  # %-2 altı = SAT

    # Model parametreleri
    TEST_ORANI = 0.2  # Son %20 test seti
    MIN_VERI = 100  # Minimum veri noktası (teknik indikatörler için)
    RANDOM_STATE = 42

    # Özellik seçimi
    MAX_OZELLIK = 30  # En iyi N özellik

    # Ensemble ağırlıkları (modeller varsa)
    AGIRLIKLAR = {
        'lightgbm': 0.4,
        'xgboost': 0.35,
        'random_forest': 0.25
    }


# ============================================
# TEKNİK İNDİKATÖRLER (Özellik Mühendisliği)
# ============================================
class TeknikIndikatorler:
    """Hisse verilerinden teknik özellikler üretir"""

    @staticmethod
    def rsi(seri, periyot=14):
        """Relative Strength Index"""
        delta = seri.diff()
        kazan = delta.where(delta > 0, 0).rolling(window=periyot).mean()
        kayip = (-delta.where(delta < 0, 0)).rolling(window=periyot).mean()
        rs = kazan / kayip
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(seri, hizli=12, yavas=26, sinyal=9):
        """MACD ve sinyal çizgisi"""
        ema_hizli = seri.ewm(span=hizli).mean()
        ema_yavas = seri.ewm(span=yavas).mean()
        macd_cizgi = ema_hizli - ema_yavas
        sinyal_cizgi = macd_cizgi.ewm(span=sinyal).mean()
        return macd_cizgi, sinyal_cizgi

    @staticmethod
    def bollinger_bantlari(seri, periyot=20, carpma=2):
        """Bollinger Bantları"""
        ortalama = seri.rolling(window=periyot).mean()
        std = seri.rolling(window=periyot).std()
        ust = ortalama + (std * carpma)
        alt = ortalama - (std * carpma)
        return ortalama, ust, alt

    @staticmethod
    def hareketli_ortalama(seri, periyot):
        """SMA"""
        return seri.rolling(window=periyot).mean()

    @staticmethod
    def atr(yuksek, dusuk, kapanis, periyot=14):
        """Average True Range"""
        tr1 = yuksek - dusuk
        tr2 = abs(yuksek - kapanis.shift())
        tr3 = abs(dusuk - kapanis.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=periyot).mean()

    @staticmethod
    def stochastic(yuksek, dusuk, kapanis, periyot=14):
        """Stochastic Oscillator"""
        en_dusuk = dusuk.rolling(window=periyot).min()
        en_yuksek = yuksek.rolling(window=periyot).max()
        return 100 * (kapanis - en_dusuk) / (en_yuksek - en_dusuk)

    @staticmethod
    def obv(kapanis, hacim):
        """On Balance Volume"""
        obv_serisi = pd.Series(index=kapanis.index, dtype=float)
        obv_serisi.iloc[0] = hacim.iloc[0]

        for i in range(1, len(kapanis)):
            if kapanis.iloc[i] > kapanis.iloc[i - 1]:
                obv_serisi.iloc[i] = obv_serisi.iloc[i - 1] + hacim.iloc[i]
            elif kapanis.iloc[i] < kapanis.iloc[i - 1]:
                obv_serisi.iloc[i] = obv_serisi.iloc[i - 1] - hacim.iloc[i]
            else:
                obv_serisi.iloc[i] = obv_serisi.iloc[i - 1]
        return obv_serisi

    @classmethod
    def tum_ozellikler(cls, df):
        """
        DataFrame'den tüm teknik özellikleri üret

        Gerekli kolonlar: Open, High, Low, Close, Volume
        """
        df = df.copy()
        kapanis = df['Close']
        yuksek = df['High']
        dusuk = df['Low']
        hacim = df['Volume']

        ozellikler = pd.DataFrame(index=df.index)

        # === TEMEL FİYAT ÖZELLİKLERİ ===
        # Günlük getiri
        ozellikler['getiri_1g'] = kapanis.pct_change()
        ozellikler['getiri_3g'] = kapanis.pct_change(3)
        ozellikler['getiri_5g'] = kapanis.pct_change(5)
        ozellikler['getiri_10g'] = kapanis.pct_change(10)
        ozellikler['getiri_20g'] = kapanis.pct_change(20)

        # Volatilite (geçmiş)
        ozellikler['volatilite_5g'] = ozellikler['getiri_1g'].rolling(5).std()
        ozellikler['volatilite_10g'] = ozellikler['getiri_1g'].rolling(10).std()
        ozellikler['volatilite_20g'] = ozellikler['getiri_1g'].rolling(20).std()

        # === HAREKETLİ ORTALAMALAR ===
        for periyot in [5, 10, 20, 50, 200]:
            ozellikler[f'sma_{periyot}'] = cls.hareketli_ortalama(kapanis, periyot)
            ozellikler[f'sma_{periyot}_orani'] = kapanis / ozellikler[f'sma_{periyot}']

        # === MOMENTUM İNDİKATÖRLERİ ===
        ozellikler['rsi_14'] = cls.rsi(kapanis, 14)
        ozellikler['rsi_7'] = cls.rsi(kapanis, 7)

        # MACD
        macd, sinyal = cls.macd(kapanis)
        ozellikler['macd'] = macd
        ozellikler['macd_sinyal'] = sinyal
        ozellikler['macd_histogram'] = macd - sinyal

        # Stochastic
        ozellikler['stoch_k'] = cls.stochastic(yuksek, dusuk, kapanis, 14)
        ozellikler['stoch_d'] = cls.stochastic(yuksek, dusuk, kapanis, 3)

        # === VOLATİLİTE İNDİKATÖRLERİ ===
        ozellikler['atr_14'] = cls.atr(yuksek, dusuk, kapanis, 14)
        ozellikler['atr_orani'] = ozellikler['atr_14'] / kapanis

        bb_ort, bb_ust, bb_alt = cls.bollinger_bantlari(kapanis)
        ozellikler['bb_ust_orani'] = (bb_ust - kapanis) / kapanis
        ozellikler['bb_alt_orani'] = (kapanis - bb_alt) / kapanis
        ozellikler['bb_genislik'] = (bb_ust - bb_alt) / bb_ort

        # === HACİM İNDİKATÖRLERİ ===
        ozellikler['hacim_ort_5g'] = hacim.rolling(5).mean()
        ozellikler['hacim_ort_20g'] = hacim.rolling(20).mean()
        ozellikler['hacim_orani'] = hacim / ozellikler['hacim_ort_20g']
        ozellikler['obv'] = cls.obv(kapanis, hacim)
        ozellikler['obv_egim'] = ozellikler['obv'].diff(5)

        # === FİYAT YAPISI ===
        ozellikler['vucut'] = (kapanis - dusuk) / (yuksek - dusuk + 1e-10)
        ozellikler['ust_golge'] = (yuksek - kapanis) / kapanis
        ozellikler['alt_golge'] = (kapanis - dusuk) / kapanis
        ozellikler['gunluk_aralik'] = (yuksek - dusuk) / kapanis

        # === TREND ÖZELLİKLERİ ===
        ozellikler['yuksek_20_max'] = yuksek.rolling(20).max()
        ozellikler['dusuk_20_min'] = dusuk.rolling(20).min()
        ozellikler['yuksek_yakinlik'] = kapanis / ozellikler['yuksek_20_max']
        ozellikler['dusuk_yakinlik'] = kapanis / ozellikler['dusuk_20_min']

        # === ZAMAN ÖZELLİKLERİ ===
        ozellikler['haftanin_gunu'] = df.index.dayofweek
        ozellikler['ayin_gunu'] = df.index.day
        ozellikler['ay'] = df.index.month

        return ozellikler


# ============================================
# VERİ YÜKLEME VE HAZIRLAMA
# ============================================
class VeriHazirlama:
    """CSV verilerini yükler, özellik üretir, hedef etiketi oluşturur"""

    def __init__(self, config: Config):
        self.config = config
        self.indikatorler = TeknikIndikatorler()

    def csv_yukle(self, dosya_yolu: Path) -> pd.DataFrame:
        """Tek CSV dosyasını yükler ve temizler"""
        try:
            df = pd.read_csv(dosya_yolu)

            # Kolon isimlerini standardize et
            df.columns = [c.strip().title() for c in df.columns]

            # Tarih parse
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            elif 'Tarih' in df.columns:
                df['Tarih'] = pd.to_datetime(df['Tarih'])
                df.set_index('Tarih', inplace=True)

            # Sırala
            df.sort_index(inplace=True)

            # Gerekli kolonları kontrol et
            gerekli = ['Open', 'High', 'Low', 'Close', 'Volume']
            eksik = [c for c in gerekli if c not in df.columns]
            if eksik:
                print(f"    ⚠️ Eksik kolonlar: {eksik} — Atlanıyor")
                return None

            # Sayısal dönüşüm
            for col in gerekli:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # NaN temizle
            df.dropna(subset=gerekli, inplace=True)

            return df

        except Exception as e:
            print(f"    ❌ Hata: {e}")
            return None

    def hedef_olustur(self, kapanis: pd.Series) -> pd.Series:
        """
        Hedef etiket oluştur:
        AL(1): N gün sonraki getiri > %2
        SAT(-1): N gün sonraki getiri < -%2
        BEKLE(0): Arada
        """
        config = self.config
        gelecek_getiri = kapanis.shift(-config.HEDEF_GUN) / kapanis - 1

        hedef = pd.Series(index=kapanis.index, dtype=int)
        hedef[gelecek_getiri > config.AL_ESIK] = 1  # AL
        hedef[gelecek_getiri < config.SAT_ESIK] = -1  # SAT
        hedef.fillna(0, inplace=True)  # BEKLE

        return hedef

    def hisse_isle(self, dosya_yolu: Path, hisse_adi: str = None) -> pd.DataFrame:
        """Tek hisse için özellik vektörü üret"""
        if hisse_adi is None:
            hisse_adi = dosya_yolu.stem.split('_')[0]

        print(f"  📊 {hisse_adi} işleniyor...")

        # Veri yükle
        df = self.csv_yukle(dosya_yolu)
        if df is None or len(df) < self.config.MIN_VERI:
            print(f"    ⚠️ Yetersiz veri ({len(df) if df is not None else 0} satır)")
            return None

        # Teknik özellikler
        ozellikler = self.indikatorler.tum_ozellikler(df)

        # Hedef etiket
        ozellikler['hedef'] = self.hedef_olustur(df['Close'])

        # Hisse adı
        ozellikler['hisse'] = hisse_adi

        # NaN temizle (indikatörlerin başlangıcındaki NaN'ler)
        ozellikler.dropna(inplace=True)

        print(f"    ✅ {len(ozellikler)} satır, {len(ozellikler.columns) - 2} özellik")

        return ozellikler

    def tum_hisseleri_isle(self, limit: int = None) -> pd.DataFrame:
        """Tüm CSV dosyalarını işle, tek DataFrame döndür"""
        csv_dosyalari = sorted(self.config.VERI_KLASORU.glob("*.csv"))
        print(f"\n📁 {len(csv_dosyalari)} CSV dosyası bulundu")

        if limit:
            csv_dosyalari = csv_dosyalari[:limit]
            print(f"   (İlk {limit} dosya işlenecek)")

        tum_veriler = []
        basarili = 0
        basarisiz = 0

        for dosya in csv_dosyalari:
            hisse_adi = dosya.stem.split('_')[0]
            sonuc = self.hisse_isle(dosya, hisse_adi)

            if sonuc is not None and len(sonuc) > 0:
                tum_veriler.append(sonuc)
                basarili += 1
            else:
                basarisiz += 1

        if not tum_veriler:
            print("⛔ Hiç veri işlenemedi!")
            return None

        # Birleştir
        tum_df = pd.concat(tum_veriler, ignore_index=True)
        print(f"\n{'=' * 50}")
        print(f"✅ TOPLAM: {basarili} başarılı, {basarisiz} başarısız")
        print(f"📊 Toplam satır: {len(tum_df):,}")
        print(f"📊 Toplam özellik: {len(tum_df.columns) - 2}")
        print(f"{'=' * 50}")

        # Hedef dağılımı
        print(f"\n🎯 Hedef Dağılımı:")
        hedef_dagilim = tum_df['hedef'].value_counts().sort_index()
        for deger, adet in hedef_dagilim.items():
            etiket = {1: 'AL', 0: 'BEKLE', -1: 'SAT'}.get(deger, str(deger))
            print(f"   {etiket:>6}: {adet:>8,} ({adet / len(tum_df) * 100:.1f}%)")

        return tum_df


# ============================================
# MODEL EĞİTİMİ
# ============================================
class ModelEgitici:
    """ML modellerini eğitir, değerlendirir, kaydeder"""

    def __init__(self, config: Config):
        self.config = config
        self.modeller = {}
        self.scaler = None
        self.secici = None
        self.ozellik_isimleri = None

    def veri_hazirla(self, df: pd.DataFrame) -> tuple:
        """
        Ham veriyi X, y formatına dönüştür
        Zaman serisi split: son %20 test
        """
        # Özellik ve hedef ayrımı
        y = df['hedef'].values
        X_raw = df.drop(columns=['hedef', 'hisse'], errors='ignore')

        # Özellik isimlerini kaydet
        self.ozellik_isimleri = list(X_raw.columns)

        # Sonsuz/NaN değerleri temizle
        X_raw = X_raw.replace([np.inf, -np.inf], np.nan)
        X_raw = X_raw.fillna(X_raw.median())

        # Zaman serisi split (kronolojik)
        n = len(X_raw)
        test_baslangic = int(n * (1 - self.config.TEST_ORANI))

        X_train = X_raw.iloc[:test_baslangic].values
        X_test = X_raw.iloc[test_baslangic:].values
        y_train = y[:test_baslangic]
        y_test = y[test_baslangic:]

        # Ölçeklendirme
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Özellik seçimi (en iyi K)
        self.secici = SelectKBest(f_classif, k=min(self.config.MAX_OZELLIK, X_train.shape[1]))
        X_train_secili = self.secici.fit_transform(X_train_scaled, y_train)
        X_test_secili = self.secici.transform(X_test_scaled)

        # Seçilen özellikleri göster
        secili_mask = self.secici.get_support()
        secili_ozellikler = [self.ozellik_isimleri[i] for i, sec in enumerate(secili_mask) if sec]
        print(f"\n🔍 Seçilen {len(secili_ozellikler)} Özellik:")
        for i, oz in enumerate(secili_ozellikler[:10], 1):
            skor = self.secici.scores_[secili_mask][i - 1]
            print(f"   {i:2}. {oz:<25} (skor: {skor:.2f})")
        if len(secili_ozellikler) > 10:
            print(f"   ... ve {len(secili_ozellikler) - 10} özellik daha")

        return X_train_secili, X_test_secili, y_train, y_test, secili_ozellikler

    def modelleri_egit(self, X_train, X_test, y_train, y_test, tune: bool = False):
        """Tüm modelleri eğit ve değerlendir"""
        sonuclar = {}

        print(f"\n{'=' * 50}")
        print("🤖 MODELLER EĞİTİLİYOR")
        print(f"{'=' * 50}")
        print(f"Eğitim seti: {len(X_train):,}")
        print(f"Test seti: {len(X_test):,}")
        print(f"Sınıf dağılımı (eğitim): AL={sum(y_train == 1)}, BEKLE={sum(y_train == 0)}, SAT={sum(y_train == -1)}")
        print(f"{'=' * 50}\n")

        # 1. Random Forest
        print("🌲 Random Forest eğitiliyor...")
        rf = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            min_samples_leaf=5,
            class_weight='balanced',
            random_state=self.config.RANDOM_STATE,
            n_jobs=-1
        )
        rf.fit(X_train, y_train)
        rf_pred = rf.predict(X_test)
        rf_acc = accuracy_score(y_test, rf_pred)
        self.modeller['random_forest'] = rf
        sonuclar['random_forest'] = {
            'dogruluk': rf_acc,
            'tahminler': rf_pred,
            'model': rf
        }
        print(f"   ✅ Doğruluk: {rf_acc:.4f}")
        print(classification_report(y_test, rf_pred, target_names=['SAT', 'BEKLE', 'AL']))

        # 2. LightGBM (varsa)
        if KUTUPHANE_DURUM.get('lightgbm'):
            print("⚡ LightGBM eğitiliyor...")
            lgb_model = lgb.LGBMClassifier(
                n_estimators=200,
                max_depth=10,
                learning_rate=0.05,
                class_weight='balanced',
                random_state=self.config.RANDOM_STATE,
                verbose=-1
            )
            lgb_model.fit(X_train, y_train)
            lgb_pred = lgb_model.predict(X_test)
            lgb_acc = accuracy_score(y_test, lgb_pred)
            self.modeller['lightgbm'] = lgb_model
            sonuclar['lightgbm'] = {
                'dogruluk': lgb_acc,
                'tahminler': lgb_pred,
                'model': lgb_model
            }
            print(f"   ✅ Doğruluk: {lgb_acc:.4f}")
            print(classification_report(y_test, lgb_pred, target_names=['SAT', 'BEKLE', 'AL']))

        # 3. XGBoost (varsa)
        if KUTUPHANE_DURUM.get('xgboost'):
            print("🚀 XGBoost eğitiliyor...")
            xgb_model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=10,
                learning_rate=0.05,
                random_state=self.config.RANDOM_STATE,
                n_jobs=-1
            )
            # Sınıf ağırlıkları (manuel)
            from sklearn.utils.class_weight import compute_class_weight
            classes = np.unique(y_train)
            cw = compute_class_weight('balanced', classes=classes, y=y_train)
            cw_dict = {c: w for c, w in zip(classes, cw)}
            xgb_model.fit(X_train, y_train)
            xgb_pred = xgb_model.predict(X_test)
            xgb_acc = accuracy_score(y_test, xgb_pred)
            self.modeller['xgboost'] = xgb_model
            sonuclar['xgboost'] = {
                'dogruluk': xgb_acc,
                'tahminler': xgb_pred,
                'model': xgb_model
            }
            print(f"   ✅ Doğruluk: {xgb_acc:.4f}")
            print(classification_report(y_test, xgb_pred, target_names=['SAT', 'BEKLE', 'AL']))

        # 4. Gradient Boosting (her zaman var)
        print("📈 Gradient Boosting eğitiliyor...")
        gb = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            random_state=self.config.RANDOM_STATE
        )
        gb.fit(X_train, y_train)
        gb_pred = gb.predict(X_test)
        gb_acc = accuracy_score(y_test, gb_pred)
        self.modeller['gradient_boosting'] = gb
        sonuclar['gradient_boosting'] = {
            'dogruluk': gb_acc,
            'tahminler': gb_pred,
            'model': gb
        }
        print(f"   ✅ Doğruluk: {gb_acc:.4f}")
        print(classification_report(y_test, gb_pred, target_names=['SAT', 'BEKLE', 'AL']))

        return sonuclar

    def ensemble_olustur(self, sonuclar: dict, X_test, y_test):
        """Ağırlıklı ensemble tahmin oluştur"""
        print(f"\n{'=' * 50}")
        print("🔗 ENSEMBLE OLUŞTURULUYOR")
        print(f"{'=' * 50}")

        # Mevcut modellerin ağırlıklarını ayarla
        mevcut_modeller = list(sonuclar.keys())
        agirliklar = {}

        for model_adi in mevcut_modeller:
            if model_adi in self.config.AGIRLIKLAR:
                agirliklar[model_adi] = self.config.AGIRLIKLAR[model_adi]
            else:
                agirliklar[model_adi] = 1.0 / len(mevcut_modeller)

        # Normalize
        toplam = sum(agirliklar.values())
        agirliklar = {k: v / toplam for k, v in agirliklar.items()}

        print("Ağırlıklar:")
        for model_adi, agirlik in agirliklar.items():
            print(f"   {model_adi}: {agirlik:.2%}")

        # Ağırlıklı oylama
        # Sınıf olasılıklarını al (predict_proba varsa)
        ensemble_oy = np.zeros((len(X_test), 3))  # 3 sınıf: SAT, BEKLE, AL

        for model_adi in mevcut_modeller:
            model = sonuclar[model_adi]['model']
            try:
                # Olasılık tahmini
                proba = model.predict_proba(X_test)
                # Sınıf sırası: -1, 0, 1 -> indeks 0, 1, 2
                agirlik = agirliklar[model_adi]
                ensemble_oy += proba * agirlik
            except:
                # Olasılık yoksa tahmin üzerinden one-hot
                pred = sonuclar[model_adi]['tahminler']
                # -1 -> 0, 0 -> 1, 1 -> 2
                pred_idx = pred + 1
                one_hot = np.zeros((len(pred), 3))
                one_hot[np.arange(len(pred)), pred_idx.astype(int)] = 1
                ensemble_oy += one_hot * agirliklar[model_adi]

        ensemble_pred_idx = np.argmax(ensemble_oy, axis=1)
        ensemble_pred = ensemble_pred_idx - 1  # 0,1,2 -> -1,0,1

        ensemble_acc = accuracy_score(y_test, ensemble_pred)
        print(f"\n🎯 Ensemble Doğruluk: {ensemble_acc:.4f}")
        print(classification_report(y_test, ensemble_pred, target_names=['SAT', 'BEKLE', 'AL']))

        return ensemble_pred, ensemble_oy, ensemble_acc

    def kaydet(self, secili_ozellikler: list):
        """Tüm modelleri ve ön işlemcileri kaydet"""
        self.config.MODEL_KLASORU.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        kayit_paketi = {
            'scaler': self.scaler,
            'secici': self.secici,
            'ozellik_isimleri': self.ozellik_isimleri,
            'secili_ozellikler': secili_ozellikler,
            'config': {
                'hedef_gun': self.config.HEDEF_GUN,
                'al_esik': self.config.AL_ESIK,
                'sat_esik': self.config.SAT_ESIK,
                'max_ozellik': self.config.MAX_OZELLIK
            },
            'modeller': self.modeller,
            'kutuphane_durum': KUTUPHANE_DURUM,
            'egitim_tarihi': datetime.now().isoformat()
        }

        # Ana paket
        paket_yolu = self.config.MODEL_KLASORU / f"ai_model_v43_{timestamp}.joblib"
        joblib.dump(kayit_paketi, paket_yolu)
        print(f"\n💾 Model paketi kaydedildi: {paket_yolu}")

        # Son model symlink (Windows'ta kopya)
        son_model = self.config.MODEL_KLASORU / "ai_model_latest.joblib"
        joblib.dump(kayit_paketi, son_model)
        print(f"💾 Son model güncellendi: {son_model}")

        # Metadata JSON
        meta = {
            'versiyon': '4.3',
            'tarih': datetime.now().isoformat(),
            'toplam_ozellik': len(self.ozellik_isimleri),
            'secili_ozellik': len(secili_ozellikler),
            'modeller': list(self.modeller.keys()),
            'kutuphaneler': KUTUPHANE_DURUM
        }
        meta_yolu = self.config.MODEL_KLASORU / f"metadata_{timestamp}.json"
        with open(meta_yolu, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return paket_yolu


# ============================================
# TEK HİSSE TAHMİN (Debug)
# ============================================
class TekHisseTahmin:
    """Tek hisse için tahmin yap (test amaçlı)"""

    def __init__(self, model_paketi: dict):
        self.paket = model_paketi
        self.scaler = model_paketi['scaler']
        self.secici = model_paketi['secici']
        self.modeller = model_paketi['modeller']
        self.config = model_paketi['config']

    def tahmin_et(self, df: pd.DataFrame) -> dict:
        """Tek hisse için tahmin"""
        # Özellik üret
        indikatorler = TeknikIndikatorler()
        ozellikler = indikatorler.tum_ozellikler(df)

        # Son satır (en güncel)
        son = ozellikler.iloc[-1:]
        X = son.drop(columns=['hedef', 'hisse'], errors='ignore')

        # Ölçeklendir ve seç
        X_scaled = self.scaler.transform(X.values)
        X_secili = self.secici.transform(X_scaled)

        # Her modelden tahmin
        tahminler = {}
        for model_adi, model in self.modeller.items():
            pred = model.predict(X_secili)[0]
            proba = model.predict_proba(X_secili)[0] if hasattr(model, 'predict_proba') else None
            tahminler[model_adi] = {
                'tahmin': int(pred),
                'etiket': {1: 'AL', 0: 'BEKLE', -1: 'SAT'}.get(int(pred), '?'),
                'olasilik': proba.tolist() if proba is not None else None
            }

        return tahminler


# ============================================
# ANA FONKSİYON
# ============================================
def main():
    parser = argparse.ArgumentParser(description='Borsa Komutan AI Model Eğitimi v4.3')
    parser.add_argument('--hisse', type=str, help='Tek hisse için debug (örn: AEFES)')
    parser.add_argument('--tune', action='store_true', help='Hiperparametre optimizasyonu')
    parser.add_argument('--limit', type=int, help='İşlenecek maks hisse sayısı')
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 BORSA KOMUTAN v4.3 — AI MODEL EĞİTİMİ")
    print("=" * 60)
    print(f"⏰ Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Veri: {Config.VERI_KLASORU}")
    print(f"💾 Model: {Config.MODEL_KLASORU}")
    print(f"🎯 Hedef: {Config.HEDEF_GUN} gün sonrası | AL>{Config.AL_ESIK:.0%} | SAT<{Config.SAT_ESIK:.0%}")
    print("=" * 60)

    # Kütüphane kontrolü
    print("\n📦 Kütüphane Kontrolü:")
    kutuphane_kontrol()
    ml_importlari_yukle()

    config = Config()

    # Tek hisse debug modu
    if args.hisse:
        print(f"\n🔍 TEK HİSSE MODU: {args.hisse}")
        veri_hazirla = VeriHazirlama(config)
        dosya = config.VERI_KLASORU / f"{args.hisse}_5yil.csv"
        if not dosya.exists():
            print(f"⛔ Dosya bulunamadı: {dosya}")
            # Alternatif isimler dene
            for alt in config.VERI_KLASORU.glob(f"{args.hisse}*.csv"):
                print(f"   Bulundu: {alt}")
                dosya = alt
                break

        if dosya.exists():
            sonuc = veri_hazirla.hisse_isle(dosya, args.hisse)
            if sonuc is not None:
                print(f"\n📊 Son 5 satır:")
                print(sonuc[['hedef'] + [c for c in sonuc.columns if c not in ['hedef', 'hisse']][:5]].tail())
        return

    # Tam eğitim
    print("\n" + "=" * 60)
    print("📊 VERİ HAZIRLAMA")
    print("=" * 60)

    veri_hazirla = VeriHazirlama(config)
    tum_veri = veri_hazirla.tum_hisseleri_isle(limit=args.limit)

    if tum_veri is None or len(tum_veri) == 0:
        print("⛔ Eğitim verisi oluşturulamadı!")
        return

    print("\n" + "=" * 60)
    print("🤖 MODEL EĞİTİMİ")
    print("=" * 60)

    egitici = ModelEgitici(config)
    X_train, X_test, y_train, y_test, secili_ozellikler = egitici.veri_hazirla(tum_veri)

    sonuclar = egitici.modelleri_egit(X_train, X_test, y_train, y_test, tune=args.tune)

    # Ensemble
    ensemble_pred, ensemble_oy, ensemble_acc = egitici.ensemble_olustur(sonuclar, X_test, y_test)

    # Kaydet
    print("\n" + "=" * 60)
    print("💾 MODEL KAYDETME")
    print("=" * 60)
    model_yolu = egitici.kaydet(secili_ozellikler)

    # Özet raporu
    print("\n" + "=" * 60)
    print("📋 EĞİTİM ÖZETİ")
    print("=" * 60)
    print(f"✅ Eğitim tamamlandı!")
    print(f"📁 Model: {model_yolu}")
    print(f"🎯 Ensemble Doğruluk: {ensemble_acc:.4f}")
    print(f"📊 Kullanılan Modeller: {', '.join(sonuclar.keys())}")
    print(f"⏰ Bitiş: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("\n🚀 Sıradaki adım: hisse_analiz.py'ye AI skorlama entegrasyonu!")
    print("   Yeni sohbette: 'AI Entegrasyonu başlayalım' yazın.")
    print("=" * 60)


if __name__ == "__main__":
    main()