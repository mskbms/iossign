#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
文件操作工具函数
"""

import os
import shutil
import zipfile
import tempfile
import logging
import re
from pathlib import Path
import time
import platform
import subprocess
import random

logger = logging.getLogger(__name__)

def ensure_dir(directory):
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
        logger.debug(f"创建目录: {directory}")

def copy_file(src, dst):
    """
    复制文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
    
    Returns:
        bool: 操作是否成功
    """
    try:
        shutil.copy2(src, dst)
        logger.debug(f"复制文件: {src} -> {dst}")
        return True
    except Exception as e:
        logger.error(f"复制文件失败: {e}")
        return False

def delete_file(file_path):
    """
    删除文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        bool: 操作是否成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.debug(f"删除文件: {file_path}")
            return True
        return False
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return False

def sanitize_filename(filename):
    """
    清理文件名，移除或替换不支持的字符
    
    Args:
        filename: 原始文件名
    
    Returns:
        str: 清理后的文件名
    """
    # 如果文件名包含非ASCII字符，使用英文替代
    if any(ord(c) > 127 for c in filename):
        # 保留文件扩展名
        name, ext = os.path.splitext(filename)
        # 使用更具可读性的名称，并确保唯一性
        import hashlib
        hash_obj = hashlib.md5(name.encode('utf-8'))
        hash_str = hash_obj.hexdigest()[:8]
        return f"app_{hash_str}{ext}"
    return filename

def sanitize_app_contents(app_path):
    """
    清理应用内部的中文文件名（不再重命名可执行文件，保留原始名）
    Args:
        app_path: 应用目录路径
    Returns:
        bool: 操作是否成功
    """
    try:
        # 读取Info.plist
        info_plist_path = os.path.join(app_path, "Info.plist")
        if not os.path.exists(info_plist_path):
            logger.error(f"找不到Info.plist文件: {info_plist_path}")
            return False
        info_plist = read_plist(info_plist_path)
        if not info_plist:
            logger.error(f"读取Info.plist失败: {info_plist_path}")
            return False
        # 获取可执行文件名，禁止对其重命名
        executable_name = info_plist.get("CFBundleExecutable", "")
        # 处理其他可能包含中文的文件（排除可执行文件）
        for root, dirs, files in os.walk(app_path):
            for file in files:
                if file == executable_name:
                    continue  # 跳过可执行文件
                if any(ord(c) > 127 for c in file):
                    old_path = os.path.join(root, file)
                    new_file = sanitize_filename(file)
                    new_path = os.path.join(root, new_file)
                    os.rename(old_path, new_path)
                    logger.debug(f"重命名文件: {file} -> {new_file}")
            for i, dir_name in enumerate(dirs):
                if any(ord(c) > 127 for c in dir_name):
                    old_path = os.path.join(root, dir_name)
                    new_dir = sanitize_filename(dir_name)
                    new_path = os.path.join(root, new_dir)
                    os.rename(old_path, new_path)
                    dirs[i] = new_dir  # 更新目录列表，以便继续遍历
                    logger.debug(f"重命名目录: {dir_name} -> {new_dir}")
        return True
    except Exception as e:
        logger.error(f"清理应用内部中文文件名失败: {e}")
        return False

def extract_ipa(ipa_path, extract_dir=None):
    """
    解压IPA文件，返回解压目录和原始.app名称
    Returns:
        (extract_dir, original_app_name)
    """
    try:
        # 在当前目录创建unzip目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_dir = os.path.dirname(os.path.dirname(current_dir))  # 获取项目根目录
        unzip_dir = os.path.join(base_dir, "unzip")
        
        # 确保unzip目录存在
        if not os.path.exists(unzip_dir):
            os.makedirs(unzip_dir)
        
        # 生成随机13位数字作为解压目录名
        random_id = ''.join(str(random.randint(0, 9)) for _ in range(13))
        extract_dir = os.path.join(unzip_dir, random_id)
        
        # 确保解压目录存在
        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir)
        
        logger.info(f"开始解压IPA文件: {ipa_path} -> {extract_dir}")
        
        # 使用内置7z工具解压
        tools_dir = os.path.join(base_dir, "tools", "7Z")
        seven_zip_path = os.path.join(tools_dir, "7Z.exe")
        
        if not os.path.exists(seven_zip_path):
            logger.error(f"内置7z工具不存在: {seven_zip_path}")
            raise Exception("内置7z工具不存在")
        
        # 使用内置7z解压，确保所有路径使用短路径格式避免中文问题
        cmd = [seven_zip_path, "x", "-y", "-bso0", "-bsp0", f"-o{extract_dir}", ipa_path]
        
        # 使用subprocess.CREATE_NO_WINDOW标志隐藏命令窗口（仅在Windows上）
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = 0x08000000  # CREATE_NO_WINDOW
        
        result = subprocess.run(cmd, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE, 
                              text=True,
                              creationflags=creation_flags)
        
        if result.returncode != 0:
            logger.error(f"7z解压失败，返回码: {result.returncode}")
            logger.error(f"标准输出: {result.stdout}")
            logger.error(f"标准错误: {result.stderr}")
            raise Exception(f"7z解压失败: {result.stderr}")
        else:
            logger.info("使用内置7z成功解压IPA文件")
        
        logger.info(f"IPA文件解压完成: {ipa_path} -> {extract_dir}")
        
        # 获取原始应用名称
        original_app_name = None
        payload_dir = os.path.join(extract_dir, "Payload")
        if os.path.exists(payload_dir):
            for item in os.listdir(payload_dir):
                item_path = os.path.join(payload_dir, item)
                if os.path.isdir(item_path):
                    if item.endswith(".app"):
                        original_app_name = item
                        logger.info(f"找到原始应用名称: {original_app_name}")
                        break
                    else:
                        original_app_name = item
                        logger.info(f"找到可能的原始应用名称: {original_app_name}")
        
        # 获取应用路径
        app_path = get_app_path_in_ipa(extract_dir)
        if app_path:
            logger.info(f"找到应用路径: {app_path}")
            sanitize_app_contents(app_path)
        else:
            logger.warning("未找到.app目录，尝试手动查找和重命名")
            payload_dir = os.path.join(extract_dir, "Payload")
            if os.path.exists(payload_dir):
                for item in os.listdir(payload_dir):
                    item_path = os.path.join(payload_dir, item)
                    if os.path.isdir(item_path):
                        if not item.endswith(".app"):
                            new_name = f"app_{int(time.time())}.app"
                            new_path = os.path.join(payload_dir, new_name)
                            try:
                                os.rename(item_path, new_path)
                                logger.info(f"重命名可能的应用目录: {item} -> {new_name}")
                                app_path = get_app_path_in_ipa(extract_dir)
                                if app_path:
                                    sanitize_app_contents(app_path)
                                    break
                            except Exception as e:
                                logger.error(f"重命名目录失败: {e}")
        
        return extract_dir, original_app_name
    except Exception as e:
        logger.error(f"解压IPA文件失败: {e}")
        return None, None

def _extract_with_system_commands(ipa_path, extract_dir):
    """废弃的系统命令解压方法，现在只使用内置7z"""
    logger.error("不再支持系统命令解压，请使用内置7z工具")
    return False

def _extract_with_zipfile(ipa_path, extract_dir):
    """废弃的zipfile解压方法，现在只使用内置7z"""
    logger.error("不再支持zipfile解压，请使用内置7z工具")
    return False

def create_ipa(app_dir, output_path):
    """
    创建IPA文件
    
    Args:
        app_dir: 应用目录路径
        output_path: 输出IPA文件路径
    
    Returns:
        bool: 操作是否成功
    """
    try:
        # 创建临时目录结构
        temp_dir = tempfile.mkdtemp(prefix="ipa_create_")
        payload_dir = os.path.join(temp_dir, "Payload")
        os.makedirs(payload_dir)
        
        # 复制应用到Payload目录 - 不再重命名中文应用目录
        app_name = os.path.basename(app_dir)
        target_app_dir = os.path.join(payload_dir, app_name)
        
        # 直接复制，不再检查和重命名中文名称
        logger.debug(f"复制应用目录: {app_dir} -> {target_app_dir}")
        shutil.copytree(app_dir, target_app_dir)
        
        # 创建ZIP文件
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        # 清理临时目录
        shutil.rmtree(temp_dir)
        
        logger.debug(f"创建IPA文件: {app_dir} -> {output_path}")
        return True
    except Exception as e:
        logger.error(f"创建IPA文件失败: {e}")
        return False

def get_app_path_in_ipa(extract_dir):
    """
    获取解压后的IPA中的.app路径
    
    Args:
        extract_dir: IPA解压目录
    
    Returns:
        str: .app路径，如果未找到则返回None
    """
    try:
        payload_dir = os.path.join(extract_dir, "Payload")
        if not os.path.exists(payload_dir):
            logger.error(f"无效的IPA结构: 未找到Payload目录")
            return None
        
        # 查找.app目录
        for item in os.listdir(payload_dir):
            if item.endswith(".app") and os.path.isdir(os.path.join(payload_dir, item)):
                return os.path.join(payload_dir, item)
        
        logger.error(f"无效的IPA结构: 未找到.app目录")
        return None
    except Exception as e:
        logger.error(f"获取.app路径失败: {e}")
        return None

def read_plist(plist_path):
    """
    读取plist文件
    
    Args:
        plist_path: plist文件路径
    
    Returns:
        dict: plist内容，如果失败则返回None
    """
    try:
        # 首先尝试使用原生plistlib
        try:
            import plistlib
            with open(plist_path, 'rb') as fp:
                return plistlib.load(fp)
        except Exception as e1:
            logger.warning(f"使用原生plistlib读取失败: {e1}")
            
            # 尝试使用biplist作为备选
            try:
                from biplist import readPlist
                return readPlist(plist_path)
            except Exception as e2:
                logger.warning(f"使用biplist读取失败: {e2}")
                
                # 最后尝试使用第三种方法
                try:
                    import subprocess
                    import json
                    import tempfile
                    
                    # 使用plutil转换为JSON（仅在macOS上可用）
                    if platform.system() == "Darwin":
                        temp_json = tempfile.mktemp(suffix=".json")
                        subprocess.run(["plutil", "-convert", "json", "-o", temp_json, plist_path], check=True)
                        with open(temp_json, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        os.unlink(temp_json)
                        return data
                except Exception as e3:
                    logger.error(f"所有读取plist方法都失败: {e3}")
                    return None
    except Exception as e:
        logger.error(f"读取plist文件失败: {e}")
        return None

def write_plist(plist_path, data):
    """
    写入plist文件
    
    Args:
        plist_path: plist文件路径
        data: 要写入的数据
    
    Returns:
        bool: 操作是否成功
    """
    try:
        # 首先尝试使用原生plistlib
        try:
            import plistlib
            with open(plist_path, 'wb') as fp:
                plistlib.dump(data, fp)
            logger.debug(f"使用原生plistlib写入plist文件: {plist_path}")
            return True
        except Exception as e1:
            logger.warning(f"使用原生plistlib写入失败: {e1}")
            
            # 尝试使用biplist作为备选
            try:
                from biplist import writePlist
                writePlist(data, plist_path)
                logger.debug(f"使用biplist写入plist文件: {plist_path}")
                return True
            except Exception as e2:
                logger.error(f"所有写入plist方法都失败: {e2}")
                return False
    except Exception as e:
        logger.error(f"写入plist文件失败: {e}")
        return False

def get_file_size(file_path):
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
    
    Returns:
        int: 文件大小(字节)
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"获取文件大小失败: {e}")
        return 0

def get_file_md5(file_path):
    """
    获取文件MD5值
    
    Args:
        file_path: 文件路径
    
    Returns:
        str: MD5值，如果失败则返回None
    """
    try:
        import hashlib
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"获取文件MD5值失败: {e}")
        return None

def restore_original_app_name(extract_dir, output_ipa_path, original_app_name):
    """
    恢复原始的应用名称
    Args:
        extract_dir: 解压目录路径
        output_ipa_path: 输出的IPA文件路径
        original_app_name: 原始.app目录名
    Returns:
        str: 恢复原始名称后的IPA文件路径
    """
    try:
        if not original_app_name:
            logger.warning("原始应用名称为空，无法恢复")
            return output_ipa_path
        logger.info(f"准备恢复原始应用名称: {original_app_name}")
        temp_dir = tempfile.mkdtemp(prefix="restore_app_name_")
        with zipfile.ZipFile(output_ipa_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        payload_dir = os.path.join(temp_dir, "Payload")
        current_app_path = None
        current_app_name = None
        if os.path.exists(payload_dir):
            for item in os.listdir(payload_dir):
                item_path = os.path.join(payload_dir, item)
                if os.path.isdir(item_path) and item.endswith(".app"):
                    current_app_path = item_path
                    current_app_name = item
                    break
        if not current_app_path or not current_app_name:
            logger.warning("找不到当前应用目录，无法恢复原始名称")
            shutil.rmtree(temp_dir)
            return output_ipa_path
        if current_app_name != original_app_name:
            new_app_path = os.path.join(payload_dir, original_app_name)
            try:
                os.rename(current_app_path, new_app_path)
                logger.info(f"重命名应用目录: {current_app_name} -> {original_app_name}")
            except Exception as e:
                logger.error(f"重命名应用目录失败: {e}")
                shutil.rmtree(temp_dir)
                return output_ipa_path
        output_dir = os.path.dirname(output_ipa_path)
        filename = os.path.basename(output_ipa_path)
        name, ext = os.path.splitext(filename)
        restored_ipa_path = os.path.join(output_dir, f"{name}_restored{ext}")
        with zipfile.ZipFile(restored_ipa_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        logger.info(f"创建恢复原始名称的IPA文件: {restored_ipa_path}")
        shutil.rmtree(temp_dir)
        try:
            os.remove(output_ipa_path)
            logger.debug(f"删除原始签名文件: {output_ipa_path}")
        except Exception as e:
            logger.warning(f"删除原始签名文件失败: {e}")
        return restored_ipa_path
    except Exception as e:
        logger.error(f"恢复原始应用名称失败: {e}")
        return output_ipa_path

def get_app_dylibs(app_path):
    """
    获取应用的动态库列表
    
    Args:
        app_path: 应用目录路径
    
    Returns:
        list: 动态库列表，包含名称和路径
    """
    dylibs = []
    try:
        # 检查应用目录是否存在
        if not os.path.exists(app_path) or not os.path.isdir(app_path):
            logger.error(f"应用目录不存在: {app_path}")
            return dylibs
        
        # 获取可执行文件路径
        info_plist_path = os.path.join(app_path, "Info.plist")
        if not os.path.exists(info_plist_path):
            logger.error(f"找不到Info.plist文件: {info_plist_path}")
            return dylibs
        
        info_plist = read_plist(info_plist_path)
        if not info_plist:
            logger.error(f"读取Info.plist失败: {info_plist_path}")
            return dylibs
        
        executable_name = info_plist.get("CFBundleExecutable", "")
        if not executable_name:
            logger.error("无法获取可执行文件名称")
            return dylibs
        
        executable_path = os.path.join(app_path, executable_name)
        if not os.path.exists(executable_path):
            logger.error(f"可执行文件不存在: {executable_path}")
            return dylibs
        
        # 在macOS上使用otool命令获取动态库列表
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(["otool", "-L", executable_path], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE, 
                                      text=True)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    # 跳过第一行（可执行文件路径）
                    for line in lines[1:]:
                        line = line.strip()
                        if line:
                            # 提取动态库路径
                            parts = line.split('(')
                            if parts:
                                dylib_path = parts[0].strip()
                                dylib_name = os.path.basename(dylib_path)
                                
                                # 获取动态库类型
                                dylib_type = "系统"
                                if "framework" in dylib_path.lower():
                                    dylib_type = "框架"
                                elif not (dylib_path.startswith("/System/") or dylib_path.startswith("/usr/lib/")):
                                    dylib_type = "自定义"
                                
                                dylibs.append({
                                    "name": dylib_name,
                                    "path": dylib_path,
                                    "type": dylib_type,
                                    "location": "链接"
                                })
            except Exception as e:
                logger.error(f"使用otool获取动态库列表失败: {e}")
        
        # 查找Frameworks目录中的动态库
        frameworks_dir = os.path.join(app_path, "Frameworks")
        if os.path.exists(frameworks_dir) and os.path.isdir(frameworks_dir):
            for item in os.listdir(frameworks_dir):
                if item.endswith(".dylib") or item.endswith(".framework"):
                    dylib_path = os.path.join(frameworks_dir, item)
                    
                    # 判断动态库类型
                    dylib_type = "自定义"
                    if item.endswith(".framework"):
                        dylib_type = "框架"
                    
                    # 获取文件大小
                    file_size = 0
                    try:
                        file_size = os.path.getsize(dylib_path)
                    except:
                        pass
                    
                    # 格式化文件大小
                    size_str = ""
                    if file_size > 0:
                        if file_size < 1024:
                            size_str = f"{file_size} B"
                        elif file_size < 1024 * 1024:
                            size_str = f"{file_size / 1024:.1f} KB"
                        else:
                            size_str = f"{file_size / (1024 * 1024):.1f} MB"
                    
                    dylibs.append({
                        "name": item,
                        "path": dylib_path,
                        "type": dylib_type,
                        "location": "Frameworks",
                        "size": size_str
                    })
        
        # 查找可执行文件目录中的动态库
        for item in os.listdir(app_path):
            if item.endswith(".dylib"):
                dylib_path = os.path.join(app_path, item)
                
                # 获取文件大小
                file_size = 0
                try:
                    file_size = os.path.getsize(dylib_path)
                except:
                    pass
                
                # 格式化文件大小
                size_str = ""
                if file_size > 0:
                    if file_size < 1024:
                        size_str = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_str = f"{file_size / 1024:.1f} KB"
                    else:
                        size_str = f"{file_size / (1024 * 1024):.1f} MB"
                
                dylibs.append({
                    "name": item,
                    "path": dylib_path,
                    "type": "自定义",
                    "location": "根目录",
                    "size": size_str
                })
        
        logger.info(f"找到 {len(dylibs)} 个动态库")
        return dylibs
    except Exception as e:
        logger.error(f"获取动态库列表失败: {e}")
        return dylibs

def update_app_info(app_path, bundle_id=None, display_name=None, bundle_name=None, version_code=None, version_name=None):
    """
    批量更新Info.plist的关键信息
    Args:
        app_path: .app目录路径
        bundle_id: CFBundleIdentifier
        display_name: CFBundleDisplayName
        bundle_name: CFBundleName
        version_code: CFBundleVersion
        version_name: CFBundleShortVersionString
    Returns:
        bool: 操作是否成功
    """
    try:
        info_plist_path = os.path.join(app_path, "Info.plist")
        info = read_plist(info_plist_path)
        if not info:
            logger.error(f"读取Info.plist失败: {info_plist_path}")
            return False
        
        # 记录原始值和更改
        changes = []
        original_info = info.copy()
        
        if bundle_id and info.get("CFBundleIdentifier") != bundle_id:
            old_value = info.get("CFBundleIdentifier", "无")
            info["CFBundleIdentifier"] = bundle_id
            changes.append(f"BundleID: {old_value} → {bundle_id}")
            
        if display_name is not None:
            old_value = info.get("CFBundleDisplayName", "无")
            if display_name.strip():
                if info.get("CFBundleDisplayName") != display_name:
                    info["CFBundleDisplayName"] = display_name
                    changes.append(f"显示名称: {old_value} → {display_name}")
            elif "CFBundleDisplayName" in info:
                del info["CFBundleDisplayName"]
                changes.append(f"显示名称: {old_value} → 已删除")
                
        if bundle_name and info.get("CFBundleName") != bundle_name:
            old_value = info.get("CFBundleName", "无")
            info["CFBundleName"] = bundle_name
            changes.append(f"应用名称: {old_value} → {bundle_name}")
            
        if version_code and info.get("CFBundleVersion") != version_code:
            old_value = info.get("CFBundleVersion", "无")
            info["CFBundleVersion"] = version_code
            changes.append(f"版本号: {old_value} → {version_code}")
            
        if version_name and info.get("CFBundleShortVersionString") != version_name:
            old_value = info.get("CFBundleShortVersionString", "无")
            info["CFBundleShortVersionString"] = version_name
            changes.append(f"版本名称: {old_value} → {version_name}")
        
        # 只有在真正有变化时才写入和记录
        if changes:
            write_plist(info_plist_path, info)
            logger.info(f"已更新Info.plist: {info_plist_path}")
            for change in changes:
                logger.info(f"  - {change}")
        else:
            logger.info(f"Info.plist无需更新: {info_plist_path}")
            
        return True
    except Exception as e:
        logger.error(f"更新Info.plist失败: {e}")
        return False 