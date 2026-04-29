#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
使用macholib库处理MachO文件的RPATH
"""

import os
import logging
import struct
from typing import List, Optional

logger = logging.getLogger(__name__)

def add_rpath_to_macho(binary_path: str, rpath: str) -> bool:
    """
    使用macholib为MachO文件添加RPATH
    
    Args:
        binary_path: MachO二进制文件路径
        rpath: 要添加的RPATH路径
        
    Returns:
        bool: 操作是否成功
    """
    try:
        from macholib import MachO
        from macholib.mach_o import (
            LC_RPATH, load_command, rpath_command, MH_MAGIC, MH_MAGIC_64,
            MH_CIGAM, MH_CIGAM_64
        )
        
        logger.info(f"正在使用macholib为 {binary_path} 添加RPATH: {rpath}")
        
        # 读取文件
        with open(binary_path, 'rb') as f:
            data = bytearray(f.read())
        
        # 检查是否是MachO文件
        if len(data) < 4:
            logger.error("文件太小，不是有效的MachO文件")
            return False
        
        magic = struct.unpack('<I', data[:4])[0]
        if magic not in [MH_MAGIC, MH_MAGIC_64, MH_CIGAM, MH_CIGAM_64]:
            logger.error("不是有效的MachO文件")
            return False
        
        # 解析MachO文件
        macho = MachO.MachO(binary_path)
        
        for header in macho.headers:
            # 检查是否已经存在该RPATH
            for load_cmd, cmd_info, data_bytes in header.commands:
                if load_cmd.cmd == LC_RPATH:
                    # 提取现有的RPATH路径
                    try:
                        # RPATH命令的路径通常在命令结构之后
                        path_offset = cmd_info.path
                        if isinstance(path_offset, int):
                            # 从命令开始位置计算实际路径位置
                            path_start = max(0, path_offset - 8)  # 减去load_command的大小，确保不为负
                            if path_start < len(data_bytes):
                                # 尝试解码路径，处理可能的编码问题
                                try:
                                    path_end = data_bytes.find(b'\x00', path_start)
                                    if path_end == -1:
                                        path_end = len(data_bytes)
                                    existing_path = data_bytes[path_start:path_end].decode('utf-8')
                                except UnicodeDecodeError:
                                    existing_path = data_bytes[path_start:].split(b'\x00')[0].decode('utf-8', errors='ignore')
                                if existing_path == rpath:
                                    logger.info(f"RPATH '{rpath}' 已存在")
                                    return True
                    except Exception as e:
                        logger.debug(f"解析现有RPATH时出错: {e}")
                        continue
        
        # 如果到这里，说明RPATH不存在，需要添加
        logger.info(f"RPATH '{rpath}' 不存在，将添加到文件中")
        
        # 使用更直接的方法修改二进制文件
        return add_rpath_binary(binary_path, rpath)
        
    except ImportError:
        logger.error("macholib库不可用")
        return False
    except Exception as e:
        logger.exception(f"使用macholib添加RPATH时出错: {e}")
        return False

def add_rpath_binary(binary_path: str, rpath: str) -> bool:
    """
    直接修改二进制文件来添加RPATH
    
    Args:
        binary_path: MachO二进制文件路径
        rpath: 要添加的RPATH路径
        
    Returns:
        bool: 操作是否成功
    """
    try:
        logger.info(f"尝试直接修改二进制文件添加RPATH: {rpath}")
        
        # 创建备份
        backup_path = binary_path + ".backup"
        with open(binary_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        
        logger.info(f"已创建备份文件: {backup_path}")
        
        # 读取文件
        with open(binary_path, 'rb') as f:
            data = bytearray(f.read())
        
        # 检查魔数
        magic = struct.unpack('<I', data[:4])[0]
        is_64bit = magic in [0xfeedfacf, 0xcffaedfe]  # MH_MAGIC_64, MH_CIGAM_64
        is_little_endian = magic in [0xfeedface, 0xfeedfacf]  # 小端序
        
        # 确定结构体大小
        header_size = 32 if is_64bit else 28
        load_cmd_size = 8
        
        if len(data) < header_size:
            logger.error("文件太小，无法解析MachO头")
            return False
        
        # 解析头部
        if is_little_endian:
            ncmds = struct.unpack('<I', data[16:20])[0]
            sizeofcmds = struct.unpack('<I', data[20:24])[0]
        else:
            ncmds = struct.unpack('>I', data[16:20])[0]
            sizeofcmds = struct.unpack('>I', data[20:24])[0]
        
        logger.info(f"MachO头信息: ncmds={ncmds}, sizeofcmds={sizeofcmds}, 64bit={is_64bit}")
        
        # 检查现有的RPATH命令
        LC_RPATH = 0x8000001c
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
            
            if cmd == LC_RPATH:
                # 检查是否已存在相同的RPATH
                if current_offset + 12 <= len(data):
                    if is_little_endian:
                        path_offset = struct.unpack('<I', data[current_offset+8:current_offset+12])[0]
                    else:
                        path_offset = struct.unpack('>I', data[current_offset+8:current_offset+12])[0]
                    
                    # 计算路径的实际位置
                    path_start = current_offset + path_offset
                    if path_start < len(data):
                        try:
                            existing_path = data[path_start:current_offset+cmdsize].split(b'\x00')[0].decode('utf-8')
                            if existing_path == rpath:
                                logger.info(f"RPATH '{rpath}' 已存在")
                                # 删除备份文件
                                if os.path.exists(backup_path):
                                    os.remove(backup_path)
                                return True
                        except Exception as e:
                            logger.debug(f"解析RPATH路径时出错: {e}")
            
            current_offset += cmdsize
        
        # 创建新的RPATH命令
        rpath_bytes = rpath.encode('utf-8') + b'\x00'
        # 对齐到4字节边界
        while len(rpath_bytes) % 4 != 0:
            rpath_bytes += b'\x00'
        
        new_cmdsize = 12 + len(rpath_bytes)  # rpath_command结构体大小 + 路径长度
        
        # 构建新的RPATH命令
        if is_little_endian:
            new_command = struct.pack('<III', LC_RPATH, new_cmdsize, 12) + rpath_bytes
        else:
            new_command = struct.pack('>III', LC_RPATH, new_cmdsize, 12) + rpath_bytes
        
        # 在load commands区域末尾添加新命令
        load_commands_end = header_size + sizeofcmds
        
        # 构建新的文件内容
        new_data = bytearray()
        new_data.extend(data[:load_commands_end])  # 头部 + 现有load commands
        new_data.extend(new_command)  # 新的RPATH命令
        new_data.extend(data[load_commands_end:])  # 其余数据
        
        # 更新头部中的命令数量和大小
        new_ncmds = ncmds + 1
        new_sizeofcmds = sizeofcmds + len(new_command)
        
        if is_little_endian:
            struct.pack_into('<I', new_data, 16, new_ncmds)
            struct.pack_into('<I', new_data, 20, new_sizeofcmds)
        else:
            struct.pack_into('>I', new_data, 16, new_ncmds)
            struct.pack_into('>I', new_data, 20, new_sizeofcmds)
        
        # 写入修改后的文件
        with open(binary_path, 'wb') as f:
            f.write(new_data)
        
        logger.info(f"成功添加RPATH '{rpath}' 到 {binary_path}")
        
        # 删除备份文件
        if os.path.exists(backup_path):
            os.remove(backup_path)
        
        return True
        
    except Exception as e:
        logger.exception(f"直接修改二进制文件时出错: {e}")
        # 如果出错，尝试恢复备份
        backup_path = binary_path + ".backup"
        if os.path.exists(backup_path):
            try:
                with open(backup_path, 'rb') as src, open(binary_path, 'wb') as dst:
                    dst.write(src.read())
                os.remove(backup_path)
                logger.info("已恢复原始文件")
            except Exception as restore_e:
                logger.error(f"恢复备份文件时出错: {restore_e}")
        return False

def check_rpath_exists(binary_path: str, rpath: str) -> bool:
    """
    检查MachO文件中是否存在指定的RPATH
    
    Args:
        binary_path: MachO二进制文件路径
        rpath: 要检查的RPATH路径
        
    Returns:
        bool: 是否存在该RPATH
    """
    try:
        # 使用我们自己的二进制解析逻辑，更可靠
        rpaths = list_rpaths_binary(binary_path)
        return rpath in rpaths
        
    except Exception as e:
        logger.debug(f"检查RPATH时出错: {e}")
        return False

def list_rpaths_binary(binary_path: str) -> List[str]:
    """
    使用二进制解析列出MachO文件中的所有RPATH
    
    Args:
        binary_path: MachO二进制文件路径
        
    Returns:
        List[str]: RPATH列表
    """
    rpaths = []
    
    try:
        with open(binary_path, 'rb') as f:
            data = f.read()
        
        if len(data) < 32:
            return rpaths
        
        # 检查魔数
        magic = struct.unpack('<I', data[:4])[0]
        is_64bit = magic in [0xfeedfacf, 0xcffaedfe]  # MH_MAGIC_64, MH_CIGAM_64
        is_little_endian = magic in [0xfeedface, 0xfeedfacf]  # 小端序
        
        # 确定结构体大小
        header_size = 32 if is_64bit else 28
        
        if len(data) < header_size:
            return rpaths
        
        # 解析头部
        if is_little_endian:
            ncmds = struct.unpack('<I', data[16:20])[0]
            sizeofcmds = struct.unpack('<I', data[20:24])[0]
        else:
            ncmds = struct.unpack('>I', data[16:20])[0]
            sizeofcmds = struct.unpack('>I', data[20:24])[0]
        
        # 检查RPATH命令
        LC_RPATH = 0x8000001c
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
            
            if cmd == LC_RPATH:
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
                            # 查找路径字符串的结尾
                            path_end = data.find(b'\x00', path_start)
                            if path_end == -1:
                                path_end = current_offset + cmdsize
                            
                            existing_path = data[path_start:path_end].decode('utf-8')
                            logger.debug(f"解析到RPATH: '{existing_path}'")
                            rpaths.append(existing_path)
                        except Exception as e:
                            logger.debug(f"解析RPATH路径时出错: {e}")
            
            current_offset += cmdsize
        
    except Exception as e:
        logger.debug(f"列出RPATH时出错: {e}")
    
    return rpaths

def list_rpaths(binary_path: str) -> List[str]:
    """
    列出MachO文件中的所有RPATH
    
    Args:
        binary_path: MachO二进制文件路径
        
    Returns:
        List[str]: RPATH列表
    """
    # 优先使用我们的二进制解析方法
    try:
        return list_rpaths_binary(binary_path)
    except Exception as e:
        logger.debug(f"二进制解析失败，尝试macholib: {e}")
    
    # 回退到macholib方法
    rpaths = []
    try:
        from macholib import MachO
        from macholib.mach_o import LC_RPATH
        
        macho = MachO.MachO(binary_path)
        
        for header in macho.headers:
            for load_cmd, cmd_info, data_bytes in header.commands:
                if load_cmd.cmd == LC_RPATH:
                    try:
                        # 提取RPATH路径
                        path_offset = cmd_info.path
                        if isinstance(path_offset, int):
                            path_start = path_offset - 8
                            if path_start >= 0 and path_start < len(data_bytes):
                                existing_path = data_bytes[path_start:].split(b'\x00')[0].decode('utf-8')
                                rpaths.append(existing_path)
                    except Exception as e:
                        logger.debug(f"提取RPATH时出错: {e}")
                        continue
        
    except ImportError:
        logger.debug("macholib不可用")
    except Exception as e:
        logger.debug(f"列出RPATH时出错: {e}")
    
    return rpaths 