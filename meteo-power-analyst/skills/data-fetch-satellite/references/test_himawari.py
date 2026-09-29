"""
葵花 8/9 (Himawari-8/9) 卫星数据下载测试脚本

数据来源：JAXA P-Tree System (https://www.eorc.jaxa.jp/ptree/)
访问方式：FTP（需要注册账号）
注册地址：https://www.eorc.jaxa.jp/ptree/registration_top.html

数据特点：
- Himawari-8: 2015年7月投入业务，10分钟间隔
- Himawari-9: 2016年11月发射，2017年3月开始备份运行
- 2024年12月起 Himawari-9 接替 Himawari-8 成为主星
- 覆盖范围：东亚-澳洲区域（80°E-160°W, 60°N-60°S）
- 数据产品：全圆盘(Full Disk)、日本区域(Japan)、目标区域(Target)
- 数据格式：HSD（Himawari Standard Data，二进制）, NetCDF, Beta.gz

获取流程：
1. 在 JAXA P-Tree 网站注册账号
2. 邮件收到 FTP 账号密码
3. 使用 FTP 客户端或 Python ftplib 下载

测试记录：
- 2026-07-18 测试 FTP 连接成功（220 JAXA/EORC FTP Server）
- 匿名登录被拒绝（预期行为），需要注册账号
"""

import os
import ftplib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional


# FTP 连接信息（需要注册后填写）
FTP_HOST = "ftp.ptree.jaxa.jp"
FTP_USER = os.environ.get("HIMAWARI_FTP_USER", "")  # 从环境变量读取
FTP_PASS = os.environ.get("HIMAWARI_FTP_PASS", "")

# 数据产品路径模板
# /jma/hsd/YYYYMM/DD/HH/HS_H09_YYYYMMDD_HHMM_BXX_FLDK_R20_S1010.DAT.bz2
# 说明：
#   H09 = Himawari-9 (H08 = Himawari-8)
#   BXX = 波段编号 (B01-B16)
#   FLDK = Full Disk (全圆盘)
#   R20 = 分辨率 (R20=20bit, 0.5~1km; R15=15bit)
#   S1010 = 1010 像素规格

DATA_PRODUCTS = {
    "full_disk_vis": "/jma/hsd/{ymd}/{dd}/{hh}/HS_H09_{ymd}_{hhmm}_B01_FLDK_R20_S1010.DAT.bz2",
    "full_disk_ir": "/jma/hsd/{ymd}/{dd}/{hh}/HS_H09_{ymd}_{hhmm}_B13_FLDK_R20_S1010.DAT.bz2",
    "japan_vis": "/jma/hsd/{ymd}/{dd}/{hh}/HS_H09_{ymd}_{hhmm}_B01_JPN_R20_S0410.DAT.bz2",
}


def test_ftp_connection():
    """测试 FTP 连接（无账号时会返回认证失败，验证主机可达）"""
    print("=" * 60)
    print("测试 1: JAXA P-Tree FTP 连接")
    print("=" * 60)

    print(f"  FTP 主机: {FTP_HOST}")
    print(f"  用户名: {FTP_USER or '(未设置，将匿名尝试)'}")

    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=15)
        print(f"  ✅ TCP 连接成功，FTP 服务器响应: {ftp.welcome[:80]}")

        # 尝试登录
        try:
            if FTP_USER:
                ftp.login(FTP_USER, FTP_PASS)
                print(f"  ✅ 登录成功")
                # 列出根目录
                files = []
                ftp.cwd("/jma/hsd")
                ftp.dir(files.append)
                print(f"  📁 /jma/hsd 下子目录数: {len(files)}")
                if files:
                    print(f"  示例: {files[0][:80]}")
                ftp.quit()
                return True
            else:
                # 匿名登录（会失败，但能验证服务器可达）
                try:
                    ftp.login("anonymous", "test@test.com")
                    print(f"  ✅ 匿名登录成功（意外）")
                    ftp.quit()
                    return True
                except ftplib.error_perm as e:
                    print(f"  ⚠️ 匿名登录被拒绝（预期行为）: {e}")
                    print(f"  💡 服务器可达，需要注册有效账号才能下载")
                    return False
        except ftplib.error_perm as e:
            print(f"  ❌ 认证失败: {e}")
            print(f"  💡 请检查 FTP 账号密码，或前往注册：")
            print(f"     https://www.eorc.jaxa.jp/ptree/registration_top.html")
            return False
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        print(f"  💡 可能原因：网络不通、DNS 解析失败、防火墙拦截")
        return False


def list_available_products(target_time: datetime):
    """列出指定时间可用的产品（需要登录）"""
    print("\n" + "=" * 60)
    print(f"测试 2: 列出 {target_time:%Y-%m-%d %H:%M} UTC 的可用产品")
    print("=" * 60)

    if not FTP_USER:
        print("  ⚠️ 未设置 FTP 账号，跳过此测试")
        print("  💡 设置环境变量后可运行：")
        print("     $env:HIMAWARI_FTP_USER='your_account'")
        print("     $env:HIMAWARI_FTP_PASS='your_password'")
        return False

    ymd = target_time.strftime("%Y%m%d")
    dd = target_time.strftime("%d")
    hh = target_time.strftime("%H")
    hhmm = target_time.strftime("%H%M")

    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=30)
        ftp.login(FTP_USER, FTP_PASS)

        # 切换到对应目录
        remote_dir = f"/jma/hsd/{ymd}/{dd}/{hh}"
        ftp.cwd(remote_dir)
        print(f"  📁 当前目录: {remote_dir}")

        # 列出文件
        files = []
        ftp.dir(files.append)
        print(f"  📄 找到 {len(files)} 个文件")

        # 过滤 Himawari-9 全圆盘可见光文件
        h09_files = [f for f in files if "HS_H09" in f and "B01_FLDK" in f]
        print(f"  🌟 Himawari-9 B01 FLDK 文件: {len(h09_files)} 个")
        if h09_files:
            print(f"  示例:")
            for f in h09_files[:3]:
                print(f"    {f}")

        ftp.quit()
        return True
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return False


def download_product(target_time: datetime, product_type: str = "full_disk_vis",
                     output_dir: str = "c:/work/meteo/data/himawari"):
    """下载指定产品"""
    print("\n" + "=" * 60)
    print(f"测试 3: 下载 {product_type} ({target_time:%Y-%m-%d %H:%M} UTC)")
    print("=" * 60)

    if not FTP_USER:
        print("  ⚠️ 未设置 FTP 账号，无法下载")
        return False

    ymd = target_time.strftime("%Y%m%d")
    dd = target_time.strftime("%d")
    hh = target_time.strftime("%H")
    hhmm = target_time.strftime("%H%M")

    remote_path = DATA_PRODUCTS[product_type].format(ymd=ymd, dd=dd, hh=hh, hhmm=hhmm)
    filename = Path(remote_path).name
    local_path = Path(output_dir) / filename
    local_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        ftp = ftplib.FTP(FTP_HOST, timeout=60)
        ftp.login(FTP_USER, FTP_PASS)

        # 获取文件大小
        size = ftp.size(remote_path)
        print(f"  📦 远程文件: {remote_path}")
        print(f"  📏 文件大小: {size / 1024 / 1024:.1f} MB")

        # 下载
        print(f"  ⬇️  开始下载...")
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {remote_path}", f.write, blocksize=1024 * 1024)

        actual_size = local_path.stat().st_size
        print(f"  ✅ 下载完成: {local_path}")
        print(f"  📏 本地大小: {actual_size / 1024 / 1024:.1f} MB")

        ftp.quit()
        return True
    except Exception as e:
        print(f"  ❌ 下载失败: {e}")
        return False


def print_registration_guide():
    """打印注册指南"""
    print("\n" + "=" * 60)
    print("葵花数据注册指南")
    print("=" * 60)
    print("""
📋 获取葵花 8/9 数据的步骤：

1. 访问 JAXA P-Tree 注册页面：
   https://www.eorc.jaxa.jp/ptree/registration_top.html

2. 填写注册信息：
   - 姓名、机构、邮箱
   - 用途说明（科研/业务）
   - 同意使用条款

3. 等待邮件（通常 1-3 个工作日）：
   - 邮件中包含 FTP 账号和密码
   - FTP 主机: ftp.ptree.jaxa.jp

4. 设置环境变量：
   PowerShell:
     $env:HIMAWARI_FTP_USER='your_account'
     $env:HIMAWARI_FTP_PASS='your_password'

   或写入系统环境变量永久保存。

5. 重新运行本脚本进行下载。

📌 数据产品说明：
   - H08 = Himawari-8（2015-2024 主星，现已转为备份）
   - H09 = Himawari-9（2024年12月起为主星）
   - B01-B16 = 16个波段（B01可见光蓝, B02绿, B03红, B04近红外, B13红外11μm）
   - FLDK = Full Disk 全圆盘（每10分钟）
   - JPN = Japan 区域（每2.5分钟）
   - R20 = 20bit 数据

📁 目录结构：
   /jma/hsd/YYYYMM/DD/HH/HS_H09_YYYYMMDD_HHMM_BXX_FLDK_R20_S1010.DAT.bz2
   - 文件为 bz2 压缩的 HSD 二进制格式
   - 解压后需要用专门的 HSD 读取库（如 satpy、pyresample）
""")


if __name__ == "__main__":
    print(f"葵花 8/9 卫星数据下载测试")
    print(f"测试时间: {datetime.utcnow():%Y-%m-%d %H:%M:%S} UTC\n")

    # 测试 FTP 连接
    r1 = test_ftp_connection()

    # 测试列出产品（需要账号）
    target = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    r2 = list_available_products(target)

    # 打印注册指南
    print_registration_guide()

    print("\n" + "=" * 60)
    print("测试汇总")
    print("=" * 60)
    print(f"  FTP 连接: {'✅ 成功' if r1 else '⚠️ 需要注册账号'}")
    print(f"  产品列表: {'✅ 成功' if r2 else '⚠️ 需要注册账号'}")
    print(f"\n💡 完整下载流程需要注册 JAXA P-Tree 账号")
