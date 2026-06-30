# =============================================================================
# ai_skorlayici.py - Borsa Komutan v4.3 (Ensemble AI + Feature Engineering)
# =============================================================================

import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    import yfinance as yf
    YF_AKTIF = True
except ImportError:
    YF_AKTIF = False

try:
    import ta
    TA_AKTIF = True
except ImportError:
    print("[UYARI] 'ta' kutuphanesi yuklenemedi. pip install ta")
    TA_AKTIF = False

try:
    import xgboost as xgb
    XGB_AKTIF = True
except ImportError:
    print("[UYARI] 'xgboost' yuklenemedi. Sadece RF kullanilacak.")
    XGB_AKTIF = False

from sklearn.ensemble import RandomForestClassifier, VotingClassifier


class AIModel:
    """Ensemble AI Model (RF + XGBoost) + Gelişmiş Feature Engineering"""
    
    def __init__(self, model_path=None):
        self.scaler = None
        self.secici = None
        self.secili_ozellikler = []
        self.ozellik_isimleri = []
        self.al_esik = 0.45  # AL threshold: AL olasiligi bu esigin altindaysa BEKLE'ye cevir (sweep optimal)
        
        # Model dizini
        model_dir = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\modeller"
        
        # En son modeli otomatik bul (once v431, sonra v43)
        if model_path is None:
            modeller = [
                f for f in os.listdir(model_dir) 
                if (f.startswith('ai_model_v43_') or f.startswith('ai_model_v431_'))
                and f.endswith('.joblib') and not f.endswith('.bak')
            ]
            
            if modeller:
                modeller.sort(reverse=True)
                model_path = os.path.join(model_dir, modeller[0])
                print(f"[OK] En son model: {modeller[0]}")
            else:
                pipeline_path = os.path.join(model_dir, 'pipeline_ai_model_latest.joblib')
                if os.path.exists(pipeline_path):
                    model_path = pipeline_path
                    print("[OK] Pipeline model bulundu")
                else:
                    model_path = None
        
        # Model yükle veya oluştur
        if model_path and os.path.exists(model_path):
            try:
                paket = joblib.load(model_path)
                print(f"[OK] AI Model yüklendi: {os.path.basename(model_path)}")
                if isinstance(paket, dict) and 'modeller' in paket:
                    self.paket = paket
                    self.scaler = paket.get('scaler')
                    self.secici = paket.get('secici')
                    self.ozellik_isimleri = paket.get('ozellik_isimleri', [])
                    self.secili_ozellikler = paket.get('secili_ozellikler', [])
                    self.sinif_dagilimi = paket.get('sinif_dagilimi', {})
                    self.model = paket['modeller'].get('random_forest')
                    print(f"   Package model: {list(paket['modeller'].keys())}, sinif_dagilimi: {bool(self.sinif_dagilimi)}")
                else:
                    self.model = paket
                    print(f"   Model tipi: {type(self.model).__name__}")
            except Exception as e:
                print(f"[UYARI] Model yüklenemedi: {e}")
                self._model_olustur()
        else:
            print("[UYARI] Model dosyası bulunamadı, yeni model oluşturuluyor...")
            self._model_olustur()
    
    def _model_olustur(self):
        """Yeni ensemble model olustur"""
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1
        )
        
        if XGB_AKTIF:
            self.xgb_model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=10,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            
            self.ensemble = VotingClassifier(
                estimators=[
                    ('rf', self.rf_model),
                    ('xgb', self.xgb_model)
                ],
                voting='soft'
            )
            self.model = self.ensemble
            print("[OK] Ensemble Model (RF + XGBoost) olusturuldu")
        else:
            self.model = self.rf_model
            print("[OK] Random Forest Model olusturuldu")
    
    def ozellikleri_hazirla(self, data):
        """Gelismis feature engineering (RSI, MACD, Bollinger, vb.)"""
        if data is None or len(data) < 50:
            return None
        
        df = data.copy()
        
        # Temel getiri
        df['returns'] = df['Close'].pct_change()
        df['log_returns'] = np.log(df['Close'] / df['Close'].shift(1))
        
        # Hareketli ortalamalar
        for window in [5, 10, 20, 50]:
            df[f'sma_{window}'] = df['Close'].rolling(window).mean()
            df[f'ema_{window}'] = df['Close'].ewm(span=window).mean()
            df[f'close_sma_ratio_{window}'] = df['Close'] / df[f'sma_{window}']
        
        # Volatilite
        df['volatility_10'] = df['returns'].rolling(10).std()
        df['volatility_20'] = df['returns'].rolling(20).std()
        df['volatility_ratio'] = df['volatility_10'] / df['volatility_20']
        
        # RSI
        if TA_AKTIF:
            df['rsi_14'] = ta.momentum.rsi(df['Close'], window=14)
            df['rsi_7'] = ta.momentum.rsi(df['Close'], window=7)
            
            # MACD
            macd = ta.trend.MACD(df['Close'])
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            df['macd_diff'] = macd.macd_diff()
            df['macd_diff_norm'] = df['macd_diff'] / df['Close']
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(df['Close'])
            df['bb_high'] = bb.bollinger_hband()
            df['bb_low'] = bb.bollinger_lband()
            df['bb_width'] = bb.bollinger_wband()
            df['bb_position'] = (df['Close'] - df['bb_low']) / (df['bb_high'] - df['bb_low'])
            
            # Stochastic
            stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'])
            df['stoch_k'] = stoch.stoch()
            df['stoch_d'] = stoch.stoch_signal()
            
            # ADX (Trend gucu)
            adx = ta.trend.ADXIndicator(df['High'], df['Low'], df['Close'])
            df['adx'] = adx.adx()
            df['adx_pos'] = adx.adx_pos()
            df['adx_neg'] = adx.adx_neg()
            
            # OBV
            df['obv'] = ta.volume.on_balance_volume(df['Close'], df['Volume'])
            df['obv_ema'] = df['obv'].ewm(span=20).mean()
            
            # ATR
            atr = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close'])
            df['atr'] = atr.average_true_range()
            df['atr_ratio'] = df['atr'] / df['Close']
            
            # Momentum
            df['momentum_10'] = df['Close'] / df['Close'].shift(10) - 1
            df['momentum_20'] = df['Close'] / df['Close'].shift(20) - 1
            
            # Williams %R
            wr = ta.momentum.WilliamsRIndicator(df['High'], df['Low'], df['Close'])
            df['williams_r'] = wr.williams_r()
        
        # Hacim ozellikleri
        df['volume_sma_20'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_sma_20']
        df['volume_price_trend'] = df['Volume'] * df['returns']
        
        # Fiyat ozellikleri
        df['high_low_ratio'] = df['High'] / df['Low']
        df['close_open_ratio'] = df['Close'] / df['Open']
        
        # Trend ozellikleri
        df['trend_20'] = (df['Close'] - df['Close'].shift(20)) / df['Close'].shift(20)
        df['trend_50'] = (df['Close'] - df['Close'].shift(50)) / df['Close'].shift(50)
        
        # NaN temizle
        df = df.dropna()
        
        if len(df) < 10:
            return None
        
        # Ozellik vektoru (son satir)
        exclude = ['Open', 'High', 'Low', 'Close', 'Volume', 'Adj Close']
        feature_cols = [c for c in df.columns if c not in exclude]
        
        self.ozellik_isimleri = feature_cols
        
        return df[feature_cols].iloc[-1:]
    
    def etiket_olustur(self, data, esik_al=0.02, esik_sat=-0.02):
        """Gelecek gun getirisine gore etiket"""
        returns = data['Close'].pct_change().shift(-1).dropna()
        
        labels = []
        for ret in returns:
            if ret > esik_al:
                labels.append('AL')
            elif ret < esik_sat:
                labels.append('SAT')
            else:
                labels.append('BEKLE')
        
        return labels
    
    def egit(self, hisse_listesi, period="5y", esik_al=0.02, esik_sat=-0.02):
        """Tum hisselerle ensemble model egit"""
        import yfinance as yf
        
        print(f"\n{'='*60}")
        print(f"🚀 AI EGITIMI BASLIYOR")
        print(f"   Hisseler: {len(hisse_listesi)}")
        print(f"   Period: {period}")
        print(f"   AL esik: %{esik_al*100}, SAT esik: %{esik_sat*100}")
        print(f"{'='*60}")
        
        X_list = []
        y_list = []
        
        for i, ticker in enumerate(hisse_listesi):
            try:
                if i % 50 == 0:
                    print(f"  📊 {i+1}/{len(hisse_listesi)} hisse isleniyor...")
                
                # 5 yillik veri cek
                data = yf.download(ticker + '.IS', period=period, progress=False)
                if len(data) < 100:
                    continue
                
                # Ozellikleri hazirla
                X = self.ozellikleri_hazirla(data)
                if X is None or len(X) == 0:
                    continue
                
                # Etiketleri olustur
                labels = self.etiket_olustur(data, esik_al, esik_sat)
                
                # X ve y'yi eslestir
                # X son satir haric (cunku etiket gelecek gun)
                X_full = data.copy()
                X_full = self.ozellikleri_hazirla(X_full)
                if X_full is None or len(X_full) < 2:
                    continue
                
                # Son satir haric al (etiket icin)
                X_train = X_full.iloc[:-1]
                y_train = labels[:len(X_train)]
                
                if len(X_train) != len(y_train):
                    min_len = min(len(X_train), len(y_train))
                    X_train = X_train.iloc[:min_len]
                    y_train = y_train[:min_len]
                
                X_list.append(X_train)
                y_list.extend(y_train)
                
            except Exception as e:
                print(f"    ⚠️ {ticker} hatasi: {str(e)[:60]}")
                continue
        
        if len(X_list) == 0:
            print("❌ Egitim verisi yok!")
            return False
        
        # Birlestir
        X_final = pd.concat(X_list, ignore_index=True)
        y_final = pd.Series(y_list)
        
        # Sinif dagilimi
        print(f"\n{'='*60}")
        print(f"📊 EGITIM VERISETI")
        print(f"{'='*60}")
        print(f"   Toplam ornek: {len(X_final)}")
        print(f"   Ozellik sayisi: {len(X_final.columns)}")
        print(f"   Sinif dagilimi:")
        for cls, count in y_final.value_counts().items():
            print(f"      {cls}: {count} (%{count/len(y_final)*100:.1f})")
        
        # Modeli egit
        print(f"\n⏳ Model egitiliyor...")
        self.model.fit(X_final, y_final)
        
        # Kaydet
        model_dir = os.path.join(os.path.dirname(__file__), 'modeller')
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, 'ensemble_ai_model_v43.joblib')
        joblib.dump(self.model, model_path)
        
        # Pipeline modeline de kaydet (geriye uyumluluk)
        pipeline_path = os.path.join(model_dir, 'pipeline_ai_model_latest.joblib')
        joblib.dump(self.model, pipeline_path)
        
        print(f"\n✅ AI Egitimi tamamlandi!")
        print(f"   Model: {model_path}")
        print(f"   Ozellik sayisi: {len(X_final.columns)}")
        print(f"{'='*60}")
        
        return True
    
    def _remap_proba(self, proba, classes):
        """Model probasini [-1(SAT), 0(BEKLE), 1(AL)] sirasina cevir"""
        has_neg1 = -1 in classes or -1.0 in classes
        remapped = np.zeros(3)
        for i, c in enumerate(classes):
            if c in (-1.0, -1):
                remapped[0] = proba[i]
            elif c in (0.0, 0):
                if has_neg1:
                    remapped[1] = proba[i]  # [-1,0,1] → 0=BEKLE
                else:
                    remapped[0] = proba[i]  # [0,1,2] → 0=SAT
            elif c in (1.0, 1):
                if has_neg1:
                    remapped[2] = proba[i]  # [-1,0,1] → 1=AL
                else:
                    remapped[1] = proba[i]  # [0,1,2] → 1=BEKLE
            elif c in (2.0, 2):
                remapped[2] = proba[i]  # [0,1,2] → 2=AL
        return remapped

    def _get_regime(self):
        """BIST-100 20-gun getirisine gore piyasa rejimini tespit et (1 saat cache)"""
        if not YF_AKTIF:
            return 'sideways'
        now = datetime.now()
        if hasattr(self, '_regime_cache') and hasattr(self, '_regime_cache_time'):
            if (now - self._regime_cache_time).total_seconds() < 3600:
                return self._regime_cache
        try:
            bist = yf.download('XU100.IS', period='3mo', progress=False, auto_adjust=True)
            if bist is not None and len(bist) > 25:
                ret_20 = float(bist['Close'].squeeze().pct_change(20).iloc[-1])
                if ret_20 > 0.03:
                    regime = 'bull'
                elif ret_20 < -0.03:
                    regime = 'bear'
                else:
                    regime = 'sideways'
            else:
                regime = 'sideways'
        except Exception:
            regime = 'sideways'
        # Threshold'u rejime gore ayarla
        if regime == 'bull':
            self.al_esik = 0.40
        elif regime == 'bear':
            self.al_esik = 0.55
        else:
            self.al_esik = 0.47
        self._regime_cache = regime
        self._regime_cache_time = now
        return regime

    def _package_tahmin(self, data):
        from ai_egit import TeknikIndikatorler
        
        # Piyasa rejimine gore threshold'u dinamik ayarla
        self._get_regime()
        
        oz = TeknikIndikatorler.tum_ozellikler(data)
        if oz is None or len(oz) == 0:
            return self._varsayilan_sonuc()
        
        row = oz.iloc[[-1]].copy()
        for col in self.ozellik_isimleri:
            if col not in row.columns:
                row[col] = 0.0
        X = row[self.ozellik_isimleri].fillna(0).replace([np.inf, -np.inf], 0).values
        
        if self.scaler:
            X = self.scaler.transform(X)
        if self.secici:
            X = self.secici.transform(X)
        
        modeller = self.paket.get('modeller', {})
        regime = self._regime_cache if hasattr(self, '_regime_cache') else 'sideways'
        
        # GB primary signal
        gb = modeller.get('gradient_boosting')
        if gb is not None:
            gb_p = gb.predict_proba(X)[0]
            gb_remap = self._remap_proba(gb_p, gb.classes_)
            gb_al = gb_remap[2]
        else:
            gb_al = 0.0
        
        # Regime-based decision
        rf_al = None
        reason = None
        if gb_al >= self.al_esik:
            if regime == 'bear':
                rf = modeller.get('random_forest')
                if rf is not None:
                    rf_p = rf.predict_proba(X)[0]
                    rf_remap = self._remap_proba(rf_p, rf.classes_)
                    rf_al = rf_remap[2]
                else:
                    rf_al = 1.0
                if rf_al >= 0.35:
                    karar_al = True
                    reason = 'GB_PASS'
                else:
                    karar_al = False
                    reason = 'RF_GUARD'
            else:
                karar_al = True
                reason = 'GB_PASS'
        else:
            karar_al = False
            reason = 'GB_LOW'
        
        proba = gb_remap if karar_al else np.array([0.0, 1.0, 0.0])
        std_classes = np.array([-1, 0, 1])
        sonuc = self._sonuc_uret(proba, std_classes)
        sonuc['detay']['rejim'] = regime
        sonuc['detay']['esik'] = self.al_esik
        sonuc['detay']['gb_al'] = round(float(gb_al), 4)
        sonuc['detay']['rf_al'] = round(float(rf_al), 4) if rf_al is not None else None
        sonuc['detay']['rf_guard_aktif'] = (regime == 'bear')
        sonuc['detay']['reason'] = reason
        return sonuc
    
    def _varsayilan_sonuc(self):
        return {'ai_skor': 50, 'etiket': 'BEKLE', 'guven': 0.0,
                'detay': {}, 'timestamp': datetime.now().isoformat()}
    
    def _sonuc_uret(self, proba, classes):
        sinif_list = list(classes)
        # Map float classes [-1, 0, 1] or string classes ['SAT', 'BEKLE', 'AL']
        sinif_etiket = {-1: 'SAT', 0: 'BEKLE', 1: 'AL'}
        
        idx_sat = sinif_list.index('SAT') if 'SAT' in sinif_list else (sinif_list.index(-1.0) if -1.0 in sinif_list else 0)
        idx_bekle = sinif_list.index('BEKLE') if 'BEKLE' in sinif_list else (sinif_list.index(0.0) if 0.0 in sinif_list else 1)
        idx_al = sinif_list.index('AL') if 'AL' in sinif_list else (sinif_list.index(1.0) if 1.0 in sinif_list else 2)
        
        sat_prob = float(proba[idx_sat])
        bekle_prob = float(proba[idx_bekle])
        al_prob = float(proba[idx_al])
        
        en_yuksek_idx = int(np.argmax(proba))
        en_yuksek_sinif = sinif_list[en_yuksek_idx]
        etiket = sinif_etiket.get(en_yuksek_sinif, 'BEKLE')
        if isinstance(en_yuksek_sinif, str) and en_yuksek_sinif in ['AL', 'SAT', 'BEKLE']:
            etiket = en_yuksek_sinif
        
        # AL esik kontrolu: AL olasiligi esigin altindaysa BEKLE'ye cevir
        if etiket == 'AL' and self.al_esik > 0 and al_prob < self.al_esik:
            etiket = 'BEKLE'
        
        ai_skor = int((al_prob - sat_prob) * 50 + 50)
        ai_skor = max(0, min(100, ai_skor))
        
        return {
            'ai_skor': ai_skor,
            'etiket': etiket,
            'guven': round(max(sat_prob, bekle_prob, al_prob), 4),
            'detay': {
                'sat_olasilik': round(sat_prob, 4),
                'bekle_olasilik': round(bekle_prob, 4),
                'al_olasilik': round(al_prob, 4),
            },
            'timestamp': datetime.now().isoformat()
        }
    
    def tahmin_et(self, data):
        if hasattr(self, 'paket') and self.paket:
            return self._package_tahmin(data)
        
        X = self.ozellikleri_hazirla(data)
        if X is None:
            return self._varsayilan_sonuc()
        
        print(f"X shape: {X.shape}")
        if self.scaler:
            X_scaled = self.scaler.transform(X)
        if self.secici:
            X_secili = self.secici.transform(X_scaled if self.scaler else X)
        
        proba = self.model.predict_proba(X)[0]
        return self._sonuc_uret(proba, self.model.classes_)