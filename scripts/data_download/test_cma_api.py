"""
测试 data.cma.cn 公开 API 连接
"""
import requests

USER = "xhlcn@163.com"
PWD = "iyDm!1Y6x"

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