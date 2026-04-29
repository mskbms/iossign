#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
zsign工具封装模块
"""

import os
import logging
import subprocess
import platform

logger = logging.getLogger(__name__)


def _safe_name(path):
    """仅记录文件名，避免日志泄露本机绝对路径。"""
    return os.path.basename(path) if path else ""

class ZsignWrapper:
    """zsign工具封装类"""
    
    def __init__(self):
        """初始化zsign封装类"""
        self.zsign_path = self._get_zsign_path()
    
    def _get_zsign_path(self):
        """
        获取zsign工具路径
        
        Returns:
            str: zsign工具路径
        """
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # 根据平台获取zsign路径
        system = platform.system()
        if system == "Windows":
            zsign_path = os.path.join(current_dir, "tools", "zsign", "zsign.exe")
        elif system == "Darwin":  # macOS
            zsign_path = os.path.join(current_dir, "tools", "zsign", "zsign")
        else:  # Linux
            zsign_path = os.path.join(current_dir, "tools", "zsign", "zsign")
        
        # 检查zsign是否存在
        if not os.path.exists(zsign_path):
            logger.warning(f"zsign工具不存在: {zsign_path}")
            return None
        
        return zsign_path
    
    def sign(self, p12, password, app, output=None, prov=None, bundle_id=None, 
             bundle_name=None, bundle_version=None, dylibs=None, time_limit=None,
             force=False, deep=False, no_verify=False):
        """
        使用zsign签名应用
        
        Args:
            p12: p12证书文件路径
            password: p12证书密码
            app: 应用目录路径
            output: 输出IPA文件路径，如果为None则不输出IPA
            prov: 描述文件路径
            bundle_id: 新的Bundle ID
            bundle_name: 新的应用名称
            bundle_version: 新的版本号
            dylibs: 要注入的动态库路径列表
            time_limit: 有效期限制（天数）
            force: 是否强制签名
            deep: 是否深度签名
            no_verify: 是否跳过验证
        
        Returns:
            bool: 签名是否成功
        """
        if not self.zsign_path:
            logger.error("zsign工具不可用")
            return False
        
        # 检查证书文件是否存在
        if not p12:
            logger.error("证书路径为空")
            return False
            
        if not os.path.exists(p12):
            logger.error(f"证书文件不存在: {_safe_name(p12)}")
            return False
            
        # 检查证书文件大小
        try:
            cert_size = os.path.getsize(p12)
            if cert_size == 0:
                logger.error(f"证书文件为空: {_safe_name(p12)}")
                return False
            logger.debug(f"证书文件大小: {cert_size} 字节")
        except Exception as e:
            logger.error(f"检查证书文件失败: {e}")
            
        # 检查密码是否为空
        if not password:
            logger.error("证书密码为空")
            return False
            
        # 检查应用目录是否存在
        if not os.path.exists(app):
            logger.error(f"应用目录不存在: {_safe_name(app)}")
            return False
            
        # 检查描述文件是否存在
        if prov and not os.path.exists(prov):
            logger.error(f"描述文件不存在: {_safe_name(prov)}")
            return False
        
        # 构建zsign命令参数
        args = [
            self.zsign_path,
            "-k", f'"{p12}"',  # 使用引号包围路径
            "-p", password
        ]
        
        # 添加输出参数
        if output:
            args.extend(["-o", f'"{output}"'])  # 使用引号包围路径
        
        # 添加描述文件参数
        if prov:
            args.extend(["-m", f'"{prov}"'])  # 使用引号包围路径
        else:
            # 如果没有提供描述文件，使用ad-hoc签名
            args.append("-a")
            logger.warning("未提供描述文件，将使用ad-hoc签名")
        
        # 添加Bundle ID参数
        if bundle_id:
            args.extend(["-b", bundle_id])
        
        # 添加应用名称参数
        if bundle_name:
            args.extend(["-n", bundle_name])
        
        # 添加版本号参数
        if bundle_version:
            args.extend(["-r", bundle_version])
        
        # 注意：zsign没有时间限制参数，time_limit参数被忽略
        if time_limit:
            logger.warning(f"zsign不支持时间限制参数，忽略time_limit: {time_limit}")
        
        # 添加强制签名参数
        if force:
            args.append("-f")
        
        # 添加深度签名参数（对应entitlements参数）
        if deep:
            args.append("-e")
        
        # 添加跳过验证参数
        if no_verify:
            args.append("-s")
        
        # 添加SHA256签名参数（iOS 13+必需）
        args.extend(["-z", "9"])  # 强制使用SHA256签名算法
        
        # 注意：dylib注入现在使用纯Python方式直接处理，不再通过zsign的-l参数
        if dylibs:
            logger.warning(f"忽略dylib参数，已通过纯Python方式直接注入: {len(dylibs)} 个动态库")
        
        # 添加输入文件参数 - 使用引号包围路径
        args.append(f'"{app}"')
        
        # 记录详细的命令信息（注意移除密码）
        log_args = args.copy()
        if "-p" in log_args:
            p_index = log_args.index("-p")
            if p_index + 1 < len(log_args):
                log_args[p_index + 1] = "******"
        logger.info(f"执行签名命令: {' '.join(log_args)}")
        
        # 创建静默模式的subprocess参数
        creation_flags = 0
        if platform.system() == "Windows":
            creation_flags = 0x08000000  # CREATE_NO_WINDOW
        
        try:
            # 在Windows上使用shell=True来正确处理引号路径
            use_shell = platform.system() == "Windows"
            
            # 执行zsign命令
            process = subprocess.Popen(
                args if not use_shell else ' '.join(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=use_shell,
                creationflags=creation_flags
            )
            
            stdout, stderr = process.communicate()
            
            # 详细记录命令执行结果
            logger.info(f"zsign命令返回码: {process.returncode}")
            if stdout:
                logger.info(f"zsign标准输出: {stdout}")
            if stderr:
                logger.info(f"zsign标准错误: {stderr}")
            
            if process.returncode != 0:
                logger.error(f"zsign执行失败: {stderr or stdout}")
                
                # 尝试分析错误原因
                if "cannot parse p12 file" in (stderr or stdout or ""):
                    logger.error("证书文件格式错误或密码不正确")
                elif "cannot find private key" in (stderr or stdout or ""):
                    logger.error("证书中找不到私钥")
                elif "mobileprovision" in (stderr or stdout or "") and "not valid" in (stderr or stdout or ""):
                    logger.error("描述文件无效")
                elif "failed to parse" in (stderr or stdout or ""):
                    logger.error("解析证书或描述文件失败")
                
                return False
            
            logger.info("zsign执行成功")
            
            # 验证签名结果
            if os.path.exists(app):
                # 检查_CodeSignature目录是否存在
                code_signature_dir = os.path.join(app, "_CodeSignature")
                if os.path.exists(code_signature_dir):
                    logger.info(f"签名目录存在: {code_signature_dir}")
                    
                    # 检查CodeResources文件是否存在
                    code_resources_path = os.path.join(code_signature_dir, "CodeResources")
                    if os.path.exists(code_resources_path):
                        logger.info(f"CodeResources文件存在: {code_resources_path}")
                    else:
                        logger.warning(f"CodeResources文件不存在: {code_resources_path}")
                else:
                    logger.warning(f"签名目录不存在: {code_signature_dir}")
                
                # 检查embedded.mobileprovision文件
                entitlements_path = os.path.join(app, "embedded.mobileprovision")
                if not os.path.exists(entitlements_path) and prov:
                    logger.warning("签名后未找到embedded.mobileprovision文件，可能签名不完整")
                elif os.path.exists(entitlements_path):
                    logger.info(f"描述文件已嵌入: {entitlements_path}")
                
                # 检查Info.plist中的签名信息
                info_plist_path = os.path.join(app, "Info.plist")
                if os.path.exists(info_plist_path):
                    logger.debug(f"签名后的Info.plist存在: {info_plist_path}")
                else:
                    logger.warning(f"签名后未找到Info.plist文件: {info_plist_path}")
            
            return True
            
        except Exception as e:
            logger.exception(f"执行zsign命令出错: {e}")
            return False
    
    def verify(self, app_path):
        """
        验证应用签名
        
        Args:
            app_path: 应用路径
        
        Returns:
            bool: 验证是否通过
        """
        if not self.zsign_path:
            logger.error("zsign工具不可用")
            return False
            
        # 检查应用路径是否存在
        if not os.path.exists(app_path):
            logger.error(f"应用路径不存在: {app_path}")
            return False
            
        # 检查是否为目录
        if not os.path.isdir(app_path):
            logger.error(f"应用路径不是目录: {app_path}")
            return False
            
        # 检查签名文件是否存在
        signature_path = os.path.join(app_path, "_CodeSignature", "CodeResources")
        if not os.path.exists(signature_path):
            logger.error(f"签名文件不存在: {signature_path}")
            return False
            
        # 检查描述文件是否存在
        provision_path = os.path.join(app_path, "embedded.mobileprovision")
        if not os.path.exists(provision_path):
            logger.warning(f"描述文件不存在: {provision_path}")
            # 继续验证，因为某些情况下可能不需要描述文件
        else:
            logger.info(f"找到描述文件: {provision_path}")
            # 检查描述文件大小
            try:
                size = os.path.getsize(provision_path)
                logger.debug(f"描述文件大小: {size} 字节")
            except Exception as e:
                logger.warning(f"获取描述文件大小失败: {e}")
        
        # zsign没有专门的验证命令，我们通过检查文件来验证
        # 这里不执行任何zsign命令，而是通过检查签名文件来验证
        logger.debug("zsign没有验证命令，通过检查签名文件来验证")
        
        # 验证签名相关文件是否完整
        logger.info("验证通过: 签名文件检查完成")
        return True 