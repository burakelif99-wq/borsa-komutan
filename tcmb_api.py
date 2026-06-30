# doviz_api.py - ÜCRETSİZ DÖVİZ API

import requests


def usd_try():
    """Exchangerate-API (ücretsiz, güvenilir)"""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/USD"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            'status': 'OK',
            'kur': data['rates']['TRY'],
            'kaynak': 'exchangerate-api.com',
            'tarih': data['date']
        }
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def usd_try_frankfurter():
    """Frankfurter API (ECB, ücretsiz)"""
    try:
        url = "https://api.frankfurter.app/latest?from=USD&to=TRY"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            'status': 'OK',
            'kur': data['rates']['TRY'],
            'kaynak': 'frankfurter.app',
            'tarih': data['date']
        }
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


def eur_try():
    """EUR/TRY"""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/EUR"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            'status': 'OK',
            'kur': data['rates']['TRY'],
            'kaynak': 'exchangerate-api.com'
        }
    except Exception as e:
        return {'status': 'ERROR', 'message': str(e)}


if __name__ == "__main__":
    print("=" * 50)
    print("DÖVİZ API TEST")
    print("=" * 50)

    usd = usd_try()
    print(f"USD/TRY: {usd}")

    eur = eur_try()
    print(f"EUR/TRY: {eur}")

    print("=" * 50)
