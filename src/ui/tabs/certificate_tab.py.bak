#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
证书管理选项卡模块
"""

import os
import logging
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
    QGroupBox, QFormLayout, QCheckBox, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal

from ...core.certificate_manager import CertificateManager

logger = logging.getLogger(__name__)

class AddCertificateDialog(QDialog):
    """添加证书对话框"""
    
    def __init__(self, parent=None):
        """初始化对话框"""
        super().__init__(parent)
        
        self.setWindowTitle("添加证书")
        self.setMinimumWidth(500)
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 证书名称
        self.name_edit = QLineEdit()
        form_layout.addRow("证书名称:", self.name_edit)
        
        # P12证书文件
        p12_layout = QHBoxLayout()
        self.p12_path_edit = QLineEdit()
        self.p12_path_edit.setReadOnly(True)
        
        browse_p12_button = QPushButton("浏览...")
        browse_p12_button.clicked.connect(self._browse_p12)
        
        p12_layout.addWidget(self.p12_path_edit)
        p12_layout.addWidget(browse_p12_button)
        
        form_layout.addRow("P12证书文件:", p12_layout)
        
        # 证书密码
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("证书密码:", self.password_edit)
        
        # 描述文件
        mobileprovision_layout = QHBoxLayout()
        self.mobileprovision_path_edit = QLineEdit()
        self.mobileprovision_path_edit.setReadOnly(True)
        
        browse_mobileprovision_button = QPushButton("浏览...")
        browse_mobileprovision_button.clicked.connect(self._browse_mobileprovision)
        
        mobileprovision_layout.addWidget(self.mobileprovision_path_edit)
        mobileprovision_layout.addWidget(browse_mobileprovision_button)
        
        form_layout.addRow("描述文件:", mobileprovision_layout)
        
        layout.addLayout(form_layout)
        
        # 按钮
        buttons_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.ok_button)
        buttons_layout.addWidget(cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def _browse_p12(self):
        """浏览P12证书文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择P12证书文件", "", "P12证书文件 (*.p12);;所有文件 (*.*)"
        )
        
        if file_path:
            self.p12_path_edit.setText(file_path)
    
    def _browse_mobileprovision(self):
        """浏览描述文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择描述文件", "", "描述文件 (*.mobileprovision);;所有文件 (*.*)"
        )
        
        if file_path:
            self.mobileprovision_path_edit.setText(file_path)
    
    def get_certificate_info(self):
        """
        获取证书信息
        
        Returns:
            dict: 证书信息
        """
        return {
            "name": self.name_edit.text(),
            "p12_path": self.p12_path_edit.text(),
            "password": self.password_edit.text(),
            "mobileprovision_path": self.mobileprovision_path_edit.text() or None
        }

class CertificateTab(QWidget):
    """证书管理选项卡类"""
    
    def __init__(self, certificate_manager):
        """
        初始化证书管理选项卡
        
        Args:
            certificate_manager: 证书管理器
        """
        super().__init__()
        
        self.certificate_manager = certificate_manager
        
        # 初始化UI
        self._init_ui()
        
        # 加载证书列表
        self._load_certificates()
    
    def _init_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 证书列表
        list_group = QGroupBox("证书列表")
        list_layout = QVBoxLayout(list_group)
        
        self.cert_table = QTableWidget(0, 4)
        self.cert_table.setHorizontalHeaderLabels(["名称", "证书文件", "描述文件", "操作"])
        self.cert_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cert_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.cert_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.cert_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cert_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        list_layout.addWidget(self.cert_table)
        
        main_layout.addWidget(list_group)
        
        # 操作按钮
        buttons_layout = QHBoxLayout()
        
        self.add_button = QPushButton("添加证书")
        self.add_button.clicked.connect(self._add_certificate)
        
        self.refresh_button = QPushButton("刷新列表")
        self.refresh_button.clicked.connect(self._load_certificates)
        
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addStretch()
        
        main_layout.addLayout(buttons_layout)
        
        # 添加伸缩项
        main_layout.addStretch()
    
    def _load_certificates(self):
        """加载证书列表"""
        # 清空表格
        self.cert_table.setRowCount(0)
        
        # 获取证书列表
        certificates = self.certificate_manager.get_all_certificates()
        
        # 填充表格
        for i, cert in enumerate(certificates):
            self.cert_table.insertRow(i)
            
            # 名称
            name_item = QTableWidgetItem(cert.get("name", "未命名证书"))
            name_item.setData(Qt.UserRole, cert.get("id"))
            self.cert_table.setItem(i, 0, name_item)
            
            # 证书文件
            p12_path = cert.get("p12_path", "")
            p12_item = QTableWidgetItem(os.path.basename(p12_path) if p12_path else "")
            p12_item.setToolTip(p12_path)
            self.cert_table.setItem(i, 1, p12_item)
            
            # 描述文件
            mobileprovision_path = cert.get("mobileprovision_path", "")
            mobileprovision_item = QTableWidgetItem(os.path.basename(mobileprovision_path) if mobileprovision_path else "")
            mobileprovision_item.setToolTip(mobileprovision_path)
            self.cert_table.setItem(i, 2, mobileprovision_item)
            
            # 操作按钮
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.setContentsMargins(5, 0, 5, 0)
            
            edit_button = QPushButton("编辑")
            edit_button.setProperty("cert_id", cert.get("id"))
            edit_button.clicked.connect(self._edit_certificate)
            
            delete_button = QPushButton("删除")
            delete_button.setProperty("cert_id", cert.get("id"))
            delete_button.clicked.connect(self._delete_certificate)
            
            button_layout.addWidget(edit_button)
            button_layout.addWidget(delete_button)
            
            self.cert_table.setCellWidget(i, 3, button_widget)
    
    def _add_certificate(self):
        """添加证书"""
        dialog = AddCertificateDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            cert_info = dialog.get_certificate_info()
            
            # 验证输入
            if not cert_info["name"]:
                QMessageBox.warning(self, "输入错误", "请输入证书名称")
                return
            
            if not cert_info["p12_path"] or not os.path.exists(cert_info["p12_path"]):
                QMessageBox.warning(self, "输入错误", "请选择有效的P12证书文件")
                return
            
            if not cert_info["password"]:
                QMessageBox.warning(self, "输入错误", "请输入证书密码")
                return
            
            # 添加证书
            cert_id, error_msg = self.certificate_manager.add_certificate(
                cert_info["name"],
                cert_info["p12_path"],
                cert_info["password"],
                cert_info["mobileprovision_path"]
            )
            
            if cert_id:
                QMessageBox.information(self, "添加成功", f"证书 '{cert_info['name']}' 添加成功")
                self._load_certificates()
            else:
                QMessageBox.critical(self, "添加失败", f"证书添加失败: {error_msg}")
    
    def _edit_certificate(self):
        """编辑证书"""
        # 获取发送者
        sender = self.sender()
        cert_id = sender.property("cert_id")
        
        # 获取证书信息
        cert = self.certificate_manager.get_certificate(cert_id)
        if not cert:
            QMessageBox.warning(self, "错误", "未找到证书")
            return
        
        # 创建对话框
        dialog = AddCertificateDialog(self)
        dialog.setWindowTitle("编辑证书")
        
        # 设置初始值
        dialog.name_edit.setText(cert.get("name", ""))
        dialog.p12_path_edit.setText(cert.get("p12_path", ""))
        dialog.password_edit.setText(cert.get("password", ""))
        dialog.mobileprovision_path_edit.setText(cert.get("mobileprovision_path", ""))
        
        # 显示对话框
        if dialog.exec_() == QDialog.Accepted:
            cert_info = dialog.get_certificate_info()
            
            # 验证输入
            if not cert_info["name"]:
                QMessageBox.warning(self, "输入错误", "请输入证书名称")
                return
            
            # 更新证书
            success = self.certificate_manager.update_certificate(
                cert_id,
                cert_info["name"],
                cert_info["password"] if cert_info["password"] != cert.get("password") else None,
                cert_info["mobileprovision_path"] if cert_info["mobileprovision_path"] != cert.get("mobileprovision_path") else None
            )
            
            if success:
                QMessageBox.information(self, "更新成功", f"证书 '{cert_info['name']}' 更新成功")
                self._load_certificates()
            else:
                QMessageBox.critical(self, "更新失败", "证书更新失败，请检查日志获取详细信息")
    
    def _delete_certificate(self):
        """删除证书"""
        # 获取发送者
        sender = self.sender()
        cert_id = sender.property("cert_id")
        
        # 获取证书信息
        cert = self.certificate_manager.get_certificate(cert_id)
        if not cert:
            QMessageBox.warning(self, "错误", "未找到证书")
            return
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除证书 '{cert.get('name')}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 删除证书
            success = self.certificate_manager.remove_certificate(cert_id)
            
            if success:
                QMessageBox.information(self, "删除成功", f"证书 '{cert.get('name')}' 已删除")
                self._load_certificates()
            else:
                QMessageBox.critical(self, "删除失败", "证书删除失败，请检查日志获取详细信息") 