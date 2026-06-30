"""
Quant Dashboard Helper Module
Model sonuclarini dashboard JSON formatina donusturur
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any

class DashboardExporter:
    def __init__(self, output_dir: str = "dashboard_data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def export_metrics(self,
                      system_health: str = "SAGLIKLI",
                      live_return: float = 0.0,
                      overall_accuracy: float = 0.0,
                      buy_precision: float = 0.0,
                      buy_rate: float = 0.0,
                      active_signals: int = 0,
                      cash: float = 0.0,
                      model_version: str = "",
                      strategy: str = "",
                      experiment_day: int = 0,
                      experiment_total: int = 14) -> None:
        """Ana sistem metriklerini export et"""
        metrics = {
            "system_health": system_health,
            "system_health_emoji": "✅" if system_health == "SAGLIKLI" else "⚠️",
            "live_return": live_return,
            "overall_accuracy": overall_accuracy,
            "buy_precision": buy_precision,
            "buy_rate": buy_rate,
            "active_signals": active_signals,
            "cash": cash,
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "experiment_day": experiment_day,
            "experiment_total": experiment_total,
            "model_version": model_version,
            "strategy": strategy,
            "data_range": "Son 5 Gun",
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        self._save("metrics.json", metrics)

    def export_signals(self, signals: List[Dict[str, Any]]) -> None:
        """Sinyal listesini export et"""
        self._save("signals.json", signals)

    def export_performance(self,
                          v1_return: float = 0.0,
                          v2_return: float = 0.0,
                          benchmark: float = 0.0,
                          risk_reduction_pct: float = 0.0,
                          new_opportunities: int = 0,
                          agreement_pct: float = 0.0,
                          v1_drawdown: float = 0.0,
                          v2_drawdown: float = 0.0,
                          v1_precision: float = 0.0,
                          v2_precision: float = 0.0) -> None:
        """v1 vs v2 performans karsilastirmasi"""
        performance = {
            "v1_return": v1_return,
            "v2_return": v2_return,
            "benchmark": benchmark,
            "risk_reduction_pct": risk_reduction_pct,
            "new_opportunities": new_opportunities,
            "agreement_pct": agreement_pct,
            "v1_drawdown": v1_drawdown,
            "v2_drawdown": v2_drawdown,
            "v1_precision": v1_precision,
            "v2_precision": v2_precision,
            "experiment_days": 14,
            "current_day": 8
        }
        self._save("performance.json", performance)

    def export_canary(self, canary_list: List[Dict[str, Any]]) -> None:
        """Risk RED listesi (v1=AL, v2=BEKLE)"""
        self._save("canary.json", canary_list)

    def export_opportunities(self, opportunities: List[Dict[str, Any]]) -> None:
        """Yeni firsatlar (v1=BEKLE, v2=AL)"""
        self._save("opportunities.json", opportunities)

    def export_filtered(self,
                       atr_limit: List[Dict[str, Any]] = None,
                       liquidity: List[Dict[str, Any]] = None,
                       rf_guard: List[Dict[str, Any]] = None) -> None:
        """Filtrelenen hisseler"""
        filtered = {
            "atr_limit": atr_limit or [],
            "liquidity": liquidity or [],
            "rf_guard": rf_guard or []
        }
        self._save("filtered.json", filtered)

    def export_equity(self,
                     portfolio_values: List[float],
                     benchmark_values: List[float],
                     dates: List[str],
                     max_drawdown: float = 0.0,
                     sharpe_ratio: float = 0.0,
                     win_rate: float = 0.0) -> None:
        """Equity curve verisi"""
        equity = {
            "portfolio_values": portfolio_values,
            "benchmark_values": benchmark_values,
            "dates": dates,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate
        }
        self._save("equity.json", equity)

    def export_confusion(self,
                        matrix: List[List[int]],
                        labels: List[str],
                        accuracy: float = 0.0,
                        precision_al: float = 0.0,
                        recall_al: float = 0.0,
                        f1_al: float = 0.0) -> None:
        """Confusion matrix"""
        confusion = {
            "matrix": matrix,
            "labels": labels,
            "accuracy": accuracy,
            "precision_al": precision_al,
            "recall_al": recall_al,
            "f1_al": f1_al
        }
        self._save("confusion.json", confusion)

    def export_prf_trend(self,
                        days: List[str],
                        precision: List[float],
                        recall: List[float],
                        f1: List[float]) -> None:
        """Precision/Recall/F1 trend"""
        prf = {
            "days": days,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }
        self._save("prf_trend.json", prf)

    def export_all(self, data: Dict[str, Any]) -> None:
        """Tum verileri tek seferde export et"""
        for key, value in data.items():
            self._save(f"{key}.json", value)

    def _save(self, filename: str, data: Any) -> None:
        """JSON dosyasina kaydet"""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[OK] {filename} kaydedildi")


# Kullanim ornegi
if __name__ == "__main__":
    exporter = DashboardExporter()

    # Metrikleri export et
    exporter.export_metrics(
        system_health="SAGLIKLI",
        live_return=2.34,
        overall_accuracy=51.9,
        buy_precision=0.52,
        buy_rate=46,
        active_signals=64,
        cash=32,
        model_version="ai_model_v43_20260627_221915",
        strategy="GB=1.0 | RF Guard (bear only)",
        experiment_day=8,
        experiment_total=14
    )

    # Sinyalleri export et
    exporter.export_signals([
        {"ticker": "ACSEL", "decision": "AL", "gb": 0.734, "confidence": "HIGH", "regime": "bull"},
        {"ticker": "ALBRK", "decision": "BEKLE", "gb": 0.674, "confidence": "MEDIUM", "regime": "bear", "guard": True}
    ])

    print("\nTum veriler export edildi!")