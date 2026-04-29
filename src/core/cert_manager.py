#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil
import logging
import subprocess
import tempfile
import datetime
import plistlib
from pathlib import Path
from Crypto.PublicKey import RSA
from Crypto.Util.asn1 import DerSequence
import binascii


class CertManager:
    """证书管理模块，负责证书和描述文件的管理"""
    
    def __init__(self, config):
        """初始化证书管理器
        
        Args:
            config (dict): 应用配置字典
        """
        self.logger = logging.getLogger("CertManager")
        self.config = config
        self.cert_dir = config["certificates"]["cert_dir"]
        
        # 确保证书目录存在
        os.makedirs(self.cert_dir, exist_ok=True)
        os.makedirs(os.path.join(self.cert_dir, "certs"), exist_ok=True)
        os.makedirs(os.path.join(self.cert_dir, "provisions"), exist_ok=True)
    
    def import_certificate(self, cert_path, password=None, new_name=None):
        """导入证书
        
        Args:
            cert_path (str): 证书(.p12)文件路径
            password (str, optional): 证书密码
            new_name (str, optional): 新的证书名称
        
        Returns:
            tuple: (bool, str) - (是否成功, 导入后的路径或错误消息)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(cert_path):
                return False, f"证书文件不存在: {cert_path}"
            
            # 验证证书格式
            if not cert_path.lower().endswith('.p12'):
                return False, "证书文件必须是.p12格式"
            
            # 获取证书信息
            cert_info = self.get_certificate_info(cert_path, password)
            if not cert_info:
                return False, "无法读取证书信息，请检查证书格式和密码"
            
            # 确定保存路径
            if new_name:
                cert_name = f"{new_name}.p12"
            else:
                cert_name = os.path.basename(cert_path)
            
            target_path = os.path.join(self.cert_dir, "certs", cert_name)
            
            # 复制证书文件
            shutil.copy2(cert_path, target_path)
            
            # 保存证书信息
            info_path = os.path.join(self.cert_dir, "certs", f"{os.path.splitext(cert_name)[0]}.info")
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(f"Name: {cert_info.get('name', 'Unknown')}\n")
                f.write(f"Subject: {cert_info.get('subject', 'Unknown')}\n")
                f.write(f"Issuer: {cert_info.get('issuer', 'Unknown')}\n")
                f.write(f"Valid From: {cert_info.get('valid_from', 'Unknown')}\n")
                f.write(f"Valid To: {cert_info.get('valid_to', 'Unknown')}\n")
                f.write(f"Serial: {cert_info.get('serial', 'Unknown')}\n")
                if password:
                    f.write(f"Password: {password}\n")
            
            self.logger.info(f"证书已导入: {target_path}")
            return True, target_path
            
        except Exception as e:
            self.logger.error(f"导入证书失败: {str(e)}")
            return False, f"导入证书失败: {str(e)}"
    
    def import_provision(self, provision_path, new_name=None):
        """导入描述文件
        
        Args:
            provision_path (str): 描述文件(.mobileprovision)路径
            new_name (str, optional): 新的描述文件名称
        
        Returns:
            tuple: (bool, str) - (是否成功, 导入后的路径或错误消息)
        """
        try:
            # 检查文件是否存在
            if not os.path.exists(provision_path):
                return False, f"描述文件不存在: {provision_path}"
            
            # 验证描述文件格式
            if not provision_path.lower().endswith('.mobileprovision'):
                return False, "描述文件必须是.mobileprovision格式"
            
            # 获取描述文件信息
            provision_info = self.get_provision_info(provision_path)
            if not provision_info:
                return False, "无法读取描述文件信息，请检查文件格式"
            
            # 确定保存路径
            if new_name:
                provision_name = f"{new_name}.mobileprovision"
            else:
                provision_name = os.path.basename(provision_path)
            
            target_path = os.path.join(self.cert_dir, "provisions", provision_name)
            
            # 复制描述文件
            shutil.copy2(provision_path, target_path)
            
            # 保存描述文件信息
            info_path = os.path.join(self.cert_dir, "provisions", f"{os.path.splitext(provision_name)[0]}.info")
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(f"Name: {provision_info.get('name', 'Unknown')}\n")
                f.write(f"UUID: {provision_info.get('uuid', 'Unknown')}\n")
                f.write(f"Team ID: {provision_info.get('team_id', 'Unknown')}\n")
                f.write(f"App ID: {provision_info.get('app_id', 'Unknown')}\n")
                f.write(f"Creation Date: {provision_info.get('creation_date', 'Unknown')}\n")
                f.write(f"Expiration Date: {provision_info.get('expiration_date', 'Unknown')}\n")
                f.write(f"Entitlements: {provision_info.get('entitlements', {})}\n")
            
            self.logger.info(f"描述文件已导入: {target_path}")
            return True, target_path
            
        except Exception as e:
            self.logger.error(f"导入描述文件失败: {str(e)}")
            return False, f"导入描述文件失败: {str(e)}"
    
    def get_certificate_info(self, cert_path, password=None):
        """获取证书信息
        
        Args:
            cert_path (str): 证书(.p12)文件路径
            password (str, optional): 证书密码
        
        Returns:
            dict: 证书信息字典，如果失败则返回None
        """
        try:
            # 使用openssl命令获取证书信息
            with tempfile.NamedTemporaryFile(suffix='.pem', delete=False) as temp:
                temp_path = temp.name
            
            # 转换p12为pem格式
            cmd = ["openssl", "pkcs12", "-in", cert_path, "-out", temp_path, "-nodes"]
            if password:
                cmd.extend(["-passin", f"pass:{password}"])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"证书转换失败: {result.stderr}")
                os.unlink(temp_path)
                return None
            
            # 读取pem文件获取信息
            cmd = ["openssl", "x509", "-in", temp_path, "-text", "-noout"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"读取证书信息失败: {result.stderr}")
                os.unlink(temp_path)
                return None
            
            # 解析证书信息
            cert_info = {}
            output = result.stdout
            
            # 提取主题
            subject_match = re.search(r"Subject:.*?CN\s*=\s*([^\n,]+)", output, re.DOTALL)
            if subject_match:
                cert_info["name"] = subject_match.group(1).strip()
                cert_info["subject"] = subject_match.group(0).strip()
            
            # 提取颁发者
            issuer_match = re.search(r"Issuer:.*", output)
            if issuer_match:
                cert_info["issuer"] = issuer_match.group(0).strip()
            
            # 提取有效期
            validity_match = re.search(r"Not Before:\s*(.*?)\s*Not After\s*:\s*(.*?)$", output, re.MULTILINE)
            if validity_match:
                cert_info["valid_from"] = validity_match.group(1).strip()
                cert_info["valid_to"] = validity_match.group(2).strip()
            
            # 提取序列号
            serial_match = re.search(r"Serial Number:.*?([\da-fA-F:]+)", output)
            if serial_match:
                cert_info["serial"] = serial_match.group(1).strip()
            
            # 清理临时文件
            os.unlink(temp_path)
            
            return cert_info
            
        except Exception as e:
            self.logger.error(f"获取证书信息失败: {str(e)}")
            return None
    
    def get_provision_info(self, provision_path):
        """获取描述文件信息
        
        Args:
            provision_path (str): 描述文件(.mobileprovision)路径
        
        Returns:
            dict: 描述文件信息字典，如果失败则返回None
        """
        try:
            # 使用临时文件
            with tempfile.NamedTemporaryFile(suffix='.plist', delete=False) as temp:
                temp_path = temp.name
            
            # 提取plist数据
            cmd = ["security", "cms", "-D", "-i", provision_path, "-o", temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                self.logger.error(f"提取描述文件信息失败: {result.stderr}")
                os.unlink(temp_path)
                return None
            
            # 读取plist文件
            with open(temp_path, 'rb') as f:
                plist_data = plistlib.load(f)
            
            # 解析描述文件信息
            provision_info = {}
            
            # 名称
            if 'Name' in plist_data:
                provision_info["name"] = plist_data['Name']
            
            # UUID
            if 'UUID' in plist_data:
                provision_info["uuid"] = plist_data['UUID']
            
            # 团队ID
            if 'TeamIdentifier' in plist_data:
                provision_info["team_id"] = plist_data['TeamIdentifier'][0]
            
            # 应用ID
            if 'AppIDName' in plist_data:
                provision_info["app_id"] = plist_data['AppIDName']
            
            # 创建日期
            if 'CreationDate' in plist_data:
                provision_info["creation_date"] = plist_data['CreationDate'].strftime("%Y-%m-%d %H:%M:%S")
            
            # 过期日期
            if 'ExpirationDate' in plist_data:
                provision_info["expiration_date"] = plist_data['ExpirationDate'].strftime("%Y-%m-%d %H:%M:%S")
            
            # Entitlements
            if 'Entitlements' in plist_data:
                provision_info["entitlements"] = plist_data['Entitlements']
            
            # 清理临时文件
            os.unlink(temp_path)
            
            return provision_info
            
        except Exception as e:
            self.logger.error(f"获取描述文件信息失败: {str(e)}")
            return None
    
    def list_certificates(self):
        """列出所有已导入的证书
        
        Returns:
            list: 证书信息列表
        """
        try:
            certs_dir = os.path.join(self.cert_dir, "certs")
            if not os.path.exists(certs_dir):
                return []
            
            certs = []
            for file in os.listdir(certs_dir):
                if file.lower().endswith('.p12'):
                    cert_path = os.path.join(certs_dir, file)
                    info_path = os.path.join(certs_dir, f"{os.path.splitext(file)[0]}.info")
                    
                    cert_info = {
                        "name": os.path.splitext(file)[0],
                        "path": cert_path
                    }
                    
                    # 读取证书信息文件
                    if os.path.exists(info_path):
                        with open(info_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    cert_info[key.strip().lower()] = value.strip()
                    
                    certs.append(cert_info)
            
            return certs
            
        except Exception as e:
            self.logger.error(f"列出证书失败: {str(e)}")
            return []
    
    def list_provisions(self):
        """列出所有已导入的描述文件
        
        Returns:
            list: 描述文件信息列表
        """
        try:
            provisions_dir = os.path.join(self.cert_dir, "provisions")
            if not os.path.exists(provisions_dir):
                return []
            
            provisions = []
            for file in os.listdir(provisions_dir):
                if file.lower().endswith('.mobileprovision'):
                    provision_path = os.path.join(provisions_dir, file)
                    info_path = os.path.join(provisions_dir, f"{os.path.splitext(file)[0]}.info")
                    
                    provision_info = {
                        "name": os.path.splitext(file)[0],
                        "path": provision_path
                    }
                    
                    # 读取描述文件信息文件
                    if os.path.exists(info_path):
                        with open(info_path, 'r', encoding='utf-8') as f:
                            for line in f:
                                if ':' in line:
                                    key, value = line.split(':', 1)
                                    provision_info[key.strip().lower()] = value.strip()
                    
                    provisions.append(provision_info)
            
            return provisions
            
        except Exception as e:
            self.logger.error(f"列出描述文件失败: {str(e)}")
            return []
    
    def delete_certificate(self, cert_path):
        """删除证书
        
        Args:
            cert_path (str): 证书路径
        
        Returns:
            bool: 是否成功
        """
        try:
            if not os.path.exists(cert_path):
                return False
            
            # 删除证书文件
            os.remove(cert_path)
            
            # 删除信息文件
            info_path = f"{os.path.splitext(cert_path)[0]}.info"
            if os.path.exists(info_path):
                os.remove(info_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"删除证书失败: {str(e)}")
            return False
    
    def delete_provision(self, provision_path):
        """删除描述文件
        
        Args:
            provision_path (str): 描述文件路径
        
        Returns:
            bool: 是否成功
        """
        try:
            if not os.path.exists(provision_path):
                return False
            
            # 删除描述文件
            os.remove(provision_path)
            
            # 删除信息文件
            info_path = f"{os.path.splitext(provision_path)[0]}.info"
            if os.path.exists(info_path):
                os.remove(info_path)
            
            return True
            
        except Exception as e:
            self.logger.error(f"删除描述文件失败: {str(e)}")
            return False 