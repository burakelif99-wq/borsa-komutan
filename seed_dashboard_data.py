from dashboard_exporter import DashboardExporter
exporter = DashboardExporter(output_dir="dashboard_data")

exporter.export_metrics(
    system_health="SAGLIKLI", live_return=2.34, overall_accuracy=51.9,
    buy_precision=0.52, buy_rate=46, active_signals=64, cash=32,
    model_version="ai_model_v43_20260627_221915",
    strategy="GB=1.0 | RF Guard (bear only)",
    experiment_day=1, experiment_total=14
)

exporter.export_signals([
    {"ticker": "ACSEL", "decision": "AL", "gb": 0.734, "rf": None, "guard": False, "reason": "GB_PASS", "regime": "bull", "esik": 0.40, "fiyat": 100.0},
    {"ticker": "RALYH", "decision": "BEKLE", "gb": 0.903, "rf": None, "guard": False, "reason": "ATR_LIMIT", "regime": "bull", "esik": 0.40, "fiyat": 158.4},
    {"ticker": "SANEL", "decision": "BEKLE", "gb": 0.671, "rf": None, "guard": False, "reason": "ATR_LIMIT", "regime": "bull", "esik": 0.40, "fiyat": 100.0},
    {"ticker": "ALBRK", "decision": "BEKLE", "gb": 0.674, "rf": 0.301, "guard": True, "reason": "RF_GUARD", "regime": "bear", "esik": 0.55, "fiyat": 100.0},
    {"ticker": "THYAO", "decision": "BEKLE", "gb": 0.432, "rf": None, "guard": False, "reason": "GB_LOW", "regime": "sideways", "esik": 0.45, "fiyat": 100.0},
])

exporter.export_performance(
    v1_return=5.82, v2_return=7.31, benchmark=1.92,
    risk_reduction_pct=24, new_opportunities=13, agreement_pct=93.6,
    v1_drawdown=-12.4, v2_drawdown=-9.4, v1_precision=0.42, v2_precision=0.52
)

exporter.export_canary([
    {"ticker": "RALYH", "v1": "AL", "v2": "BEKLE", "reason": "ATR_LIMIT", "gb": 0.903, "change_pct": 10.0},
    {"ticker": "SANEL", "v1": "AL", "v2": "BEKLE", "reason": "ATR_LIMIT", "gb": 0.671, "change_pct": 10.0},
])

exporter.export_opportunities([
    {"ticker": "ARCLK", "v1": "BEKLE", "v2": "AL", "gb": 0.720},
    {"ticker": "TUPRS", "v1": "BEKLE", "v2": "AL", "gb": 0.680},
    {"ticker": "GARAN", "v1": "BEKLE", "v2": "AL", "gb": 0.650},
])

exporter.export_filtered(
    atr_limit=[
        {"ticker": "RALYH", "gb": 0.903, "atr_pct": 8.4, "kacirilan_getiri": 10.0},
        {"ticker": "SANEL", "gb": 0.671, "atr_pct": 7.2, "kacirilan_getiri": 10.0},
        {"ticker": "KONTR", "gb": 0.580, "atr_pct": 9.1, "kacirilan_getiri": 6.5},
    ],
    liquidity=[{"ticker": "XYZ", "gb": 0.72, "reason": "Hacim < 1M TL"}],
    rf_guard=[{"ticker": "ALBRK", "gb": 0.674, "reason": "RF Guard (Bear)"}],
)

exporter.export_equity(
    portfolio_values=[100000, 103200, 107800, 112400, 108900, 115600, 119400],
    benchmark_values=[100000, 101500, 102800, 103200, 101800, 103500, 101920],
    dates=["Gun 1", "Gun 5", "Gun 10", "Gun 15", "Gun 20", "Gun 25", "Gun 30"],
    max_drawdown=-8.5, sharpe_ratio=1.24, win_rate=62.0
)

exporter.export_confusion(
    matrix=[[42, 8, 3], [5, 12, 2], [2, 1, 8]],
    labels=["AL", "BEKLE", "SAT"],
    accuracy=0.519, precision_al=0.50, recall_al=0.75, f1_al=0.60
)

exporter.export_prf_trend(
    days=["G1","G2","G3","G4","G5","G6","G7","G8","G9","G10","G11","G12","G13","G14"],
    precision=[0.42,0.44,0.45,0.48,0.47,0.49,0.50,0.51,0.50,0.52,0.51,0.53,0.52,0.52],
    recall=[0.68,0.70,0.72,0.71,0.73,0.74,0.75,0.74,0.76,0.75,0.77,0.76,0.75,0.75],
    f1=[0.52,0.54,0.55,0.57,0.56,0.58,0.59,0.59,0.60,0.60,0.61,0.61,0.60,0.60]
)

print("Tum JSON dosyalari olusturuldu.")
