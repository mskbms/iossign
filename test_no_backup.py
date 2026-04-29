#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试不创建备份文件的功能
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.macho_dylib_injection import inject_dylib_to_macho, list_dylibs

def test_no_backup():
    """测试不创建备份文件的注入"""
    print("🧪 测试不创建备份文件的注入功能...")
    
    # 查找测试应用（优先读取环境变量，避免硬编码本机路径）
    test_paths = []
    env_test_app = os.environ.get("IOSSIGN_TEST_APP_PATH")
    if env_test_app:
        test_paths.append(env_test_app)
    
    for app_path in test_paths:
        if os.path.exists(app_path):
            print(f"\n📱 测试应用: {app_path}")
            
            # 查找主二进制文件
            app_name = os.path.basename(app_path).replace('.app', '')
            binary_path = os.path.join(app_path, app_name)
            
            if not os.path.exists(binary_path):
                print(f"❌ 主二进制文件不存在: {binary_path}")
                continue
            
            # 创建临时副本进行测试
            temp_dir = tempfile.mkdtemp(prefix="test_no_backup_")
            temp_binary = os.path.join(temp_dir, "test_binary")
            shutil.copy2(binary_path, temp_binary)
            
            print(f"📋 临时测试文件: {temp_binary}")
            
            # 注入前的动态库数量
            before_dylibs = list_dylibs(temp_binary)
            print(f"🔗 注入前动态库数量: {len(before_dylibs)}")
            
            # 测试注入（不创建备份）
            test_dylib = "@executable_path/Frameworks/TestLibrary.dylib"
            print(f"\n🚀 开始注入测试库: {test_dylib}")
            print("⚡ 使用无备份模式（性能优化）")
            
            # 检查是否有备份文件
            backup_path = temp_binary + ".backup_dylib"
            backup_exists_before = os.path.exists(backup_path)
            
            # 执行注入（不创建备份）
            success = inject_dylib_to_macho(temp_binary, test_dylib, weak=False, create_backup=False)
            
            # 检查是否创建了备份文件
            backup_exists_after = os.path.exists(backup_path)
            
            if success:
                print("✅ 注入成功!")
                
                # 验证注入结果
                after_dylibs = list_dylibs(temp_binary)
                print(f"🔗 注入后动态库数量: {len(after_dylibs)}")
                
                if test_dylib in after_dylibs:
                    print(f"✅ 验证成功: 找到注入的动态库 {test_dylib}")
                else:
                    print(f"❌ 验证失败: 未找到注入的动态库")
                
                # 检查备份文件状态
                if not backup_exists_before and not backup_exists_after:
                    print("✅ 性能优化成功: 没有创建备份文件")
                elif backup_exists_after:
                    print("❌ 意外创建了备份文件")
                    
            else:
                print("❌ 注入失败!")
            
            # 清理临时文件
            try:
                shutil.rmtree(temp_dir)
                print(f"🧹 清理临时目录: {temp_dir}")
            except Exception as e:
                print(f"⚠️ 清理临时目录失败: {e}")
            
            break
    else:
        print("❌ 没有找到测试应用")

def test_with_backup():
    """测试创建备份文件的注入（对比）"""
    print("\n🧪 测试创建备份文件的注入功能（对比）...")
    
    # 创建临时测试文件
    temp_dir = tempfile.mkdtemp(prefix="test_with_backup_")
    
    # 创建一个简单的测试文件
    test_file = os.path.join(temp_dir, "test_file")
    with open(test_file, 'wb') as f:
        # 写入一个简单的MachO头部（64位）
        f.write(b'\xcf\xfa\xed\xfe')  # magic
        f.write(b'\x00' * 28)  # 其他头部数据
    
    print(f"📋 临时测试文件: {test_file}")
    
    # 检查备份文件
    backup_path = test_file + ".backup_dylib"
    backup_exists_before = os.path.exists(backup_path)
    
    print("🚀 开始注入测试库（使用备份模式）")
    
    # 执行注入（创建备份）
    test_dylib = "@executable_path/Frameworks/TestLibrary.dylib"
    success = inject_dylib_to_macho(test_file, test_dylib, weak=False, create_backup=True)
    
    # 检查备份文件
    backup_exists_after = os.path.exists(backup_path)
    
    if not backup_exists_before and backup_exists_after:
        print("✅ 备份功能正常: 创建了备份文件")
    elif backup_exists_before:
        print("ℹ️ 备份文件已存在")
    else:
        print("❌ 备份功能异常: 未创建备份文件")
    
    # 清理临时文件
    try:
        shutil.rmtree(temp_dir)
        print(f"🧹 清理临时目录: {temp_dir}")
    except Exception as e:
        print(f"⚠️ 清理临时目录失败: {e}")

def main():
    """主函数"""
    print("🔧 测试MachO注入备份优化")
    print("=" * 50)
    
    test_no_backup()
    test_with_backup()
    
    print("\n✅ 测试完成!")
    print("\n💡 优化效果:")
    print("1. ⚡ 性能提升 - 签名过程中不创建备份文件")
    print("2. 💾 减少I/O - 避免不必要的文件复制和删除")
    print("3. 🛡️ 保持安全 - 独立工具使用时仍可选择创建备份")

if __name__ == "__main__":
    main() 