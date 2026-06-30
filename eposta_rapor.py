"""
eposta_rapor.py - Borsa Komutan v4.0
Otomatik e-posta raporlama sistemi
"""

import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# =============================================================================
# AYARLAR
# =============================================================================

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

GONDERICI_EMAIL = "burakelif99@gmail.com"
ALICI_EMAIL = "burakelif99@gmail.com"


# =============================================================================
# E-POSTA GONDERME (Once tanimlanmali)
# =============================================================================

def eposta_gonder(rapor_path, konu="Borsa Komutan - Gunluk Rapor",
                  sifre=None, ek_dosya=None):
    """
    Raporu e-posta ile gonder.
    """

    if sifre is None:
        import getpass
        sifre = getpass.getpass("Gmail App Password: ")

    try:
        # Raporu oku
        with open(rapor_path, 'r', encoding='utf-8') as f:
            rapor_icerik = f.read()

        # E-posta olustur
        msg = MIMEMultipart()
        msg['From'] = GONDERICI_EMAIL
        msg['To'] = ALICI_EMAIL
        msg['Subject'] = f"{konu} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # HTML icerik
        html_icerik = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .footer {{ padding: 10px; text-align: center; color: #888; }}
                pre {{ background: #222; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 BORSA KOMUTAN v4.0</h1>
                <p>Gunluk Analiz Raporu</p>
                <p>{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            <div class="content">
                <pre>{rapor_icerik}</pre>
            </div>
            <div class="footer">
                <p>Borsa Komutan v4.0 - AI Destekli Yatirim Sistemi</p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_icerik, 'html'))

        # Ek dosya (varsa)
        if ek_dosya and os.path.exists(ek_dosya):
            with open(ek_dosya, 'rb') as f:
                ek = MIMEBase('application', 'octet-stream')
                ek.set_payload(f.read())
            encoders.encode_base64(ek)
            ek.add_header('Content-Disposition', f'attachment; filename={os.path.basename(ek_dosya)}')
            msg.attach(ek)

        # Gmail'e baglan
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(GONDERICI_EMAIL, sifre)
            server.send_message(msg)

        print(f"[OK] E-posta gonderildi: {ALICI_EMAIL}")
        return True

    except Exception as e:
        print(f"[HATA] E-posta gonderilemedi: {e}")
        return False


# =============================================================================
# GUNLUK RAPOR GONDERME (Sonra tanimlanmali)
# =============================================================================

def gunluk_rapor_gonder(rapor_dir, sifre=None):
    """
    Son raporu otomatik olarak gonder.
    """
    try:
        # Son raporu bul
        raporlar = [f for f in os.listdir(rapor_dir) if f.endswith('.txt')]
        if not raporlar:
            print("[HATA] Rapor bulunamadi")
            return False

        son_rapor = sorted(raporlar)[-1]
        rapor_path = os.path.join(rapor_dir, son_rapor)

        # JSON rapor da varsa ekle
        json_rapor = son_rapor.replace('.txt', '.json')
        json_path = os.path.join(rapor_dir, json_rapor)

        # E-posta gonder
        return eposta_gonder(rapor_path,
                             konu=f"Borsa Komutan - {son_rapor.replace('analiz_raporu_', '').replace('.txt', '')}",
                             sifre=sifre,
                             ek_dosya=json_path if os.path.exists(json_path) else None)

    except Exception as e:
        print(f"[HATA] Gunluk rapor: {e}")
        return False


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    RAPOR_DIR = r"C:\Users\Administrator\PycharmProjects\PythonProject\Kimi\rapor"

    print("=" * 60)
    print("E-POSTA RAPOR SISTEMI - TEST")
    print("=" * 60)

    # Son raporu gonder
    gunluk_rapor_gonder(RAPOR_DIR)

    print("\nTEST TAMAMLANDI")