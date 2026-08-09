"""
forecast_horizon_ablation.py -- 预测步长消融实验
====================================
原理: 固定输入长度,改变预测步长,观察精度变化

测试目的:
  固定输入长度 512, 逐步增大 output_length (16->32->64->128->256),
  在正常数据和漂移数据两种场景下, 观测预测精度随预测步长的衰减规律,
  为工业部署提供"安全预测窗口"的量化依据.

调用次数: 20 次 (2模型 * 5长度 * 2场景)

Author: Janesong
Create Date: 2026/07/05
"""

import numpy as np
import pandas as pd

from core.timecho import forecast, calc_metrics
from config.constants import TRAIN_SEQ_LEN_512, FORECAST_POINT_LEN_256

# ============================================================
# Configuration
# ============================================================
N_TRAIN = TRAIN_SEQ_LEN_512
MAX_FORECAST = FORECAST_POINT_LEN_256
DRIFT_OFFSET = 15.0         # 漂移段的数值跳跃幅度
DRIFT_TREND_START = 65.0    # 漂移段趋势起始值
DRIFT_TREND_END = 90.0      # 漂移段趋势结束值
NOISE_STD_NORMAL = 2.0
NOISE_STD_DRIFT = 4.0

FORECAST_LENGTHS = [16, 32, 64, 128, 256]
MODELS = ["Chronos-2", "Timer-3.5"]
SCENARIOS = ["normal", "drift"]

def generate_test_data():
    """生成测试数据"""
    np.random.seed(42)
    
    # 1. 构造测试数据(统一生成 512+256=768 点)
    time_full = pd.date_range("2026-07-01", periods=N_TRAIN + MAX_FORECAST, freq="1h")
    time_history = time_full[:N_TRAIN]

    # --- 正常数据 ---
    trend_normal = np.linspace(50, 65, N_TRAIN + MAX_FORECAST)
    seasonal_normal = 15 * np.sin(2 * np.pi * np.arange(N_TRAIN + MAX_FORECAST) / 24)
    noise_normal = np.random.randn(N_TRAIN + MAX_FORECAST) * NOISE_STD_NORMAL
    target_normal = (trend_normal + seasonal_normal + noise_normal).round(4)

    # --- B5 复合漂移数据(历史段与正常数据相同)---
    target_drift = target_normal.copy()
    trend_drift_fc = np.linspace(DRIFT_TREND_START, DRIFT_TREND_END, MAX_FORECAST)
    seasonal_drift_fc = DRIFT_OFFSET * np.sin(2 * np.pi * np.arange(N_TRAIN, N_TRAIN + MAX_FORECAST) / 12)
    noise_drift_fc = np.random.randn(MAX_FORECAST) * NOISE_STD_DRIFT
    target_drift[N_TRAIN:] = (trend_drift_fc + seasonal_drift_fc + noise_drift_fc + DRIFT_OFFSET).round(4)

    # 历史段(两种场景共用)
    df_history = pd.DataFrame({"time": time_history, "target": target_normal[:N_TRAIN]})

    # Ground truth 字典(按长度切片)
    gt_normal = {L: target_normal[N_TRAIN:N_TRAIN + L] for L in FORECAST_LENGTHS}
    gt_drift = {L: target_drift[N_TRAIN:N_TRAIN + L] for L in FORECAST_LENGTHS}

    print(f"训练长度: {N_TRAIN}, 最大预测长度: {MAX_FORECAST}")
    print(f"模型: {MODELS}")
    print(f"预测长度: {FORECAST_LENGTHS}")
    print(f"场景: {SCENARIOS}")
    print(f"预计调用: {len(MODELS) * len(FORECAST_LENGTHS) * len(SCENARIOS)} 次")
    print()

    return df_history, gt_normal, gt_drift


# Main Execution Block 执行测试
def run_forecast_experiments(df_history, gt_normal, gt_drift):
    """执行预测实验"""

    # results[scenario][model][length] = {"mae": float, "step_mae": np.ndarray, "pred_len": int}
    results = {}

    for scenario in SCENARIOS:
        results[scenario] = {}
        scenario_name = "正常数据" if scenario == "normal" else "B5复合漂移"
        print(f"{'='*70}")
        print(f"场景: {scenario_name}")
        print(f"{'='*70}")

        for model_id in MODELS:
            results[scenario][model_id] = {}
            print(f"\n  模型: {model_id}")

            for L in FORECAST_LENGTHS:
                gt = gt_normal[L] if scenario == "normal" else gt_drift[L]
                try:
                    pred, _, _ = forecast(
                        targets=df_history,
                        model_id=model_id,
                        output_length=L,
                        time_col="time"
                    )
                    metrics = calc_metrics(pred, gt)
                    mae = metrics["MAE"]
                    step_mae = np.abs(pred - gt)
                    results[scenario][model_id][L] = {
                        "mae": mae,
                        "step_mae": step_mae,
                        "pred_len": len(pred)
                    }
                    print(f"    L={L:>3d}  MAE={mae:.4f}  (pred_len={len(pred)})")
                except Exception as e:
                    print(f"    L={L:>3d}  失败: {type(e).__name__}: {e}")
                    results[scenario][model_id][L] = {"mae": None, "step_mae": None, "pred_len": 0}

        print()
    
    return results


def print_summary_table(results):
    """打印汇总表"""
    print(f"{'='*80}")
    print("C2 预测长度消融 - 汇总")
    print(f"{'='*80}")
    print(f"{'场景':<12s} | {'模型':<15s} | {'L=16':>8s} | {'L=32':>8s} | {'L=64':>8s} | {'L=128':>8s} | {'L=256':>8s}")
    print("-" * 80)
    
    for scenario in SCENARIOS:
        scenario_name = "正常数据" if scenario == "normal" else "B5漂移"
        for model_id in MODELS:
            vals = []
            for L in FORECAST_LENGTHS:
                mae = results[scenario][model_id][L]["mae"]
                vals.append(f"{mae:.4f}" if mae is not None else "N/A")
            print(f"{scenario_name:<12s} | {model_id:<15s} | {vals[0]:>8s} | {vals[1]:>8s} | {vals[2]:>8s} | {vals[3]:>8s} | {vals[4]:>8s}")
        print("-" * 80)


def print_step_decay_analysis(results):
    """打印逐步衰减分析"""
    print(f"\n{'='*80}")
    print("逐步 MAE 衰减(前16步, 跨预测长度对比)")
    print(f"{'='*80}")

    for scenario in SCENARIOS:
        scenario_name = "正常数据" if scenario == "normal" else "B5漂移"
        for model_id in MODELS:
            print(f"\n  [{scenario_name} - {model_id}]")
            print(f"  {'步数':<6s} | ", end="")
            for L in FORECAST_LENGTHS:
                print(f"L={L:<5d}", end=" | ")
            print()
            print("  " + "-" * (8 + 10 * len(FORECAST_LENGTHS)))

            for step in range(16):
                print(f"  t+{step+1:<4d} | ", end="")
                for L in FORECAST_LENGTHS:
                    sm = results[scenario][model_id][L]["step_mae"]
                    if sm is not None and step < len(sm):
                        print(f"{sm[step]:.3f} ", end=" | ")
                    else:
                        print(f"  N/A ", end=" | ")
                print()


def print_ratio_analysis(results):
    """打印关键比值分析"""
    print(f"\n{'='*80}")
    print("精度衰减比(L=256 的 MAE / L=16 的 MAE)")
    print(f"{'='*80}")
    
    for scenario in SCENARIOS:
        scenario_name = "正常数据" if scenario == "normal" else "B5漂移"
        for model_id in MODELS:
            mae_16 = results[scenario][model_id][16]["mae"]
            mae_256 = results[scenario][model_id][256]["mae"]
            if mae_16 and mae_256 and mae_16 > 0:
                ratio = mae_256 / mae_16
                print(f"  {scenario_name:<12s} | {model_id:<15s} | L=16: {mae_16:.4f} -> L=256: {mae_256:.4f} | 衰减比: {ratio:.2f}x")


def main():
    """主函数"""
    print(f"训练长度: {N_TRAIN}, 最大预测长度: {MAX_FORECAST}")
    print(f"模型: {MODELS}")
    print(f"预测长度: {FORECAST_LENGTHS}")
    print(f"场景: {SCENARIOS}")
    print(f"预计调用: {len(MODELS) * len(FORECAST_LENGTHS) * len(SCENARIOS)} 次")
    print()

    # 1. 生成测试数据
    df_history, gt_normal, gt_drift = generate_test_data()

    # 2. 执行预测实验
    results = run_forecast_experiments(df_history, gt_normal, gt_drift)

    # 3. 打印汇总表
    print_summary_table(results)

    # 4. 打印逐步衰减分析
    print_step_decay_analysis(results)

    # 5. 打印比值分析
    print_ratio_analysis(results)


# ============================================================
# 程序入口
# ============================================================
if __name__ == "__main__":
    main()
