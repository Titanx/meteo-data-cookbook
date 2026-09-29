"""
FY-4A LMI 闪电数据 FTP 批量下载

使用方法：
1. 在 NSMC 网站 (https://satellite.nsmc.org.cn/DataPortal/) 登录
2. 搜索选择需要的 LMI 文件，提交订单
3. 订单处理完成后，获取 FTP 地址、用户名、密码
4. 把文件列表保存为一个文本文件，每行一个文件名
5. 运行本脚本，自动批量下载

Example:
    python scripts/data_download/download_fy4_lmi_ftp.py \
      --ftp ftp.nsmc.org.cn \
      --user your_username \
      --pass your_password \
      --file-list ./fy4_file_list.txt \
      --output ./data/fy4/lmi
"""
import ftplib
import argparse
import os
from pathlib import Path

def download_files(ftp_host, username, password, file_list_path, output_dir):
    """批量下载文件"""
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 读取文件列表
    with open(file_list_path, 'r', encoding='utf-8') as f:
        files = [line.strip() for line in f if line.strip()]
    
    print(f"=== 开始批量下载 ===")
    print(f"FTP: {ftp_host}")
    print(f"文件数: {len(files)}")
    print(f"输出目录: {output_dir}")
    print()
    
    # 连接 FTP
    try:
        ftp = ftplib.FTP(ftp_host)
        ftp.login(username, password)
        print(f"✓ 登录成功")
        print(f"  当前目录: {ftp.pwd()}")
        print()
    except Exception as e:
        print(f"✗ 登录失败: {e}")
        return []
    
    downloaded = []
    failed = []
    
    for i, filename in enumerate(files):
        # 处理相对路径
        basename = os.path.basename(filename)
        local_path = output_dir / basename
        
        if local_path.exists():
            print(f"[{i+1}/{len(files)}] 跳过，已存在: {basename}")
            downloaded.append(str(local_path))
            continue
        
        print(f"[{i+1}/{len(files)}] 下载: {filename}")
        try:
            with open(local_path, 'wb') as f:
                ftp.retrbinary(f'RETR {filename}', f.write)
            
            size_kb = local_path.stat().st_size / 1024
            print(f"  ✓ 完成: {basename} ({size_kb:.1f} KB)")
            downloaded.append(str(local_path))
        except Exception as e:
            print(f"  ✗ 失败: {e}")
            failed.append(filename)
            if local_path.exists():
                local_path.unlink()
    
    print()
    print("=== 下载完成 ===")
    print(f"成功: {len(downloaded)} 个")
    print(f"失败: {len(failed)} 个")
    if failed:
        print("失败文件:")
        for f in failed:
            print(f"  {f}")
    
    ftp.quit()
    return downloaded

def main():
    parser = argparse.ArgumentParser(
        description='FY-4A LMI 闪电数据 FTP 批量下载（NSMC 订单方式）'
    )
    parser.add_argument('--ftp', '-f', default='ftp.nsmc.org.cn',
                      help='FTP 主机地址')
    parser.add_argument('--user', '-u', required=True,
                      help='FTP 用户名')
    parser.add_argument('--pass', '-p', dest='password', required=True,
                      help='FTP 密码')
    parser.add_argument('--file-list', '-l', required=True,
                      help='文件列表文本文件，每行一个文件名')
    parser.add_argument('--output', '-o',
                      default=r'c:\work\meteo\data\fy4\lmi',
                      help='输出目录')
    args = parser.parse_args()
    
    download_files(args.ftp, args.user, args.password, args.file_list, args.output)

if __name__ == "__main__":
    main()
