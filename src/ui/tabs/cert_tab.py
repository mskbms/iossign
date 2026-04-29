#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QPushButton, QLabel, QLineEdit, QTableWidget, 
    QTableWidgetItem, QFileDialog, QGroupBox, QCheckBox,
    QMessageBox, QTabWidget, QHeaderView, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from core.cert_manager import CertManager


class CertificateTab(QWidget):
    """证书管理标签页"""
    
    status_message = pyqtSignal(str)
    
    def __init__(self, config):
        """初始化证书管理标签页
        
        Args:
            config (dict): 应用配置
        """
        super().__init__()
        
        self.logger = logging.getLogger("CertificateTab")
        self.config = config
        
        # 创建证书管理器
        self.cert_manager = CertManager(config)
        
        # 初始化UI
        self._init_ui()
        
        # 加载证书和描述文件
        self._load_certificates()
        self._load_provisions()
    
    def _init_ui(self):
        """初始化用户界面"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 创建标签页
        self.tabs = QTabWidget()
        
        # 证书标签页
        self.cert_widget = QWidget()
        self.tabs.addTab(self.cert_widget, "证书")
        
        # 描述文件标签页
        self.provision_widget = QWidget()
        self.tabs.addTab(self.provision_widget, "描述文件")
        
        main_layout.addWidget(self.tabs)
        
        # 初始化证书标签页
        self._init_cert_tab()
        
        # 初始化描述文件标签页
        self._init_provision_tab()
    
    def _init_cert_tab(self):
        """初始化证书标签页"""
        layout = QVBoxLayout(self.cert_widget)
        
        # 证书表格
        self.cert_table = QTableWidget()
        self.cert_table.setColumnCount(5)
        self.cert_table.setHorizontalHeaderLabels(["名称", "主题", "颁发者", "有效期至", "操作"])
        self.cert_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cert_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.cert_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.cert_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.cert_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.cert_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.import_cert_btn = QPushButton("导入证书")
        self.import_cert_btn.clicked.connect(self._import_certificate)
        
        self.refresh_cert_btn = QPushButton("刷新")
        self.refresh_cert_btn.clicked.connect(self._load_certificates)
        
        button_layout.addWidget(self.import_cert_btn)
        button_layout.addWidget(self.refresh_cert_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def _init_provision_tab(self):
        """初始化描述文件标签页"""
        layout = QVBoxLayout(self.provision_widget)
        
        # 描述文件表格
        self.provision_table = QTableWidget()
        self.provision_table.setColumnCount(6)
        self.provision_table.setHorizontalHeaderLabels(["名称", "UUID", "App ID", "Team ID", "过期日期", "操作"])
        self.provision_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.provision_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.provision_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.provision_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.provision_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.provision_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.provision_table)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        self.import_provision_btn = QPushButton("导入描述文件")
        self.import_provision_btn.clicked.connect(self._import_provision)
        
        self.refresh_provision_btn = QPushButton("刷新")
        self.refresh_provision_btn.clicked.connect(self._load_provisions)
        
        button_layout.addWidget(self.import_provision_btn)
        button_layout.addWidget(self.refresh_provision_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
    
    def _load_certificates(self):
        """加载证书列表"""
        # 清空表格
        self.cert_table.setRowCount(0)
        
        # 获取证书列表
        certs = self.cert_manager.list_certificates()
        
        # 填充表格
        for i, cert in enumerate(certs):
            self.cert_table.insertRow(i)
            
            # 名称
            name_item = QTableWidgetItem(cert.get("name", "Unknown"))
            name_item.setData(Qt.ItemDataRole.UserRole, cert.get("path", ""))
            self.cert_table.setItem(i, 0, name_item)
            
            # 主题
            subject_item = QTableWidgetItem(cert.get("subject", "Unknown"))
            self.cert_table.setItem(i, 1, subject_item)
            
            # 颁发者
            issuer_item = QTableWidgetItem(cert.get("issuer", "Unknown"))
            self.cert_table.setItem(i, 2, issuer_item)
            
            # 有效期
            valid_to_item = QTableWidgetItem(cert.get("valid_to", "Unknown"))
            self.cert_table.setItem(i, 3, valid_to_item)
            
            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(5)
            
            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setProperty("cert_path", cert.get("path", ""))
            delete_btn.clicked.connect(self._delete_certificate)
            
            # 设为默认按钮
            default_btn = QPushButton("设为默认")
            default_btn.setProperty("cert_path", cert.get("path", ""))
            default_btn.clicked.connect(self._set_default_certificate)
            
            btn_layout.addWidget(delete_btn)
            btn_layout.addWidget(default_btn)
            
            self.cert_table.setCellWidget(i, 4, btn_widget)
        
        # 更新状态
        self.status_message.emit(f"已加载 {len(certs)} 个证书")
    
    def _load_provisions(self):
        """加载描述文件列表"""
        # 清空表格
        self.provision_table.setRowCount(0)
        
        # 获取描述文件列表
        provisions = self.cert_manager.list_provisions()
        
        # 填充表格
        for i, provision in enumerate(provisions):
            self.provision_table.insertRow(i)
            
            # 名称
            name_item = QTableWidgetItem(provision.get("name", "Unknown"))
            name_item.setData(Qt.ItemDataRole.UserRole, provision.get("path", ""))
            self.provision_table.setItem(i, 0, name_item)
            
            # UUID
            uuid_item = QTableWidgetItem(provision.get("uuid", "Unknown"))
            self.provision_table.setItem(i, 1, uuid_item)
            
            # App ID
            app_id_item = QTableWidgetItem(provision.get("app_id", "Unknown"))
            self.provision_table.setItem(i, 2, app_id_item)
            
            # Team ID
            team_id_item = QTableWidgetItem(provision.get("team_id", "Unknown"))
            self.provision_table.setItem(i, 3, team_id_item)
            
            # 过期日期
            expiry_item = QTableWidgetItem(provision.get("expiration_date", "Unknown"))
            self.provision_table.setItem(i, 4, expiry_item)
            
            # 操作按钮
            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            btn_layout.setSpacing(5)
            
            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setProperty("provision_path", provision.get("path", ""))
            delete_btn.clicked.connect(self._delete_provision)
            
            # 设为默认按钮
            default_btn = QPushButton("设为默认")
            default_btn.setProperty("provision_path", provision.get("path", ""))
            default_btn.clicked.connect(self._set_default_provision)
            
            btn_layout.addWidget(delete_btn)
            btn_layout.addWidget(default_btn)
            
            self.provision_table.setCellWidget(i, 5, btn_widget)
        
        # 更新状态
        self.status_message.emit(f"已加载 {len(provisions)} 个描述文件")
    
    def _import_certificate(self):
        """导入证书"""
        # 选择证书文件
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("证书文件 (*.p12)")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                cert_path = selected_files[0]
                
                # 输入证书密码
                password, ok = QInputDialog.getText(
                    self,
                    "证书密码",
                    "请输入证书密码:",
                    QLineEdit.EchoMode.Password
                )
                
                if ok:
                    # 输入新名称(可选)
                    new_name, ok = QInputDialog.getText(
                        self,
                        "证书名称",
                        "请输入证书名称(可选):",
                        QLineEdit.EchoMode.Normal
                    )
                    
                    if not ok:
                        new_name = None
                    
                    # 导入证书
                    success, result = self.cert_manager.import_certificate(cert_path, password, new_name)
                    
                    if success:
                        self.status_message.emit(f"证书导入成功: {result}")
                        QMessageBox.information(self, "导入成功", f"证书已成功导入")
                        self._load_certificates()
                    else:
                        self.status_message.emit(f"证书导入失败: {result}")
                        QMessageBox.critical(self, "导入失败", f"证书导入失败:\n{result}")
    
    def _import_provision(self):
        """导入描述文件"""
        # 选择描述文件
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("描述文件 (*.mobileprovision)")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                provision_path = selected_files[0]
                
                # 输入新名称(可选)
                new_name, ok = QInputDialog.getText(
                    self,
                    "描述文件名称",
                    "请输入描述文件名称(可选):",
                    QLineEdit.EchoMode.Normal
                )
                
                if not ok:
                    new_name = None
                
                # 导入描述文件
                success, result = self.cert_manager.import_provision(provision_path, new_name)
                
                if success:
                    self.status_message.emit(f"描述文件导入成功: {result}")
                    QMessageBox.information(self, "导入成功", f"描述文件已成功导入")
                    self._load_provisions()
                else:
                    self.status_message.emit(f"描述文件导入失败: {result}")
                    QMessageBox.critical(self, "导入失败", f"描述文件导入失败:\n{result}")
    
    def _delete_certificate(self):
        """删除证书"""
        sender = self.sender()
        cert_path = sender.property("cert_path")
        
        if cert_path:
            reply = QMessageBox.question(
                self,
                "确认删除",
                "确定要删除此证书吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.cert_manager.delete_certificate(cert_path)
                
                if success:
                    self.status_message.emit(f"证书已删除: {cert_path}")
                    self._load_certificates()
                else:
                    self.status_message.emit(f"删除证书失败: {cert_path}")
                    QMessageBox.critical(self, "删除失败", "无法删除证书")
    
    def _delete_provision(self):
        """删除描述文件"""
        sender = self.sender()
        provision_path = sender.property("provision_path")
        
        if provision_path:
            reply = QMessageBox.question(
                self,
                "确认删除",
                "确定要删除此描述文件吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                success = self.cert_manager.delete_provision(provision_path)
                
                if success:
                    self.status_message.emit(f"描述文件已删除: {provision_path}")
                    self._load_provisions()
                else:
                    self.status_message.emit(f"删除描述文件失败: {provision_path}")
                    QMessageBox.critical(self, "删除失败", "无法删除描述文件")
    
    def _set_default_certificate(self):
        """设置默认证书"""
        sender = self.sender()
        cert_path = sender.property("cert_path")
        
        if cert_path:
            self.config["certificates"]["default_cert"] = cert_path
            self.status_message.emit(f"已设置默认证书: {cert_path}")
            QMessageBox.information(self, "设置默认", "已设置为默认证书")
    
    def _set_default_provision(self):
        """设置默认描述文件"""
        sender = self.sender()
        provision_path = sender.property("provision_path")
        
        if provision_path:
            self.config["certificates"]["default_provision"] = provision_path
            self.status_message.emit(f"已设置默认描述文件: {provision_path}")
            QMessageBox.information(self, "设置默认", "已设置为默认描述文件")
    
    def update_config(self, config):
        """更新配置
        
        Args:
            config (dict): 新的配置
        """
        self.config = config
        self.cert_manager = CertManager(config) 