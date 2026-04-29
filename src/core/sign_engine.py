#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
签名引擎模块
"""

import os
import logging
import subprocess
import time
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import threading

from ..utils.file_utils import extract_ipa, get_app_path_in_ipa, create_ipa, restore_original_app_name, update_app_info
from ..utils.zsign_utils import ZsignWrapper
from ..utils.macho_utils import add_frameworks_rpath
from ..utils.macho_dylib_injection import inject_frameworks_to_app
from ..utils.injection_verify import print_verification_result, verify_frameworks_structure, verify_dylib_injection

logger = logging.getLogger(__name__)


def _safe_name(path):
    """仅记录文件名，避免日志泄露本机绝对路径。"""
    return os.path.basename(path) if path else ""

class SignEngine:
    """签名引擎类"""
    
    def __init__(self, certificate_manager):
        """
        初始化签名引擎
        
        Args:
            certificate_manager: 证书管理器
        """
        self.certificate_manager = certificate_manager
        self.zsign_wrapper = ZsignWrapper()
        self.progress_callback = None
        self.cancel_flag = False
        self.cancel_lock = threading.Lock()
    
    def set_progress_callback(self, callback):
        """
        设置进度回调函数
        
        Args:
            callback: 回调函数，接收进度值(0-100)和消息
        """
        self.progress_callback = callback
    
    def _update_progress(self, progress, message):
        """
        更新进度
        
        Args:
            progress: 进度值(0-100)
            message: 进度消息
        """
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    def cancel(self):
        """取消签名过程"""
        with self.cancel_lock:
            self.cancel_flag = True
    
    def _check_cancelled(self):
        """
        检查是否已取消
        
        Returns:
            bool: 是否已取消
        """
        with self.cancel_lock:
            return self.cancel_flag
    
    def _reset_cancel_flag(self):
        """重置取消标志"""
        with self.cancel_lock:
            self.cancel_flag = False
    
    def sign_ipa(self, ipa_path, cert_id, output_path=None, bundle_id=None, 
                 bundle_name=None, bundle_version=None, inject_dylibs=None,
                 time_limit=None, original_app_name=None, display_name=None,
                 version_code=None, version_name=None, inject_frameworks=None,
                 extract_dir=None, app_path=None):
        """
        签名IPA文件
        
        Args:
            ipa_path: IPA文件路径
            cert_id: 证书ID
            output_path: 输出文件路径，如果为None则自动生成
            bundle_id: 新的Bundle ID，如果为None则保持不变
            bundle_name: 新的应用名称，如果为None则保持不变
            bundle_version: 新的版本号，如果为None则保持不变
            inject_dylibs: 注入的动态库路径列表，如果为None则不注入
            time_limit: 有效期限制（天数），如果为None则不限制
            original_app_name: 原始应用名称，如果为None则不恢复
            display_name: 显示名称，如果为None则保持不变
            version_code: 版本代码，如果为None则保持不变
            version_name: 版本名称，如果为None则保持不变
            inject_frameworks: 要注入的Framework列表，默认为None
            extract_dir: 已解压的目录路径，如果提供则跳过解压步骤
            app_path: 已解压的.app路径，如果提供则跳过获取路径步骤
        
        Returns:
            str: 签名后的IPA文件路径，如果失败则返回None
        """
        # 重置取消标志
        self._reset_cancel_flag()
        
        # 获取证书信息
        certificate = self.certificate_manager.get_certificate(cert_id)
        if not certificate:
            logger.error(f"找不到证书: {cert_id}")
            self._update_progress(0, f"找不到证书: {cert_id}")
            return None
        
        # 尝试多种可能的键名获取证书密码
        p12_path = certificate.get("p12_path", "")
        # 尝试多种可能的键名获取密码
        p12_password = certificate.get("password", "")
        if not p12_password:
            p12_password = certificate.get("p12_password", "")
            if not p12_password:
                p12_password = certificate.get("cert_password", "")
                
        mobileprovision_path = certificate.get("mobileprovision_path", "")
        
        # 详细记录证书信息（注意不记录密码）
        logger.debug(f"证书ID: {cert_id}")
        logger.debug(f"证书文件: {_safe_name(p12_path)}")
        logger.debug(f"密码是否为空: {not p12_password}")
        logger.debug(f"描述文件: {_safe_name(mobileprovision_path)}")
        logger.debug(f"证书对象键: {list(certificate.keys())}")
        
        # 详细检查证书文件
        if not p12_path:
            logger.error("证书路径为空")
            self._update_progress(0, "证书路径为空")
            return None
            
        if not os.path.exists(p12_path):
            logger.error(f"证书文件不存在: {_safe_name(p12_path)}")
            self._update_progress(0, "证书文件不存在")
            return None
            
        if not os.path.isfile(p12_path):
            logger.error(f"证书路径不是文件: {_safe_name(p12_path)}")
            self._update_progress(0, "证书路径不是文件")
            return None
            
        # 检查证书文件大小
        try:
            cert_size = os.path.getsize(p12_path)
            if cert_size == 0:
                logger.error(f"证书文件为空: {_safe_name(p12_path)}")
                self._update_progress(0, "证书文件为空")
                return None
            logger.debug(f"证书文件大小: {cert_size} 字节")
        except Exception as e:
            logger.error(f"检查证书文件失败: {e}")
        
        # 检查描述文件
        if mobileprovision_path:
            if not os.path.exists(mobileprovision_path):
                logger.error(f"描述文件不存在: {_safe_name(mobileprovision_path)}")
                self._update_progress(0, "描述文件不存在")
                return None
            
            if not os.path.isfile(mobileprovision_path):
                logger.error(f"描述文件路径不是文件: {_safe_name(mobileprovision_path)}")
                self._update_progress(0, "描述文件路径不是文件")
                return None
        else:
            logger.warning("未指定描述文件，将使用默认签名")
        
        # 临时变量用于跟踪解压目录
        temp_extract_dir = None
        try:
            # 检查是否已取消
            if self._check_cancelled():
                logger.info("签名过程已取消")
                return None
            
            # 解压IPA文件（如果还没有解压的话）
            if extract_dir and app_path:
                # 使用已提供的解压路径
                logger.info(f"使用已解压的路径: {extract_dir}")
                logger.info(f"使用已解压的应用路径: {app_path}")
                self._update_progress(20, "使用已解压的文件...")
                
                # 验证路径是否有效
                if not os.path.exists(extract_dir) or not os.path.exists(app_path):
                    logger.warning("提供的解压路径无效，重新解压...")
                    extract_dir = None
                    app_path = None
            
            if not extract_dir or not app_path:
                # 需要重新解压
                self._update_progress(10, "正在解压IPA文件...")
                temp_extract_dir, original_app_name = extract_ipa(ipa_path)
                if not temp_extract_dir:
                    logger.error("解压IPA文件失败")
                    self._update_progress(0, "解压IPA文件失败")
                    return None
                
                extract_dir = temp_extract_dir  # 更新extract_dir
                
                # 检查是否已取消
                if self._check_cancelled():
                    logger.info("签名过程已取消")
                    return None
                
                # 获取.app路径
                self._update_progress(20, "正在获取应用信息...")
                app_path = get_app_path_in_ipa(extract_dir)
                if not app_path:
                    logger.error("找不到.app目录")
                    self._update_progress(0, "找不到.app目录")
                    return None
            
            # 检查是否已取消
            if self._check_cancelled():
                logger.info("签名过程已取消")
                return None
            
            # 签名前同步Info.plist（仅在有实际修改时）
            has_info_changes = bool(bundle_id or display_name is not None or bundle_name or version_code or version_name)
            if has_info_changes:
                logger.info("检测到Info.plist修改选项，正在更新...")
                update_app_info(
                    app_path,
                    bundle_id=bundle_id,
                    display_name=display_name,
                    bundle_name=bundle_name,
                    version_code=version_code,
                    version_name=version_name
                )
            else:
                logger.info("未检测到Info.plist修改选项，保持原始设置")
            
            # 复制框架到Frameworks目录
            if inject_frameworks:
                self._update_progress(25, "正在复制Framework...")
                frameworks_dir = os.path.join(app_path, "Frameworks")
                
                # 确保Frameworks目录存在
                if not os.path.exists(frameworks_dir):
                    os.makedirs(frameworks_dir)
                    logger.info(f"创建Frameworks目录: {frameworks_dir}")
                
                # 准备框架主二进制文件列表，用于后续注入
                framework_dylibs = []
                
                for framework_info in inject_frameworks:
                    framework_dir = framework_info["framework_dir"]
                    framework_name = framework_info["framework_name"]
                    binary_path = framework_info["binary_path"]
                    
                    if os.path.exists(framework_dir):
                        target_framework_dir = os.path.join(frameworks_dir, framework_name)
                        
                        # 如果目标目录已存在，先删除
                        if os.path.exists(target_framework_dir):
                            shutil.rmtree(target_framework_dir)
                            logger.info(f"删除已存在的Framework: {target_framework_dir}")
                        
                        # 复制框架目录
                        shutil.copytree(framework_dir, target_framework_dir)
                        logger.info(f"已复制Framework: {framework_name} -> {target_framework_dir}")
                        
                        # 添加框架主二进制文件到注入列表（使用iOS标准的install name）
                        framework_binary_name = framework_name.replace('.framework', '')
                        target_framework_binary = os.path.join(target_framework_dir, framework_binary_name)
                        
                        # 检查复制后的二进制文件是否存在
                        if os.path.exists(target_framework_binary):
                            # 直接使用正确的install name，而不是文件路径
                            framework_install_name = f"@executable_path/Frameworks/{framework_name}/{framework_binary_name}"
                            framework_dylibs.append(framework_install_name)
                            logger.info(f"准备注入Framework (install name): {framework_install_name}")
                            logger.info(f"Framework二进制文件存在: {target_framework_binary}")
                        else:
                            logger.error(f"复制后的Framework二进制文件不存在: {target_framework_binary}")
                            logger.warning(f"跳过Framework注入: {framework_name}")
                    else:
                        logger.warning(f"Framework目录不存在: {framework_dir}")
                
                # 添加RPATH到主二进制文件（iOS必需）
                if framework_dylibs:
                    logger.info("正在添加Frameworks RPATH...")
                    rpath_success = add_frameworks_rpath(app_path)
                    if rpath_success:
                        logger.info("成功添加Frameworks RPATH")
                    else:
                        logger.warning("添加Frameworks RPATH失败，但将继续处理")
                    
                    # 使用纯Python方法注入Framework动态库
                    logger.info("正在注入Framework动态库...")
                    injection_success = inject_frameworks_to_app(app_path, framework_dylibs)
                    if injection_success:
                        logger.info(f"成功注入 {len(framework_dylibs)} 个Framework动态库")
                    else:
                        logger.error("Framework动态库注入失败")
                        # 不返回错误，继续签名过程
                    
                    # 不再将Framework添加到zsign的dylib参数中，因为我们已经直接注入了
                    # 保持原有的inject_dylibs不变
                        
                # 检查是否已取消
                if self._check_cancelled():
                    logger.info("签名过程已取消")
                    return None
            
            # 处理传统动态库注入（在签名前进行）
            if inject_dylibs:
                self._update_progress(28, "正在注入传统动态库...")
                logger.info(f"开始注入 {len(inject_dylibs)} 个传统动态库")
                
                # 转换dylib路径为install name格式
                dylib_install_names = []
                for dylib_path in inject_dylibs:
                    # 检查dylib文件是否存在
                    if not os.path.exists(dylib_path):
                        logger.warning(f"动态库文件不存在，跳过: {dylib_path}")
                        continue
                    
                    # 复制dylib到Frameworks目录
                    frameworks_dir = os.path.join(app_path, "Frameworks")
                    if not os.path.exists(frameworks_dir):
                        os.makedirs(frameworks_dir)
                        logger.info(f"创建Frameworks目录: {frameworks_dir}")
                    
                    dylib_name = os.path.basename(dylib_path)
                    target_dylib_path = os.path.join(frameworks_dir, dylib_name)
                    
                    # 复制dylib文件
                    try:
                        import shutil
                        shutil.copy2(dylib_path, target_dylib_path)
                        logger.info(f"已复制动态库: {dylib_name} -> {target_dylib_path}")
                        
                        # 生成install name
                        install_name = f"@executable_path/Frameworks/{dylib_name}"
                        dylib_install_names.append(install_name)
                        logger.info(f"准备注入动态库 (install name): {install_name}")
                    except Exception as e:
                        logger.error(f"复制动态库失败: {dylib_path}, 错误: {e}")
                        continue
                
                # 注入动态库到MachO文件
                if dylib_install_names:
                    logger.info("正在注入传统动态库到MachO文件...")
                    injection_success = inject_frameworks_to_app(app_path, dylib_install_names)
                    if injection_success:
                        logger.info(f"成功注入 {len(dylib_install_names)} 个传统动态库")
                    else:
                        logger.error("传统动态库注入失败")
                        # 不返回错误，继续签名过程
                else:
                    logger.warning("没有有效的传统动态库需要注入")
                
                # 检查是否已取消
                if self._check_cancelled():
                    logger.info("签名过程已取消")
                    return None
            
            # 设置zsign参数
            self._update_progress(30, "准备签名...")
            zsign_params = {
                "p12": p12_path,
                "password": p12_password,
                "app": app_path,
                "output": None,  # 不输出IPA，我们将自己创建
                "force": True,   # 强制签名
                "deep": True,    # 深度签名
                "no_verify": False  # 启用验证
            }
            
            # 添加可选参数
            if mobileprovision_path:
                zsign_params["prov"] = mobileprovision_path
            
            if bundle_id:
                zsign_params["bundle_id"] = bundle_id
            
            if bundle_name:
                zsign_params["bundle_name"] = bundle_name
            
            if bundle_version:
                zsign_params["bundle_version"] = bundle_version
            
            if time_limit:
                zsign_params["time_limit"] = time_limit
            
            # 注入动态库
            if inject_dylibs:
                zsign_params["dylibs"] = inject_dylibs
            
            # 检查是否已取消
            if self._check_cancelled():
                logger.info("签名过程已取消")
                return None
            
            # 执行签名
            self._update_progress(40, "正在签名应用...")
            logger.info(f"开始签名应用: {app_path}")
            logger.info(f"使用证书: {_safe_name(p12_path)}")
            logger.info(f"使用描述文件: {_safe_name(mobileprovision_path)}")
            
            success = self.zsign_wrapper.sign(**zsign_params)
            
            # 如果首次签名失败，尝试使用不同参数再次签名
            if not success:
                logger.warning("首次签名失败，尝试使用备用参数...")
                self._update_progress(50, "首次签名失败，尝试使用备用参数...")
                
                # 检查是否已取消
                if self._check_cancelled():
                    logger.info("签名过程已取消")
                    return None
                
                # 第二次尝试：强制深度签名，但不跳过验证（避免-s参数冲突）
                if "prov" in zsign_params:
                    logger.info("尝试使用描述文件进行签名")
                    zsign_params["force"] = True
                    zsign_params["deep"] = True
                    zsign_params["no_verify"] = True  # 第二次尝试跳过验证
                    success = self.zsign_wrapper.sign(**zsign_params)
                
                # 如果还是失败，尝试ad-hoc签名
                if not success:
                    logger.warning("第二次签名失败，尝试ad-hoc签名...")
                    self._update_progress(55, "尝试ad-hoc签名...")
                    
                    # 检查是否已取消
                    if self._check_cancelled():
                        logger.info("签名过程已取消")
                        return None
                    
                    # 最后的尝试 - 只使用证书进行ad-hoc签名
                    zsign_params.pop("prov", None)  # 移除描述文件
                    zsign_params["force"] = True
                    zsign_params["deep"] = False
                    zsign_params["no_verify"] = False  # 恢复验证
                    logger.info("尝试仅使用证书进行ad-hoc签名")
                    success = self.zsign_wrapper.sign(**zsign_params)
            
            if not success:
                logger.error("签名应用失败，已尝试所有可能的签名方法")
                self._update_progress(0, "签名应用失败，请确保证书和描述文件有效")
                return None
            
            logger.info("应用签名成功")
            
            # 验证传统dylib注入（如果有的话）
            if inject_dylibs:
                logger.info("正在验证传统动态库注入...")
                
                # 验证注入结果
                verification_result = verify_dylib_injection(app_path, dylib_install_names if 'dylib_install_names' in locals() else [])
                if verification_result["success"]:
                    logger.info("传统动态库注入验证成功")
                    if verification_result["found_dylibs"]:
                        for dylib in verification_result["found_dylibs"]:
                            logger.info(f"  ✅ 验证成功: {dylib}")
                else:
                    logger.warning("传统动态库注入验证失败")
                    if verification_result["missing_dylibs"]:
                        for dylib in verification_result["missing_dylibs"]:
                            logger.warning(f"  ❌ 验证失败: {dylib}")
            
            # 验证Framework结构（如果有framework的话）
            if inject_frameworks:
                logger.info("正在验证Framework结构...")
                framework_verification = verify_frameworks_structure(app_path, inject_frameworks)
                if framework_verification["success"]:
                    logger.info("Framework结构验证成功")
                else:
                    logger.warning("Framework结构验证失败")
                    logger.warning(f"缺失的Framework: {framework_verification['missing_frameworks']}")
            
            # 检查是否已取消
            if self._check_cancelled():
                logger.info("签名过程已取消")
                return None
            
            # 生成输出路径
            if not output_path:
                output_dir = os.path.dirname(ipa_path)
                filename = os.path.basename(ipa_path)
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                output_path = os.path.join(output_dir, f"{name}_signed_{timestamp}{ext}")
            
            # 创建IPA文件
            self._update_progress(70, "正在打包IPA文件...")
            if not create_ipa(app_path, output_path):
                logger.error("创建IPA文件失败")
                self._update_progress(0, "创建IPA文件失败")
                return None
            
            # 检查是否已取消
            if self._check_cancelled():
                logger.info("签名过程已取消")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return None
            
            # 验证签名结果
            self._update_progress(80, "正在验证签名...")
            verification_result = self.zsign_wrapper.verify(app_path)
            if not verification_result:
                logger.warning("签名验证失败，但仍将继续处理")
                self._update_progress(85, "签名验证失败，但仍将继续处理")
                
                # 尝试手动检查签名文件是否存在
                signature_path = os.path.join(app_path, "_CodeSignature", "CodeResources")
                provision_path = os.path.join(app_path, "embedded.mobileprovision")
                
                if os.path.exists(signature_path):
                    logger.info(f"签名文件存在: {signature_path}")
                else:
                    logger.error(f"签名文件不存在: {signature_path}")
                
                if os.path.exists(provision_path):
                    logger.info(f"描述文件存在: {provision_path}")
                    # 检查描述文件大小
                    try:
                        size = os.path.getsize(provision_path)
                        logger.info(f"描述文件大小: {size} 字节")
                    except Exception as e:
                        logger.warning(f"获取描述文件大小失败: {e}")
                else:
                    logger.error(f"描述文件不存在: {provision_path}")
            else:
                logger.info("签名验证成功")
                self._update_progress(85, "签名验证成功")
            
            # 恢复原始应用名称（如果需要）
            self._update_progress(90, "正在恢复原始应用名称...")
            restored_path = restore_original_app_name(extract_dir, output_path, original_app_name)
            
            self._update_progress(100, "签名完成")
            logger.info(f"IPA文件签名成功: {restored_path}")
            
            return restored_path
        
        except Exception as e:
            logger.exception(f"签名过程出错: {e}")
            self._update_progress(0, f"签名过程出错: {str(e)}")
            return None
        
        finally:
            # 清理临时文件
            try:
                if extract_dir and os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
                    logger.debug(f"清理临时目录: {extract_dir}")
                
                # 清理unzip目录中超过1小时未修改的文件夹
                current_dir = os.path.dirname(os.path.abspath(__file__))
                base_dir = os.path.dirname(os.path.dirname(current_dir))  # 获取项目根目录
                unzip_dir = os.path.join(base_dir, "unzip")
                
                if os.path.exists(unzip_dir):
                    now = datetime.now()
                    for item in os.listdir(unzip_dir):
                        item_path = os.path.join(unzip_dir, item)
                        if os.path.isdir(item_path):
                            # 获取文件夹的最后修改时间
                            mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                            # 如果超过1小时未修改，则删除
                            if now - mtime > timedelta(hours=1):
                                try:
                                    shutil.rmtree(item_path)
                                    logger.debug(f"清理过期临时目录: {item_path}")
                                except Exception as e:
                                    logger.warning(f"清理临时目录失败: {e}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}") 