#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置工具函数
"""

import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 配置文件路径
CONFIG_DIR = os.path.expanduser("~/.iossigner")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# 默认配置
DEFAULT_CONFIG = {
    "certificates": [],
    "recent_files": [],
    "output_dir": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "apps"),
    "max_recent_files": 10,
    "auto_check_update": True,
    "language": "zh_CN"
}

def ensure_config_dir():
    """
    确保配置目录存在
    """
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
        logger.debug(f"创建配置目录: {CONFIG_DIR}")

def load_config():
    """
    加载配置
    
    Returns:
        dict: 配置数据
    """
    ensure_config_dir()
    
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 确保所有默认配置项都存在
        for key, value in DEFAULT_CONFIG.items():
            if key not in config:
                config[key] = value
        
        logger.debug("加载配置成功")
        return config
    except Exception as e:
        logger.error(f"加载配置失败: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """
    保存配置
    
    Args:
        config: 配置数据
    
    Returns:
        bool: 操作是否成功
    """
    ensure_config_dir()
    
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        logger.debug("保存配置成功")
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {e}")
        return False

def get_config_value(key, default=None):
    """
    获取配置值
    
    Args:
        key: 配置键
        default: 默认值
    
    Returns:
        配置值
    """
    config = load_config()
    return config.get(key, default)

def set_config_value(key, value):
    """
    设置配置值
    
    Args:
        key: 配置键
        value: 配置值
    
    Returns:
        bool: 操作是否成功
    """
    config = load_config()
    config[key] = value
    return save_config(config)

def add_recent_file(file_path):
    """
    添加最近使用的文件
    
    Args:
        file_path: 文件路径
    
    Returns:
        bool: 操作是否成功
    """
    config = load_config()
    recent_files = config.get("recent_files", [])
    
    # 如果文件已存在，先移除
    if file_path in recent_files:
        recent_files.remove(file_path)
    
    # 添加到列表开头
    recent_files.insert(0, file_path)
    
    # 限制列表大小
    max_files = config.get("max_recent_files", 10)
    if len(recent_files) > max_files:
        recent_files = recent_files[:max_files]
    
    config["recent_files"] = recent_files
    return save_config(config)

def get_recent_files():
    """
    获取最近使用的文件列表
    
    Returns:
        list: 文件路径列表
    """
    config = load_config()
    recent_files = config.get("recent_files", [])
    
    # 过滤不存在的文件
    return [f for f in recent_files if os.path.exists(f)]

def get_output_dir():
    """
    获取输出目录
    
    Returns:
        str: 输出目录路径
    """
    output_dir = get_config_value("output_dir", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "apps"))
    
    # 确保目录存在
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except:
            # 如果创建失败，使用当前目录下的apps目录
            output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "apps")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
    
    return output_dir

def set_output_dir(directory):
    """
    设置输出目录
    
    Args:
        directory: 目录路径
    
    Returns:
        bool: 操作是否成功
    """
    if os.path.isdir(directory):
        return set_config_value("output_dir", directory)
    return False 