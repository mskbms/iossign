#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Framework注入详细调试工具
"""

import os
import sys
import struct
import json
from datetime import datetime

def analyze_macho_dylibs(binary_path):
    """分析MachO文件中的所有动态库"""
    results = {
        "file_exists": False,
        "is_macho": False,
        "dylibs": [],
        "rpaths": [],
        "framework_dylibs": [],
        "error": None
    }
    
    if not os.path.exists(binary_path):
        results["error"] = "文件不存在"
        return results
    
    results["file_exists"] = True
    
    try:
        with open(binary_path, 'rb') as f:
            data = f.read()
        
        if len(data) < 32:
            results["error"] = "文件太小"
            return results
        
        # 检查魔数
        magic = struct.unpack('<I', data[:4])[0]
        if magic not in [0xfeedface, 0xfeedfacf, 0xcefaedfe, 0xcffaedfe]:
            results["error"] = f"不是MachO文件，魔数: 0x{magic:08x}"
            return results
        
        results["is_macho"] = True
        
        is_64bit = magic in [0xfeedfacf, 0xcffaedfe]
        is_little_endian = magic in [0xfeedface, 0xfeedfacf]
        
        # 确定结构体大小
        header_size = 32 if is_64bit else 28
        
        if len(data) < header_size:
            results["error"] = "头部太小"
            return results
        
        # 解析头部
        if is_little_endian:
            ncmds = struct.unpack('<I', data[16:20])[0]
        else:
            ncmds = struct.unpack('>I', data[16:20])[0]
        
        # 定义load command常量
        LC_LOAD_DYLIB = 0xc
        LC_RPATH = 0x8000001c
        
        # 解析load commands
        current_offset = header_size
        
        for i in range(ncmds):
            if current_offset + 8 > len(data):
                break
                
            if is_little_endian:
                cmd = struct.unpack('<I', data[current_offset:current_offset+4])[0]
                cmdsize = struct.unpack('<I', data[current_offset+4:current_offset+8])[0]
            else:
                cmd = struct.unpack('>I', data[current_offset:current_offset+4])[0]
                cmdsize = struct.unpack('>I', data[current_offset+4:current_offset+8])[0]
            
            if cmd == LC_LOAD_DYLIB:
                # 解析动态库路径
                if current_offset + 24 <= len(data):
                    if is_little_endian:
                        name_offset = struct.unpack('<I', data[current_offset+8:current_offset+12])[0]
                    else:
                        name_offset = struct.unpack('>I', data[current_offset+8:current_offset+12])[0]
                    
                    # 计算路径的实际位置
                    path_start = current_offset + name_offset
                    if path_start < len(data):
                        try:
                            path_end = data.find(b'\x00', path_start)
                            if path_end == -1:
                                path_end = current_offset + cmdsize
                            
                            dylib_path = data[path_start:path_end].decode('utf-8')
                            results["dylibs"].append(dylib_path)
                            
                            # 检查是否是Framework路径
                            if "@executable_path/Frameworks/" in dylib_path:
                                results["framework_dylibs"].append(dylib_path)
                            
                        except Exception as e:
                            results["error"] = f"解析动态库路径失败: {e}"
            
            elif cmd == LC_RPATH:
                # 解析RPATH路径
                if current_offset + 12 <= len(data):
                    if is_little_endian:
                        path_offset = struct.unpack('<I', data[current_offset+8:current_offset+12])[0]
                    else:
                        path_offset = struct.unpack('>I', data[current_offset+8:current_offset+12])[0]
                    
                    # 计算路径的实际位置
                    path_start = current_offset + path_offset
                    if path_start < len(data):
                        try:
                            path_end = data.find(b'\x00', path_start)
                            if path_end == -1:
                                path_end = current_offset + cmdsize
                            
                            rpath = data[path_start:path_end].decode('utf-8')
                            results["rpaths"].append(rpath)
                            
                        except Exception as e:
                            results["error"] = f"解析RPATH路径失败: {e}"
            
            current_offset += cmdsize
        
    except Exception as e:
        results["error"] = f"解析文件时出错: {e}"
    
    return results

def check_app_detailed(app_path):
    """详细检查应用结构"""
    print(f"🔍 详细检查应用: {app_path}")
    print("=" * 80)
    
    app_info = {
        "app_path": app_path,
        "app_exists": os.path.exists(app_path),
        "main_binary": None,
        "frameworks_dir": None,
        "frameworks": [],
        "macho_analysis": None,
        "timestamp": datetime.now().isoformat()
    }
    
    if not app_info["app_exists"]:
        print(f"❌ 应用目录不存在: {app_path}")
        return app_info
    
    print(f"✅ 应用目录存在")
    
    # 获取应用名称
    app_name = os.path.basename(app_path)
    if app_name.endswith('.app'):
        app_name = app_name[:-4]
    
    # 检查主二进制文件
    main_binary = os.path.join(app_path, app_name)
    app_info["main_binary"] = {
        "path": main_binary,
        "exists": os.path.exists(main_binary),
        "size": os.path.getsize(main_binary) if os.path.exists(main_binary) else 0
    }
    
    if app_info["main_binary"]["exists"]:
        print(f"✅ 主二进制文件: {main_binary}")
        print(f"   文件大小: {app_info['main_binary']['size']} 字节")
        
        # 分析MachO文件
        print("\n🔬 分析MachO文件...")
        app_info["macho_analysis"] = analyze_macho_dylibs(main_binary)
        
        if app_info["macho_analysis"]["is_macho"]:
            print(f"✅ 有效的MachO文件")
            print(f"   动态库数量: {len(app_info['macho_analysis']['dylibs'])}")
            print(f"   RPATH数量: {len(app_info['macho_analysis']['rpaths'])}")
            print(f"   Framework动态库数量: {len(app_info['macho_analysis']['framework_dylibs'])}")
            
            # 显示RPATH
            if app_info["macho_analysis"]["rpaths"]:
                print("\n📋 RPATH列表:")
                for i, rpath in enumerate(app_info["macho_analysis"]["rpaths"], 1):
                    print(f"   {i}. {rpath}")
            
            # 显示Framework动态库
            if app_info["macho_analysis"]["framework_dylibs"]:
                print("\n🎯 Framework动态库:")
                for i, dylib in enumerate(app_info["macho_analysis"]["framework_dylibs"], 1):
                    print(f"   {i}. {dylib}")
            else:
                print("\n❌ 没有发现Framework动态库注入")
            
            # 显示所有动态库（前10个）
            print(f"\n📚 所有动态库 (前10个):")
            for i, dylib in enumerate(app_info["macho_analysis"]["dylibs"][:10], 1):
                print(f"   {i}. {dylib}")
            if len(app_info["macho_analysis"]["dylibs"]) > 10:
                print(f"   ... 还有 {len(app_info['macho_analysis']['dylibs']) - 10} 个")
                
        else:
            print(f"❌ {app_info['macho_analysis']['error']}")
    else:
        print(f"❌ 主二进制文件不存在: {main_binary}")
    
    # 检查Frameworks目录
    frameworks_dir = os.path.join(app_path, "Frameworks")
    app_info["frameworks_dir"] = {
        "path": frameworks_dir,
        "exists": os.path.exists(frameworks_dir),
        "frameworks": []
    }
    
    print(f"\n📁 Frameworks目录: {frameworks_dir}")
    if app_info["frameworks_dir"]["exists"]:
        print(f"✅ Frameworks目录存在")
        
        frameworks = [f for f in os.listdir(frameworks_dir) if f.endswith('.framework')]
        app_info["frameworks_dir"]["frameworks"] = frameworks
        
        if frameworks:
            print(f"   发现 {len(frameworks)} 个Framework:")
            for i, framework in enumerate(frameworks, 1):
                framework_path = os.path.join(frameworks_dir, framework)
                print(f"   {i}. {framework}")
                
                # 检查Framework二进制文件
                framework_name = framework.replace('.framework', '')
                framework_binary = os.path.join(framework_path, framework_name)
                if os.path.exists(framework_binary):
                    size = os.path.getsize(framework_binary)
                    print(f"      ✅ 二进制文件: {size} 字节")
                else:
                    print(f"      ❌ 二进制文件不存在: {framework_binary}")
        else:
            print(f"   📁 目录存在但为空")
    else:
        print(f"❌ Frameworks目录不存在")
    
    # 检查签名文件
    print(f"\n🔐 签名文件检查:")
    code_signature_dir = os.path.join(app_path, "_CodeSignature")
    if os.path.exists(code_signature_dir):
        print(f"✅ 签名目录存在: {code_signature_dir}")
        
        code_resources = os.path.join(code_signature_dir, "CodeResources")
        if os.path.exists(code_resources):
            size = os.path.getsize(code_resources)
            print(f"   ✅ CodeResources: {size} 字节")
        else:
            print(f"   ❌ CodeResources不存在")
    else:
        print(f"❌ 签名目录不存在")
    
    return app_info

def compare_before_after(before_path, after_path):
    """比较签名前后的应用状态"""
    print(f"\n🔄 比较签名前后状态")
    print("=" * 80)
    
    if not os.path.exists(before_path):
        print(f"❌ 签名前应用不存在: {before_path}")
        return
    
    if not os.path.exists(after_path):
        print(f"❌ 签名后应用不存在: {after_path}")
        return
    
    print(f"📱 签名前: {before_path}")
    before_info = check_app_detailed(before_path)
    
    print(f"\n📱 签名后: {after_path}")
    after_info = check_app_detailed(after_path)
    
    # 比较Framework注入情况
    print(f"\n📊 Framework注入对比:")
    before_frameworks = before_info.get("macho_analysis", {}).get("framework_dylibs", [])
    after_frameworks = after_info.get("macho_analysis", {}).get("framework_dylibs", [])
    
    print(f"   签名前Framework动态库: {len(before_frameworks)}")
    print(f"   签名后Framework动态库: {len(after_frameworks)}")
    
    if len(after_frameworks) > len(before_frameworks):
        print(f"   ✅ 新增 {len(after_frameworks) - len(before_frameworks)} 个Framework注入")
        for fw in after_frameworks:
            if fw not in before_frameworks:
                print(f"      + {fw}")
    elif len(after_frameworks) == len(before_frameworks):
        print(f"   ⚠️  Framework注入数量没有变化")
    else:
        print(f"   ❌ Framework注入减少了!")
    
    # 比较Frameworks目录
    before_fw_exists = before_info.get("frameworks_dir", {}).get("exists", False)
    after_fw_exists = after_info.get("frameworks_dir", {}).get("exists", False)
    
    print(f"\n📁 Frameworks目录对比:")
    print(f"   签名前: {'存在' if before_fw_exists else '不存在'}")
    print(f"   签名后: {'存在' if after_fw_exists else '不存在'}")
    
    if after_fw_exists and not before_fw_exists:
        print(f"   ✅ 新创建了Frameworks目录")
    elif not after_fw_exists:
        print(f"   ❌ Frameworks目录仍然不存在")

def save_analysis_report(app_info, filename="framework_analysis.json"):
    """保存分析报告"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(app_info, f, indent=2, ensure_ascii=False)
        print(f"\n💾 分析报告已保存: {filename}")
    except Exception as e:
        print(f"\n❌ 保存报告失败: {e}")

if __name__ == "__main__":
    print("🔬 Framework注入详细调试工具")
    print("=" * 80)
    
    if len(sys.argv) < 2:
        print("❌ 请提供应用路径")
        print("\n💡 使用方法:")
        print("   python debug_framework.py <应用路径>")
        print("   python debug_framework.py <签名前路径> <签名后路径>  # 比较模式")
        sys.exit(1)
    
    if len(sys.argv) == 2:
        # 单个应用分析模式
        app_path = sys.argv[1]
        app_info = check_app_detailed(app_path)
        save_analysis_report(app_info)
        
    elif len(sys.argv) == 3:
        # 比较模式
        before_path = sys.argv[1]
        after_path = sys.argv[2]
        compare_before_after(before_path, after_path)
    
    print("\n" + "=" * 80)
    print("🎯 调试完成!")
    print("\n💡 如果Framework注入失败，请检查:")
    print("   1. UI中是否正确添加了Framework")
    print("   2. 签名日志中是否有Framework复制消息")
    print("   3. zsign命令参数是否包含-l参数") 