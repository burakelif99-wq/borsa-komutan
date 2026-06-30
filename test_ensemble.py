import sys
sys.path.insert(0, r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi")

from hisse_analiz import ensemble_skor_hesapla

tavanlar = ["CELHA.IS", "BIGCH.IS", "DGGYO.IS", "BAKAB.IS", "BORLS.IS", "TRILC.IS", "KORDS.IS"]

for ticker in tavanlar:
    try:
        skor = ensemble_skor_hesapla(ticker)
        print(f"{ticker}: Ensemble Skor = {skor}")
    except Exception as e:
        print(f"{ticker}: HATA - {str(e)[:150]}")
