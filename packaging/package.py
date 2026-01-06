#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
from pathlib import Path


def install_pyinstaller():
    """安装PyInstaller"""
    print("正在检查PyInstaller是否已安装...")
    try:
        # 检查PyInstaller是否已安装
        subprocess.run(["pyinstaller", "--version"], 
                      check=True, capture_output=True, text=True)
        print("PyInstaller已安装")
    except subprocess.CalledProcessError:
        print("PyInstaller未安装，正在安装...")
        try:
            subprocess.run(["pip", "install", "pyinstaller"], 
                          check=True, capture_output=True, text=True)
            print("PyInstaller安装成功")
        except subprocess.CalledProcessError as e:
            print(f"PyInstaller安装失败: {e}")
            sys.exit(1)


def get_python_scripts():
    """获取父目录下所有Python脚本"""
    # 父目录路径
    parent_dir = os.path.abspath(os.path.join(".", ".."))
    scripts = []
    for file in os.listdir(parent_dir):
        if file.endswith(".py") and file != "package.py":
            scripts.append(os.path.join(parent_dir, file))
    return sorted(scripts)


def package_script(script_path):
    """使用PyInstaller打包单个脚本"""
    print(f"\n正在打包脚本: {script_path}")
    
    # 构建PyInstaller命令
    cmd = [
        "pyinstaller",
        "--onefile",  # 生成单个可执行文件
        "--name", Path(script_path).stem,  # 使用脚本名作为可执行文件名
        "--clean",  # 清理临时文件
        "--distpath", "./dist",  # 指定输出目录
        "--workpath", "./build",  # 指定工作目录
        script_path
    ]
    
    try:
        # 执行打包命令
        subprocess.run(cmd, check=True, text=True)
        print(f"✓ 成功打包: {script_path} -> dist/{Path(script_path).stem}.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ 打包失败: {script_path}")
        print(f"错误信息: {e}")
        return False


def main():
    """主函数"""
    # 创建解析器
    parser = argparse.ArgumentParser(
        description="打包Python脚本为可执行文件",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 添加脚本参数，支持多个脚本或'all'关键字
    parser.add_argument(
        "scripts",
        nargs="*",  # 支持多个参数
        default=["split_time.py"],  # 默认打包split_time.py
        help="要打包的脚本名，支持多个脚本，或使用'all'打包所有脚本\n"
             "默认: split_time.py\n"
             "示例: python package.py speaker2.py\n"
             "示例: python package.py all"
    )
    
    # 解析参数
    args = parser.parse_args()
    
    # 确保dist目录存在
    os.makedirs("./dist", exist_ok=True)
    
    # 安装PyInstaller
    install_pyinstaller()
    
    # 获取父目录路径
    parent_dir = os.path.abspath(os.path.join(".", ".."))
    
    # 获取要打包的脚本列表
    scripts_to_package = []
    
    if args.scripts == ["all"]:
        # 打包所有Python脚本
        scripts_to_package = get_python_scripts()
        print(f"\n将打包所有脚本: {[os.path.basename(script) for script in scripts_to_package]}")
    else:
        # 打包指定的脚本
        for script in args.scripts:
            # 如果是相对路径，转换为绝对路径（相对于父目录）
            if not os.path.isabs(script):
                script = os.path.join(parent_dir, script)
            scripts_to_package.append(script)
    
    # 验证脚本存在
    valid_scripts = []
    for script in scripts_to_package:
        if os.path.exists(script):
            valid_scripts.append(script)
        else:
            print(f"警告: 脚本 {script} 不存在，将跳过")
    
    if not valid_scripts:
        print("错误: 没有要打包的有效脚本")
        sys.exit(1)
    
    # 执行打包
    success_count = 0
    fail_count = 0
    
    for script in valid_scripts:
        if package_script(script):
            success_count += 1
        else:
            fail_count += 1
    
    # 打印结果摘要
    print(f"\n{'='*50}")
    print(f"打包完成: 成功 {success_count}, 失败 {fail_count}")
    print(f"可执行文件位于: {os.path.abspath('./dist')}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()