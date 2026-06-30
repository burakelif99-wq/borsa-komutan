# kimi_al.py - RİSK MODÜLÜ

import numpy as np
import pandas as pd
from datetime import datetime


def calculate_risk_metrics(df):
    """
    BIST 100 risk metrikleri hesaplar
    Girdi: veri_al.py çıktısı (DataFrame)
    Çıktı: Risk skoru ve metrikler
    """
    if df is None or len(df) < 30:
        return {
            'status': 'ERROR',
            'message': 'Yetersiz veri (min 30 gün)'
        }

    close = df['Close']
    returns = close.pct_change().dropna()

    if len(returns) < 10:
        return {
            'status': 'ERROR',
            'message': 'Yetersiz getiri verisi'
        }

    # 1. Volatilite (Yıllık)
    volatility = returns.std() * np.sqrt(252) * 100

    # 2. Sharpe Ratio (risksiz faiz %50 -> 0.50)
    risk_free_rate = 0.50 / 252
    excess_return = returns.mean() - risk_free_rate
    sharpe = (excess_return / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0

    # 3. Value at Risk (95% güven)
    var_95 = np.percentile(returns, 5) * 100

    # 4. Maximum Drawdown
    cummax = close.cummax()
    drawdown = (close - cummax) / cummax
    max_dd = drawdown.min() * 100

    # 5. ATR bazlı risk
    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift(1))
    low_close = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(14, min_periods=1).mean().iloc[-1]
    atr_risk = (atr / close.iloc[-1]) * 100

    # 6. Composite Risk Skoru (0-100, 100 = en riskli)
    vol_score = min(volatility / 50 * 100, 100)
    sharpe_score = max(0, min((sharpe + 2) / 4 * 100, 100))
    var_score = min(abs(var_95) / 5 * 100, 100)
    dd_score = min(abs(max_dd) / 20 * 100, 100)

    risk_skor = (
            vol_score * 0.30 +
            (100 - sharpe_score) * 0.25 +
            var_score * 0.25 +
            dd_score * 0.20
    )

    return {
        'status': 'OK',
        'symbol': 'XU100',
        'last_price': round(close.iloc[-1], 2),
        'metrics': {
            'volatility_yearly': round(volatility, 2),
            'sharpe_ratio': round(sharpe, 3),
            'var_95_percent': round(var_95, 2),
            'max_drawdown_percent': round(max_dd, 2),
            'atr_percent': round(atr_risk, 2)
        },
        'risk_skor': round(risk_skor, 1),
        'risk_level': get_risk_level(risk_skor),
        'ensemble_weight': 0.25,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def get_risk_level(skor):
    if skor < 30:
        return 'DUSUK_RISK'
    elif skor < 50:
        return 'ORTA_RISK'
    elif skor < 70:
        return 'YUKSEK_RISK'
    else:
        return 'COK_YUKSEK_RISK'


if __name__ == "__main__":
    from veri_al import get_bist100

    result = get_bist100()
    if result['status'] == 'OK':
        risk = calculate_risk_metrics(result['data'])
        print(f"\n{'=' * 50}")
        print(f"RİSK MODÜLÜ (kimi_al.py)")
        print(f"{'=' * 50}")
        print(f"Son Fiyat: {risk['last_price']}")
        print(f"\nMetrikler:")
        for k, v in risk['metrics'].items():
            print(f"  {k}: {v}")
        print(f"\nRisk Skoru: {risk['risk_skor']}/100")
        print(f"Risk Seviyesi: {risk['risk_level']}")
        print(f"Ensemble Ağırlık: {risk['ensemble_weight']}")
        print(f"{'=' * 50}")
    else:
        print(f"Veri hatası: {result['message']}")
