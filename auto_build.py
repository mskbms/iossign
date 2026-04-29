#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
自动编译打包脚本
"""

import os
import sys
import shutil
import subprocess
import platform
import time
import zipfile
from datetime import datetime

def print_step(message):
    """打印步骤信息"""
    print("\n" + "=" * 50)
    print(f">>> {message}")
    print("=" * 50)

def clean_build():
    """清理旧的构建文件"""
    print_step("清理旧的构建文件")
    
    # 尝试终止可能正在运行的应用实例
    if platform.system() == "Windows":
        try:
            subprocess.run(["taskkill", "/F", "/IM", "iOS签名工具.exe"], 
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("已终止正在运行的应用实例")
            # 等待进程完全退出
            time.sleep(2)
        except Exception as e:
            print(f"尝试终止应用实例时出错: {e}")
    
    # 删除构建目录
    dirs_to_remove = ['build', 'dist']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"已删除 {dir_name} 目录")
            except Exception as e:
                print(f"删除 {dir_name} 目录失败: {e}")
                return False
    
    # 删除spec文件
    spec_file = "iOS签名工具.spec"
    if os.path.exists(spec_file):
        try:
            os.remove(spec_file)
            print(f"已删除 {spec_file} 文件")
        except Exception as e:
            print(f"删除 {spec_file} 文件失败: {e}")
    
    return True

def build_app():
    """构建应用程序"""
    print_step("开始构建应用程序")
    
    # 运行构建脚本
    try:
        result = subprocess.run(["python", "build.py"], capture_output=True, text=True)
        if result.returncode == 0:
            print("构建成功!")
            print(result.stdout.strip())
            return True
        else:
            print("构建失败!")
            print(result.stderr.strip())
            return False
    except Exception as e:
        print(f"构建过程出错: {e}")
        return False

def create_package():
    """创建发布包"""
    print_step("创建发布包")
    
    # 检查dist目录是否存在
    if not os.path.exists("dist"):
        print("错误: dist目录不存在，构建可能失败")
        return False
    
    # 创建发布目录
    release_dir = "release"
    if not os.path.exists(release_dir):
        os.makedirs(release_dir)
    
    # 生成发布包名称
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    release_name = f"iOS签名工具_v1.0_{timestamp}"
    release_path = os.path.join(release_dir, release_name)
    
    # 创建发布目录
    if not os.path.exists(release_path):
        os.makedirs(release_path)
    
    # 复制可执行文件和必要的文件
    try:
        # 复制可执行文件
        shutil.copytree("dist", os.path.join(release_path, "app"))
        print("已复制应用程序文件")
        
        # 复制tools目录
        if os.path.exists("tools"):
            shutil.copytree("tools", os.path.join(release_path, "tools"))
            print("已复制tools目录")
        
        # 创建apps目录
        os.makedirs(os.path.join(release_path, "apps"), exist_ok=True)
        print("已创建apps目录")
        
        # 创建README.txt
        with open(os.path.join(release_path, "README.txt"), "w", encoding="utf-8") as f:
            f.write("iOS签名工具使用说明\n")
            f.write("=================\n\n")
            f.write("1. 运行 app/iOS签名工具.exe 启动应用程序\n")
            f.write("2. 签名后的IPA文件将保存在apps目录中\n")
            f.write("3. 请确保tools目录中包含zsign.exe工具\n")
        print("已创建README.txt文件")
        
        # 创建ZIP包
        zip_file = os.path.join(release_dir, f"{release_name}.zip")
        with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(release_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, release_path)
                    zipf.write(file_path, arcname)
        
        print(f"已创建发布包: {zip_file}")
        return True
    except Exception as e:
        print(f"创建发布包失败: {e}")
        return False

def main():
    """主函数"""
    print_step("自动编译打包脚本")
    
    # 清理旧的构建文件
    if not clean_build():
        print("清理失败，终止构建")
        return 1
    
    # 构建应用程序
    if not build_app():
        print("构建失败，终止打包")
        return 1
    
    # 创建发布包
    if not create_package():
        print("打包失败")
        return 1
    
    print_step("编译打包完成!")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 