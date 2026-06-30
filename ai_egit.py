#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BORSA KOMUTAN v4.3.2 — AI Modeli Eğitimi (580 Hisse)
=====================================================
535 hisse → 580 hisse genişletilmiş eğitim
Sektör-relative özellikler + Ensemble (RF+XGBoost)

Çalıştırma:
    python ai_egit.py                    # Tam eğitim (580 hisse)
    python ai_egit.py --limit 100        # İlk 100 hisse (test)
    python ai_egit.py --hisse AEFES      # Tek hisse debug
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

from collections import Counter
import numpy as np
import pandas as pd

# ============================================
# KÜTÜPHANE KONTROLÜ
# ============================================
KUTUPHANE_DURUM = {}

def kutuphane_kontrol():
    global KUTUPHANE_DURUM
    kutuphaneler = {
        'sklearn': ('scikit-learn', 'pip install scikit-learn'),
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
        sys.exit(1)
    return KUTUPHANE_DURUM

def ml_importlari_yukle():
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import classification_report, accuracy_score
    from sklearn.feature_selection import SelectKBest, f_classif
    
    global RandomForestClassifier, GradientBoostingClassifier
    global StandardScaler, TimeSeriesSplit
    global classification_report, accuracy_score
    global SelectKBest, f_classif
    
    if KUTUPHANE_DURUM.get('xgboost'):
        import xgboost as xgb
        global xgb

# ============================================
# YAPILANDIRMA
# ============================================
class Config:
    VERI_KLASORU = Path(r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\veri")
    MODEL_KLASORU = Path(r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\modeller")
    RAPOR_KLASORU = Path(r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\rapor")
    
    HEDEF_GUN = 5
    AL_ESIK = 0.02
    SAT_ESIK = -0.02
    
    TEST_ORANI = 0.2
    MIN_VERI = 100
    RANDOM_STATE = 42
    
    MAX_OZELLIK = 42  # 38 → 42 (sektör özellikleri için)
    
    # Ensemble ağırlıkları
    AGIRLIKLAR = {
        'xgboost': 0.45,
        'random_forest': 0.35,
        'gradient_boosting': 0.20
    }

# ============================================
# SEKTÖR BİLGİLERİ
# ============================================
SEKTORLER = {
    # Bankacılık
    'AKBNK': 'banka', 'GARAN': 'banka', 'ISCTR': 'banka', 'YKBNK': 'banka',
    'HALKB': 'banka', 'VAKBN': 'banka', 'ALBRK': 'banka', 'QNBFB': 'banka',
    # Holding
    'KCHOL': 'holding', 'SAHOL': 'holding', 'TAVHL': 'holding', 'AGHOL': 'holding',
    # Enerji
    'TUPRS': 'enerji', 'PETKM': 'enerji', 'EKGYO': 'enerji', 'ZOREN': 'enerji',
    # Teknoloji
    'ASELS': 'teknoloji', 'KAREL': 'teknoloji', 'LOGO': 'teknoloji',
    # Otomotiv
    'FROTO': 'otomotiv', 'TOASO': 'otomotiv', 'DOHOL': 'otomotiv',
    # Gıda
    'BIMAS': 'gida', 'SOKM': 'gida', 'MGROS': 'gida', 'AEFES': 'gida',
    # İnşaat
    'EGEEN': 'insaat', 'ENKAI': 'insaat', 'TSKB': 'insaat',
    # Havacılık
    'THYAO': 'havacilik', 'PGSUS': 'havacilik',
    # Telekom
    'TTKOM': 'telekom', 'TCELL': 'telekom',
    # Diğer
}

def sektor_bul(hisse_adi):
    """Hisse adından sektör bul"""
    return SEKTORLER.get(hisse_adi.upper(), 'diger')

# ============================================
# TEKNİK İNDİKATÖRLER
# ============================================
class TeknikIndikatorler:
    @staticmethod
    def rsi(seri, periyot=14):
        delta = seri.diff()
        kazan = delta.where(delta > 0, 0).rolling(window=periyot).mean()
        kayip = (-delta.where(delta < 0, 0)).rolling(window=periyot).mean()
        rs = kazan / kayip
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(seri, hizli=12, yavas=26, sinyal=9):
        ema_hizli = seri.ewm(span=hizli).mean()
        ema_yavas = seri.ewm(span=yavas).mean()
        macd_cizgi = ema_hizli - ema_yavas
        sinyal_cizgi = macd_cizgi.ewm(span=sinyal).mean()
        return macd_cizgi, sinyal_cizgi
    
    @staticmethod
    def bollinger_bantlari(seri, periyot=20, carpma=2):
        ortalama = seri.rolling(window=periyot).mean()
        std = seri.rolling(window=periyot).std()
        return ortalama, ortalama + (std * carpma), ortalama - (std * carpma)
    
    @staticmethod
    def hareketli_ortalama(seri, periyot):
        return seri.rolling(window=periyot).mean()
    
    @staticmethod
    def atr(yuksek, dusuk, kapanis, periyot=14):
        tr1 = yuksek - dusuk
        tr2 = abs(yuksek - kapanis.shift())
        tr3 = abs(dusuk - kapanis.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(window=periyot).mean()
    
    @staticmethod
    def stochastic(yuksek, dusuk, kapanis, periyot=14):
        en_dusuk = dusuk.rolling(window=periyot).min()
        en_yuksek = yuksek.rolling(window=periyot).max()
        return 100 * (kapanis - en_dusuk) / (en_yuksek - en_dusuk)
    
    @staticmethod
    def obv(kapanis, hacim):
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
    def tum_ozellikler(cls, df, hisse_adi=None, sektor_ortalamalari=None):
        df = df.copy()
        kapanis = df['Close']
        yuksek = df['High']
        dusuk = df['Low']
        hacim = df['Volume']
        
        ozellikler = pd.DataFrame(index=df.index)
        
        # === TEMEL FİYAT ÖZELLİKLERİ ===
        ozellikler['getiri_1g'] = kapanis.pct_change(fill_method=None)
        ozellikler['getiri_3g'] = kapanis.pct_change(3, fill_method=None)
        ozellikler['getiri_5g'] = kapanis.pct_change(5, fill_method=None)
        ozellikler['getiri_10g'] = kapanis.pct_change(10, fill_method=None)
        ozellikler['getiri_20g'] = kapanis.pct_change(20, fill_method=None)
        
        # Volatilite
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
        
        macd, sinyal = cls.macd(kapanis)
        ozellikler['macd'] = macd
        ozellikler['macd_sinyal'] = sinyal
        ozellikler['macd_histogram'] = macd - sinyal
        
        ozellikler['stoch_k'] = cls.stochastic(yuksek, dusuk, kapanis, 14)
        ozellikler['stoch_d'] = cls.stochastic(yuksek, dusuk, kapanis, 3)
        
        # === VOLATİLİTE ===
        ozellikler['atr_14'] = cls.atr(yuksek, dusuk, kapanis, 14)
        ozellikler['atr_orani'] = ozellikler['atr_14'] / kapanis
        
        bb_ort, bb_ust, bb_alt = cls.bollinger_bantlari(kapanis)
        ozellikler['bb_ust_orani'] = (bb_ust - kapanis) / kapanis
        ozellikler['bb_alt_orani'] = (kapanis - bb_alt) / kapanis
        ozellikler['bb_genislik'] = (bb_ust - bb_alt) / bb_ort
        
        # === HACİM ===
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
        
        # === TREND ===
        ozellikler['yuksek_20_max'] = yuksek.rolling(20).max()
        ozellikler['dusuk_20_min'] = dusuk.rolling(20).min()
        ozellikler['yuksek_yakinlik'] = kapanis / ozellikler['yuksek_20_max']
        ozellikler['dusuk_yakinlik'] = kapanis / ozellikler['dusuk_20_min']
        
        # === SEKTÖR-RELATİF ÖZELLİKLER ===
        if sektor_ortalamalari is not None and hisse_adi is not None:
            sektor = sektor_bul(hisse_adi)
            if sektor in sektor_ortalamalari:
                sektor_data = sektor_ortalamalari[sektor]

                if 'getiri_5g' in sektor_data:
                    ozellikler['sektor_getiri_5g_fark'] = ozellikler['getiri_5g'] - sektor_data['getiri_5g']

                if 'momentum_10' in sektor_data:
                    ozellikler['sektor_momentum_10_fark'] = (kapanis / kapanis.shift(10) - 1) * 100 - sektor_data['momentum_10']

                if 'volatilite_10g' in sektor_data:
                    ozellikler['sektor_vol_10g_oran'] = ozellikler['volatilite_10g'] / (sektor_data['volatilite_10g'] + 1e-10)

                if 'rsi_14' in sektor_data:
                    ozellikler['sektor_rsi_14_fark'] = ozellikler['rsi_14'] - sektor_data['rsi_14']

                if 'hacim_orani' in sektor_data:
                    ozellikler['sektor_hacim_oran'] = ozellikler['hacim_orani'] / (sektor_data['hacim_orani'] + 1e-10)

                if 'bb_pozisyon' in sektor_data:
                    bb_pozisyon = (kapanis - bb_alt) / (bb_ust - bb_alt + 1e-10)
                    ozellikler['sektor_bb_pozisyon_fark'] = bb_pozisyon - sektor_data['bb_pozisyon']

                if 'getiri_1g' in sektor_data:
                    ozellikler['sektor_getiri_1g_fark'] = ozellikler['getiri_1g'] - sektor_data['getiri_1g']

        return ozellikler

# ============================================
# SEKTÖR ORTALAMALARI HESAPLAMA
# ============================================
def sektor_ortalamalari_hesapla(tum_hisse_verileri):
    """Tüm hisselerin sektör ortalamalarını hesapla"""
    sektor_ozellikleri = {}
    
    for hisse_adi, df in tum_hisse_verileri.items():
        sektor = sektor_bul(hisse_adi)
        if sektor not in sektor_ozellikleri:
            sektor_ozellikleri[sektor] = []
        sektor_ozellikleri[sektor].append(df)
    
    sektor_ortalamalari = {}
    for sektor, dfs in sektor_ozellikleri.items():
        if not dfs:
            continue
        
        birlesik = pd.concat([df[['Close', 'Volume']].rename(columns={'Close': f'Close_{i}', 'Volume': f'Volume_{i}'}) 
                             for i, df in enumerate(dfs)], axis=1)
        
        ortalama_kapanis = birlesik.filter(like='Close_').mean(axis=1)
        ortalama_hacim = birlesik.filter(like='Volume_').mean(axis=1)
        
        bb_ort_s = ortalama_kapanis.rolling(20).mean()
        bb_ust_s = bb_ort_s + ortalama_kapanis.rolling(20).std() * 2
        bb_alt_s = bb_ort_s - ortalama_kapanis.rolling(20).std() * 2
        sektor_ortalamalari[sektor] = {
            'getiri_5g': ortalama_kapanis.pct_change(5) * 100,
            'getiri_1g': ortalama_kapanis.pct_change() * 100,
            'momentum_10': (ortalama_kapanis / ortalama_kapanis.shift(10) - 1) * 100,
            'volatilite_10g': ortalama_kapanis.pct_change().rolling(10).std() * 100,
            'rsi_14': TeknikIndikatorler.rsi(ortalama_kapanis, 14),
            'hacim_orani': ortalama_hacim / ortalama_hacim.rolling(20).mean(),
            'sma_20': bb_ort_s,
            'bb_pozisyon': (ortalama_kapanis - bb_alt_s) / (bb_ust_s - bb_alt_s + 1e-10)
        }
    
    return sektor_ortalamalari

# ============================================
# VERİ YÜKLEME
# ============================================
class VeriHazirlama:
    def __init__(self, config: Config):
        self.config = config
        self.indikatorler = TeknikIndikatorler()
    
    def csv_yukle(self, dosya_yolu: Path) -> pd.DataFrame:
        try:
            df = pd.read_csv(dosya_yolu)
            df.columns = [c.strip().title() for c in df.columns]
            
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            elif 'Tarih' in df.columns:
                df['Tarih'] = pd.to_datetime(df['Tarih'])
                df.set_index('Tarih', inplace=True)
            
            df.sort_index(inplace=True)
            
            gerekli = ['Open', 'High', 'Low', 'Close', 'Volume']
            eksik = [c for c in gerekli if c not in df.columns]
            if eksik:
                print(f"    ⚠️ Eksik kolonlar: {eksik} — Atlanıyor")
                return None
            
            for col in gerekli:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.dropna(subset=gerekli, inplace=True)
            return df
        except Exception as e:
            print(f"    ❌ Hata: {e}")
            return None
    
    def hedef_olustur(self, kapanis: pd.Series) -> pd.Series:
        config = self.config
        gelecek_getiri = kapanis.shift(-config.HEDEF_GUN) / kapanis - 1
        
        hedef = pd.Series(index=kapanis.index, dtype=int)
        hedef[gelecek_getiri > config.AL_ESIK] = 1
        hedef[gelecek_getiri < config.SAT_ESIK] = -1
        hedef.fillna(0, inplace=True)
        return hedef
    
    def tum_hisseleri_yukle(self, limit: int = None) -> dict:
        csv_dosyalari = sorted(self.config.VERI_KLASORU.glob("*.csv"))
        print(f"\n📁 {len(csv_dosyalari)} CSV dosyası bulundu")
        
        if limit:
            csv_dosyalari = csv_dosyalari[:limit]
            print(f"   (İlk {limit} dosya işlenecek)")
        
        tum_veriler = {}
        basarili = 0
        
        for dosya in csv_dosyalari:
            hisse_adi = dosya.stem.split('_')[0].replace('.IS', '')
            df = self.csv_yukle(dosya)
            
            if df is not None and len(df) >= self.config.MIN_VERI:
                tum_veriler[hisse_adi] = df
                basarili += 1
        
        print(f"✅ {basarili} hisse yüklendi")
        return tum_veriler
    
    def tum_hisseleri_isle(self, limit: int = None, sektor_ortalamalari: dict = None) -> pd.DataFrame:
        tum_hisse_verileri = self.tum_hisseleri_yukle(limit)
        
        if sektor_ortalamalari is None:
            print("\n📊 Sektör ortalamaları hesaplanıyor...")
            sektor_ortalamalari = sektor_ortalamalari_hesapla(tum_hisse_verileri)
            print(f"   {len(sektor_ortalamalari)} sektor hesaplandı")
        
        tum_veriler = []
        for hisse_adi, df in tum_hisse_verileri.items():
            print(f"  {hisse_adi} isleniyor...")
            
            ozellikler = self.indikatorler.tum_ozellikler(df, hisse_adi, sektor_ortalamalari)
            if ozellikler is None:
                print(f"  UYARI: {hisse_adi} ozellikler None")
                continue
            
            ozellikler['hedef'] = self.hedef_olustur(df['Close'])
            ozellikler['hisse'] = hisse_adi
            
            ozellikler.dropna(inplace=True)
            
            if len(ozellikler) > 0:
                tum_veriler.append(ozellikler)
        
        if not tum_veriler:
            return None
        
        tum_df = pd.concat(tum_veriler, ignore_index=True)
        print(f"\n{'='*50}")
        print(f"📊 Toplam satır: {len(tum_df):,}")
        print(f"📊 Toplam özellik: {len(tum_df.columns) - 2}")
        
        print(f"\n🎯 Hedef Dağılımı:")
        hedef_dagilim = tum_df['hedef'].value_counts().sort_index()
        for deger, adet in hedef_dagilim.items():
            etiket = {1: 'AL', 0: 'BEKLE', -1: 'SAT'}.get(deger, str(deger))
            print(f"   {etiket:>6}: {adet:>8,} ({adet/len(tum_df)*100:.1f}%)")
        
        return tum_df

# ============================================
# MODEL EĞİTİMİ
# ============================================
class ModelEgitici:
    def __init__(self, config: Config):
        self.config = config
        self.modeller = {}
        self.scaler = None
        self.secici = None
        self.ozellik_isimleri = None
    
    def veri_hazirla(self, df: pd.DataFrame) -> tuple:
        y = df['hedef'].values
        X_raw = df.drop(columns=['hedef', 'hisse'], errors='ignore')
        
        self.ozellik_isimleri = list(X_raw.columns)
        
        X_raw = X_raw.replace([np.inf, -np.inf], np.nan)
        X_raw = X_raw.fillna(X_raw.median())
        
        n = len(X_raw)
        test_baslangic = int(n * (1 - self.config.TEST_ORANI))
        
        X_train = X_raw.iloc[:test_baslangic].values
        X_test = X_raw.iloc[test_baslangic:].values
        y_train = y[:test_baslangic]
        y_test = y[test_baslangic:]
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.secici = SelectKBest(f_classif, k=min(self.config.MAX_OZELLIK, X_train.shape[1]))
        X_train_secili = self.secici.fit_transform(X_train_scaled, y_train)
        X_test_secili = self.secici.transform(X_test_scaled)
        
        secili_mask = self.secici.get_support()
        secili_ozellikler = [self.ozellik_isimleri[i] for i, sec in enumerate(secili_mask) if sec]
        print(f"\n🔍 Seçilen {len(secili_ozellikler)} Özellik:")
        for i, oz in enumerate(secili_ozellikler[:15], 1):
            skor = self.secici.scores_[secili_mask][i-1]
            print(f"   {i:2}. {oz:<30} (skor: {skor:.2f})")
        if len(secili_ozellikler) > 15:
            print(f"   ... ve {len(secili_ozellikler)-15} özellik daha")
        
        return X_train_secili, X_test_secili, y_train, y_test, secili_ozellikler
    
    def modelleri_egit(self, X_train, X_test, y_train, y_test, tune: bool = False):
        sonuclar = {}
        
        print(f"\n{'='*50}")
        print("🤖 MODELLER EĞİTİLİYOR")
        print(f"{'='*50}")
        print(f"Eğitim seti: {len(X_train):,}")
        print(f"Test seti: {len(X_test):,}")
        print(f"Sınıf dağılımı: AL={sum(y_train==1)}, BEKLE={sum(y_train==0)}, SAT={sum(y_train==-1)}")
        
        sinif_say = Counter(y_train)
        toplam = len(y_train)
        self.sinif_dagilimi = {-1: sinif_say.get(-1, 0), 0: sinif_say.get(0, 0), 1: sinif_say.get(1, 0)}
        print(f"Sınıf dağılımı: SAT={sinif_say.get(-1,0)}, BEKLE={sinif_say.get(0,0)}, AL={sinif_say.get(1,0)}")
        
        # 1. Random Forest
        print("\n🌲 Random Forest eğitiliyor...")
        rf = RandomForestClassifier(
            n_estimators=1000,
            max_depth=20,
            min_samples_split=5,
            min_samples_leaf=2,
            class_weight='balanced',
            random_state=self.config.RANDOM_STATE,
            n_jobs=-1
        )
        rf.fit(X_train, y_train)
        rf_pred = rf.predict(X_test)
        rf_acc = accuracy_score(y_test, rf_pred)
        self.modeller['random_forest'] = rf
        sonuclar['random_forest'] = {'dogruluk': rf_acc, 'tahminler': rf_pred, 'model': rf}
        print(f"   ✅ Doğruluk: {rf_acc:.4f}")
        print(classification_report(y_test, rf_pred, target_names=['SAT','BEKLE','AL']))
        
        # 2. XGBoost
        if KUTUPHANE_DURUM.get('xgboost'):
            print("\n🚀 XGBoost eğitiliyor...")
            try:
                from sklearn.utils.class_weight import compute_sample_weight
                y_train_map = y_train + 1
                y_test_map = y_test + 1
                
                xgb_model = xgb.XGBClassifier(
                    n_estimators=500,
                    max_depth=10,
                    learning_rate=0.05,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=self.config.RANDOM_STATE,
                    n_jobs=-1
                )
                sample_weights = compute_sample_weight(class_weight='balanced', y=y_train_map)
                xgb_model.fit(X_train, y_train_map, sample_weight=sample_weights)
                xgb_pred = xgb_model.predict(X_test) - 1
                xgb_acc = accuracy_score(y_test, xgb_pred)
                self.modeller['xgboost'] = xgb_model
                sonuclar['xgboost'] = {'dogruluk': xgb_acc, 'tahminler': xgb_pred, 'model': xgb_model}
                print(f"   ✅ XGBoost Doğruluk: {xgb_acc:.4f}")
                print(classification_report(y_test, xgb_pred, target_names=['SAT','BEKLE','AL']))
            except Exception as e:
                print(f"   ⚠️ XGBoost atlandı: {e}")
        
        # 3. Gradient Boosting
        print("\n📈 Gradient Boosting eğitiliyor...")
        gb = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.1,
            random_state=self.config.RANDOM_STATE
        )
        gb.fit(X_train, y_train)
        gb_pred = gb.predict(X_test)
        gb_acc = accuracy_score(y_test, gb_pred)
        self.modeller['gradient_boosting'] = gb
        sonuclar['gradient_boosting'] = {'dogruluk': gb_acc, 'tahminler': gb_pred, 'model': gb}
        print(f"   ✅ Doğruluk: {gb_acc:.4f}")
        
        return sonuclar
    
    def ensemble_olustur(self, sonuclar: dict, X_test, y_test):
        print(f"\n{'='*50}")
        print("🔗 ENSEMBLE OLUŞTURULUYOR")
        print(f"{'='*50}")
        
        mevcut_modeller = list(sonuclar.keys())
        agirliklar = {}
        for model_adi in mevcut_modeller:
            agirliklar[model_adi] = self.config.AGIRLIKLAR.get(model_adi, 1.0/len(mevcut_modeller))
        
        toplam = sum(agirliklar.values())
        agirliklar = {k: v/toplam for k, v in agirliklar.items()}
        
        print("Ağırlıklar:")
        for model_adi, agirlik in agirliklar.items():
            print(f"   {model_adi}: {agirlik:.2%}")
        
        ensemble_oy = np.zeros((len(X_test), 3))
        
        for model_adi in mevcut_modeller:
            model = sonuclar[model_adi]['model']
            try:
                proba = model.predict_proba(X_test)
                agirlik = agirliklar[model_adi]
                ensemble_oy += proba * agirlik
            except:
                pred = sonuclar[model_adi]['tahminler']
                pred_idx = pred + 1
                one_hot = np.zeros((len(pred), 3))
                one_hot[np.arange(len(pred)), pred_idx.astype(int)] = 1
                ensemble_oy += one_hot * agirliklar[model_adi]
        
        ensemble_pred_idx = np.argmax(ensemble_oy, axis=1)
        ensemble_pred = ensemble_pred_idx - 1
        
        ensemble_acc = accuracy_score(y_test, ensemble_pred)
        print(f"\n🎯 Ensemble Doğruluk: {ensemble_acc:.4f}")
        print(classification_report(y_test, ensemble_pred, target_names=['SAT','BEKLE','AL']))
        
        return ensemble_pred, ensemble_oy, ensemble_acc
    
    def kaydet(self, secili_ozellikler: list):
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
            'agirliklar': self.config.AGIRLIKLAR,
            'kutuphane_durum': KUTUPHANE_DURUM,
            'sinif_dagilimi': getattr(self, 'sinif_dagilimi', {}),
            'egitim_tarihi': datetime.now().isoformat()
        }
        
        paket_yolu = self.config.MODEL_KLASORU / f"ai_model_v43_{timestamp}.joblib"
        joblib.dump(kayit_paketi, paket_yolu)
        print(f"\n💾 Model paketi: {paket_yolu}")
        
        son_model = self.config.MODEL_KLASORU / "ai_model_latest.joblib"
        joblib.dump(kayit_paketi, son_model)
        print(f"💾 Son model: {son_model}")
        
        meta = {
            'versiyon': '4.3.2',
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

def main():
    parser = argparse.ArgumentParser(description='Borsa Komutan AI Eğitim v4.3.2')
    parser.add_argument('--hisse', type=str, help='Tek hisse debug')
    parser.add_argument('--limit', type=int, help='Maks hisse sayısı (test için)')
    parser.add_argument('--tune', action='store_true', help='Hiperparametre optimizasyonu')
    parser.add_argument('--karsilastir', action='store_true', help='Karsilastirma backtest modu')
    parser.add_argument('--coklu', action='store_true', help='Coklu donem karsilastirma')
    parser.add_argument('--ticker', type=str, default='AEFES', help='Hisse sembolu (karsilastirma icin)')
    parser.add_argument('--gun', type=int, default=30, help='Backtest gun sayisi')
    args = parser.parse_args()
    
    print("="*60)
    print("🚀 BORSA KOMUTAN v4.3.2 — AI MODEL EĞİTİMİ (580 Hisse)")
    print("="*60)
    print(f"⏰ Başlangıç: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Veri: {Config.VERI_KLASORU}")
    print(f"💾 Model: {Config.MODEL_KLASORU}")
    print(f"🎯 Hedef: {Config.HEDEF_GUN} gün | AL>{Config.AL_ESIK:.0%} | SAT<{Config.SAT_ESIK:.0%}")
    print("="*60)
     # KARŞILAŞTIRMA MODU
    if args.karsilastir:
        print(f"\n🔍 KARŞILAŞTIRMA MODU: {args.ticker}")
        # backtest_karsilastir fonksiyonunu çağır
        # Not: Bu fonksiyon hisse_analiz.py'de olmalı
        try:
            from hisse_analiz import backtest_karsilastir
            backtest_karsilastir(args.ticker, gun_sayisi=args.gun, model_mod="hepsi")
        except ImportError:
            print("❌ hisse_analiz.py bulunamadı veya backtest_karsilastir yok")
        return
    
    # ÇOKLU DÖNEM MODU
    if args.coklu:
        print(f"\n🔍 ÇOKLU DÖNEM MODU: {args.ticker}")
        try:
            from hisse_analiz import coklu_donem_karsilastir
            coklu_donem_karsilastir(args.ticker, model_mod="hepsi")
        except ImportError:
            print("❌ hisse_analiz.py bulunamadı veya coklu_donem_karsilastir yok")
        return
    print("\n📦 Kütüphane Kontrolü:")
    kutuphane_kontrol()
    ml_importlari_yukle()
    
    config = Config()
    
    if args.hisse:
        print(f"\n🔍 TEK HİSSE: {args.hisse}")
        return
    
    print("\n" + "="*60)
    print("📊 VERİ HAZIRLAMA")
    print("="*60)
    
    veri_hazirla = VeriHazirlama(config)
    tum_veri = veri_hazirla.tum_hisseleri_isle(limit=args.limit)
    
    if tum_veri is None or len(tum_veri) == 0:
        print("⛔ Eğitim verisi oluşturulamadı!")
        return
    
    print("\n" + "="*60)
    print("🤖 MODEL EĞİTİMİ")
    print("="*60)
    
    egitici = ModelEgitici(config)
    X_train, X_test, y_train, y_test, secili_ozellikler = egitici.veri_hazirla(tum_veri)
    
    sonuclar = egitici.modelleri_egit(X_train, X_test, y_train, y_test, tune=args.tune)
    
    ensemble_pred, ensemble_oy, ensemble_acc = egitici.ensemble_olustur(sonuclar, X_test, y_test)
    
    print("\n" + "="*60)
    print("💾 MODEL KAYDETME")
    print("="*60)
    model_yolu = egitici.kaydet(secili_ozellikler)
    
    print("\n" + "="*60)
    print("📋 EĞİTİM ÖZETİ")
    print("="*60)
    print(f"✅ Eğitim tamamlandı!")
    print(f"📁 Model: {model_yolu}")
    print(f"🎯 Ensemble Doğruluk: {ensemble_acc:.4f}")
    print(f"📊 Modeller: {', '.join(sonuclar.keys())}")
    print(f"⏰ Bitiş: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    main()