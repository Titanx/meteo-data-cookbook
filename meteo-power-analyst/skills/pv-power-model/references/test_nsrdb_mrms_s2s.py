"""三数据源可达性探测: NSRDB (nrel-pds-nsrdb) / MRMS (noaa-mrms-pds) / S2S (ECDS)"""
import requests

TIMEOUT = 30
results = {}

def probe(name, url, **kw):
    try:
        r = requests.get(url, timeout=TIMEOUT, **kw)
        results[name] = (r.status_code, len(r.content))
        print(f"[{r.status_code}] {name}  bytes={len(r.content)}")
        return r
    except Exception as e:
        results[name] = ("ERR", str(e)[:120])
        print(f"[ERR] {name}  {str(e)[:120]}")
        return None

S3 = "https://{}.s3.amazonaws.com/?list-type=2&prefix={}&delimiter=/"

print("=== 1. NSRDB (nrel-pds-nsrdb, AWS S3 匿名) ===")
r = probe("nsrdb_top", S3.format("nrel-pds-nsrdb", ""))
if r is not None and r.status_code == 200:
    import re
    keys = re.findall(r"<Prefix>(.*?)</Prefix>", r.text)
    print("  top-level dirs:", [k for k in keys if k][:25])

print()
print("=== 2. MRMS (noaa-mrms-pds, AWS S3 匿名) ===")
r = probe("mrms_conus", S3.format("noaa-mrms-pds", "CONUS/"))
if r is not None and r.status_code == 200:
    import re
    keys = re.findall(r"<Prefix>(.*?)</Prefix>", r.text)
    qpe = [k for k in keys if "QPE" in k]
    print(f"  CONUS 产品目录共 {len(keys)} 个, QPE 相关:", qpe[:15])

print()
print("=== 3. MRMS 官网直连 (mrms.ncep.noaa.gov) ===")
probe("mrms_web_2d", "https://mrms.ncep.noaa.gov/2D/")

print()
print("=== 4. S2S @ ECDS (需注册, 测门户可达性) ===")
probe("ecds_s2s", "https://ecds.ecmwf.int/datasets/s2s-forecasts?tab=overview")
probe("ecds_api", "https://ecds.ecmwf.int/api/catalog/v1/collections")
