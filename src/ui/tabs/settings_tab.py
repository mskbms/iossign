#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
设置选项卡模块
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QGroupBox, QFormLayout, QCheckBox, QSpinBox, QComboBox, QFileDialog,
    QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from ...utils.config_utils import (
    get_config_value, set_config_value, get_output_dir, set_output_dir
)
from ...utils.process_utils import is_tool_available

logger = logging.getLogger(__name__)

class SettingsTab(QWidget):
    """设置选项卡类"""
    
    def __init__(self):
        """初始化设置选项卡"""
        super().__init__()
        
        # 初始化UI
        self._init_ui()
        
        # 加载配置
        self._load_config()
        
        # 检查工具可用性
        self._check_tools()
    
    def _init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 常规设置
        general_group = QGroupBox("常规设置")
        general_layout = QFormLayout(general_group)
        
        # 输出目录
        output_layout = QHBoxLayout()
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self._browse_output_dir)
        
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(browse_button)
        
        general_layout.addRow("输出目录:", output_layout)
        
        # 最近文件数量
        self.recent_files_spin = QSpinBox()
        self.recent_files_spin.setMinimum(0)
        self.recent_files_spin.setMaximum(50)
        general_layout.addRow("最近文件数量:", self.recent_files_spin)
        
        # 自动检查更新
        self.auto_update_check = QCheckBox("启动时检查更新")
        general_layout.addRow("", self.auto_update_check)
        
        main_layout.addWidget(general_group)
        
        # 工具设置
        tools_group = QGroupBox("工具设置")
        tools_layout = QFormLayout(tools_group)
        
        # zsign工具状态
        self.zsign_status_label = QLabel("未检测")
        tools_layout.addRow("zsign:", self.zsign_status_label)
        

        
        # 刷新工具状态按钮
        refresh_tools_button = QPushButton("刷新工具状态")
        refresh_tools_button.clicked.connect(self._check_tools)
        tools_layout.addRow("", refresh_tools_button)
        
        main_layout.addWidget(tools_group)
        
        # 语言设置
        language_group = QGroupBox("语言设置")
        language_layout = QFormLayout(language_group)
        
        self.language_combo = QComboBox()
        self.language_combo.addItem("简体中文", "zh_CN")
        self.language_combo.addItem("English", "en_US")
        language_layout.addRow("界面语言:", self.language_combo)
        
        main_layout.addWidget(language_group)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        
        self.save_button = QPushButton("保存设置")
        self.save_button.clicked.connect(self._save_config)
        
        self.reset_button = QPushButton("重置设置")
        self.reset_button.clicked.connect(self._reset_config)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.reset_button)
        buttons_layout.addWidget(self.save_button)
        
        main_layout.addLayout(buttons_layout)
        
        # 状态标签
        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)
        
        # 添加伸缩项
        main_layout.addStretch()
    
    def _load_config(self):
        """加载配置"""
        # 输出目录
        self.output_dir_edit.setText(get_output_dir())
        
        # 最近文件数量
        self.recent_files_spin.setValue(get_config_value("max_recent_files", 10))
        
        # 自动检查更新
        self.auto_update_check.setChecked(get_config_value("auto_check_update", True))
        
        # 语言
        language = get_config_value("language", "zh_CN")
        index = self.language_combo.findData(language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
    
    def _save_config(self):
        """保存配置"""
        # 输出目录
        output_dir = self.output_dir_edit.text()
        set_output_dir(output_dir)
        
        # 最近文件数量
        max_recent_files = self.recent_files_spin.value()
        set_config_value("max_recent_files", max_recent_files)
        
        # 自动检查更新
        auto_check_update = self.auto_update_check.isChecked()
        set_config_value("auto_check_update", auto_check_update)
        
        # 语言
        language = self.language_combo.currentData()
        set_config_value("language", language)
        
        # 显示保存成功
        self.status_label.setText("设置已保存")
        
        # 提示需要重启
        QMessageBox.information(
            self,
            "设置已保存",
            "设置已成功保存。\n\n"
            "部分设置（如语言）需要重启应用后才能生效。"
        )
    
    def _reset_config(self):
        """重置设置"""
        # 确认重置
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要将所有设置重置为默认值吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 重置配置
        set_config_value("output_dir", os.path.expanduser("~/Desktop"))
        set_config_value("max_recent_files", 10)
        set_config_value("auto_check_update", True)
        set_config_value("language", "zh_CN")
        
        # 重新加载配置
        self._load_config()
        
        # 显示重置成功
        self.status_label.setText("设置已重置为默认值")
    
    def _browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", self.output_dir_edit.text()
        )
        
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def _check_tools(self):
        """检查工具可用性"""
        # 检查zsign
        if is_tool_available("zsign"):
            self.zsign_status_label.setText("可用")
            self.zsign_status_label.setStyleSheet("color: green")
        else:
            self.zsign_status_label.setText("不可用")
            self.zsign_status_label.setStyleSheet("color: red")
        
 