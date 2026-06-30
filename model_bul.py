
# ============================================
# MODEL DOSYALARINI BULMA SCRIPTI
# Proje klasorunde calistir
# ============================================

import os
import glob

# Baslangic dizini (proje koku)
BASE_DIR = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi"

print("="*70)
print("🔍 MODEL DOSYASI ARAMA")
print("="*70)
print(f"Arama dizini: {BASE_DIR}")
print()

# Aranacak dosya uzantilari
uzantilar = ['*.pkl', '*.joblib', '*.h5', '*.onnx', '*.pt', '*.pth']

bulunan_dosyalar = []

for uzanti in uzantilar:
    pattern = os.path.join(BASE_DIR, "**", uzanti)
    dosyalar = glob.glob(pattern, recursive=True)
    for d in dosyalar:
        bulunan_dosyalar.append(d)
        print(f"✅ BULUNDU: {d}")

print()
print("="*70)
print(f"Toplam {len(bulunan_dosyalar)} model dosyasi bulundu.")
print("="*70)

# Eger hic dosya bulunamazsa
if len(bulunan_dosyalar) == 0:
    print("\n❌ HIC MODEL DOSYASI BULUNAMADI!")
    print("\nOlası sebepler:")
    print("  1. Model henuz egitilmemis (ai_egit.py calistirilmamis)")
    print("  2. Model farkli bir klasore kaydedilmis")
    print("  3. Dosya uzantisi farkli (.pkl yerine .sav, .model vb.)")
    print("\nYapman gereken:")
    print("  → ai_egit.py'yi calistir ve modeli kaydet")
    print("  → VEYA model dosyasinin gercek konumunu bul")