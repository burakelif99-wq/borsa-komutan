"""
komutan_karar.py - Borsa Komutan v4.0
Tam Otomatik Karar Motoru + Deneme-Yanilma Ogrenmesi
"""

import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Proje dizini
BASE_DIR = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi"
OGRENME_DB = os.path.join(BASE_DIR, "ogrenme_db.json")
ARŞIV_DIR = os.path.join(BASE_DIR, "arsiv")
os.makedirs(ARŞIV_DIR, exist_ok=True)


# =============================================================================
# OGRENME MOTORU (Deneme-Yanilma)
# =============================================================================

class OgrenmeMotoru:
    """
    Q-Learning tabanli deneme-yanilma ogrenme motoru.
    Her kararin sonucunu kaydeder, basariya gore agirliklari gunceller.
    """

    def __init__(self, db_path=OGRENME_DB):
        self.db_path = db_path
        self.veriler = self._yukle()
        self.alfa = 0.1   # Ogrenme hizi
        self.gamma = 0.9  # Gelecek odul onemi

    def _yukle(self):
        """Veritabanini yukle."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'kararlar': [],
            'agirliklar': {},
            'uzman_basari': {},
            'portfoy': {},
            'istatistik': {
                'toplam_karar': 0,
                'basarili': 0,
                'basarisiz': 0,
                'toplam_kar': 0.0,
                'toplam_zarar': 0.0
            }
        }

    def _kaydet(self):
        """Veritabanini kaydet."""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.veriler, f, ensure_ascii=False, indent=2)

    def karar_kaydet(self, ticker, skorlar, ensemble, karar, fiyat):
        """
        Yeni karar kaydet.

        Args:
            ticker: Hisse kodu
            skorlar: Uzman skorlari (dict)
            ensemble: Ensemble skor
            karar: 'AL', 'SAT', veya 'BEKLE'
            fiyat: Anlik fiyat
        """
        kayit = {
            'id': f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'tarih': datetime.now().isoformat(),
            'ticker': ticker,
            'skorlar': skorlar,
            'ensemble': ensemble,
            'karar': karar,
            'fiyat': fiyat,
            'gerceklesen_kar': None,
            'gerceklesen_fiyat': None,
            'durum': 'BEKLIYOR'  # BEKLIYOR, KAPANDI
        }

        self.veriler['kararlar'].append(kayit)
        self.veriler['istatistik']['toplam_karar'] += 1
        self._kaydet()

        return kayit['id']

    def sonuc_kaydet(self, karar_id, gerceklesen_fiyat):
        """
        Kararin sonucunu kaydet (1-5 gun sonra).

        Args:
            karar_id: Karar ID
            gerceklesen_fiyat: Gerceklesen fiyat
        """
        for k in self.veriler['kararlar']:
            if k['id'] == karar_id and k['durum'] == 'BEKLIYOR':
                k['gerceklesen_fiyat'] = gerceklesen_fiyat

                # Kar/zarar hesapla
                if k['karar'] == 'AL':
                    k['gerceklesen_kar'] = (gerceklesen_fiyat - k['fiyat']) / k['fiyat']
                elif k['karar'] == 'SAT':
                    k['gerceklesen_kar'] = (k['fiyat'] - gerceklesen_fiyat) / k['fiyat']
                else:
                    k['gerceklesen_kar'] = 0.0

                k['durum'] = 'KAPANDI'

                # Istatistik guncelle
                if k['gerceklesen_kar'] > 0:
                    self.veriler['istatistik']['basarili'] += 1
                    self.veriler['istatistik']['toplam_kar'] += k['gerceklesen_kar']
                else:
                    self.veriler['istatistik']['basarisiz'] += 1
                    self.veriler['istatistik']['toplam_zarar'] += abs(k['gerceklesen_kar'])

                # Uzman basarisini guncelle
                self._uzman_basari_guncelle(k)

                self._kaydet()
                return True

        return False

    def _uzman_basari_guncelle(self, karar):
        """Uzman basarisini guncelle."""
        for uzman, skor in karar['skorlar'].items():
            if uzman not in self.veriler['uzman_basari']:
                self.veriler['uzman_basari'][uzman] = {
                    'toplam': 0, 'basarili': 0, 'toplam_skor': 0.0
                }

            self.veriler['uzman_basari'][uzman]['toplam'] += 1
            self.veriler['uzman_basari'][uzman]['toplam_skor'] += skor

            if karar['gerceklesen_kar'] > 0:
                self.veriler['uzman_basari'][uzman]['basarili'] += 1

    def uzman_basari_orani(self, uzman_adi):
        """Belirli uzmanin basari orani."""
        if uzman_adi not in self.veriler['uzman_basari']:
            return 0.5  # Varsayilan

        u = self.veriler['uzman_basari'][uzman_adi]
        if u['toplam'] == 0:
            return 0.5

        return u['basarili'] / u['toplam']

    def genel_basari_orani(self):
        """Genel basari orani."""
        i = self.veriler['istatistik']
        if i['toplam_karar'] == 0:
            return 0.0
        return i['basarili'] / i['toplam_karar']

    def kar_zarar_ozet(self):
        """Kar/zarar ozeti."""
        i = self.veriler['istatistik']
        return {
            'toplam_karar': i['toplam_karar'],
            'basarili': i['basarili'],
            'basarisiz': i['basarisiz'],
            'basari_orani': self.genel_basari_orani(),
            'toplam_kar': i['toplam_kar'],
            'toplam_zarar': i['toplam_zarar'],
            'net_kar': i['toplam_kar'] - i['toplam_zarar']
        }


# =============================================================================
# KOMUTAN KARAR MOTORU (Tam Otomatik)
# =============================================================================

class KomutanKararMotoru:
    """
    %100 Otomik Karar Motoru.
    Kullanici mudahalesi yok. Deneme-yanilma ile ogrenir.
    """

    def __init__(self):
        self.ogrenme = OgrenmeMotoru()

        # Varsayilan agirliklar (esit dagilim)
        self.varsayilan_agirliklar = {
            'teknik': 0.125,
            'temel': 0.125,
            'yatirimci': 0.125,
            'risk': 0.125,
            'risk_tolerance': 0.125,
            'makro': 0.125,
            'mikro': 0.125,
            'max_drawdown': 0.125
        }

        # Ogrenilmis agirliklar (varsa)
        self.agirliklar = self.ogrenme.veriler.get('agirliklar', self.varsayilan_agirliklar.copy())

        # Karar esikleri (ogrenilecek)
        self.al_esik = 0.6
        self.sat_esik = 0.4

        # Risk yonetimi
        self.max_risk = 0.3
        self.max_pozisyon = 10  # Max 10 hisse

    def karar_ver(self, ticker, skorlar, fiyat, pm_verileri=None):
        """
        Tam otomatik karar ver.

        Args:
            ticker: Hisse kodu
            skorlar: Uzman skorlari (dict)
            fiyat: Anlik fiyat
            pm_verileri: Pre-market verileri (opsiyonel)

        Returns:
            dict: Karar detaylari
        """
        # 1. PM verilerini entegre et
        if pm_verileri:
            skorlar = self._pm_entegre_et(skorlar, pm_verileri)

        # 2. Ogrenilmis agirliklari uygula
        agirlikli_skorlar = {}
        for uzman, skor in skorlar.items():
            agirlik = self.agirliklar.get(uzman, 0.125)
            agirlikli_skorlar[uzman] = skor * agirlik

        # 3. Ensemble skor hesapla
        ensemble_skor = sum(agirlikli_skorlar.values())
        ensemble_skor = max(0.0, min(1.0, ensemble_skor))

        # 4. Risk kontrolu
        risk_durumu = self._risk_kontrol(skorlar, ensemble_skor)

        # 5. Portfoy kontrolu
        portfoy_durumu = self._portfoy_kontrol(ticker)

        # 6. KARAR VER (Tam Otomatik)
        karar = self._karar_olustur(ensemble_skor, risk_durumu, portfoy_durumu, pm_verileri)

        # 7. Kaydet (ogrenme icin)
        karar_id = self.ogrenme.karar_kaydet(ticker, skorlar, ensemble_skor, karar['karar'], fiyat)
        karar['id'] = karar_id

        return karar

    def _pm_entegre_et(self, skorlar, pm):
        """Pre-market verilerini skorlara entegre et."""

        # PM piyasa durumu
        piyasa = pm.get('piyasa_durumu', 'Notr')

        if piyasa == 'Pozitif':
            skorlar['yatirimci'] += 0.08
            skorlar['teknik'] += 0.05
        elif piyasa == 'Negatif':
            skorlar['risk'] -= 0.05
            skorlar['makro'] -= 0.03

        # PM firsatlari
        for firsat in pm.get('firsatlar', []):
            if firsat.get('gap', 0) > 2:
                skorlar['yatirimci'] += 0.05
                skorlar['teknik'] += 0.03

        # PM riskleri
        for risk in pm.get('riskler', []):
            if risk.get('gap', 0) < -2:
                skorlar['risk'] -= 0.05

        # Normalize et (0-1 arasi)
        for k in skorlar:
            skorlar[k] = max(0.0, min(1.0, skorlar[k]))

        return skorlar

    def _risk_kontrol(self, skorlar, ensemble):
        """Risk durumunu kontrol et."""
        risk_skor = skorlar.get('risk', 0.5)
        max_dd = skorlar.get('max_drawdown', 0.5)

        if risk_skor < 0.1 or max_dd < 0.2:
            return {'durum': 'TEHLIKELI', 'seviye': 'YUKSEK'}
        elif risk_skor < 0.3:
            return {'durum': 'DUSUK', 'seviye': 'ORTA'}
        else:
            return {'durum': 'GUVENLI', 'seviye': 'DUSUK'}

    def _portfoy_kontrol(self, ticker):
        """Portfoy durumunu kontrol et."""
        acik_pozisyon = sum(1 for k in self.ogrenme.veriler['kararlar']
                          if k['durum'] == 'BEKLIYOR' and k['karar'] == 'AL')

        return {
            'musait': acik_pozisyon < self.max_pozisyon,
            'acik_pozisyon': acik_pozisyon,
            'max_pozisyon': self.max_pozisyon
        }

    def _karar_olustur(self, ensemble, risk, portfoy, pm):
        """Tam otomatik karar olustur."""

        # KARAR MATRISI (Tam Otomatik - Kullanici mudahalesi yok)

        # 1. COK GUVENLI AL (Skor > 0.75, Risk dusuk, Portfoy musait)
        if ensemble >= 0.75 and risk['durum'] == 'GUVENLI' and portfoy['musait']:
            return {
                'karar': 'AL',
                'guven': 'COK_YUKSEK',
                'miktar': 'TAM',
                'neden': f"Ensemble: {ensemble:.3f}, Risk: {risk['seviye']}, PM: {pm.get('piyasa_durumu', 'N/A') if pm else 'N/A'}",
                'beklenen_getiri': ensemble * 0.15
            }

        # 2. NORMAL AL (Skor > 0.6, Risk kabul edilebilir)
        elif ensemble >= self.al_esik and risk['durum'] != 'TEHLIKELI' and portfoy['musait']:
            return {
                'karar': 'AL',
                'guven': 'YUKSEK',
                'miktar': 'YARIM',
                'neden': f"Ensemble: {ensemble:.3f}, Risk: {risk['seviye']}",
                'beklenen_getiri': ensemble * 0.10
            }

        # 3. ZORUNLU SAT (Skor < 0.25 veya Risk cok yuksek)
        elif ensemble <= 0.25 or risk['durum'] == 'TEHLIKELI':
            return {
                'karar': 'SAT',
                'guven': 'COK_YUKSEK',
                'miktar': 'TAM',
                'neden': f"Dusuk skor: {ensemble:.3f} veya Yuksek risk: {risk['seviye']}",
                'beklenen_getiri': -0.05
            }

        # 4. NORMAL SAT (Skor < 0.4)
        elif ensemble <= self.sat_esik:
            return {
                'karar': 'SAT',
                'guven': 'ORTA',
                'miktar': 'YARIM',
                'neden': f"Dusuk skor: {ensemble:.3f}",
                'beklenen_getiri': -0.02
            }

        # 5. BEKLE (Nötr bölge)
        else:
            return {
                'karar': 'BEKLE',
                'guven': 'DUSUK',
                'miktar': 'YOK',
                'neden': f"Nötr bölge: {ensemble:.3f}",
                'beklenen_getiri': 0.0
            }

    def ogren(self, karar_id, gerceklesen_fiyat):
        """
        Deneme-yanilma ile ogren.
        Kar/zarar gerceklesince cagrilir.

        Args:
            karar_id: Karar ID
            gerceklesen_fiyat: Gerceklesen fiyat
        """
        # Sonucu kaydet
        basarili = self.ogrenme.sonuc_kaydet(karar_id, gerceklesen_fiyat)

        if not basarili:
            print(f"[HATA] Karar bulunamadi: {karar_id}")
            return

        # Karari bul
        karar = None
        for k in self.ogrenme.veriler['kararlar']:
            if k['id'] == karar_id:
                karar = k
                break

        if not karar or karar['gerceklesen_kar'] is None:
            return

        gerceklesen = karar['gerceklesen_kar']

        # Q-Learning: Agirliklari guncelle
        print(f"\n[ÖĞRENME] {karar['ticker']}: Beklenen {karar.get('beklenen_getiri', 0):.2%}, "
              f"Gerçekleşen {gerceklesen:.2%}")

        for uzman, skor in karar['skorlar'].items():
            if uzman not in self.agirliklar:
                continue

            # Hata hesapla (beklenen - gerceklesen)
            hata = karar.get('beklenen_getiri', 0) - gerceklesen

            # Uzman basarisi
            uzman_basari = self.ogrenme.uzman_basari_orani(uzman)

            # Agirlik guncelleme
            if gerceklesen > 0:  # Kar ettiysek
                # Basarili uzmanin agirligini artir
                if skor > 0.5:
                    self.agirliklar[uzman] += self.ogrenme.alfa * abs(hata) * uzman_basari
                else:
                    self.agirliklar[uzman] -= self.ogrenme.alfa * abs(hata) * 0.5
            else:  # Zarar ettiysek
                # Basarisiz uzmanin agirligini azalt
                if skor > 0.5:
                    self.agirliklar[uzman] -= self.ogrenme.alfa * abs(hata)
                else:
                    self.agirliklar[uzman] += self.ogrenme.alfa * abs(hata) * 0.3

        # Normalize et (toplam 1 olmali)
        toplam = sum(self.agirliklar.values())
        if toplam > 0:
            for k in self.agirliklar:
                self.agirliklar[k] = max(0.01, self.agirliklar[k] / toplam)

        # Kaydet
        self.ogrenme.veriler['agirliklar'] = self.agirliklar
        self.ogrenme._kaydet()

        # Rapor
        print(f"[ÖĞRENME] Yeni agirliklar:")
        for u, a in sorted(self.agirliklar.items(), key=lambda x: x[1], reverse=True):
            print(f"  {u}: {a:.4f}")

        # Istatistik
        ozet = self.ogrenme.kar_zarar_ozet()
        print(f"[ÖĞRENME] Genel basari: {ozet['basari_orani']:.1%}, "
              f"Net kar: {ozet['net_kar']:.2%}")

    def istatistik_rapor(self):
        """Detayli istatistik raporu."""
        ozet = self.ogrenme.kar_zarar_ozet()

        rapor = f"""
{'='*60}
  KOMUTAN KARAR MOTORU - İSTATİSTİK RAPORU
{'='*60}

  Genel Performans:
    Toplam Karar: {ozet['toplam_karar']}
    Başarili: {ozet['basarili']} ({ozet['basari_orani']:.1%})
    Başarisiz: {ozet['basarisiz']}
    Net Kar: {ozet['net_kar']:.2%}

  Uzman Basarilari:
"""
        for uzman in sorted(self.agirliklar.keys()):
            basari = self.ogrenme.uzman_basari_orani(uzman)
            agirlik = self.agirliklar.get(uzman, 0)
            rapor += f"    {uzman:15s}: Basari {basari:.1%}, Agirlik {agirlik:.4f}"
            if agirlik > 0.15:
                rapor += " ★"
            rapor += "\n"

        rapor += f"\n{'='*60}\n"

        return rapor


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("="*60)
    print("KOMUTAN KARAR MOTORU - TEST")
    print("="*60)

    komutan = KomutanKararMotoru()

    # Test skorlari
    skorlar = {
        'teknik': 0.85,
        'temel': 0.50,
        'yatirimci': 1.00,
        'risk': 0.10,
        'risk_tolerance': 0.50,
        'makro': 0.72,
        'mikro': 0.50,
        'max_drawdown': 0.80
    }

    pm = {
        'piyasa_durumu': 'Pozitif',
        'firsatlar': [{'ticker': 'THYAO.IS', 'gap': 2.5}],
        'riskler': []
    }

    # Karar ver
    karar = komutan.karar_ver("THYAO.IS", skorlar, 325.50, pm)
    print(f"\nKarar: {karar['karar']}")
    print(f"Neden: {karar['neden']}")
    print(f"Beklenen Getiri: {karar.get('beklenen_getiri', 0):.2%}")

    # Ogren (1 gun sonra)
    print("\n--- 1 Gun Sonra ---")
    komutan.ogren(karar['id'], 342.00)  # %5 kar

    # Istatistik
    print(komutan.istatistik_rapor())

    print("\nTEST TAMAMLANDI")