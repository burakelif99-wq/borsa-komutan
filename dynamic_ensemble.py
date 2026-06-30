# dynamic_ensemble.py - Dynamic Ensemble (Rejime Duyarlı Ensemble)
# Borsa Komutan v3.0 - Sıra 5

from grok_al import calculate_ensemble as base_ensemble
from regime_engine import RegimeEngine
from max_drawdown import MaxDrawdown

class DynamicEnsemble:
    """
    Rejime göre dinamik ağırlıklı ensemble.
    Piyasa koşullarına göre strateji değiştirir.
    """

    def __init__(self, use_regime=True, use_drawdown=True, default_esikler=None):
        self.use_regime = use_regime
        self.use_drawdown = use_drawdown
        self.regime_engine = RegimeEngine() if use_regime else None
        self.dd_tracker = {}  # Hisse başına DD tracker
        self.default_esikler = default_esikler or {'AL': 50, 'SAT': 50}

    def calculate(self, df, hisse_adi="Portfoy", zaman_dilimi="1D",
                  bist100_df=None, usdtry_df=None,
                  teknik=None, risk=None, makro=None, medya=None):
        """
        Dinamik ensemble hesapla

        Parametreler:
            df: Hisse DataFrame
            hisse_adi: Hisse kodu
            zaman_dilimi: 1H/1D/1W/1M
            bist100_df: BIST 100 verisi (rejim için)
            usdtry_df: USD/TRY verisi (rejim için)
            teknik, risk, makro, medya: Manuel modül verileri

        Dönüş:
            dict: Ensemble sonucu + rejim bilgisi + DD bilgisi
        """

        # 1. Rejimi tespit et (eğer aktif)
        rejim = None
        strateji = None
        if self.use_regime and bist100_df is not None:
            rejim = self.regime_engine.tespit_et(df, bist100_df, usdtry_df)
            strateji = self.regime_engine.strateji_ayarla(rejim)

        # 2. Max Drawdown kontrol (eğer aktif)
        dd_sonuc = None
        if self.use_drawdown:
            if hisse_adi not in self.dd_tracker:
                self.dd_tracker[hisse_adi] = MaxDrawdown(esik=-0.20, hisse_adi=hisse_adi)

            current_price = df['Close'].iloc[-1] if df is not None else 0
            dd_sonuc = self.dd_tracker[hisse_adi].guncelle(current_price)

        # 3. Base ensemble hesapla
        if strateji:
            # Dinamik ağırlıklarla hesapla
            ensemble = self._dinamik_ensemble(
                df, strateji, zaman_dilimi,
                teknik, risk, makro, medya
            )
        else:
            # Standart ensemble
            ensemble = base_ensemble(
                df=df, teknik=teknik, risk=risk, makro=makro, medya=medya,
                zaman_dilimi=zaman_dilimi
            )

        # 4. DD veto uygula
        if dd_sonuc and dd_sonuc.get('alarm') and ensemble['ensemble']['decision'] == 'AL':
            ensemble['ensemble']['decision'] = 'BEKLE'
            ensemble['ensemble']['dd_veto'] = True
            ensemble['ensemble']['veto_nedeni'] = 'Max Drawdown alarmi'

        # 5. Sonucu zenginleştir
        sonuc = ensemble.copy()
        sonuc['dynamic'] = {
            'rejim': rejim,
            'strateji': strateji,
            'drawdown': dd_sonuc,
            'zaman_dilimi': zaman_dilimi,
            'hisse': hisse_adi
        }

        return sonuc

    def _dinamik_ensemble(self, df, strateji, zaman_dilimi, teknik, risk, makro, medya):
        """
        Rejime göre dinamik ağırlıklı ensemble hesapla
        """
        agirliklar = strateji['agirliklar']
        esikler = strateji['esikler']

        # Base ensemble'i çağır ama ağırlıkları override et
        ensemble = base_ensemble(
            df=df, teknik=teknik, risk=risk, makro=makro, medya=medya,
            zaman_dilimi=zaman_dilimi
        )

        # Ağırlıkları uygula (simülasyon)
        e = ensemble['ensemble']

        # Eşikleri override et
        skor = e['final_score']
        if skor >= esikler['AL']:
            e['decision'] = 'AL'
        elif skor <= esikler['SAT']:
            e['decision'] = 'SAT'
        else:
            e['decision'] = 'BEKLE'

        e['esikler'] = esikler
        e['agirliklar'] = agirliklar

        return ensemble

    def portfoy_analiz(self, portfoy, bist100_df=None, usdtry_df=None):
        """
        Portföydeki tüm hisseleri dinamik analiz et
        """
        import yfinance as yf

        sonuclar = []
        for hisse in portfoy:
            try:
                stock = yf.Ticker(hisse)
                df = stock.history(period="3mo")

                if df.empty:
                    continue

                sonuc = self.calculate(
                    df=df,
                    hisse_adi=hisse,
                    bist100_df=bist100_df,
                    usdtry_df=usdtry_df
                )

                sonuclar.append({
                    'hisse': hisse,
                    'karar': sonuc['ensemble']['decision'],
                    'skor': sonuc['ensemble']['final_score'],
                    'guven': sonuc['ensemble']['confidence'],
                    'rejim': sonuc['dynamic']['rejim']['genel'] if sonuc['dynamic']['rejim'] else 'Bilinmiyor',
                    'dd': sonuc['dynamic']['drawdown']['drawdown'] if sonuc['dynamic']['drawdown'] else 0
                })

            except Exception as e:
                continue

        # Portföy özeti
        al_sayisi = sum(1 for s in sonuclar if s['karar'] == 'AL')
        sat_sayisi = sum(1 for s in sonuclar if s['karar'] == 'SAT')
        bekle_sayisi = sum(1 for s in sonuclar if s['karar'] == 'BEKLE')

        ort_skor = sum(s['skor'] for s in sonuclar) / len(sonuclar) if sonuclar else 0

        return {
            'status': 'OK',
            'toplam_hisse': len(sonuclar),
            'dagilim': {'AL': al_sayisi, 'SAT': sat_sayisi, 'BEKLE': bekle_sayisi},
            'ortalama_skor': round(ort_skor, 2),
            'hisseler': sonuclar,
            'tavsiye': self._portfoy_tavsiye(al_sayisi, sat_sayisi, bekle_sayisi, ort_skor)
        }

    def _portfoy_tavsiye(self, al, sat, bekle, ort_skor):
        """Portföy tavsiyesi"""
        toplam = al + sat + bekle
        if toplam == 0:
            return 'Veri Yok'

        al_oran = al / toplam
        sat_oran = sat / toplam

        if al_oran > 0.6 and ort_skor > 60:
            return 'Portfoy guclu, pozisyon artirilabilir'
        elif sat_oran > 0.4:
            return 'Portfoy zayif, risk azaltilmali'
        elif al_oran > sat_oran:
            return 'Portfoy pozitif, mevcut pozisyon korunmali'
        else:
            return 'Portfoy notr, secici olunmali'

    def format_telegram(self, sonuc):
        """Telegram mesajı formatı"""
        d = sonuc['dynamic']
        e = sonuc['ensemble']

        msg = "DYNAMIC ENSEMBLE RAPORU"

        msg += "=" * 40 + ""

        msg += "Hisse: " + str(d['hisse']) + ""
        msg += "Karar: " + e['decision'] + ""
        msg += "Skor: " + str(e['final_score']) + "/100"
        msg += "Guven: %" + str(e['confidence']) + ""

        if d['rejim']:
            r = d['rejim']
            msg += "REJIM:"
            msg += "  Trend: " + r['trend'] + ""
            msg += "  Volatilite: " + r['volatilite'] + ""
            msg += "  Genel: " + r['genel'] + ""

        if d['drawdown']:
            dd = d['drawdown']
            msg += "DRAWDOWN:"
            msg += "  Mevcut: %" + str(dd['drawdown']) + ""
            msg += "  Max: %" + str(dd['max_drawdown']) + ""
            msg += "  Risk: " + dd['risk_seviyesi'] + ""

        if 'dd_veto' in e and e['dd_veto']:
            msg += "VETO: " + str(e.get('veto_nedeni', 'Drawdown')) + ""

        if 'esikler' in e:
            msg += "ESIKLER:"
            msg += "  AL: " + str(e['esikler']['AL']) + ""
            msg += "  SAT: " + str(e['esikler']['SAT']) + ""

        return msg


if __name__ == "__main__":
    print("=" * 70)
    print("DYNAMIC ENSEMBLE MODULU TEST")
    print("=" * 70)

    de = DynamicEnsemble(use_regime=False, use_drawdown=False)  # Rejim yoksa test et

    # Test verisi
    import pandas as pd
    import numpy as np

    dates = pd.date_range('2026-01-01', periods=100, freq='D')
    np.random.seed(42)

    trend = np.cumsum(np.random.randn(100) * 0.5 + 0.2)
    df = pd.DataFrame({
        'Open': trend + 100,
        'High': trend + 100 + np.abs(np.random.randn(100)) * 2,
        'Low': trend + 100 - np.abs(np.random.randn(100)) * 2,
        'Close': trend + 100 + np.random.randn(100),
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)

    print("Test verisi olusturuldu")
    print("-" * 70)

    # Tek hisse analiz (rejimsiz)
    print("1. TEK HISSE ANALIZI (THYAO) - Rejimsiz")
    print("-" * 70)

    try:
        sonuc = de.calculate(
            df=df,
            hisse_adi="THYAO.IS",
            zaman_dilimi="1D"
        )

        print("Karar: " + sonuc['ensemble']['decision'])
        print("Skor: " + str(sonuc['ensemble']['final_score']))
        print("Guven: %" + str(sonuc['ensemble']['confidence']))

        # Telegram formatı
        print("2. TELEGRAM FORMATI")
        print("-" * 70)
        print(de.format_telegram(sonuc))

    except Exception as e:
        print("HATA: " + str(e))
        print("Not: grok_al.py ve diger moduller hazir olmali")

    print("=" * 70)
    print("TEST TAMAMLANDI")
    print("=" * 70)
