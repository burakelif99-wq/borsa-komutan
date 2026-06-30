# premarket_scan.py - Premarket Tarama Modülü
# Borsa Komutan v3.0 - Sıra 3

import yfinance as yf
from datetime import datetime, timedelta

class PremarketScan:
    """
    Piyasa açılmadan önce (09:00-09:30) fırsat taraması yapar.
    Gap up/down, hacim anomalileri ve sektör rotasyonu tespit eder.
    """

    def __init__(self):
        self.kriterler = {
            'gap_up': 0.02,       # %2 üstü gap
            'gap_down': -0.02,    # %2 altı gap
            'hacim_esik': 2.0,    # 2x normal hacim
            'fiyat_hareketi': 0.05 # %5 üstü hareket
        }
        self.sektor_oncelik = {
            'Banka': 1.2,
            'Holding': 1.1,
            'Savunma': 1.15,
            'Enerji': 1.1,
            'Havacilik': 1.05
        }

    def tara(self, hisse_listesi):
        """
        Premarket tarama yap
        """
        firsatlar = []
        riskler = []
        aktifler = []

        for ticker in hisse_listesi:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="5d")
                if len(hist) < 2:
                    continue

                dun_kapanis = hist['Close'].iloc[-2]
                bugun_acilis = hist['Open'].iloc[-1]
                bugun_kapanis = hist['Close'].iloc[-1]

                gap = (bugun_acilis - dun_kapanis) / dun_kapanis
                gunluk_degisim = (bugun_kapanis - dun_kapanis) / dun_kapanis

                ort_hacim = hist['Volume'].iloc[-5:-1].mean()
                bugun_hacim = hist['Volume'].iloc[-1]
                hacim_oran = bugun_hacim / ort_hacim if ort_hacim > 0 else 0

                sektor = self._sektor_tahmin(ticker)
                sektor_carpani = self.sektor_oncelik.get(sektor, 1.0)

                gap_skor = abs(gap) * 100
                hacim_skor = min(hacim_oran * 10, 50)
                hareket_skor = abs(gunluk_degisim) * 100

                toplam_skor = (gap_skor + hacim_skor + hareket_skor) * sektor_carpani

                veri = {
                    'ticker': ticker,
                    'sektor': sektor,
                    'gap': round(gap * 100, 2),
                    'gunluk_degisim': round(gunluk_degisim * 100, 2),
                    'hacim_oran': round(hacim_oran, 2),
                    'dun_kapanis': round(dun_kapanis, 2),
                    'bugun_acilis': round(bugun_acilis, 2),
                    'bugun_kapanis': round(bugun_kapanis, 2),
                    'skor': round(toplam_skor, 1),
                    'hacim': int(bugun_hacim)
                }

                if gap >= self.kriterler['gap_up'] and hacim_oran >= self.kriterler['hacim_esik']:
                    firsatlar.append(veri)
                elif gap <= self.kriterler['gap_down']:
                    riskler.append(veri)
                elif abs(gunluk_degisim) >= self.kriterler['fiyat_hareketi']:
                    aktifler.append(veri)

            except Exception as e:
                continue

        firsatlar.sort(key=lambda x: x['skor'], reverse=True)
        riskler.sort(key=lambda x: x['skor'], reverse=True)
        aktifler.sort(key=lambda x: x['skor'], reverse=True)

        sektor_analiz = self._sektor_analiz(firsatlar, riskler)

        return {
            'status': 'OK',
            'tarih': datetime.now().strftime('%Y-%m-%d'),
            'piyasa_durumu': self._piyasa_durumu(firsatlar, riskler),
            'firsatlar': firsatlar,
            'riskler': riskler,
            'aktifler': aktifler,
            'sektor_analiz': sektor_analiz,
            'ozet': {
                'toplam_firsat': len(firsatlar),
                'toplam_risk': len(riskler),
                'toplam_aktif': len(aktifler),
                'en_yuksek_gap': max([f['gap'] for f in firsatlar]) if firsatlar else 0,
                'en_dusuk_gap': min([r['gap'] for r in riskler]) if riskler else 0
            }
        }

    def _sektor_tahmin(self, ticker):
        """Hisse kodundan sektör tahmini"""
        sektor_map = {
            'GARAN': 'Banka', 'AKBNK': 'Banka', 'ISCTR': 'Banka', 'YKBNK': 'Banka',
            'THYAO': 'Havacilik', 'PGSUS': 'Havacilik',
            'ASELS': 'Savunma', 'KONTR': 'Savunma',
            'TUPRS': 'Enerji', 'ASTOR': 'Enerji',
            'KCHOL': 'Holding', 'SAHOL': 'Holding',
            'EREGL': 'Celik', 'SASA': 'Tekstil',
            'BIMAS': 'Perakende', 'FROTO': 'Otomotiv'
        }
        kod = ticker.replace('.IS', '')
        return sektor_map.get(kod, 'Diger')

    def _sektor_analiz(self, firsatlar, riskler):
        """Sektörel dağılım analizi"""
        sektorler = {}

        for f in firsatlar:
            s = f['sektor']
            if s not in sektorler:
                sektorler[s] = {'firsat': 0, 'risk': 0, 'toplam_skor': 0}
            sektorler[s]['firsat'] += 1
            sektorler[s]['toplam_skor'] += f['skor']

        for r in riskler:
            s = r['sektor']
            if s not in sektorler:
                sektorler[s] = {'firsat': 0, 'risk': 0, 'toplam_skor': 0}
            sektorler[s]['risk'] += 1

        sonuc = []
        for s, d in sektorler.items():
            sonuc.append({
                'sektor': s,
                'firsat': d['firsat'],
                'risk': d['risk'],
                'net': d['firsat'] - d['risk'],
                'ortalama_skor': round(d['toplam_skor'] / d['firsat'], 1) if d['firsat'] > 0 else 0
            })

        sonuc.sort(key=lambda x: x['net'], reverse=True)
        return sonuc

    def _piyasa_durumu(self, firsatlar, riskler):
        """Genel piyasa durumu tespiti"""
        firsat_sayisi = len(firsatlar)
        risk_sayisi = len(riskler)

        if firsat_sayisi > risk_sayisi * 2:
            return 'Pozitif'
        elif risk_sayisi > firsat_sayisi * 2:
            return 'Negatif'
        elif firsat_sayisi > 0 or risk_sayisi > 0:
            return 'Karisk'
        else:
            return 'Notr'

    def format_telegram(self, sonuc):
        """Telegram mesajı formatı"""
        o = sonuc['ozet']
        p = sonuc['piyasa_durumu']

        emoji = {'Pozitif': 'G', 'Negatif': 'R', 'Karisk': 'Y', 'Notr': 'W'}

        msg = "PREMARKET TARAMA (" + sonuc['tarih'] + ")"
        msg += emoji.get(p, 'W') + " Piyasa: " + p + ""
        msg += "Ozet:"
        msg += "  Firsat: " + str(o['toplam_firsat']) + " hisse"
        msg += "  Risk: " + str(o['toplam_risk']) + " hisse"
        msg += "  Aktif: " + str(o['toplam_aktif']) + " hisse"

        if sonuc['firsatlar']:
            msg += "FIRSATLAR:"
            for f in sonuc['firsatlar'][:5]:
                msg += "  " + f['ticker'] + ": +" + str(f['gap']) + "% gap | " + str(f['hacim_oran']) + "x hacim | Skor: " + str(f['skor']) + ""

        if sonuc['riskler']:
            msg += "RISKLER:"
            for r in sonuc['riskler'][:5]:
                msg += "  " + r['ticker'] + ": " + str(r['gap']) + "% gap | " + str(r['hacim_oran']) + "x hacim | Skor: " + str(r['skor']) + ""

        if sonuc['sektor_analiz']:
            msg += "SEKTORLER:"
            for s in sonuc['sektor_analiz'][:3]:
                msg += "  " + s['sektor'] + ": +" + str(s['firsat']) + " / -" + str(s['risk']) + " (Net: " + str(s['net']) + ")"
        return msg


if __name__ == "__main__":
    print("=" * 70)
    print("PREMARKET SCAN MODULU TEST")
    print("=" * 70)

    pm = PremarketScan()

    test_hisseler = [
        'THYAO.IS', 'GARAN.IS', 'ASELS.IS', 'EREGL.IS', 'SASA.IS',
        'BIMAS.IS', 'KCHOL.IS', 'TUPRS.IS', 'FROTO.IS', 'ISCTR.IS'
    ]

    print("Taranan Hisseler: " + str(len(test_hisseler)))
    print("-" * 70)

    sonuc = pm.tara(test_hisseler)

    print("Piyasa Durumu: " + sonuc['piyasa_durumu'])
    print("   Tarih: " + sonuc['tarih'])

    o = sonuc['ozet']
    print("Ozet:")
    print("   Firsat: " + str(o['toplam_firsat']) + " hisse")
    print("   Risk: " + str(o['toplam_risk']) + " hisse")
    print("   Aktif: " + str(o['toplam_aktif']) + " hisse")

    if sonuc['firsatlar']:
        print("FIRSATLAR (" + str(len(sonuc['firsatlar'])) + " hisse):")
        for f in sonuc['firsatlar'][:5]:
            print("   " + f['ticker'] + ": +" + str(f['gap']) + "% gap | " + str(f['hacim_oran']) + "x hacim | Skor: " + str(f['skor']))

    if sonuc['riskler']:
        print("RISKLER (" + str(len(sonuc['riskler'])) + " hisse):")
        for r in sonuc['riskler'][:5]:
            print("   " + r['ticker'] + ": " + str(r['gap']) + "% gap | " + str(r['hacim_oran']) + "x hacim | Skor: " + str(r['skor']))

    if sonuc['sektor_analiz']:
        print("SEKTOR ANALIZI:")
        for s in sonuc['sektor_analiz'][:5]:
            print("   " + s['sektor'] + ": +" + str(s['firsat']) + " firsat | -" + str(s['risk']) + " risk | Net: " + str(s['net']))

    print("Telegram Formati:")
    print("-" * 70)
    print(pm.format_telegram(sonuc))

    print("=" * 70)
    print("TUM TESTLER TAMAMLANDI")
    print("=" * 70)
