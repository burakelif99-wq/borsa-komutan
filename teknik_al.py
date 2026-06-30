# teknik_al.py - TEKNİK ANALİZ MODÜLÜ

import pandas as pd
import numpy as np


def calculate_technical_indicators(df):
    if df is None or len(df) < 30:
        return {'status': 'ERROR', 'message': 'Yetersiz veri'}

    close = df['Close']
    high = df['High']
    low = df['Low']

    # RSI (14)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal

    # Bollinger Bands (20, 2)
    sma20 = close.rolling(window=20).mean()
    std20 = close.rolling(window=20).std()
    bb_upper = sma20 + (std20 * 2)
    bb_lower = sma20 - (std20 * 2)
    bb_position = (close - bb_lower) / (bb_upper - bb_lower)

    # SMA Kesişim - DÜZELTİLMİŞ
    sma50 = close.rolling(window=50).mean()
    sma200 = close.rolling(window=min(len(close), 50)).mean()  # Max 50 günlük

    golden_cross = sma50 > sma200
    death_cross = sma50 < sma200

    # Son değerler
    last = len(close) - 1

    # NaN kontrolü
    rsi_last = rsi.iloc[last] if not pd.isna(rsi.iloc[last]) else 50
    macd_last = macd.iloc[last] if not pd.isna(macd.iloc[last]) else 0
    signal_last = signal.iloc[last] if not pd.isna(signal.iloc[last]) else 0
    hist_last = histogram.iloc[last] if not pd.isna(histogram.iloc[last]) else 0
    bb_pos_last = bb_position.iloc[last] if not pd.isna(bb_position.iloc[last]) else 0.5
    sma50_last = sma50.iloc[last] if not pd.isna(sma50.iloc[last]) else close.iloc[last]
    sma200_last = sma200.iloc[last] if not pd.isna(sma200.iloc[last]) else close.iloc[last]

    # Skor hesaplama
    rsi_score = min(rsi_last, 100) if not pd.isna(rsi_last) else 50

    macd_score = 50
    if not pd.isna(hist_last):
        if hist_last > 0 and hist_last > (
        histogram.iloc[last - 1] if last > 0 and not pd.isna(histogram.iloc[last - 1]) else 0):
            macd_score = 70
        elif hist_last < 0:
            macd_score = 30

    bb_score = bb_pos_last * 100 if not pd.isna(bb_pos_last) else 50
    if bb_score > 80:
        bb_score = 80
    elif bb_score < 20:
        bb_score = 20

    sma_score = 50
    if not pd.isna(golden_cross.iloc[last]):
        if golden_cross.iloc[last]:
            sma_score = 70
        elif death_cross.iloc[last]:
            sma_score = 30

    technical_score = (
            rsi_score * 0.25 +
            macd_score * 0.30 +
            bb_score * 0.25 +
            sma_score * 0.20
    )

    return {
        'status': 'OK',
        'indicators': {
            'rsi': round(float(rsi_last), 2) if not pd.isna(rsi_last) else 50.0,
            'macd': round(float(macd_last), 4) if not pd.isna(macd_last) else 0.0,
            'macd_signal': round(float(signal_last), 4) if not pd.isna(signal_last) else 0.0,
            'macd_histogram': round(float(hist_last), 4) if not pd.isna(hist_last) else 0.0,
            'bb_upper': round(float(bb_upper.iloc[last]), 2) if not pd.isna(bb_upper.iloc[last]) else round(
                float(close.iloc[last]), 2),
            'bb_lower': round(float(bb_lower.iloc[last]), 2) if not pd.isna(bb_lower.iloc[last]) else round(
                float(close.iloc[last]), 2),
            'bb_position': round(float(bb_pos_last), 4) if not pd.isna(bb_pos_last) else 0.5,
            'sma50': round(float(sma50_last), 2) if not pd.isna(sma50_last) else round(float(close.iloc[last]), 2),
            'sma200': round(float(sma200_last), 2) if not pd.isna(sma200_last) else round(float(close.iloc[last]), 2),
            'golden_cross': bool(golden_cross.iloc[last]) if not pd.isna(golden_cross.iloc[last]) else False,
            'death_cross': bool(death_cross.iloc[last]) if not pd.isna(death_cross.iloc[last]) else False
        },
        'signals': {
            'rsi_signal': 'ASIRI_ALIM' if rsi_last > 70 else 'ASIRI_SATIM' if rsi_last < 30 else 'NÖTR',
            'macd_signal': 'YUKARI' if hist_last > 0 else 'AŞAĞI',
            'bb_signal': 'UST_BAND' if bb_pos_last > 0.8 else 'ALT_BAND' if bb_pos_last < 0.2 else 'ORTA',
            'sma_signal': 'GOLDEN_CROSS' if (
                        not pd.isna(golden_cross.iloc[last]) and golden_cross.iloc[last]) else 'DEATH_CROSS' if (
                        not pd.isna(death_cross.iloc[last]) and death_cross.iloc[last]) else 'NÖTR'
        },
        'score': round(float(technical_score), 1) if not pd.isna(technical_score) else 50.0,
        'weight': 0.40,
        'timestamp': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }
