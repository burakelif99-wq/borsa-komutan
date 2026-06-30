#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kimi Onay: Pipeline AL listesindeki hisseleri Kimi ile kontrol eder.
Kullanim: python kimi_onay.py
"""
import os, sys, json, glob
from datetime import datetime

KIMI_DIR = os.path.dirname(__file__)
sys.path.insert(0, KIMI_DIR)

# Kimi model yukle
try:
    from ai_skorlayici import AIModel
    model_dir = os.path.join(KIMI_DIR, "modeller")
    modeller = [f for f in os.listdir(model_dir) if f.startswith('ai_model_v43_20260626_165942') and f.endswith('.joblib')]
    if not modeller:
        modeller = sorted([f for f in os.listdir(model_dir) if f.startswith('ai_model_v43') and f.endswith('.joblib') and 'v431' not in f], reverse=True)
    if modeller:
        AI_MODEL = AIModel(os.path.join(model_dir, modeller[0]))
        print(f"[OK] Kimi model: {modeller[0]}")
    else:
        print("[HATA] Model bulunamadi")
        sys.exit(1)
except Exception as e:
    print(f"[HATA] Model yuklenemedi: {e}")
    sys.exit(1)

# Pipeline raporlarini tara (ortak workspace)
adaylar = [
    os.path.join(os.path.dirname(KIMI_DIR), "kind-knight", "raporlar"),
    r"C:\Users\Administrator\.local\share\opencode\worktree\ca751c77d3f8b0bcb92c6ff8149f6fa07240f66f\kind-knight\raporlar",
]
rapor_dizini = None
for aday in adaylar:
    if os.path.exists(aday):
        rapor_dizini = aday
        break
if not rapor_dizini:
    print("[HATA] Pipeline rapor dizini bulunamadi")
    sys.exit(1)

# En son pipeline raporunu bul
raporlar = glob.glob(os.path.join(rapor_dizini, "rapor_sabah_*.txt"))
raporlar += glob.glob(os.path.join(rapor_dizini, "rapor_ogle_*.txt"))
raporlar += glob.glob(os.path.join(rapor_dizini, "rapor_aksam_*.txt"))
raporlar.sort(reverse=True)

if not raporlar:
    print("[HATA] Rapor bulunamadi")
    sys.exit(1)

son_rapor = raporlar[0]
print(f"\n[OK] Pipeline raporu: {os.path.basename(son_rapor)}")

with open(son_rapor, "r", encoding="utf-8") as f:
    rapor_icerik = f.read()

# AL listesini ayikla (ENSEMBLE DETAY bolumunden)
al_hisseler = []
ensemble_bolumu = False
for satir in rapor_icerik.split("\n"):
    if "ENSEMBLE DETAY" in satir:
        ensemble_bolumu = True
        continue
    if ensemble_bolumu and "===" in satir:
        break
    if ensemble_bolumu and "AL" in satir and satir.strip():
        # "  SEKUR.IS     skor:66 AL" -> SEKUR
        hisse = satir.strip().split()[0].replace(".IS", "").strip()
        if hisse and len(hisse) <= 6:
            al_hisseler.append(hisse)

if not al_hisseler:
    # Fallback: GENEL TOP 10'dan en yuksek skorlulari al
    genel_bolumu = False
    for satir in rapor_icerik.split("\n"):
        if "GENEL TOP 10" in satir:
            genel_bolumu = True
            continue
        if genel_bolumu and ("[G] GECERSIZ" in satir or "===" in satir):
            break
        if genel_bolumu and satir.strip():
            hisse = satir.strip().split()[0].replace(".IS", "").strip()
            if hisse and len(hisse) <= 6 and hisse.isalpha():
                al_hisseler.append(hisse)
    print(f"  (GENEL TOP 10 kullanildi: {len(al_hisseler)} hisse)")

# Veri dosyalarini bul
veri_dizini = os.path.join(KIMI_DIR, "veri")
alis_verileri = []

for hisse in al_hisseler:
    for ek in ["_5yil.csv", ".csv"]:
        csv_path = os.path.join(veri_dizini, f"{hisse}{ek}")
        if os.path.exists(csv_path):
            alis_verileri.append(hisse)
            break

if not alis_verileri:
    print("[UYARI] AL listesindeki hisseler icin veri bulunamadi")
    sys.exit(1)

# Kimi ile degerlendir
import pandas as pd
print(f"\n=== KIMI ONAY ===")
print(f"Pipeline AL: {len(alis_verileri)} hisse")

kimi_al = []
kimi_sat = []
kimi_bekle = []

for hisse in alis_verileri[:30]:
    csv_path = None
    for ek in ["_5yil.csv", ".csv"]:
        aday = os.path.join(veri_dizini, f"{hisse}{ek}")
        if os.path.exists(aday):
            csv_path = aday
            break
    if csv_path is None:
        continue
    try:
        df = pd.read_csv(csv_path)
        if len(df) < 200:
            continue
        sonuc = AI_MODEL.tahmin_et(df)
        if isinstance(sonuc, tuple):
            tahmin = sonuc[0]
        else:
            tahmin = sonuc
        if tahmin == 1:
            kimi_al.append(hisse)
        elif tahmin == -1:
            kimi_sat.append(hisse)
        else:
            kimi_bekle.append(hisse)
    except Exception as e:
        print(f"    {hisse}: {e}")
        continue

print(f"Kimi AL:  {len(kimi_al)} hisse")
print(f"Kimi SAT: {len(kimi_sat)} hisse")
print(f"Kimi BEKLE: {len(kimi_bekle)} hisse")
print()

if kimi_al:
    print("[G] KESISIM (Pipeline AL + Kimi AL):")
    for h in kimi_al:
        print(f"  {h}")
else:
    print("Kesisim yok")

# Raporu kaydet
rapor = {
    "tarih": datetime.now().isoformat(),
    "pipeline_rapor": os.path.basename(son_rapor),
    "pipeline_al_sayisi": len(alis_verileri),
    "kimi_al_sayisi": len(kimi_al),
    "kesisim": kimi_al
}
rapor_dir = os.path.join(KIMI_DIR, "rapor")
os.makedirs(rapor_dir, exist_ok=True)
with open(os.path.join(rapor_dir, "kimi_onay.json"), "w") as f:
    json.dump(rapor, f, indent=2, ensure_ascii=False)
print(f"\n[OK] Rapor: rapor/kimi_onay.json")
