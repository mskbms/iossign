#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试优化效果
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.macho_dylib_injection import list_dylibs

def test_macho_analysis():
    """测试MachO分析"""
    print("🔬 测试MachO分析功能...")
    
    # 查找测试应用（优先读取环境变量，避免硬编码本机路径）
    test_paths = []
    env_test_app = os.environ.get("IOSSIGN_TEST_APP_PATH")
    if env_test_app:
        test_paths.append(env_test_app)
    
    for app_path in test_paths:
        if os.path.exists(app_path):
            print(f"\n📱 分析应用: {app_path}")
            
            # 查找主二进制文件
            app_name = os.path.basename(app_path).replace('.app', '')
            binary_path = os.path.join(app_path, app_name)
            
            if not os.path.exists(binary_path):
                # 尝试查找其他二进制文件
                for item in os.listdir(app_path):
                    item_path = os.path.join(app_path, item)
                    if os.path.isfile(item_path) and os.path.getsize(item_path) > 50000:
                        binary_path = item_path
                        break
            
            if os.path.exists(binary_path):
                print(f"📋 主二进制文件: {binary_path}")
                
                # 分析动态库
                dylibs = list_dylibs(binary_path)
                print(f"🔗 动态库数量: {len(dylibs)}")
                
                # 显示Framework相关的动态库
                framework_dylibs = [d for d in dylibs if "@executable_path/Frameworks/" in d]
                print(f"🎯 Framework动态库数量: {len(framework_dylibs)}")
                
                if framework_dylibs:
                    print("Framework动态库列表:")
                    for i, dylib in enumerate(framework_dylibs, 1):
                        print(f"  {i}. {dylib}")
                else:
                    print("❌ 没有发现Framework动态库")
                
                # 显示前5个动态库
                print(f"\n📚 前5个动态库:")
                for i, dylib in enumerate(dylibs[:5], 1):
                    print(f"  {i}. {dylib}")
                
                if len(dylibs) > 5:
                    print(f"  ... 还有 {len(dylibs) - 5} 个")
            else:
                print(f"❌ 找不到主二进制文件")
            break
    else:
        print("❌ 没有找到测试应用")

def test_7z_tool():
    """测试内置7z工具"""
    print("\n🗂️ 测试内置7z工具...")
    
    tools_dir = os.path.join(project_root, "tools", "7Z")
    seven_zip_path = os.path.join(tools_dir, "7Z.exe")
    
    if os.path.exists(seven_zip_path):
        print(f"✅ 内置7z工具存在: {seven_zip_path}")
        
        # 检查文件大小
        size = os.path.getsize(seven_zip_path)
        print(f"📦 文件大小: {size / 1024:.1f} KB")
        
        # 检查DLL文件
        dll_path = os.path.join(tools_dir, "7z.dll")
        if os.path.exists(dll_path):
            dll_size = os.path.getsize(dll_path)
            print(f"📦 DLL文件大小: {dll_size / 1024 / 1024:.1f} MB")
        else:
            print("❌ 7z.dll文件不存在")
    else:
        print(f"❌ 内置7z工具不存在: {seven_zip_path}")

def main():
    """主函数"""
    print("🧪 iOS签名工具优化测试")
    print("=" * 50)
    
    # 设置日志级别
    logging.basicConfig(level=logging.INFO)
    
    # 测试项目
    test_7z_tool()
    test_macho_analysis()
    
    print("\n✅ 测试完成!")
    print("\n💡 测试要点:")
    print("1. 检查内置7z工具是否正常")
    print("2. 验证MachO动态库分析功能")
    print("3. 确认Framework注入检测")

if __name__ == "__main__":
    main() 