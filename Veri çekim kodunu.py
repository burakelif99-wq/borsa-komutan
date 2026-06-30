import yfinance as yf

tavanlar = ["CELHA.IS", "BIGCH.IS", "DGGYO.IS", "BAKAB.IS", "BORLS.IS", "TRILC.IS", "KORDS.IS"]

for ticker in tavanlar:
    try:
        data = yf.download(ticker, period="5d", progress=False)
        if len(data) >= 2:
            # .item() ile tek float değer al
            son = float(data['Close'].iloc[-1])
            onceki = float(data['Close'].iloc[-2])
            degisim = ((son - onceki) / onceki) * 100
            print(f"✅ {ticker}: Son: {son:.2f}, Önceki: {onceki:.2f}, Değişim: {degisim:.2f}%")
        else:
            print(f"⚠️ {ticker}: Yetersiz veri ({len(data)} satır)")
    except Exception as e:
        print(f"❌ {ticker}: HATA - {str(e)[:100]}")