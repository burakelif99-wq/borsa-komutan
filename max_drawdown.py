# max_drawdown.py - Max Drawdown Takip Modulu

class MaxDrawdown:
    def __init__(self, esik=-0.20, hisse_adi="Portfoy"):
        self.hisse_adi = hisse_adi
        self.esik = esik
        self.zirve = 0
        self.anlik = 0
        self.drawdown = 0.0
        self.max_drawdown = 0.0
    
    def guncelle(self, fiyat, tarih=None):
        if fiyat > self.zirve:
            self.zirve = fiyat
            self.anlik = fiyat
            self.drawdown = 0.0
        else:
            self.anlik = fiyat
            self.drawdown = (self.anlik - self.zirve) / self.zirve
        
        if self.drawdown < self.max_drawdown:
            self.max_drawdown = self.drawdown
        
        alarm = self.drawdown < self.esik
        
        return {
            'hisse': self.hisse_adi,
            'zirve': round(self.zirve, 2),
            'anlik': round(self.anlik, 2),
            'drawdown': round(self.drawdown * 100, 2),
            'max_drawdown': round(self.max_drawdown * 100, 2),
            'alarm': alarm,
            'risk_seviyesi': self._risk_seviyesi()
        }
    
    def _risk_seviyesi(self):
        dd = abs(self.drawdown)
        if dd < 0.05:
            return 'DUSUK'
        elif dd < 0.10:
            return 'ORTA'
        elif dd < 0.20:
            return 'YUKSEK'
        else:
            return 'ASIRI'
    
    def reset(self):
        self.zirve = 0
        self.anlik = 0
        self.drawdown = 0.0
        self.max_drawdown = 0.0


if __name__ == '__main__':
    print('Max Drawdown hazir')
    dd = MaxDrawdown(esik=-0.20, hisse_adi='THYAO.IS')
    print(dd.guncelle(100))
    print(dd.guncelle(85))
    print('Test tamam')
