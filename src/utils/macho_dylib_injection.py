#!/usr/bin/env python3
"""
MachO动态库注入工具
纯Python实现，支持Windows平台
"""

import struct
import os
import logging
import shutil
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# MachO常量
MAGIC_64 = 0xfeedfacf
MAGIC_32 = 0xfeedface

# Load Command类型
LC_LOAD_DYLIB = 0x0c
LC_LOAD_WEAK_DYLIB = 0x18
LC_RPATH = 0x1c

# MachO头部大小
MACH_HEADER_64_SIZE = 32
MACH_HEADER_32_SIZE = 28

def inject_dylib_to_macho(binary_path: str, dylib_path: str, weak: bool = False, create_backup: bool = True) -> bool:
    """
    向MachO二进制文件注入动态库
    
    Args:
        binary_path: 二进制文件路径
        dylib_path: 动态库路径（install name，如@executable_path/Frameworks/xxx.dylib）
        weak: 是否为弱链接
        create_backup: 是否创建备份文件，默认True。在签名过程中可设为False以提高性能
    
    Returns:
        bool: 是否成功
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(binary_path):
            logger.error(f"二进制文件不存在: {binary_path}")
            return False
        
        backup_path = None
        if create_backup:
            # 创建备份
            backup_path = binary_path + ".backup_dylib"
            shutil.copy2(binary_path, backup_path)
            logger.info(f"创建备份文件: {backup_path}")
        else:
            logger.debug("跳过备份文件创建（性能优化）")
        
        # 读取文件
        with open(binary_path, 'rb') as f:
            data = bytearray(f.read())
        
        # 解析MachO头部
        magic = struct.unpack('<I', data[:4])[0]
        
        if magic == MAGIC_64:
            is_64bit = True
            header_size = MACH_HEADER_64_SIZE
            logger.debug("检测到64位MachO文件")
        elif magic == MAGIC_32:
            is_64bit = False
            header_size = MACH_HEADER_32_SIZE
            logger.debug("检测到32位MachO文件")
        else:
            logger.error(f"不支持的MachO文件格式，magic: 0x{magic:x}")
            return False
        
        # 获取load commands信息
        ncmds = struct.unpack('<I', data[16:20])[0]
        sizeofcmds = struct.unpack('<I', data[20:24])[0]
        
        logger.debug(f"Load commands数量: {ncmds}")
        logger.debug(f"Load commands大小: {sizeofcmds}")
        
        # 检查是否已经存在该dylib
        if _check_dylib_exists(data, header_size, ncmds, dylib_path):
            logger.warning(f"动态库已存在，跳过注入: {dylib_path}")
            # 如果创建了备份，删除它
            if backup_path and os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                    logger.debug("删除不必要的备份文件")
                except:
                    pass
            return True
        
        # 创建新的LC_LOAD_DYLIB命令
        load_command_type = LC_LOAD_WEAK_DYLIB if weak else LC_LOAD_DYLIB
        new_command = _create_dylib_load_command(dylib_path, load_command_type)
        
        # 插入新的load command
        success = _insert_load_command(data, header_size, ncmds, sizeofcmds, new_command)
        
        if not success:
            logger.error("插入load command失败")
            return False
        
        # 写回文件
        with open(binary_path, 'wb') as f:
            f.write(data)
        
        logger.info(f"成功注入动态库: {dylib_path}")
        
        # 验证注入结果
        if _verify_dylib_injection(binary_path, dylib_path):
            logger.info("动态库注入验证成功")
            # 删除备份文件（如果创建了的话）
            if backup_path and os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                    logger.debug("删除备份文件")
                except:
                    pass
            return True
        else:
            logger.error("动态库注入验证失败，恢复备份")
            if backup_path and os.path.exists(backup_path):
                shutil.copy2(backup_path, binary_path)
                os.remove(backup_path)
            return False
            
    except Exception as e:
        logger.exception(f"注入动态库时出错: {e}")
        # 恢复备份（如果创建了的话）
        if backup_path and os.path.exists(backup_path):
            try:
                shutil.copy2(backup_path, binary_path)
                os.remove(backup_path)
                logger.info("已恢复备份文件")
            except:
                pass
        return False

def inject_multiple_dylibs(binary_path: str, dylib_paths: List[str], weak: bool = False, create_backup: bool = True) -> bool:
    """
    向MachO二进制文件注入多个动态库
    
    Args:
        binary_path: 二进制文件路径
        dylib_paths: 动态库路径列表
        weak: 是否为弱链接
        create_backup: 是否创建备份文件，默认True。在签名过程中可设为False以提高性能
    
    Returns:
        bool: 是否全部成功
    """
    if not dylib_paths:
        return True
    
    logger.info(f"开始注入 {len(dylib_paths)} 个动态库到: {binary_path}")
    
    success_count = 0
    for i, dylib_path in enumerate(dylib_paths, 1):
        logger.info(f"注入动态库 {i}/{len(dylib_paths)}: {dylib_path}")
        
        # 只在第一个dylib注入时创建备份（如果需要的话）
        should_backup = create_backup and (i == 1)
        
        if inject_dylib_to_macho(binary_path, dylib_path, weak, should_backup):
            success_count += 1
            logger.info(f"✅ 成功注入: {dylib_path}")
        else:
            logger.error(f"❌ 注入失败: {dylib_path}")
    
    logger.info(f"动态库注入完成: {success_count}/{len(dylib_paths)} 成功")
    return success_count == len(dylib_paths)

def _check_dylib_exists(data: bytearray, header_size: int, ncmds: int, dylib_path: str) -> bool:
    """检查动态库是否已存在"""
    offset = header_size
    
    for i in range(ncmds):
        cmd = struct.unpack('<I', data[offset:offset+4])[0]
        cmd_size = struct.unpack('<I', data[offset+4:offset+8])[0]
        
        if cmd in [LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB]:
            # 读取dylib路径
            name_offset = struct.unpack('<I', data[offset+8:offset+12])[0]
            dylib_name_offset = offset + name_offset
            
            # 查找字符串结束
            end_offset = dylib_name_offset
            while end_offset < len(data) and data[end_offset] != 0:
                end_offset += 1
            
            existing_dylib = data[dylib_name_offset:end_offset].decode('utf-8', errors='ignore')
            if existing_dylib == dylib_path:
                return True
        
        offset += cmd_size
    
    return False

def _create_dylib_load_command(dylib_path: str, load_command_type: int) -> bytearray:
    """创建LC_LOAD_DYLIB命令"""
    # dylib_command结构:
    # uint32_t cmd;              // LC_LOAD_DYLIB
    # uint32_t cmdsize;          // 命令大小
    # struct lc_str name;        // 动态库路径
    # uint32_t timestamp;        // 时间戳
    # uint32_t current_version;  // 当前版本
    # uint32_t compatibility_version; // 兼容版本
    
    # 计算字符串大小（包含null终止符）
    dylib_path_bytes = dylib_path.encode('utf-8') + b'\x00'
    
    # 计算命令大小（需要4字节对齐）
    base_size = 24  # 基本结构大小
    string_size = len(dylib_path_bytes)
    total_size = base_size + string_size
    
    # 4字节对齐
    aligned_size = (total_size + 3) & ~3
    padding = aligned_size - total_size
    
    # 构建命令
    command = bytearray()
    
    # 命令头
    command.extend(struct.pack('<I', load_command_type))  # cmd
    command.extend(struct.pack('<I', aligned_size))       # cmdsize
    command.extend(struct.pack('<I', 24))                 # name.offset (相对于命令开始)
    command.extend(struct.pack('<I', 2))                  # timestamp
    command.extend(struct.pack('<I', 0x10000))            # current_version (1.0.0)
    command.extend(struct.pack('<I', 0x10000))            # compatibility_version (1.0.0)
    
    # 字符串数据
    command.extend(dylib_path_bytes)
    
    # 填充到4字节对齐
    command.extend(b'\x00' * padding)
    
    return command

def _insert_load_command(data: bytearray, header_size: int, ncmds: int, sizeofcmds: int, new_command: bytearray) -> bool:
    """插入新的load command"""
    try:
        # 插入位置：所有load commands之后
        insert_offset = header_size + sizeofcmds
        
        # 插入新命令
        data[insert_offset:insert_offset] = new_command
        
        # 更新MachO头部
        new_ncmds = ncmds + 1
        new_sizeofcmds = sizeofcmds + len(new_command)
        
        # 更新ncmds
        data[16:20] = struct.pack('<I', new_ncmds)
        
        # 更新sizeofcmds
        data[20:24] = struct.pack('<I', new_sizeofcmds)
        
        logger.debug(f"更新MachO头部: ncmds {ncmds} -> {new_ncmds}, sizeofcmds {sizeofcmds} -> {new_sizeofcmds}")
        
        return True
        
    except Exception as e:
        logger.error(f"插入load command失败: {e}")
        return False

def _verify_dylib_injection(binary_path: str, expected_dylib: str) -> bool:
    """验证动态库注入是否成功"""
    try:
        with open(binary_path, 'rb') as f:
            data = f.read()
        
        magic = struct.unpack('<I', data[:4])[0]
        
        if magic == MAGIC_64:
            header_size = MACH_HEADER_64_SIZE
        elif magic == MAGIC_32:
            header_size = MACH_HEADER_32_SIZE
        else:
            return False
        
        ncmds = struct.unpack('<I', data[16:20])[0]
        offset = header_size
        
        for i in range(ncmds):
            cmd = struct.unpack('<I', data[offset:offset+4])[0]
            cmd_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            
            if cmd in [LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB]:
                name_offset = struct.unpack('<I', data[offset+8:offset+12])[0]
                dylib_name_offset = offset + name_offset
                dylib_name = data[dylib_name_offset:].split(b'\x00')[0].decode('utf-8', errors='ignore')
                
                if dylib_name == expected_dylib:
                    return True
            
            offset += cmd_size
        
        return False
        
    except Exception as e:
        logger.error(f"验证注入失败: {e}")
        return False

def list_dylibs(binary_path: str) -> List[str]:
    """列出MachO文件中的所有动态库"""
    dylibs = []
    
    try:
        with open(binary_path, 'rb') as f:
            data = f.read()
        
        magic = struct.unpack('<I', data[:4])[0]
        
        if magic == MAGIC_64:
            header_size = MACH_HEADER_64_SIZE
        elif magic == MAGIC_32:
            header_size = MACH_HEADER_32_SIZE
        else:
            return dylibs
        
        ncmds = struct.unpack('<I', data[16:20])[0]
        offset = header_size
        
        for i in range(ncmds):
            cmd = struct.unpack('<I', data[offset:offset+4])[0]
            cmd_size = struct.unpack('<I', data[offset+4:offset+8])[0]
            
            if cmd in [LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB]:
                name_offset = struct.unpack('<I', data[offset+8:offset+12])[0]
                dylib_name_offset = offset + name_offset
                dylib_name = data[dylib_name_offset:].split(b'\x00')[0].decode('utf-8', errors='ignore')
                dylibs.append(dylib_name)
            
            offset += cmd_size
    
    except Exception as e:
        logger.error(f"列出动态库失败: {e}")
    
    return dylibs

# 兼容性函数
def inject_frameworks_to_app(app_path: str, framework_dylibs: List[str]) -> bool:
    """
    向iOS应用注入Framework动态库
    
    Args:
        app_path: 应用路径 (.app目录)
        framework_dylibs: Framework动态库列表
    
    Returns:
        bool: 是否成功
    """
    # 查找主二进制文件
    main_binary = None
    
    # 先尝试从Info.plist获取
    info_plist_path = os.path.join(app_path, "Info.plist")
    if os.path.exists(info_plist_path):
        try:
            import plistlib
            with open(info_plist_path, 'rb') as f:
                plist = plistlib.load(f)
                executable_name = plist.get('CFBundleExecutable')
                if executable_name:
                    main_binary = os.path.join(app_path, executable_name)
        except:
            pass
    
    # 如果从plist获取失败，扫描文件
    if not main_binary or not os.path.exists(main_binary):
        for item in os.listdir(app_path):
            item_path = os.path.join(app_path, item)
            if (os.path.isfile(item_path) and 
                not item.startswith('.') and 
                not item.endswith('.png') and
                not item.endswith('.plist') and
                not item.endswith('.car') and
                not item.endswith('.mobileprovision') and
                item != 'PkgInfo'):
                # 检查文件大小
                if os.path.getsize(item_path) > 50000:  # 50KB以上
                    main_binary = item_path
                    break
    
    if not main_binary:
        logger.error(f"找不到主二进制文件: {app_path}")
        return False
    
    logger.info(f"主二进制文件: {main_binary}")
    
    # 注入Framework动态库 - 在签名过程中不创建备份以提高性能
    return inject_multiple_dylibs(main_binary, framework_dylibs, weak=False, create_backup=False)

if __name__ == "__main__":
    # 测试代码
    import sys
    
    if len(sys.argv) >= 3:
        binary_path = sys.argv[1]
        dylib_path = sys.argv[2]
        
        print(f"测试注入: {dylib_path} -> {binary_path}")
        
        # 显示注入前的dylib列表
        print("\n注入前的动态库:")
        dylibs = list_dylibs(binary_path)
        for i, dylib in enumerate(dylibs, 1):
            print(f"  {i}. {dylib}")
        
        # 执行注入
        success = inject_dylib_to_macho(binary_path, dylib_path)
        
        if success:
            print("\n✅ 注入成功!")
            
            # 显示注入后的dylib列表
            print("\n注入后的动态库:")
            dylibs = list_dylibs(binary_path)
            for i, dylib in enumerate(dylibs, 1):
                print(f"  {i}. {dylib}")
        else:
            print("\n❌ 注入失败!")
    else:
        print("用法: python macho_dylib_injection.py <binary_path> <dylib_path>") 