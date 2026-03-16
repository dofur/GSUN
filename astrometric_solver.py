r"""
ASTAP 天文定位求解器模块
通过命令行调用 ASTAP 程序进行图像解析或分析

================================================================================
路径包含空格的说明
================================================================================

【重要】当路径包含空格时（如 F:\astap）：

1. 从 Python 代码调用 astrometric_solver() 函数时：
   - Python 的 subprocess.Popen 会自动正确处理路径中的空格
   - 无需任何额外操作，直接传入路径字符串即可

2. 从命令行直接调用时：
   - 需要用双引号将路径括起来
   - 示例：-a "F:\astap\astap.exe"

================================================================================
调用范例
================================================================================

【范例1】从其他 Python 程序调用（指定坐标搜索）

    import sys
    sys.path.append(r'd:\xingming-program\EAST-PROC\astap-py')
    from astrometric_solver import astrometric_solver
    
    astap_path = r'd:\astap\astap.exe'
    fits_file = r'd:\data\image.fits'
    
    # 有坐标时的小范围搜索
    success, exit_code = astrometric_solver(
        astap_path=astap_path,
        fits_file=fits_file,
        ra=239.5,           # 赤经 (度)
        spd=112.5,          # 太阳距 = 赤纬 + 90°
        search_radius=30,   # 搜索半径 (度)
        fov=0.94,           # 视场 Y 方向 (度)
        update_header=True  # 写入 FITS 头
    )
    
    if success:
        print("解析成功")
    else:
        print(f"解析失败，错误码: {exit_code}")

【范例2】从其他 Python 程序调用（全天盲解）

    import sys
    sys.path.append(r'd:\xingming-program\EAST-PROC\astap-py')
    from astrometric_solver import astrometric_solver
    
    astap_path = r'd:\astap\astap.exe'
    fits_file = r'd:\data\image.fits'
    
    # 无坐标时全天盲解
    success, exit_code = astrometric_solver(
        astap_path=astap_path,
        fits_file=fits_file,
        search_radius=180,  # 180 表示全天搜索
        fov=0.94,           # 视场 Y 方向 (度)
        update_header=True  # 写入 FITS 头
    )
    
    if success:
        print("解析成功")
    else:
        print(f"解析失败，错误码: {exit_code}")

【范例3】批量处理多个 FITS 文件

    import glob
    import sys
    sys.path.append(r'd:\xingming-program\EAST-PROC\astap-py')
    from astrometric_solver import astrometric_solver
    
    astap_path = r'd:\astap\astap.exe'
    fits_pattern = r'd:\data\*.fits'
    
    success_count = 0
    fail_count = 0
    
    for fits_file in glob.glob(fits_pattern):
        print(f"\n处理: {fits_file}")
        success, code = astrometric_solver(
            astap_path=astap_path,
            fits_file=fits_file,
            search_radius=30,
            fov=0.94,
            update_header=True
        )
        
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    print(f"\n完成: 成功 {success_count} 个，失败 {fail_count} 个")

【范例4】循环调用直到成功（带重试）

    import time
    import sys
    sys.path.append(r'd:\xingming-program\EAST-PROC\astap-py')
    from astrometric_solver import astrometric_solver
    
    astap_path = r'd:\astap\astap.exe'
    fits_file = r'd:\data\image.fits'
    max_retries = 3
    
    for attempt in range(max_retries):
        print(f"尝试 {attempt + 1}/{max_retries}")
        
        success, code = astrometric_solver(
            astap_path=astap_path,
            fits_file=fits_file,
            ra=239.5,
            spd=112.5,
            search_radius=30,
            fov=0.94
        )
        
        if success:
            print("解析成功")
            break
        else:
            print(f"错误码: {code}")
            if attempt < max_retries - 1:
                print("等待重试...")
                time.sleep(2)
    else:
        print("重试次数耗尽，解析失败")

【范例5】命令行调用

    # 路径不包含空格时：
    python d:\xingming-program\EAST-PROC\astap-py\astrometric_solver.py ^
        -a d:\astap\astap.exe ^
        -f d:\data\image.fits ^
        -ra 239.5 ^
        -spd 112.5 ^
        -r 30 ^
        -fov 0.94 ^
        -update

    # 路径包含空格时（必须用双引号括起路径）：
    python d:\xingming-program\EAST-PROC\astap-py\astrometric_solver.py ^
        -a "C:\Program Files\astap\astap.exe" ^
        -f "d:\my data\image.fits" ^
        -ra 239.5 ^
        -spd 112.5 ^
        -r 30 ^
        -fov 0.94 ^
        -update

【范例6】从 Python 调用时路径包含空格（无需额外处理）

    import sys
    sys.path.append(r'd:\xingming-program\EAST-PROC\astap-py')
    from astrometric_solver import astrometric_solver
    
    # Python 会自动正确处理路径中的空格
    astap_path = r'C:\Program Files\astap\astap.exe'
    fits_file = r'C:\my data\image.fits'
    
    success, code = astrometric_solver(
        astap_path=astap_path,
        fits_file=fits_file,
        search_radius=30,
        fov=0.94,
        update_header=True
    )

================================================================================
"""

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用

import os
import sys
import subprocess
import ctypes
from typing import Optional, Tuple


# 错误码定义
ERROR_CODES = {
    0: "成功 - No errors",
    1: "无法解析 - No solution",
    2: "检测到的星点不足 - Not enough stars detected",
    16: "读取图像文件错误 - Error reading image file",
    32: "未找到星表数据库 - No star database found",
    33: "读取星表数据库错误 - Error reading star database",
    34: "更新输入文件错误 - Error updating input file"
}


def _set_environment_path(astap_dir: str) -> None:
    """
    将 ASTAP 目录添加到系统 PATH 环境变量
    
    Args:
        astap_dir: ASTAP 程序所在目录
    """
    # 标准化路径格式（统一使用正斜杠，去除末尾分隔符）
    normalized_dir = os.path.normpath(astap_dir).rstrip(os.sep).replace('\\', '/')
    
    current_path = os.environ.get('PATH', '')
    
    # 使用更精确的路径检查
    path_list = current_path.split(os.pathsep)
    normalized_paths = [p.rstrip(os.sep).replace('\\', '/') for p in path_list]
    
    if normalized_dir not in normalized_paths:
        os.environ['PATH'] = astap_dir + os.pathsep + current_path
        print(f"[信息] 已将 ASTAP 目录添加到 PATH: {astap_dir}")
    else:
        print(f"[信息] ASTAP 目录已在 PATH 中: {astap_dir}")


def _print_error_result(exit_code: int, fits_file: str) -> bool:
    """
    打印 ASTAP 运行结果（红色输出）
    
    Args:
        exit_code: ASTAP 程序的退出码
        fits_file: 被解析的 FITS 文件路径
        
    Returns:
        bool: True 表示成功，False 表示失败
    """
    # 设置红色输出
    RED = 0x0004 | 0x0008  # FOREGROUND_RED | FOREGROUND_INTENSITY
    RESET = 0x0007  # FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED
    
    # 获取 stdout 句柄
    stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
    
    if exit_code == 0:
        # 成功 - 绿色输出
        GREEN = 0x0002 | 0x0008  # FOREGROUND_GREEN | FOREGROUND_INTENSITY
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, GREEN)
        print(f"✓ ASTAP 解析成功 ({fits_file}) (错误码: {exit_code})")
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, RESET)
        return True
    else:
        # 失败 - 红色输出
        RED = 0x0004 | 0x0008  # FOREGROUND_RED | FOREGROUND_INTENSITY
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, RED)
        
        error_desc = ERROR_CODES.get(exit_code, f"未知错误 (错误码: {exit_code})")
        print(f"✗ ASTAP 解析失败 ({fits_file}): {error_desc}")
        
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, RESET)
        return False


def astrometric_solver(
    astap_path: str,
    fits_file: str,
    ra: Optional[float] = None,
    spd: Optional[float] = None,
    search_radius: int = 180,
    fov: float = 0.0,
    star_count: int = 500,
    min_star_pixels: float = 1.5,
    use_sip: bool = False,
    generate_wcs: bool = False,
    update_header: bool = False,
    extract_csv: bool = False,
    annotate_png: bool = False
) -> Tuple[bool, int]:
    """
    调用 ASTAP 命令行进行天文定位求解
    
    Args:
        astap_path: ASTAP 可执行文件路径 (如 d:\\astap\\astap.exe)
        fits_file: 要解析的 FITS 文件路径
        ra: 近似赤经 (度)，可选
        spd: 太阳距 (赤纬 + 90°)，可选
        search_radius: 搜索半径 (度)，默认 180，180 表示全天搜索
        fov: 视场 Y 方向角度 (度)，默认 0 (自动)
        star_count: 使用的最多星点数目，默认 500
        min_star_pixels: 最小星点像素数，默认 1.5
        use_sip: 是否加入畸变修正矩阵，默认 False
        generate_wcs: 是否生成标准 WCS 文件，默认 False
        update_header: 是否将解析结果写入 FITS 文件头，默认 False
        extract_csv: 是否生成 CSV 星点信息文件，默认 False
        annotate_png: 是否生成 PNG 标注图，默认 False
        
    Returns:
        tuple[bool, int]: (是否成功, 退出码)
        
    Examples:
        # 有坐标时的小范围搜索
        result, code = astrometric_solver(
            astap_path=r"d:\astap\astap.exe",
            fits_file=r"d:\data\image.fits",
            ra=239.5, spd=112.5,  # 赤经 15h58m, 赤纬 22°30'
            search_radius=30,
            fov=0.94,
            update_header=True
        )
        
        # 无坐标时全天盲解
        result, code = astrometric_solver(
            astap_path=r"d:\astap\astap.exe",
            fits_file=r"d:\data\image.fits",
            search_radius=180,
            fov=0.94
        )
    """
    
    # 1. 验证 ASTAP 可执行文件
    if not os.path.isfile(astap_path):
        RED = 0x0004 | 0x0008
        stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, RED)
        print(f"✗ 错误: 找不到 ASTAP 可执行文件: {astap_path}")
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, 0x0007)
        return False, -1
    
    # 2. 验证 FITS 文件
    if not os.path.isfile(fits_file):
        RED = 0x0004 | 0x0008
        stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, RED)
        print(f"✗ 错误: 找不到 FITS 文件: {fits_file}")
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, 0x0007)
        return False, -1
    
    # 3. 获取 ASTAP 所在目录并添加到 PATH
    astap_dir = os.path.dirname(astap_path)
    _set_environment_path(astap_dir)
    
    # 4. 构建命令行参数
    cmd = [astap_path]
    
    # 必需参数: -f (FITS 文件)
    cmd.extend(["-f", fits_file])
    
    # 可选参数: -ra 和 -spd (坐标)
    if ra is not None:
        cmd.extend(["-ra", str(ra)])
    
    if spd is not None:
        cmd.extend(["-spd", str(spd)])
    
    # 搜索半径: -r (默认 180，只有非默认值时才添加)
    if search_radius != 180:
        cmd.extend(["-r", str(search_radius)])
    
    # 视场: -fov (默认 0，只有非默认值时才添加)
    if fov != 0.0:
        cmd.extend(["-fov", str(fov)])
    
    # 恒星数目: -s (默认 500，通常不需要指定)
    if star_count != 500:
        cmd.extend(["-s", str(star_count)])
    
    # 最小星点像素: -m (默认 1.5，通常不需要指定)
    if min_star_pixels != 1.5:
        cmd.extend(["-m", str(min_star_pixels)])
    
    # 畸变修正矩阵: -sip
    if use_sip:
        cmd.append("-sip")
    
    # 生成 WCS 文件: -wcs
    if generate_wcs:
        cmd.append("-wcs")
    
    # 更新文件头: -update
    if update_header:
        cmd.append("-update")
    
    # 生成 CSV 文件: -extract2
    if extract_csv:
        cmd.append("-extract2")
    
    # 生成 PNG 标注图: -annotate
    if annotate_png:
        cmd.append("-annotate")
    
    # 5. 打印执行命令
    cmd_str = " ".join(cmd)
    print(f"[命令] {cmd_str}")
    
    # 6. 执行命令
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False
        )
        
        stdout, stderr = process.communicate()
        
        # 打印输出
        print(stdout)
        if stderr:
            print(stderr, file=sys.stderr)
        
        # 7. 处理结果
        exit_code = process.returncode
        
        # 打印结果（红色/绿色）
        success = _print_error_result(exit_code, fits_file)
        
        # 打印退出码
        GREEN = 0x0002 | 0x0008
        RED = 0x0004 | 0x0008
        stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)
        
        if success:
            ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, GREEN)
            print(f"[完成] 退出码: {exit_code}")
        else:
            ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, RED)
            print(f"[失败] 退出码: {exit_code}")
        
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, 0x0007)
        
        # 8. 删除同一目录下的 .ini 和 .wcs 文件
        fits_dir = os.path.dirname(fits_file)
        fits_basename = os.path.splitext(os.path.basename(fits_file))[0]
        
        # 删除 .ini 文件
        ini_file = os.path.join(fits_dir, fits_basename + ".ini")
        if os.path.isfile(ini_file):
            try:
                os.remove(ini_file)
                print(f"[清理] 已删除: {ini_file}")
            except Exception as e:
                print(f"[警告] 删除 .ini 文件失败: {e}")
        
        # 删除 .wcs 文件
        wcs_file = os.path.join(fits_dir, fits_basename + ".wcs")
        if os.path.isfile(wcs_file):
            try:
                os.remove(wcs_file)
                print(f"[清理] 已删除: {wcs_file}")
            except Exception as e:
                print(f"[警告] 删除 .wcs 文件失败: {e}")
        
        return success, exit_code
        
    except Exception as e:
        RED = 0x0004 | 0x0008
        stdout_handle = ctypes.windll.kernel32.GetStdHandle(-11)
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, RED)
        print(f"✗ 执行 ASTAP 时出错: {e}")
        ctypes.windll.kernel32.SetConsoleTextAttribute(stdout_handle, 0x0007)
        return False, -1


def main():
    """
    主函数示例 - 通过命令行参数调用 astrometric_solver
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description="ASTAP 天文定位求解器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 有坐标的小范围搜索
  %(prog)s -a d:\\astap\\astap.exe -f d:\\data\\image.fits -ra 239.5 -spd 112.5 -r 30 -fov 0.94 -update
  
  # 无坐标的盲解 (r=180 表示全天搜索)
  %(prog)s -a d:\\astap\\astap.exe -f d:\\data\\image.fits -r 180 -fov 0.94 -update -wcs
        """
    )
    
    # 必需参数
    parser.add_argument("-a", "--astap", required=True, help="ASTAP 可执行文件路径")
    parser.add_argument("-f", "--fits", required=True, help="要解析的 FITS 文件路径")
    
    # 可选参数 - 坐标
    parser.add_argument("-ra", "--ra", type=float, help="近似赤经 (度)")
    parser.add_argument("-spd", "--spd", type=float, help="太阳距 (赤纬 + 90°)")
    
    # 可选参数 - 搜索参数
    parser.add_argument("-r", "--radius", type=int, default=180, help="搜索半径 (度), 默认 180")
    parser.add_argument("-fov", "--fov", type=float, default=0.0, help="视场 Y 方向 (度), 默认 0")
    parser.add_argument("-s", "--stars", type=int, default=500, help="最大星点数目, 默认 500")
    parser.add_argument("-m", "--minpix", type=float, default=1.5, help="最小星点像素, 默认 1.5")
    
    # 布尔选项
    parser.add_argument("-sip", "--sip", action="store_true", help="启用畸变修正矩阵")
    parser.add_argument("-wcs", "--wcs", action="store_true", help="生成标准 WCS 文件")
    parser.add_argument("-update", "--update", action="store_true", help="更新 FITS 文件头")
    parser.add_argument("-extract2", "--extract2", action="store_true", help="生成 CSV 星点文件")
    parser.add_argument("-annotate", "--annotate", action="store_true", help="生成 PNG 标注图")
    
    args = parser.parse_args()
    
    # 调用求解器
    success, exit_code = astrometric_solver(
        astap_path=args.astap,
        fits_file=args.fits,
        ra=args.ra,
        spd=args.spd,
        search_radius=args.radius,
        fov=args.fov,
        star_count=args.stars,
        min_star_pixels=args.minpix,
        use_sip=args.sip,
        generate_wcs=args.wcs,
        update_header=args.update,
        extract_csv=args.extract2,
        annotate_png=args.annotate
    )
    
    # 返回适当的退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()





