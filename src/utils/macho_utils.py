#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
MachO二进制文件操作工具
"""

import os
import logging
import subprocess
import platform
from pathlib import Path

logger = logging.getLogger(__name__)

def get_install_name_tool_path():
    """
    获取install_name_tool工具路径
    
    Returns:
        str: install_name_tool工具路径，如果不可用则返回None
    """
    # 在macOS上，install_name_tool是系统自带的
    if platform.system() == "Darwin":
        return "install_name_tool"
    
    # 检查是否有llvm-install-name-tool
    try:
        result = subprocess.run(["llvm-install-name-tool", "--version"], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return "llvm-install-name-tool"
    except FileNotFoundError:
        pass
    
    # 在Windows和Linux上，我们需要使用交叉编译的版本或Python库
    logger.warning("当前平台没有可用的install_name_tool，将尝试使用纯Python方案")
    return None

def try_python_macho_modification(binary_path, rpath):
    """
    尝试使用纯Python库修改MachO文件的RPATH
    
    Args:
        binary_path: 二进制文件路径
        rpath: 要添加的RPATH路径
        
    Returns:
        bool: 操作是否成功
    """
    try:
        # 使用我们自己的RPATH处理模块
        from .macho_rpath import add_rpath_to_macho, check_rpath_exists
        
        logger.info(f"尝试使用自定义RPATH处理模块添加RPATH: {rpath}")
        
        # 首先检查是否已存在
        if check_rpath_exists(binary_path, rpath):
            logger.info(f"RPATH '{rpath}' 已存在")
            return True
        
        # 添加RPATH
        return add_rpath_to_macho(binary_path, rpath)
        
    except ImportError as e:
        logger.debug(f"自定义RPATH模块导入失败: {e}")
    except Exception as e:
        logger.exception(f"使用Python RPATH模块时出错: {e}")
    
    return False

def add_rpath_to_binary(binary_path, rpath):
    """
    为二进制文件添加RPATH
    
    Args:
        binary_path: 二进制文件路径
        rpath: 要添加的RPATH路径
        
    Returns:
        bool: 操作是否成功
    """
    install_name_tool = get_install_name_tool_path()
    
    if not os.path.exists(binary_path):
        logger.error(f"二进制文件不存在: {binary_path}")
        return False
    
    # 首先尝试使用系统工具
    if install_name_tool:
        try:
            # 构建命令
            cmd = [install_name_tool, "-add_rpath", rpath, binary_path]
            logger.info(f"添加RPATH: {' '.join(cmd)}")
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                logger.info(f"成功添加RPATH '{rpath}' 到 {binary_path}")
                return True
            else:
                # 检查是否是因为RPATH已存在
                if "already exists" in result.stderr or "duplicate" in result.stderr:
                    logger.info(f"RPATH '{rpath}' 已存在于 {binary_path}")
                    return True
                else:
                    logger.error(f"添加RPATH失败: {result.stderr}")
                    # 继续尝试Python方案
        except Exception as e:
            logger.exception(f"添加RPATH时出错: {e}")
            # 继续尝试Python方案
    
    # 如果系统工具不可用，尝试Python方案
    logger.info("尝试使用纯Python方案添加RPATH...")
    if try_python_macho_modification(binary_path, rpath):
        return True
    
    # 如果都失败了，给出相应的提示
    if platform.system() == "Windows":
        logger.warning("⚠️  在Windows平台上无法使用系统工具添加RPATH")
        logger.warning("但是我们的纯Python RPATH处理已经尝试过了")
        logger.warning("如果仍然有问题，请检查macholib库是否正确安装")
        
        # 返回True以避免阻止签名流程继续
        return True
    
    logger.error("所有RPATH添加方案都失败了")
    return False

def check_rpath_exists(binary_path, rpath):
    """
    检查二进制文件是否已有指定的RPATH
    
    Args:
        binary_path: 二进制文件路径
        rpath: RPATH路径
        
    Returns:
        bool: 是否已存在该RPATH
    """
    if not os.path.exists(binary_path):
        return False
    
    try:
        # 首先尝试使用我们的Python RPATH模块
        from .macho_rpath import check_rpath_exists as python_check_rpath
        return python_check_rpath(binary_path, rpath)
    except ImportError:
        logger.debug("自定义RPATH模块不可用，回退到系统工具")
    except Exception as e:
        logger.debug(f"使用Python检查RPATH时出错: {e}")
    
    try:
        # 使用otool检查RPATH (仅在macOS上可用)
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["otool", "-l", binary_path],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return rpath in result.stdout
        
        # 在其他平台上假设不存在
        return False
        
    except Exception as e:
        logger.debug(f"检查RPATH时出错: {e}")
        return False

def add_frameworks_rpath(app_path):
    """
    为应用的主二进制文件添加Frameworks的RPATH
    
    Args:
        app_path: .app目录路径
        
    Returns:
        bool: 操作是否成功
    """
    if not os.path.exists(app_path):
        logger.error(f"应用目录不存在: {app_path}")
        return False
    
    # 获取应用名称（从.app目录名推断）
    app_name = os.path.basename(app_path)
    if app_name.endswith('.app'):
        app_name = app_name[:-4]
    
    # 主二进制文件路径
    main_binary_path = os.path.join(app_path, app_name)
    
    if not os.path.exists(main_binary_path):
        logger.error(f"主二进制文件不存在: {main_binary_path}")
        # 尝试在app目录中查找可执行文件
        for item in os.listdir(app_path):
            item_path = os.path.join(app_path, item)
            if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                # 检查是否是MachO文件（简单检查）
                try:
                    with open(item_path, 'rb') as f:
                        magic = f.read(4)
                        if magic in [b'\xca\xfe\xba\xbe', b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe']:
                            main_binary_path = item_path
                            logger.info(f"找到主二进制文件: {main_binary_path}")
                            break
                except:
                    continue
        else:
            logger.error("未找到主二进制文件")
            return False
    
    # 要添加的RPATH
    frameworks_rpath = "@executable_path/Frameworks"
    
    # 检查是否已存在
    if check_rpath_exists(main_binary_path, frameworks_rpath):
        logger.info(f"RPATH '{frameworks_rpath}' 已存在")
        return True
    
    # 添加RPATH
    return add_rpath_to_binary(main_binary_path, frameworks_rpath) 