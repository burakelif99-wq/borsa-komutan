import warnings, numpy as np, pandas as pd, os
from hisse_listesi import HISSE_LISTESI
warnings.filterwarnings('ignore')
import yfinance as yf
from ai_skorlayici import AIModel

model_dir = r'C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\modeller'
v43 = sorted([f for f in os.listdir(model_dir) if f.startswith('ai_model_v43_') and f.endswith('.joblib') and not f.endswith('.bak')])
ai = AIModel(os.path.join(model_dir, v43[-1]))

def fmt(t): return t if t.endswith('.IS') else t + '.IS'

print('Veri indiriliyor...')
veriler = {}
for ticker in HISSE_LISTESI[:20]:
    try:
        data = yf.download(fmt(ticker), period='300d', progress=False, auto_adjust=True)
        if data is not None and len(data) > 200:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.droplevel(1)
            veriler[ticker] = data
    except:
        pass
print(f'{len(veriler)} hisse')

window = 30
step = 30
min_len = min(len(d) for d in veriler.values())
# 3 non-overlapping window: son 90 gun
windows = []
for end in range(window, min_len, step):
    start = end - window
    windows.append((start, end))

print(f'{len(windows)} window')
print()
hdr = '  {:>5} {:>9} {:>10} {:>8} {:>6} {:>7}'
print(hdr.format('Donem', 'ModelPL', 'Benchmark', 'Fark', 'AL', 'Basari'))
print('  ' + '-'*55)

results = []
for start, end in windows:
    model_pl = 0; bnh_pl = 0; total_al = 0; dogru = 0; toplam = 0; hisse_say = 0
    for ticker, data in veriler.items():
        if len(data) < end + 5: continue
        hisse_say += 1
        for i in range(-end, -start):
            gecmis = data.iloc[:i]
            getiri = (data['Close'].iloc[i+1] - data['Close'].iloc[i]) / data['Close'].iloc[i]
            bnh_pl += getiri
            r = ai.tahmin_et(gecmis)
            t = r.get('etiket', 'BEKLE')
            if t == 'AL': model_pl += getiri; total_al += 1
            ok = (t=='AL' and getiri>0.01) or (t=='SAT' and getiri<-0.01) or (t=='BEKLE' and abs(getiri)<=0.01)
            if ok: dogru += 1
            toplam += 1
    if hisse_say == 0: continue
    mp = model_pl / hisse_say * 100
    bp = bnh_pl / hisse_say * 100
    fark = mp - bp
    basari = dogru/toplam*100 if toplam>0 else 0
    donem = f'{-end}..{-start}'
    results.append((donem, mp, bp, fark, total_al, basari))
    print(f'  {donem:>5} %{mp:>+7.2f} %{bp:>+7.2f} %{fark:>+6.2f} {total_al:>6} %{basari:>5.1f}')

print('  ' + '-'*55)
avg_m = np.mean([r[1] for r in results]) if results else 0
avg_b = np.mean([r[2] for r in results]) if results else 0
avg_f = np.mean([r[3] for r in results]) if results else 0
kaz = sum(1 for r in results if r[3] > 0)
print(f'  ORT   %{avg_m:>+7.2f} %{avg_b:>+7.2f} %{avg_f:>+6.2f}  Kaz:{kaz}/{len(results)}')
print()
# Son 30 gun (orijinal test)
print('SON 30 GUN (orijinal test):')
mp2 = 0; bnh2 = 0; al2 = 0; d2 = 0; t2 = 0; hs2 = 0
for ticker, data in veriler.items():
    if len(data) < 35: continue
    hs2 += 1
    for i in range(-30, -1):
        gecmis = data.iloc[:i]
        getiri = (data['Close'].iloc[i+1] - data['Close'].iloc[i]) / data['Close'].iloc[i]
        bnh2 += getiri
        r = ai.tahmin_et(gecmis)
        t = r.get('etiket', 'BEKLE')
        if t == 'AL': mp2 += getiri; al2 += 1
        ok = (t=='AL' and getiri>0.01) or (t=='SAT' and getiri<-0.01) or (t=='BEKLE' and abs(getiri)<=0.01)
        if ok: d2 += 1; t2 += 1
        else: t2 += 1
    bas2 = d2/t2*100 if t2>0 else 0
print(f'  Model: %{mp2/hs2*100 if hs2>0 else 0:+.2f}  Benchmark: %{bnh2/hs2*100 if hs2>0 else 0:+.2f}  Basari: %{bas2:.1f}  AL: {al2}')

os.remove(__file__)
