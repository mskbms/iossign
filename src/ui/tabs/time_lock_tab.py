#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
时间限制选项卡模块
"""

import os
import time
import logging
import tempfile
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout, QSpinBox, QDateEdit, QRadioButton, QButtonGroup,
    QFileDialog, QMessageBox, QCalendarWidget
)
from PyQt5.QtCore import Qt, QDate

from ...utils.file_utils import extract_ipa, get_app_path_in_ipa, read_plist, write_plist

logger = logging.getLogger(__name__)

class TimeLockTab(QWidget):
    """时间限制选项卡类"""
    
    def __init__(self):
        """初始化时间限制选项卡"""
        super().__init__()
        
        self.ipa_path = ""
        self.app_path = ""
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # IPA文件选择
        ipa_group = QGroupBox("IPA文件")
        ipa_layout = QHBoxLayout(ipa_group)
        
        self.ipa_path_edit = QLineEdit()
        self.ipa_path_edit.setReadOnly(True)
        self.ipa_path_edit.setPlaceholderText("请选择IPA文件...")
        
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._browse_ipa)
        
        ipa_layout.addWidget(self.ipa_path_edit)
        ipa_layout.addWidget(browse_button)
        
        main_layout.addWidget(ipa_group)
        
        # 应用信息
        info_group = QGroupBox("应用信息")
        info_layout = QFormLayout(info_group)
        
        self.bundle_id_label = QLabel("")
        info_layout.addRow("Bundle ID:", self.bundle_id_label)
        
        self.app_name_label = QLabel("")
        info_layout.addRow("应用名称:", self.app_name_label)
        
        main_layout.addWidget(info_group)
        
        # 时间限制设置
        time_group = QGroupBox("时间限制设置")
        time_layout = QVBoxLayout(time_group)
        
        # 限制类型选择
        type_layout = QHBoxLayout()
        
        self.type_group = QButtonGroup(self)
        
        self.days_radio = QRadioButton("按天数限制")
        self.days_radio.setChecked(True)
        self.days_radio.toggled.connect(self._toggle_limit_type)
        self.type_group.addButton(self.days_radio)
        
        self.date_radio = QRadioButton("按日期限制")
        self.date_radio.toggled.connect(self._toggle_limit_type)
        self.type_group.addButton(self.date_radio)
        
        type_layout.addWidget(self.days_radio)
        type_layout.addWidget(self.date_radio)
        type_layout.addStretch()
        
        time_layout.addLayout(type_layout)
        
        # 天数限制
        days_layout = QHBoxLayout()
        
        self.days_spin = QSpinBox()
        self.days_spin.setMinimum(1)
        self.days_spin.setMaximum(365)
        self.days_spin.setValue(7)
        
        days_layout.addWidget(QLabel("限制天数:"))
        days_layout.addWidget(self.days_spin)
        days_layout.addWidget(QLabel("天"))
        days_layout.addStretch()
        
        time_layout.addLayout(days_layout)
        
        # 日期限制
        date_layout = QHBoxLayout()
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate().addDays(7))
        self.date_edit.setEnabled(False)
        
        date_layout.addWidget(QLabel("截止日期:"))
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        
        time_layout.addLayout(date_layout)
        
        # 过期提示
        message_layout = QFormLayout()
        
        self.message_edit = QLineEdit("应用已过期，请联系管理员")
        message_layout.addRow("过期提示:", self.message_edit)
        
        time_layout.addLayout(message_layout)
        
        main_layout.addWidget(time_group)
        
        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QFormLayout(output_group)
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        
        output_button = QPushButton("选择...")
        output_button.clicked.connect(self._select_output_path)
        
        output_button_layout = QHBoxLayout()
        output_button_layout.addWidget(self.output_path_edit)
        output_button_layout.addWidget(output_button)
        
        output_layout.addRow("输出路径:", output_button_layout)
        
        main_layout.addWidget(output_group)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("应用时间限制")
        self.apply_button.setMinimumWidth(120)
        self.apply_button.clicked.connect(self._apply_time_lock)
        self.apply_button.setEnabled(False)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.apply_button)
        
        main_layout.addLayout(buttons_layout)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)
        
        # 添加伸缩项
        main_layout.addStretch()
    
    def _toggle_limit_type(self):
        """切换限制类型"""
        self.days_spin.setEnabled(self.days_radio.isChecked())
        self.date_edit.setEnabled(self.date_radio.isChecked())
    
    def _browse_ipa(self):
        """浏览IPA文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择IPA文件", "", "IPA文件 (*.ipa);;所有文件 (*.*)"
        )
        
        if file_path:
            self.set_ipa_path(file_path)
    
    def set_ipa_path(self, file_path):
        """
        设置IPA文件路径
        
        Args:
            file_path: IPA文件路径
        """
        self.ipa_path = file_path
        self.ipa_path_edit.setText(file_path)
        
        # 设置默认输出路径
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        self.output_path_edit.setText(os.path.join(os.path.dirname(file_path), f"{name}_timelocked{ext}"))
        
        # 重置状态
        self.app_path = ""
        self.bundle_id_label.setText("")
        self.app_name_label.setText("")
        self.apply_button.setEnabled(False)
        
        # 解析IPA文件
        self._parse_ipa()
    
    def _select_output_path(self):
        """选择输出路径"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出路径", self.output_path_edit.text(), "IPA文件 (*.ipa);;所有文件 (*.*)"
        )
        
        if file_path:
            self.output_path_edit.setText(file_path)
    
    def _parse_ipa(self):
        """解析IPA文件"""
        if not self.ipa_path or not os.path.exists(self.ipa_path):
            return
        
        self.status_label.setText("正在解析IPA文件...")
        
        # 解压IPA文件
        extract_dir, original_app_name = extract_ipa(self.ipa_path)
        if not extract_dir:
            self.status_label.setText("解压IPA文件失败")
            return
        
        # 获取.app路径
        app_path = get_app_path_in_ipa(extract_dir)
        if not app_path:
            self.status_label.setText("找不到.app目录")
            return
        
        self.app_path = app_path
        
        # 读取Info.plist
        info_plist_path = os.path.join(app_path, "Info.plist")
        if not os.path.exists(info_plist_path):
            self.status_label.setText("找不到Info.plist文件")
            return
        
        info_plist = read_plist(info_plist_path)
        if not info_plist:
            self.status_label.setText("读取Info.plist失败")
            return
        
        # 获取应用信息
        bundle_id = info_plist.get("CFBundleIdentifier", "")
        app_name = info_plist.get("CFBundleDisplayName", "") or info_plist.get("CFBundleName", "")
        
        self.bundle_id_label.setText(bundle_id)
        self.app_name_label.setText(app_name)
        
        # 启用应用按钮
        self.apply_button.setEnabled(True)
        self.status_label.setText("IPA文件解析成功，可以应用时间限制")
    
    def _apply_time_lock(self):
        """应用时间限制"""
        # 检查IPA路径
        if not self.ipa_path or not os.path.exists(self.ipa_path):
            QMessageBox.warning(self, "错误", "请先选择有效的IPA文件")
            return
        
        # 检查输出路径
        output_path = self.output_path_edit.text()
        if not output_path:
            QMessageBox.warning(self, "错误", "请选择输出路径")
            return
        
        # 检查应用路径
        if not self.app_path:
            QMessageBox.warning(self, "错误", "IPA文件解析失败")
            return
        
        # 获取过期时间
        if self.days_radio.isChecked():
            days = self.days_spin.value()
            expire_time = int(time.time()) + days * 24 * 60 * 60
            expire_date = datetime.now() + timedelta(days=days)
            expire_text = expire_date.strftime("%Y-%m-%d")
        else:
            qdate = self.date_edit.date()
            expire_date = datetime(qdate.year(), qdate.month(), qdate.day())
            expire_time = int(expire_date.timestamp())
            expire_text = expire_date.strftime("%Y-%m-%d")
        
        # 获取过期提示
        expire_message = self.message_edit.text() or "应用已过期"
        
        # 确认应用
        reply = QMessageBox.question(
            self,
            "确认应用",
            f"确定要应用以下时间限制吗？\n\n"
            f"过期时间: {expire_text}\n"
            f"过期提示: {expire_message}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 创建时间限制脚本
        self.status_label.setText("正在创建时间限制脚本...")
        
        time_limit_js = f"""
        var expire_time = {expire_time};
        var current_time = Math.floor(Date.now() / 1000);
        if (current_time > expire_time) {{
            throw new Error("{expire_message}");
        }}
        """
        
        # 将脚本写入文件
        js_path = os.path.join(self.app_path, "time_limit.js")
        try:
            with open(js_path, 'w', encoding='utf-8') as f:
                f.write(time_limit_js)
        except Exception as e:
            logger.error(f"写入时间限制脚本失败: {e}")
            self.status_label.setText("写入时间限制脚本失败")
            QMessageBox.critical(self, "错误", f"写入时间限制脚本失败: {str(e)}")
            return
        
        # 修改Info.plist
        info_plist_path = os.path.join(self.app_path, "Info.plist")
        info_plist = read_plist(info_plist_path)
        
        if not info_plist:
            self.status_label.setText("读取Info.plist失败")
            QMessageBox.critical(self, "错误", "读取Info.plist失败")
            return
        
        # 添加JSContext路径
        info_plist["JSContextPath"] = "time_limit.js"
        
        # 写回Info.plist
        if not write_plist(info_plist_path, info_plist):
            self.status_label.setText("写入Info.plist失败")
            QMessageBox.critical(self, "错误", "写入Info.plist失败")
            return
        
        # 重新打包IPA
        self.status_label.setText("正在重新打包IPA文件...")
        
        try:
            # 导入必要的模块
            import zipfile
            import shutil
            
            # 创建输出目录
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            
            # 获取Payload目录
            payload_dir = os.path.dirname(self.app_path)
            extract_dir = os.path.dirname(payload_dir)
            
            # 创建ZIP文件
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, extract_dir)
                        zipf.write(file_path, arcname)
            
            self.status_label.setText("时间限制应用成功")
            
            QMessageBox.information(
                self,
                "应用成功",
                f"时间限制已成功应用到IPA文件。\n\n"
                f"过期时间: {expire_text}\n"
                f"输出文件: {output_path}\n\n"
                "注意: 该IPA文件需要重新签名才能安装使用。"
            )
        except Exception as e:
            logger.error(f"重新打包IPA文件失败: {e}")
            self.status_label.setText("重新打包IPA文件失败")
            QMessageBox.critical(self, "错误", f"重新打包IPA文件失败: {str(e)}")
            return 