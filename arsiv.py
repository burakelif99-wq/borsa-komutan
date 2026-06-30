# arsiv.py - SQLite Arşiv Modülü
# Borsa Komutan v3.0 - Sıra 2

import sqlite3
from datetime import datetime
import json
import os

class Arsiv:
    """
    Tüm analizleri, kararları ve piyasa verilerini SQLite veritabanında saklar.
    Tarihsel sorgulama, trend analizi ve performans raporları sunar.
    """

    def __init__(self, db_path='borsa_komutan.db'):
        """
        Parametreler:
            db_path: Veritabanı dosya yolu (varsayılan: borsa_komutan.db)
        """
        self.db_path = db_path
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.cursor = self.db.cursor()
        self._tablolar_olustur()
        self._indexler_olustur()

    def _tablolar_olustur(self):
        """Veritabanı tablolarını oluştur"""

        # Ana analiz tablosu
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS analizler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hisse TEXT NOT NULL,
                karar TEXT NOT NULL,
                skor REAL,
                guven REAL,
                zaman_dilimi TEXT DEFAULT '1D',
                teknik_skor REAL,
                risk_skor REAL,
                makro_skor REAL,
                medya_skor REAL,
                drawdown REAL,
                fiyat REAL,
                degisim REAL,
                sektor TEXT,
                UNIQUE(tarih, hisse, zaman_dilimi)
            )
        ''')

        # Piyasa verisi tablosu
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS piyasa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                xu100 REAL,
                xu30 REAL,
                usdtry REAL,
                altin REAL,
                faiz REAL,
                petrol REAL,
                UNIQUE(tarih)
            )
        ''')

        # İşlem kayıtları (portföy)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS islemler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hisse TEXT NOT NULL,
                tip TEXT NOT NULL,
                miktar INTEGER,
                fiyat REAL,
                toplam REAL,
                kar_zarar REAL,
                aciklama TEXT
            )
        ''')

        # Max Drawdown kayıtları
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS drawdownlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hisse TEXT NOT NULL,
                zirve REAL,
                anlik REAL,
                drawdown REAL,
                max_drawdown REAL,
                risk_seviyesi TEXT
            )
        ''')

        self.db.commit()

    def _indexler_olustur(self):
        """Performans için indexler oluştur"""
        indexler = [
            "CREATE INDEX IF NOT EXISTS idx_analiz_hisse ON analizler(hisse)",
            "CREATE INDEX IF NOT EXISTS idx_analiz_tarih ON analizler(tarih)",
            "CREATE INDEX IF NOT EXISTS idx_analiz_karar ON analizler(karar)",
            "CREATE INDEX IF NOT EXISTS idx_piyasa_tarih ON piyasa(tarih)",
            "CREATE INDEX IF NOT EXISTS idx_islem_hisse ON islemler(hisse)",
            "CREATE INDEX IF NOT EXISTS idx_dd_hisse ON drawdownlar(hisse)"
        ]
        for idx in indexler:
            try:
                self.cursor.execute(idx)
            except:
                pass
        self.db.commit()

    def kaydet_analiz(self, hisse, ensemble, zaman_dilimi="1D", fiyat=None, degisim=None, sektor=None):
        """
        Analiz sonucunu kaydet
        """
        try:
            e = ensemble['ensemble']
            d = ensemble['details']

            self.cursor.execute('''
                INSERT OR REPLACE INTO analizler 
                (tarih, hisse, karar, skor, guven, zaman_dilimi, 
                 teknik_skor, risk_skor, makro_skor, medya_skor, 
                 fiyat, degisim, sektor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now(),
                hisse,
                e['decision'],
                e['final_score'],
                e['confidence'],
                zaman_dilimi,
                d['teknik']['score'],
                d['risk']['score'],
                d['makro']['score'],
                d['medya']['score'],
                fiyat,
                degisim,
                sektor
            ))
            self.db.commit()
            return {'status': 'OK', 'id': self.cursor.lastrowid}

        except Exception as ex:
            return {'status': 'HATA', 'message': str(ex)}

    def kaydet_piyasa(self, xu100=None, xu30=None, usdtry=None, altin=None, faiz=None, petrol=None):
        """Günlük piyasa verisini kaydet"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO piyasa 
                (tarih, xu100, xu30, usdtry, altin, faiz, petrol)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (datetime.now(), xu100, xu30, usdtry, altin, faiz, petrol))
            self.db.commit()
            return {'status': 'OK'}
        except Exception as ex:
            return {'status': 'HATA', 'message': str(ex)}

    def kaydet_islem(self, hisse, tip, miktar, fiyat, kar_zarar=None, aciklama=None):
        """Portföy işlemi kaydet"""
        toplam = miktar * fiyat
        self.cursor.execute('''
            INSERT INTO islemler (tarih, hisse, tip, miktar, fiyat, toplam, kar_zarar, aciklama)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now(), hisse, tip, miktar, fiyat, toplam, kar_zarar, aciklama))
        self.db.commit()
        return {'status': 'OK', 'id': self.cursor.lastrowid}

    def kaydet_drawdown(self, hisse, zirve, anlik, drawdown, max_drawdown, risk_seviyesi):
        """Drawdown verisi kaydet"""
        self.cursor.execute('''
            INSERT INTO drawdownlar (tarih, hisse, zirve, anlik, drawdown, max_drawdown, risk_seviyesi)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (datetime.now(), hisse, zirve, anlik, drawdown, max_drawdown, risk_seviyesi))
        self.db.commit()

    def getir(self, hisse, limit=30, zaman_dilimi=None):
        """Son analizleri getir"""
        if zaman_dilimi:
            self.cursor.execute('''
                SELECT * FROM analizler 
                WHERE hisse = ? AND zaman_dilimi = ?
                ORDER BY tarih DESC 
                LIMIT ?
            ''', (hisse, zaman_dilimi, limit))
        else:
            self.cursor.execute('''
                SELECT * FROM analizler 
                WHERE hisse = ?
                ORDER BY tarih DESC 
                LIMIT ?
            ''', (hisse, limit))

        return [dict(row) for row in self.cursor.fetchall()]

    def istatistik(self, hisse, gun=30):
        """İstatistiksel özet"""
        veri = self.getir(hisse, gun)

        if not veri:
            return None

        import statistics

        kararlar = {'AL': 0, 'SAT': 0, 'BEKLE': 0}
        skorlar = []
        guvenler = []

        for v in veri:
            kararlar[v['karar']] += 1
            skorlar.append(v['skor'])
            guvenler.append(v['guven'])

        return {
            'hisse': hisse,
            'periyot': gun,
            'toplam_kayit': len(veri),
            'karar_dagilimi': kararlar,
            'al_orani': round(kararlar['AL'] / len(veri) * 100, 1),
            'sat_orani': round(kararlar['SAT'] / len(veri) * 100, 1),
            'bekle_orani': round(kararlar['BEKLE'] / len(veri) * 100, 1),
            'ortalama_skor': round(statistics.mean(skorlar), 2),
            'max_skor': round(max(skorlar), 2),
            'min_skor': round(min(skorlar), 2),
            'ortalama_guven': round(statistics.mean(guvenler), 2),
            'son_skor': veri[0]['skor'],
            'ilk_skor': veri[-1]['skor'],
            'skor_trendi': 'YUKARI' if veri[0]['skor'] > veri[-1]['skor'] else 'ASAGI',
            'son_karar': veri[0]['karar'],
            'son_guven': veri[0]['guven'],
            'son_tarih': veri[0]['tarih']
        }

    def trend_analizi(self, hisse, gun=30):
        """Skor trend analizi"""
        veri = self.getir(hisse, gun)
        if len(veri) < 5:
            return None

        son_5 = [v['skor'] for v in veri[:5]]
        onceki_5 = [v['skor'] for v in veri[5:10]] if len(veri) >= 10 else [v['skor'] for v in veri[-5:]]

        import statistics
        son_ort = statistics.mean(son_5)
        onceki_ort = statistics.mean(onceki_5)

        degisim = son_ort - onceki_ort

        if degisim > 5:
            trend = 'GÜÇLÜ YUKARI'
        elif degisim > 2:
            trend = 'YUKARI'
        elif degisim < -5:
            trend = 'GÜÇLÜ ASAGI'
        elif degisim < -2:
            trend = 'ASAGI'
        else:
            trend = 'YANA'

        return {
            'hisse': hisse,
            'trend': trend,
            'degisim': round(degisim, 2),
            'son_5_ortalama': round(son_ort, 2),
            'onceki_5_ortalama': round(onceki_ort, 2),
            'tavsiye': 'AL' if trend in ['GÜÇLÜ YUKARI', 'YUKARI'] else 'SAT' if trend in ['GÜÇLÜ ASAGI', 'ASAGI'] else 'BEKLE'
        }

    def son_kararlar(self, limit=50):
        """Son kararları listele"""
        self.cursor.execute('''
            SELECT a.* FROM analizler a
            INNER JOIN (
                SELECT hisse, MAX(tarih) as son_tarih 
                FROM analizler 
                GROUP BY hisse
            ) b ON a.hisse = b.hisse AND a.tarih = b.son_tarih
            ORDER BY a.skor DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def karar_dagilimi(self, gun=7):
        """Son X günün karar dağılımı"""
        self.cursor.execute('''
            SELECT karar, COUNT(*) as sayi, AVG(skor) as ort_skor
            FROM analizler
            WHERE tarih >= datetime('now', '-{} days')
            GROUP BY karar
        '''.format(gun))
        return [dict(row) for row in self.cursor.fetchall()]

    def db_boyut(self):
        """Veritabanı boyutunu kontrol et"""
        if os.path.exists(self.db_path):
            boyut = os.path.getsize(self.db_path)
            return {'boyut_byte': boyut, 'boyut_mb': round(boyut / 1024 / 1024, 2)}
        return {'boyut_byte': 0, 'boyut_mb': 0}

    def yedekle(self, yedek_path=None):
        """Veritabanını yedekle"""
        if not yedek_path:
            yedek_path = f"borsa_komutan_yedek_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"

        import shutil
        shutil.copy2(self.db_path, yedek_path)
        return {'status': 'OK', 'yedek': yedek_path}

    def temizle(self, gun=90):
        """Eski kayıtları temizle"""
        self.cursor.execute('''
            DELETE FROM analizler 
            WHERE tarih < datetime('now', '-{} days')
        '''.format(gun))
        self.db.commit()
        return {'status': 'OK', 'silinen': self.cursor.rowcount}

    def kapat(self):
        """Bağlantıyı kapat"""
        self.db.close()
