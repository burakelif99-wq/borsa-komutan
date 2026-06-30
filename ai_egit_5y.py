# ai_egit_5y.py - 5Y Ensemble Egitim
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_skorlayici import AIModel
from hisse_listesi import HISSE_LISTESI


def main():
    print("[INFO] GECE AI EGITIMI - Ensemble v4.3")

    model = AIModel()

    basari = model.egit(
        HISSE_LISTESI,
        period="5y",
        esik_al=0.02,
        esik_sat=-0.02
    )

    if basari:
        print("\n[OK] Gece egitimi basarili!")
    else:
        print("\n[ERR] Egitim basarisiz!")


if __name__ == "__main__":
    main()
