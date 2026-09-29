"""通过 POWER API 官方参数查询端点获取全部可用参数

端点: https://power.larc.nasa.gov/api/system/manager/parameters
必须提供 community 和 temporal 参数:
- community: AG (农业), RE (可再生能源), SB (可持续建筑)
- temporal: HOURLY, DAILY, MONTHLY, CLIMATOLOGY
"""
import os
import sys
import json
from collections import defaultdict

import requests

BASE_URL = "https://power.larc.nasa.gov/api/system/manager/parameters"
COMMUNITIES = ["AG", "RE", "SB"]
TEMPORALS = ["HOURLY", "DAILY", "MONTHLY", "CLIMATOLOGY"]


def query_all_parameters():
    """查询所有 community × temporal 组合的参数，返回 (all_results, param_info_master)"""
    all_results = {}
    all_param_names = set()
    param_info_master = {}

    for comm in COMMUNITIES:
        all_results[comm] = {}
        for temp in TEMPORALS:
            url = f"{BASE_URL}?user=nasapower4r&community={comm}&temporal={temp}&metadata=true"
            try:
                resp = requests.get(url, timeout=60)
                status = resp.status_code
                if status == 200:
                    data = resp.json()
                    if isinstance(data, dict):
                        params = data
                    elif isinstance(data, list):
                        params = {}
                        for item in data:
                            if isinstance(item, dict) and "name" in item:
                                params[item["name"]] = item
                    else:
                        params = {}
                    all_results[comm][temp] = params
                    all_param_names.update(params.keys())
                    for pname, pinfo in params.items():
                        if pname not in param_info_master:
                            param_info_master[pname] = {"name": pname}
                        if isinstance(pinfo, dict):
                            for k, v in pinfo.items():
                                if v not in (None, "", [], {}):
                                    param_info_master[pname][k] = v
                    print(f"  {comm} / {temp}: {len(params):3d} 个参数 (HTTP {status})")
                else:
                    all_results[comm][temp] = {}
                    print(f"  {comm} / {temp}: HTTP {status} - {resp.text[:100]}")
            except Exception as e:
                all_results[comm][temp] = {}
                print(f"  {comm} / {temp}: 异常 {e}")

    return all_results, param_info_master, all_param_names


def print_matrix(all_results):
    """打印参数数矩阵"""
    print(f"\n--- 参数数矩阵 ---")
    print(f"{'':12}", end="")
    for temp in TEMPORALS:
        print(f"{temp:>13}", end="")
    print()
    for comm in COMMUNITIES:
        print(f"{comm:12}", end="")
        for temp in TEMPORALS:
            cnt = len(all_results[comm][temp])
            print(f"{cnt:>13}", end="")
        print()


def print_by_type(param_info_master):
    """按类型分类打印"""
    print(f"\n{'='*80}")
    print("--- 按参数类型分类 ---")
    by_type = defaultdict(list)
    for pname, pinfo in param_info_master.items():
        ptype = pinfo.get("type") or pinfo.get("Type") or "UNKNOWN"
        by_type[ptype].append(pname)

    for t, pnames in sorted(by_type.items()):
        print(f"\n  [{t}] ({len(pnames)} 个)")
        for pn in sorted(pnames):
            info = param_info_master[pn]
            units = info.get("units", info.get("Units", "?"))
            name_long = info.get("name_long", info.get("long_name", info.get("Name", "")))
            defn = info.get("definition", info.get("Definition", ""))
            label = name_long if name_long else (defn[:50] if defn else "")
            print(f"    {pn:<30} {units:<15} {label}")


def main():
    sys.stdout.reconfigure(line_buffering=True)
    print("=" * 80)
    print("NASA POWER 全部参数查询（官方 API）")
    print("=" * 80)

    all_results, param_info_master, all_param_names = query_all_parameters()

    print(f"\n{'='*80}")
    print(f"总不重复参数数: {len(all_param_names)}")

    print_matrix(all_results)

    # 参数字段结构示例
    print(f"\n--- 参数字段结构示例 ---")
    if param_info_master:
        sample_name = list(param_info_master.keys())[0]
        print(f"  参数 '{sample_name}':")
        print(f"  {json.dumps(param_info_master[sample_name], indent=2, ensure_ascii=False)}")

    print_by_type(param_info_master)

    # 保存完整 JSON（输出到脚本同级 ../../output/ 目录）
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.abspath(os.path.join(script_dir, "..", "..", "output"))
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "power_params_all.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({
            "matrix": {comm: {temp: list(all_results[comm][temp].keys()) for temp in TEMPORALS} for comm in COMMUNITIES},
            "param_info": param_info_master,
            "total_unique": len(all_param_names),
        }, f, indent=2, ensure_ascii=False)
    print(f"\n完整结果保存到: {out_file}")

    print(f"\n{'='*80}")
    print("完成!")


if __name__ == "__main__":
    main()
