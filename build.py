#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path


def build_app():
    """构建应用程序"""
    print("开始构建iOS签名工具...")
    
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 创建构建目录
    build_dir = os.path.join(current_dir, "build")
    dist_dir = os.path.join(current_dir, "dist")
    
    # 清理旧的构建文件
    try:
        if os.path.exists(build_dir):
            shutil.rmtree(build_dir)
        if os.path.exists(dist_dir):
            shutil.rmtree(dist_dir)
    except PermissionError as e:
        print(f"警告: 无法删除旧的构建文件，可能是因为应用程序正在运行: {e}")
        print("请关闭所有正在运行的应用程序实例后重试，或者手动删除dist和build目录")
        return False
    except Exception as e:
        print(f"警告: 清理旧的构建文件时出错: {e}")
    
    # 构建PyInstaller命令
    cmd = [
        "pyinstaller",
        "--name=iOS签名工具",
        "--windowed",
        # "--icon=resources/icon.ico",  # 暂时移除图标
        "--add-data=resources;resources",
        "--add-data=tools;tools",
        "run.py"
    ]
    
    # 在Linux/macOS上使用不同的路径分隔符
    if platform.system() != "Windows":
        cmd[4] = "--add-data=resources:resources"
        cmd[5] = "--add-data=tools:tools"
    
    # 执行PyInstaller命令
    try:
        subprocess.run(cmd, check=True)
        print("应用程序构建成功!")
        
        # 显示输出目录
        print(f"可执行文件位于: {os.path.join(dist_dir, 'iOS签名工具')}")
        
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {str(e)}")
        return False
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return False
    
    return True


if __name__ == "__main__":
    build_app() 