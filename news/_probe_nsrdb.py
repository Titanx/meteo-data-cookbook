"""NSRDB S3 部分读取实测 (h5coro): 找辐照主文件 + ERCOT 点位 GHI 读取"""
import re
import requests

print("=== 1. GOES/conus/v3.2.2/ 文件组清单 (unique 产品名) ===")
names = set()
token = ""
while True:
    url = f"https://nrel-pds-nsrdb.s3.amazonaws.com/?list-type=2&prefix=GOES/conus/v3.2.2/"
    if token:
        url += f"&continuation-token={token}"
    r = requests.get(url, timeout=30)
    names.update(re.findall(r"<Key>GOES/conus/v3\.2\.2/(.+?)</Key>", r.text))
    tk = re.search(r"<NextContinuationToken>(.*?)</NextContinuationToken>", r.text)
    if not tk:
        break
    token = tk.group(1)
prods = sorted({re.sub(r"_\d{4}\.h5$", "", n) for n in names if n.endswith(".h5")})
print(f"  总文件 {len(names)} 个, 产品组: {prods}")
