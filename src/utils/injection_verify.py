#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
动态库注入验证工具
"""

import os
import logging
import subprocess
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

def verify_dylib_injection(app_path, expected_dylibs):
    """
    验证动态库注入是否成功
    
    Args:
        app_path: .app目录路径
        expected_dylibs: 期望注入的动态库列表
        
    Returns:
        dict: 验证结果
    """
    result = {
        "success": False,
        "found_dylibs": [],
        "missing_dylibs": [],
        "rpath_exists": False,
        "details": {}
    }
    
    if not os.path.exists(app_path):
        result["details"]["error"] = f"应用目录不存在: {app_path}"
        return result
    
    # 获取主二进制文件路径
    app_name = os.path.basename(app_path)
    if app_name.endswith('.app'):
        app_name = app_name[:-4]
    
    main_binary_path = os.path.join(app_path, app_name)
    
    if not os.path.exists(main_binary_path):
        # 尝试查找主二进制文件
        for item in os.listdir(app_path):
            item_path = os.path.join(app_path, item)
            if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                try:
                    with open(item_path, 'rb') as f:
                        magic = f.read(4)
                        if magic in [b'\xca\xfe\xba\xbe', b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe']:
                            main_binary_path = item_path
                            break
                except:
                    continue
        else:
            result["details"]["error"] = f"未找到主二进制文件"
            return result
    
    result["details"]["binary_path"] = main_binary_path
    
    # 在Windows上，我们无法直接使用otool，但可以检查文件是否存在
    if platform.system() != "Darwin":
        logger.info("非macOS平台，只检查文件是否存在")
        
        # 检查framework文件是否存在
        frameworks_dir = os.path.join(app_path, "Frameworks")
        if os.path.exists(frameworks_dir):
            result["details"]["frameworks_dir"] = frameworks_dir
            existing_frameworks = []
            for item in os.listdir(frameworks_dir):
                if item.endswith('.framework') or item.endswith('.dylib'):
                    existing_frameworks.append(item)
            result["details"]["existing_frameworks"] = existing_frameworks
        
        # 简单检查：如果有期望的dylib且对应的文件存在，认为可能成功
        for dylib in expected_dylibs:
            if "@executable_path/Frameworks/" in dylib:
                # 提取文件名
                filename = dylib.split("/")[-1]
                if ".framework/" in dylib:
                    # Framework情况
                    framework_name = dylib.split("/")[-2]
                    framework_path = os.path.join(frameworks_dir, framework_name)
                    if os.path.exists(framework_path):
                        result["found_dylibs"].append(dylib)
                else:
                    # 普通dylib情况
                    dylib_path = os.path.join(frameworks_dir, filename)
                    if os.path.exists(dylib_path):
                        result["found_dylibs"].append(dylib)
        
        # 计算缺失的
        result["missing_dylibs"] = [d for d in expected_dylibs if d not in result["found_dylibs"]]
        result["success"] = len(result["missing_dylibs"]) == 0
        result["rpath_exists"] = True  # 假设在Windows上已正确处理
        
        return result
    
    # macOS上使用otool检查
    try:
        # 检查LC_LOAD_DYLIB命令
        result_otool = subprocess.run(
            ["otool", "-l", main_binary_path],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result_otool.returncode != 0:
            result["details"]["otool_error"] = result_otool.stderr
            return result
        
        otool_output = result_otool.stdout
        result["details"]["otool_output"] = otool_output
        
        # 解析LC_LOAD_DYLIB命令
        found_dylibs = []
        lines = otool_output.split('\n')
        for i, line in enumerate(lines):
            if "LC_LOAD_DYLIB" in line or "LC_LOAD_WEAK_DYLIB" in line:
                # 下一行通常包含name
                if i + 1 < len(lines):
                    name_line = lines[i + 1].strip()
                    if name_line.startswith("name "):
                        dylib_name = name_line.split(" ", 1)[1].split(" (")[0]
                        found_dylibs.append(dylib_name)
        
        result["found_dylibs"] = found_dylibs
        
        # 检查RPATH
        rpath_exists = "@executable_path/Frameworks" in otool_output
        result["rpath_exists"] = rpath_exists
        
        # 计算缺失的dylib
        missing_dylibs = []
        for expected in expected_dylibs:
            if expected not in found_dylibs:
                missing_dylibs.append(expected)
        
        result["missing_dylibs"] = missing_dylibs
        result["success"] = len(missing_dylibs) == 0 and rpath_exists
        
        return result
        
    except Exception as e:
        result["details"]["exception"] = str(e)
        logger.exception(f"验证注入时出错: {e}")
        return result

def print_verification_result(result):
    """
    打印验证结果
    
    Args:
        result: verify_dylib_injection的返回结果
    """
    logger.info("=== 动态库注入验证结果 ===")
    logger.info(f"验证结果: {'成功' if result['success'] else '失败'}")
    
    if result["found_dylibs"]:
        logger.info(f"已找到的动态库 ({len(result['found_dylibs'])} 个):")
        for dylib in result["found_dylibs"]:
            logger.info(f"  ✓ {dylib}")
    
    if result["missing_dylibs"]:
        logger.warning(f"缺失的动态库 ({len(result['missing_dylibs'])} 个):")
        for dylib in result["missing_dylibs"]:
            logger.warning(f"  ✗ {dylib}")
    
    logger.info(f"RPATH状态: {'存在' if result['rpath_exists'] else '缺失'}")
    
    if "error" in result["details"]:
        logger.error(f"错误: {result['details']['error']}")
    
    if "binary_path" in result["details"]:
        logger.info(f"主二进制文件: {result['details']['binary_path']}")
    
    logger.info("=== 验证完成 ===")

def verify_frameworks_structure(app_path, expected_frameworks):
    """
    验证Frameworks目录结构
    
    Args:
        app_path: .app目录路径
        expected_frameworks: 期望的framework列表
        
    Returns:
        dict: 验证结果
    """
    result = {
        "success": False,
        "frameworks_dir_exists": False,
        "found_frameworks": [],
        "missing_frameworks": [],
        "details": {}
    }
    
    frameworks_dir = os.path.join(app_path, "Frameworks")
    result["frameworks_dir_exists"] = os.path.exists(frameworks_dir)
    
    if not result["frameworks_dir_exists"]:
        result["details"]["error"] = f"Frameworks目录不存在: {frameworks_dir}"
        return result
    
    # 检查期望的framework是否存在
    for framework_info in expected_frameworks:
        framework_name = framework_info.get("framework_name", "")
        if framework_name:
            framework_path = os.path.join(frameworks_dir, framework_name)
            if os.path.exists(framework_path):
                result["found_frameworks"].append(framework_name)
                
                # 检查framework内部结构
                binary_name = framework_name.replace('.framework', '')
                binary_path = os.path.join(framework_path, binary_name)
                if os.path.exists(binary_path):
                    result["details"][f"{framework_name}_binary"] = "存在"
                else:
                    result["details"][f"{framework_name}_binary"] = "缺失"
            else:
                result["missing_frameworks"].append(framework_name)
    
    result["success"] = len(result["missing_frameworks"]) == 0
    return result 