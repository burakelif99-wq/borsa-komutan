# grok_al.py - Ensemble Motor & Karar Motoru
# Borsa Komutan v3.0 - Sıra 4

import pandas as pd
import numpy as np
from datetime import datetime

class EnsembleMotor:
    """
    5 Uzman modulun ciktilarini agirlikli birlestirir.
    Teknik, Temel, Yatirimci, Risk, Makro uzmanlarinin
    kararlarini ensemble ederek nihai karar uretir.
    """

    def __init__(self, agirliklar=None):
        # Varsayilan agirliklar (Rejim motoru tarafindan override edilebilir)
        self.agirliklar = agirliklar or {
            'teknik': 0.25,
            'temel': 0.25,
            'yatirimci': 0.20,
            'risk': 0.20,
            'makro': 0.10
        }

        # Esikler
        self.esikler = {
            'AL': 50,
            'SAT': 50,
            'BEKLE': 50
        }

    def hesapla(self, teknik=None, temel=None, yatirimci=None, risk=None, makro=None,
                df=None, zaman_dilimi='1D'):
        """
        Ensemble skor hesapla

        Her modul dict formatinda olmali:
        {'sinyal': 'AL'/'SAT'/'BEKLE', 'skor': 0-100, 'guven': 0-1, 'neden': '...'}
        """
        moduller = {
            'teknik': teknik or {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.5, 'neden': 'Veri yok'},
            'temel': temel or {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.5, 'neden': 'Veri yok'},
            'yatirimci': yatirimci or {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.5, 'neden': 'Veri yok'},
            'risk': risk or {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.5, 'neden': 'Veri yok'},
            'makro': makro or {'sinyal': 'BEKLE', 'skor': 50, 'guven': 0.5, 'neden': 'Veri yok'}
        }

        # Agirlikli skor hesapla
        toplam_skor = 0
        toplam_guven = 0
        detaylar = {}

        for modul_adi, veri in moduller.items():
            agirlik = self.agirliklar.get(modul_adi, 0.2)
            skor = veri.get('skor', 50)
            guven = veri.get('guven', 0.5)
            sinyal = veri.get('sinyal', 'BEKLE')

            # Guven agirlikli skor
            agirlikli_skor = skor * agirlik * guven
            toplam_skor += agirlikli_skor
            toplam_guven += agirlik * guven

            detaylar[modul_adi] = {
                'sinyal': sinyal,
                'skor': skor,
                'guven': round(guven, 2),
                'agirlik': agirlik,
                'agirlikli_skor': round(agirlikli_skor, 2)
            }

        # Normalize et
        if toplam_guven > 0:
            final_skor = toplam_skor / toplam_guven
        else:
            final_skor = 50

        final_skor = round(final_skor, 1)

        # KARAR MOTORU - Coklu strateji oylamasasi + Risk veto
        # 1. Risk Veto (En yuksek oncelik)
        risk_sinyal = moduller['risk'].get('sinyal', 'BEKLE')
        risk_skor = moduller['risk'].get('skor', 50)

        # Risk skoru cok dusukse (40 alti) AL veto et
        risk_veto = False
        veto_nedeni = None

        if risk_skor < 40 and final_skor >= self.esikler['AL']:
            risk_veto = True
            veto_nedeni = f"Risk skoru dusuk ({risk_skor}), AL engellendi"

        # 2. Coklu strateji oylamasi
        sinyal_oylari = {'AL': 0, 'SAT': 0, 'BEKLE': 0}
        for modul_adi, veri in moduller.items():
            sinyal = veri.get('sinyal', 'BEKLE')
            agirlik = self.agirliklar.get(modul_adi, 0.2)
            guven = veri.get('guven', 0.5)
            sinyal_oylari[sinyal] += agirlik * guven

        # Kazanan sinyal
        kazanan_sinyal = max(sinyal_oylari, key=sinyal_oylari.get)
        kazanan_oy = sinyal_oylari[kazanan_sinyal]

        # Guven hesapla (kazananin oyu / toplam)
        toplam_oy = sum(sinyal_oylari.values())
        confidence = round((kazanan_oy / toplam_oy) * 100, 1) if toplam_oy > 0 else 50

        # 3. Nihai karar (Esikler + Risk Veto)
        if risk_veto:
            decision = 'BEKLE'
        elif final_skor >= self.esikler['AL']:
            decision = 'AL'
        elif final_skor <= self.esikler['SAT'] or kazanan_sinyal == 'SAT':
            decision = 'SAT'
        else:
            decision = 'BEKLE'

        # 4. Trend guclendirme (teknik trend onayliysa)
        teknik_sinyal = moduller['teknik'].get('sinyal', 'BEKLE')
        teknik_skor = moduller['teknik'].get('skor', 50)

        trend_onay = True  # Trend onay sarti kaldirildi
        # if decision == 'AL' and teknik_sinyal == 'AL' and teknik_skor > 60:
        #     trend_onay = True
        #     confidence = min(confidence + 10, 100)
        # elif decision == 'SAT' and teknik_sinyal == 'SAT' and teknik_skor < 40:
        #     trend_onay = True
        #     confidence = min(confidence + 10, 100)

        return {
            'ensemble': {
                'decision': decision,
                'final_score': final_skor,
                'confidence': confidence,
                'kazanan_sinyal': kazanan_sinyal,
                'sinyal_oylari': {k: round(v, 3) for k, v in sinyal_oylari.items()},
                'risk_veto': risk_veto,
                'veto_nedeni': veto_nedeni,
                'trend_onay': trend_onay,
                'esikler': self.esikler,
                'agirliklar': self.agirliklar
            },
            'moduller': detaylar,
            'meta': {
                'zaman_dilimi': zaman_dilimi,
                'timestamp': datetime.now().isoformat()
            }
        }


# Geriye uyumluluk icin fonksiyon

def calculate_ensemble(df=None, teknik=None, temel=None, yatirimci=None,
                       risk=None, makro=None, medya=None, zaman_dilimi='1D'):
    """
    Geriye uyumlu ensemble hesaplama fonksiyonu.
    dynamic_ensemble.py tarafindan cagrilir.
    """
    motor = EnsembleMotor()

    # medya parametresi makro ile birlestirilebilir
    if medya and not makro:
        makro = medya
    elif medya and makro:
        # Her ikisi de varsa, makro oncelikli ama medya skorunu dahil et
        makro['skor'] = (makro.get('skor', 50) + medya.get('skor', 50)) / 2

    return motor.hesapla(
        teknik=teknik,
        temel=temel,
        yatirimci=yatirimci,
        risk=risk,
        makro=makro,
        df=df,
        zaman_dilimi=zaman_dilimi
    )


if __name__ == "__main__":
    print("=" * 70)
    print("ENSEMBLE MOTOR TEST")
    print("=" * 70)

    motor = EnsembleMotor()

    # Test 1: Guclu AL senaryosu
    print("1. GUCLU AL SENARYOSU")
    print("-" * 70)

    sonuc = motor.hesapla(
        teknik={'sinyal': 'AL', 'skor': 75, 'guven': 0.8, 'neden': 'RSI 60, MACD yukari'},
        temel={'sinyal': 'AL', 'skor': 70, 'guven': 0.7, 'neden': 'P/E 8, ROE 15'},
        yatirimci={'sinyal': 'AL', 'skor': 65, 'guven': 0.6, 'neden': 'Buffett kriterleri'},
        risk={'sinyal': 'BEKLE', 'skor': 55, 'guven': 0.7, 'neden': 'Kelly 0.25'},
        makro={'sinyal': 'AL', 'skor': 60, 'guven': 0.5, 'neden': 'USD stabil'}
    )

    e = sonuc['ensemble']
    print(f"Karar: {e['decision']}")
    print(f"Skor: {e['final_score']}")
    print(f"Guven: %{e['confidence']}")
    print(f"Risk Veto: {e['risk_veto']}")
    print(f"Trend Onay: {e['trend_onay']}")

    # Test 2: Risk Veto senaryosu
    print("2. RISK VETO SENARYOSU")
    print("-" * 70)

    sonuc2 = motor.hesapla(
        teknik={'sinyal': 'AL', 'skor': 80, 'guven': 0.9},
        temel={'sinyal': 'AL', 'skor': 75, 'guven': 0.8},
        yatirimci={'sinyal': 'AL', 'skor': 70, 'guven': 0.7},
        risk={'sinyal': 'SAT', 'skor': 35, 'guven': 0.9},  # Dusuk risk skoru!
        makro={'sinyal': 'AL', 'skor': 60, 'guven': 0.5}
    )

    e2 = sonuc2['ensemble']
    print(f"Karar: {e2['decision']} (Risk skoru dusuk oldugu icin AL engellendi)")
    print(f"Skor: {e2['final_score']}")
    print(f"Veto Nedeni: {e2['veto_nedeni']}")

    # Test 3: SAT senaryosu
    print("3. SAT SENARYOSU")
    print("-" * 70)

    sonuc3 = motor.hesapla(
        teknik={'sinyal': 'SAT', 'skor': 30, 'guven': 0.8},
        temel={'sinyal': 'SAT', 'skor': 35, 'guven': 0.7},
        yatirimci={'sinyal': 'BEKLE', 'skor': 45, 'guven': 0.6},
        risk={'sinyal': 'SAT', 'skor': 25, 'guven': 0.9},
        makro={'sinyal': 'SAT', 'skor': 40, 'guven': 0.6}
    )

    e3 = sonuc3['ensemble']
    print(f"Karar: {e3['decision']}")
    print(f"Skor: {e3['final_score']}")
    print(f"Guven: %{e3['confidence']}")

    print("" + "=" * 70)
    print("TUM TESTLER TAMAMLANDI")
    print("=" * 70)
