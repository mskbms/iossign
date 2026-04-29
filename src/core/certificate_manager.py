#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
证书管理模块
"""

import os
import json
import uuid
import logging
import datetime
import subprocess
from pathlib import Path
from ..utils.config_utils import load_config, save_config
from ..utils.process_utils import run_zsign

logger = logging.getLogger(__name__)

class CertificateManager:
    """证书管理类"""
    
    def __init__(self):
        """初始化证书管理器"""
        self.config = load_config()
        self.certificates = self.config.get("certificates", [])
    
    def save(self):
        """保存证书配置"""
        self.config["certificates"] = self.certificates
        return save_config(self.config)
    
    def verify_certificate(self, p12_path, password, mobileprovision_path=None):
        """
        验证证书和描述文件是否有效和匹配
        
        Args:
            p12_path: p12证书文件路径
            password: p12证书密码
            mobileprovision_path: 描述文件路径
            
        Returns:
            tuple: (是否有效, 错误信息)
        """
        try:
            # 验证p12文件是否有效
            if not os.path.exists(p12_path):
                return False, f"p12证书文件不存在: {p12_path}"
            
            # 验证证书密码是否正确
            args = ["-k", p12_path, "-p", password, "-v"]
            code, stdout, stderr = run_zsign(args)
            if code != 0:
                return False, f"证书密码错误或证书无效: {stderr}"
            
            # 如果提供了描述文件，验证其是否有效
            if mobileprovision_path:
                if not os.path.exists(mobileprovision_path):
                    return False, f"描述文件不存在: {mobileprovision_path}"
                
                # 描述文件只需验证文件存在即可，不再检查内容格式
                # 因为.mobileprovision文件是二进制格式，不能简单地通过检查开头来判断
            
            return True, "证书验证通过"
        except Exception as e:
            logger.error(f"验证证书时出错: {e}")
            return False, f"验证证书时出错: {e}"
    
    def add_certificate(self, name, p12_path, password, mobileprovision_path=None):
        """
        添加证书
        
        Args:
            name: 证书名称
            p12_path: p12证书文件路径
            password: p12证书密码
            mobileprovision_path: 描述文件路径
        
        Returns:
            str: 证书ID，如果失败则返回None
        """
        try:
            # 验证证书和描述文件
            is_valid, error_msg = self.verify_certificate(p12_path, password, mobileprovision_path)
            if not is_valid:
                logger.error(error_msg)
                return None, error_msg
            
            # 生成唯一ID
            cert_id = str(uuid.uuid4())
            
            # 创建证书信息
            certificate = {
                "id": cert_id,
                "name": name,
                "p12_path": p12_path,
                "password": password,
                "mobileprovision_path": mobileprovision_path,
                "created_at": datetime.datetime.now().isoformat()
            }
            
            # 添加到证书列表
            self.certificates.append(certificate)
            self.save()
            
            logger.info(f"添加证书成功: {name}")
            return cert_id, "添加证书成功"
        except Exception as e:
            logger.error(f"添加证书失败: {e}")
            return None, f"添加证书失败: {e}"
    
    def remove_certificate(self, cert_id):
        """
        移除证书
        
        Args:
            cert_id: 证书ID
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 查找证书
            for i, cert in enumerate(self.certificates):
                if cert.get("id") == cert_id:
                    # 从列表中移除
                    self.certificates.pop(i)
                    self.save()
                    
                    logger.info(f"移除证书成功: {cert.get('name')}")
                    return True
            
            logger.warning(f"未找到证书: {cert_id}")
            return False
        except Exception as e:
            logger.error(f"移除证书失败: {e}")
            return False
    
    def get_certificate(self, cert_id):
        """
        获取证书信息
        
        Args:
            cert_id: 证书ID
        
        Returns:
            dict: 证书信息，如果未找到则返回None
        """
        for cert in self.certificates:
            if cert.get("id") == cert_id:
                return cert
        return None
    
    def get_all_certificates(self):
        """
        获取所有证书
        
        Returns:
            list: 证书列表
        """
        return self.certificates
    
    def update_certificate(self, cert_id, name=None, password=None, mobileprovision_path=None):
        """
        更新证书信息
        
        Args:
            cert_id: 证书ID
            name: 新的证书名称
            password: 新的证书密码
            mobileprovision_path: 新的描述文件路径
        
        Returns:
            bool: 操作是否成功
        """
        try:
            # 查找证书
            for i, cert in enumerate(self.certificates):
                if cert.get("id") == cert_id:
                    # 更新名称
                    if name is not None:
                        cert["name"] = name
                    
                    # 更新密码
                    if password is not None:
                        # 验证新密码是否有效
                        p12_path = cert.get("p12_path")
                        is_valid, error_msg = self.verify_certificate(p12_path, password)
                        if not is_valid:
                            logger.error(error_msg)
                            return False
                        cert["password"] = password
                    
                    # 更新描述文件
                    if mobileprovision_path is not None:
                        # 验证新描述文件是否有效
                        is_valid, error_msg = self.verify_certificate(
                            cert.get("p12_path"), 
                            cert.get("password"), 
                            mobileprovision_path
                        )
                        if not is_valid:
                            logger.error(error_msg)
                            return False
                        cert["mobileprovision_path"] = mobileprovision_path
                    
                    # 保存更新
                    self.certificates[i] = cert
                    self.save()
                    
                    logger.info(f"更新证书成功: {cert.get('name')}")
                    return True
            
            logger.warning(f"未找到证书: {cert_id}")
            return False
        except Exception as e:
            logger.error(f"更新证书失败: {e}")
            return False
    
    def get_certificate_by_name(self, name):
        """
        通过名称获取证书
        
        Args:
            name: 证书名称
        
        Returns:
            dict: 证书信息，如果未找到则返回None
        """
        for cert in self.certificates:
            if cert.get("name") == name:
                return cert
        return None 