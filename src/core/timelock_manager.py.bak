#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import datetime
import requests
from pathlib import Path


class TimelockManager:
    """时间锁控制模块，负责生成和管理时间锁配置"""
    
    def __init__(self, config):
        """初始化时间锁管理器
        
        Args:
            config (dict): 应用配置字典
        """
        self.logger = logging.getLogger("TimelockManager")
        self.config = config
        self.remote_url = config["timelock"]["remote_url"]
        self.api_key = config["timelock"]["api_key"]
    
    def generate_timelock_config(self, options):
        """生成时间锁配置
        
        Args:
            options (dict): 时间锁选项，包括:
                - expiry_date: 过期日期 (YYYY-MM-DD)
                - trial_period: 试用期限 (天数)
                - max_usage_count: 最大使用次数
                - remote_control: 是否启用远程控制
                - device_id: 设备ID限制
        
        Returns:
            tuple: (bool, dict|str) - (是否成功, 配置字典或错误消息)
        """
        try:
            # 验证选项
            if "expiry_date" in options and options["expiry_date"]:
                try:
                    datetime.datetime.strptime(options["expiry_date"], "%Y-%m-%d")
                except ValueError:
                    return False, "过期日期格式错误，应为YYYY-MM-DD"
            
            if "trial_period" in options and options["trial_period"]:
                try:
                    trial_period = int(options["trial_period"])
                    if trial_period <= 0:
                        return False, "试用期限应为正整数"
                except ValueError:
                    return False, "试用期限应为整数"
            
            if "max_usage_count" in options and options["max_usage_count"]:
                try:
                    max_count = int(options["max_usage_count"])
                    if max_count <= 0:
                        return False, "最大使用次数应为正整数"
                except ValueError:
                    return False, "最大使用次数应为整数"
            
            # 构建配置
            timelock_config = {
                "enabled": True,
                "version": "1.0",
                "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 添加过期日期
            if "expiry_date" in options and options["expiry_date"]:
                timelock_config["expiry_date"] = options["expiry_date"]
            
            # 添加试用期限
            if "trial_period" in options and options["trial_period"]:
                timelock_config["trial_period_days"] = int(options["trial_period"])
            
            # 添加最大使用次数
            if "max_usage_count" in options and options["max_usage_count"]:
                timelock_config["max_usage_count"] = int(options["max_usage_count"])
            
            # 添加远程控制
            if "remote_control" in options and options["remote_control"]:
                timelock_config["remote_control"] = {
                    "enabled": True,
                    "url": self.remote_url,
                    "check_interval": 86400  # 默认24小时检查一次
                }
            
            # 添加设备ID限制
            if "device_id" in options and options["device_id"]:
                timelock_config["device_restriction"] = {
                    "enabled": True,
                    "allowed_devices": [options["device_id"]]
                }
            
            return True, timelock_config
            
        except Exception as e:
            self.logger.error(f"生成时间锁配置失败: {str(e)}")
            return False, f"生成时间锁配置失败: {str(e)}"
    
    def save_timelock_config(self, config, output_path):
        """保存时间锁配置到文件
        
        Args:
            config (dict): 时间锁配置字典
            output_path (str): 输出文件路径
        
        Returns:
            bool: 是否成功
        """
        try:
            # 确保输出目录存在
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # 写入配置文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            self.logger.info(f"时间锁配置已保存到: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存时间锁配置失败: {str(e)}")
            return False
    
    def register_timelock(self, app_id, config):
        """向远程服务器注册时间锁
        
        Args:
            app_id (str): 应用ID
            config (dict): 时间锁配置
        
        Returns:
            tuple: (bool, dict|str) - (是否成功, 响应数据或错误消息)
        """
        if not self.remote_url or not self.api_key:
            return False, "远程服务器URL或API密钥未配置"
        
        try:
            # 构建请求数据
            data = {
                "app_id": app_id,
                "config": config,
                "api_key": self.api_key
            }
            
            # 发送请求
            response = requests.post(
                f"{self.remote_url}/register",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"注册失败: {response.text}"
                
        except Exception as e:
            self.logger.error(f"注册时间锁失败: {str(e)}")
            return False, f"注册时间锁失败: {str(e)}"
    
    def verify_timelock_status(self, app_id):
        """验证应用的时间锁状态
        
        Args:
            app_id (str): 应用ID
        
        Returns:
            tuple: (bool, dict|str) - (是否成功, 状态数据或错误消息)
        """
        if not self.remote_url or not self.api_key:
            return False, "远程服务器URL或API密钥未配置"
        
        try:
            # 构建请求参数
            params = {
                "app_id": app_id,
                "api_key": self.api_key
            }
            
            # 发送请求
            response = requests.get(
                f"{self.remote_url}/status",
                params=params
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"验证失败: {response.text}"
                
        except Exception as e:
            self.logger.error(f"验证时间锁状态失败: {str(e)}")
            return False, f"验证时间锁状态失败: {str(e)}"
    
    def update_timelock_status(self, app_id, status):
        """更新应用的时间锁状态
        
        Args:
            app_id (str): 应用ID
            status (dict): 新的状态数据
        
        Returns:
            tuple: (bool, dict|str) - (是否成功, 响应数据或错误消息)
        """
        if not self.remote_url or not self.api_key:
            return False, "远程服务器URL或API密钥未配置"
        
        try:
            # 构建请求数据
            data = {
                "app_id": app_id,
                "status": status,
                "api_key": self.api_key
            }
            
            # 发送请求
            response = requests.put(
                f"{self.remote_url}/status",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                return False, f"更新失败: {response.text}"
                
        except Exception as e:
            self.logger.error(f"更新时间锁状态失败: {str(e)}")
            return False, f"更新时间锁状态失败: {str(e)}" 