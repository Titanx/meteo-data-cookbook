"""测试 data.cma.cn 公开 API 连接

凭据一律走环境变量，禁止硬编码：

    $env:CMA_USER = "<注册邮箱>"
    $env:CMA_PWD  = "<密码>"
    python test_cma_api.py

背景：CMA 网站账号与 API 账号是两套独立系统，且账号须先订阅接口服务才能用 CIMISS API。
"""
import os

import requests

USER = os.getenv("CMA_USER", "")
PWD = os.getenv("CMA_PWD", "")

if not USER or not PWD:
    raise SystemExit("缺少凭据：请先设置环境变量 CMA_USER / CMA_PWD（不要写进脚本）")

url = "http://api.data.cma.cn:8090/api"
params = {
    "userId": USER,
    "pwd": PWD,
    "dataFormat": "json",
    "interfaceId": "getSurfEleByTimeRangeAndStaID",
    "dataCode": "SURF_CHN_MUL_HOR_3H",
    "timeRange": "[20260907000000,20260907230000]",
    "staIDs": "54511",
    "elements": "Station_Id_C,Station_Name,Year,Mon,Day,Hour,TEM,PRS,RHU"
}

resp = requests.get(url, params=params, timeout=30)
print(f"状态码: {resp.status_code}")
print(f"响应: {resp.text[:1000]}")
