#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dirty_test.py —— Dirty data robustness (NaN not supported)
====================================
测试目的: 验证模型对缺失值、异常尖峰的抵抗力
作用: 测试模型对脏数据的鲁棒性
原理: 用 7 种脏数据(含 baseline)分别预测, 对比精度退化程度

API限制: TimechoAI API 不支持 NaN 值输入(包括 target 和 cov 列)

Author: Janesong
Create Date: 2026/06/29, Update on 2026/08/07.
"""

import time
import numpy as np
import pandas as pd

from config.settings import DATA_DIR, OUTPUT_DIR
from config.constants import MODEL_LIST, HISTORY_POINT_LEN_256, FORECAST_POINT_LEN_64
from core.dataResults import clean_nan_values, get_results
from core.timecho import forecast, calc_metrics
from core.resume import load_completed_results, append_result, is_rate_limited
from utils.files import read_csv_to_dataframe

# ============================================================
# Data related configuration
# ============================================================
DATA_SUBDIR = DATA_DIR / "features" / "futureCovs" / "dirtyData"    # Test data file path
DATA_CSV_PATH = DATA_SUBDIR / "dirty_clean.csv"
OUTPUT_SUBDIR = OUTPUT_DIR / "features" / "futureCovs" / "dirtyData"
OUTPUT_SUBDIR.mkdir(parents=True, exist_ok=True)
RESULT_CSV_PATH = OUTPUT_SUBDIR / "dirty_test_result.csv"    # Prediction results file

# ============================================================
# 计算测试数量
# ============================================================
completed_records, perm_fail_count = load_completed_results(str(RESULT_CSV_PATH))

# 构建已完成测试的 key 集合 (model_id, scene, pass)
completed_keys = set()
retry_keys = set()  # 待重试的限流错误

for r in completed_records:
    key = (r.get("model_id"), r.get("scene"), r.get("pass"))
    if r.get("success") == True:
        completed_keys.add(key)
    elif is_rate_limited(str(r.get("error", ""))):
        retry_keys.add(key)  # 限流错误, 加入重试集合
    # 其他失败不计入 completed_keys, 会重新测试

# 7 个测试场景
SCENES = [
    ("S0-干净",       "dirty_s0_clean.csv"),
    ("S1-缺失5%",     "dirty_s1_miss5.csv"),
    ("S2-缺失15%",    "dirty_s2_miss15.csv"),
    ("S3-连续缺失",   "dirty_s3_miss_block.csv"),
    ("S4-单点尖峰",   "dirty_s4_spike_single.csv"),
    ("S5-多点尖峰",   "dirty_s5_spike_multi.csv"),
    ("S6-混合脏",     "dirty_s6_mixed.csv"),
]

total_tests = len(MODEL_LIST) * len(SCENES) * 2   # 原始 和 预处理两轮
skipped_tests = len(completed_keys)
remaining_tests = total_tests - skipped_tests - perm_fail_count

print(f"总任务: {total_tests} | 需完成: {remaining_tests} | 已完成: {skipped_tests} | 永久失败(Skip): {perm_fail_count}")
print()

# Read data
# 读取 ground truth (用干净数据的后 64 行作为真实值)
print("  Reading data for ground truth...")
clean_df = read_csv_to_dataframe(DATA_CSV_PATH)
clean_df["time"] = pd.to_datetime(clean_df["time"])
ground_truth = clean_df.iloc[HISTORY_POINT_LEN_256:]["target"].values
future_cov = clean_df.iloc[HISTORY_POINT_LEN_256:][["time", "cov"]].copy()
print(f"   ground_truth: {len(ground_truth)} 个点")
print(f"   ground_truth range: {ground_truth.min():.2f} ~ {ground_truth.max():.2f}")
print()

def make_base_record(model_id, csv_file, nan_count, ground_truth):
    """创建 base_record,确保列顺序固定"""
    return {
        "model_id": model_id,
        "scene": None,
        "csv_file": csv_file,
        "pass": None,
        "success": None,
        "mae": None,
        "rmse": None,
        "mape": None,
        "latency_ms": None,
        "pred_min": None,
        "pred_max": None,
        "truth_min": float(np.min(ground_truth)),
        "truth_max": float(np.max(ground_truth)),
        "is_explosion": None,
        "nan_count": nan_count,
        "error": None,
    }

# ============================================================
# 逐场景 * 逐模型 测试
# ============================================================

api_call_count = 0  # API 调用计数
success_count = 0
fail_count = 0

print(f"🚀 开始测试...")
print("=" * 90)

for model_id in MODEL_LIST:
    # 判断是否为单变量模型
    is_univariate = model_id.startswith("Timer")
    print(f"\n{'─' * 90}")
    print(f"📋 模型: {model_id} (单变量模式: {is_univariate})")
    print(f"{'─' * 90}")

    for scene_name, csv_file in SCENES:
        print(f"\n  🔍 场景: {scene_name} ({csv_file})")

        # 读取脏数据
        df = read_csv_to_dataframe(DATA_SUBDIR / csv_file)
        df["time"] = pd.to_datetime(df["time"])

        history = df.iloc[:HISTORY_POINT_LEN_256].copy()
        # 检查脏数据概况
        nan_count = history["target"].isna().sum()
        valid_vals = history["target"].dropna()
        data_range = f"{valid_vals.min():.1f}~{valid_vals.max():.1f}" if len(valid_vals) > 0 else "全NaN"
        print(f"     历史 target: NaN={nan_count}, 范围={data_range}")

        scene_base = make_base_record(model_id, csv_file, nan_count, ground_truth)

        # ===== 两轮测试: 原始 + 预处理后 =====
        for pass_name, pass_df in [("原始", history.copy()), ("预处理", history.copy())]:
            label = f"{scene_name}[{pass_name}]"
            test_key = (model_id, label, pass_name)

            # 断点续跑: 检查是否已完成或待重试
            if test_key in completed_keys and test_key not in retry_keys:
                # 已成功完成, 跳过
                print(f"     [{pass_name}] 已完成, 跳过")
                continue

            # 如果是待重试的限流错误, 提示用户
            if test_key in retry_keys:
                print(f"     [{pass_name}] 重试(之前429限流)")
            
            # 无论原始还是预处理, 都填充协变量列的 NaN(避免 API 报错)
            #  因为协变量列的 NaN 不是测试重点, 只是数据质量问题, 避免API报错
            if not is_univariate and "cov" in pass_df.columns:
                cov_nan_before = pass_df["cov"].isna().sum()
                if cov_nan_before > 0:
                    pass_df["cov"] = pass_df["cov"].ffill().bfill()
                    cov_nan_after = pass_df["cov"].isna().sum()
                    print(f"     [{pass_name}] 协变量列预处理: 填充 {cov_nan_before} 个NaN")

            if pass_name == "预处理":
                # 预处理轮:填充目标列的 NaN(测试模型对预处理后数据的预测能力)
                target_nan_before = pass_df["target"].isna().sum()
                if target_nan_before > 0:
                    pass_df["target"] = pass_df["target"].ffill().bfill()
                    target_nan_after = pass_df["target"].isna().sum()
                    print(f"     [{pass_name}] 目标列预处理: 填充 {target_nan_before} 个NaN")
            else:
                # 原始轮:保持目标列的 NaN(测试模型对缺失值的反应)
                # 如果 API 不支持 NaN,会报错,这也是测试结果之一
                target_nan_count = pass_df["target"].isna().sum()
                if target_nan_count > 0:
                    print(f"     [{pass_name}] 目标列保持原始: {target_nan_count} 个NaN(测试缺失值鲁棒性)")

            history_targets = pass_df[["time", "target"]]
            history_covs = pass_df[["time", "cov"]]

            try:
                # 动态构建参数: 如果是 Timer 系列, 不传协变量
                forecast_kwargs = {
                    "targets": history_targets,
                    "model_id": model_id,
                    "output_length": FORECAST_POINT_LEN_64,
                    "time_col": "time",
                    "auto_adapt": True,
                }

                # 多变量模型才传协变量
                if not is_univariate:
                    forecast_kwargs["history_covs"] = history_covs
                    forecast_kwargs["future_covs"] = future_cov

                # 通过 core/timecho.py 的封装调用 API (间接使用 utils/client.py)
                api_call_count += 1
                print(f"     [{pass_name}] API调用 #{api_call_count}...")

                pred_values, elapsed_ms, error = forecast(**forecast_kwargs)

                if error:
                    
                    # 判断是否为限流错误
                    if is_rate_limited(error):
                        print(f"     [{pass_name}] 限流(429), 已记录, 下次重试")
                    else:
                        print(f"     [{pass_name}] 失败: {error[:80]}")
                    
                    fail_count += 1

                    result_record = {
                        **scene_base,
                        "scene": label,
                        "pass": pass_name,
                        "success": False,
                        "latency_ms": elapsed_ms,
                        "error": error,
                    }
                    result_record = clean_nan_values(result_record)
                    append_result(str(RESULT_CSV_PATH), result_record)

                else:
                    # 使用 core/timecho.py 的 calc_metrics 计算精度指标
                    metrics = calc_metrics(pred_values, ground_truth)
                    mae = metrics["MAE"]
                    rmse = metrics["RMSE"]
                    mape = metrics["MAPE"]

                    # 检测预测是否"起飞"或"雪崩"
                    pred_max = float(np.max(pred_values))
                    pred_min = float(np.min(pred_values))
                    truth_max = float(np.max(ground_truth))
                    truth_min = float(np.min(ground_truth))
                    is_explosion = pred_max > truth_max * 1.5 or pred_min < truth_min * 0.5

                    status = "💥 起飞/雪崩!" if is_explosion else "✅ 正常"
                    print(f"     [{pass_name}] {status} MAE={mae:.4f}, 范围={pred_min:.2f}~{pred_max:.2f}")
                    
                    success_count += 1

                    result_record = {
                        **scene_base,
                        "scene": label,
                        "pass": pass_name,
                        "success": True,
                        "mae": mae,
                        "rmse": rmse,
                        "mape": mape,
                        "latency_ms": elapsed_ms,
                        "pred_min": pred_min,
                        "pred_max": pred_max,
                        "is_explosion": is_explosion,
                    }
                    result_record = clean_nan_values(result_record)
                    append_result(str(RESULT_CSV_PATH), result_record)

            except Exception as e:
                error_msg = str(e)

                # 判断是否为限流错误
                if is_rate_limited(error_msg):
                    print(f"     [{pass_name}] 限流(429), 已记录, 下次重试")
                else:
                    print(f"     [{pass_name}] 失败: {error_msg[:80]}")
                
                fail_count += 1

                result_record = {
                    **scene_base,
                    "scene": label,
                    "pass": pass_name,
                    "success": False,
                    "latency_ms": 0,
                    "error": error_msg,
                }
                result_record = clean_nan_values(result_record)
                append_result(str(RESULT_CSV_PATH), result_record)

            time.sleep(1)

# ============================================================
# 测试统计
# ============================================================
print()
print("=" * 90)
print("测试统计")
print(f"  API调用次数: {api_call_count} | 成功: {success_count} | 失败: {fail_count} | 跳过(已完成): {skipped_tests}")
print("=" * 90)

# ============================================================
# 读取完整结果并生成汇总报告
# ============================================================
print("=" * 90)
print("读取完整结果, 生成汇总报告")
print("=" * 90)

# 读取所有结果(包括之前完成的)
results_data, _ = load_completed_results(str(RESULT_CSV_PATH))

print("\n" + "=" * 100)
print("📋 鲁棒性分析结论")
print("=" * 100)

for model_id in MODEL_LIST:
    model_results = [r for r in results_data if r["model_id"] == model_id]
    
    if len(model_results) == 0:
        print(f"  [{model_id}] 无结果数据")
        continue
    
    print(f"\n  【{model_id}】")
    s0_pre = get_results(results_data, model_id, "S0", "预处理")
    
    if not s0_pre or not s0_pre["success"]:
        print(f"    [warning] 基准场景都失败了, 无法评估鲁棒性.")
        continue

    baseline_mae = s0_pre["mae"]
    print(f"    基准(S0干净[预处理]) MAE = {baseline_mae:.4f}")

    # 分析缺失值场景
    print(f"\n    ▶ 缺失值抵抗力 (基于[预处理]结果):")
    for scene_prefix in ["S1", "S2", "S3"]:
        r_pre = get_results(results_data, model_id, scene_prefix, "预处理")
        r_raw = get_results(results_data, model_id, scene_prefix, "原始")
        if r_raw and not r_raw["success"]:
            print(f"      {r_raw['scene'].replace('[原始]',''):>14s} (原始): ❌ 报错 (不支持 NaN)")
        if r_pre and r_pre["success"]:
            ratio = r_pre["mae"] / baseline_mae if baseline_mae > 0 else float("inf")
            verdict = "✅ 无影响" if ratio < 1.5 else ("🟡 轻微退化" if ratio < 3 else "🔴 明显退化")
            print(f"      {r_pre['scene'].replace('[预处理]',''):>14s} (预处理): MAE={r_pre['mae']:.4f} (基准的 {ratio:.1f}x) -> {verdict}")

    # 异常尖峰抵抗力
    print(f"\n    ▶ 异常尖峰抵抗力 (基于[原始]结果):")
    for scene_prefix in ["S4", "S5"]:
        r_raw = get_results(results_data, model_id, scene_prefix, "原始")
        if r_raw and r_raw["success"]:
            ratio = r_raw["mae"] / baseline_mae if baseline_mae > 0 else float("inf")
            verdict = "💥 起飞/雪崩!" if r_raw["is_explosion"] else ("✅ 扛住了" if ratio < 1.5 else "[warning] 精度退化")
            print(f"      {r_raw['scene'].replace('[原始]',''):>14s}: MAE={r_raw['mae']:.4f} (基准的 {ratio:.1f}x) -> {verdict}")

    # 混合脏数据
    print(f"\n    ▶ 混合脏数据 (基于[预处理]结果):")
    r_pre = get_results(results_data, model_id, "S6", "预处理")
    if r_pre and r_pre["success"]:
        ratio = r_pre["mae"] / baseline_mae if baseline_mae > 0 else float("inf")
        verdict = "💥 起飞/雪崩!" if r_pre["is_explosion"] else ("✅ 工业可用" if ratio < 1.5 else "🔴 不可用")
        print(f"      S6-混合脏 (预处理): MAE={r_pre['mae']:.4f} (基准的 {ratio:.1f}x) -> {verdict}")
    print()

# ============================================================
# Results File
# ============================================================
print("=" * 90)
print(" Results File")
print("=" * 90)
print(f"   CSV结果路径: {RESULT_CSV_PATH}")
print(" Test completed!")
print("=" * 90)
