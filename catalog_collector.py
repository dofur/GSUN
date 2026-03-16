"""
目录采集工具

作者: Guoyou Sun (孙国佑)
网站: http://sunguoyou.lamost.org/
版本: 1.0

版权所有 © 2025-2030 Guoyou Sun (孙国佑)
"""

import sys
import os
import time
import urllib.parse
import configparser
import pandas as pd
import requests
from bs4 import BeautifulSoup
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                             QProgressBar, QDialog, QMessageBox, QFileDialog,
                             QGroupBox, QLineEdit, QFormLayout, QListWidget, 
                             QAbstractItemView, QListWidgetItem, QDialogButtonBox, QSplitter)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QDateTime
from PyQt5.QtGui import QFont


class CatalogCollectionThread(QThread):
    """目录采集线程"""
    progress_signal = pyqtSignal(str)
    completed_signal = pyqtSignal(pd.DataFrame)
    error_signal = pyqtSignal(str)
    
    def __init__(self, base_url="https://download.china-vo.org/psp/hmt/PSP-HMT-DATA/data/", selected_months=None):
        super().__init__()
        self.base_url = base_url
        self.is_cancelled = False
        self.catalog_data = []
        self.selected_months = selected_months or {}
        
    def cancel(self):
        """取消采集操作"""
        self.is_cancelled = True
        self.progress_signal.emit("用户取消了采集操作")
        
    def run(self):
        try:
            self.progress_signal.emit("开始采集目录数据...")
            
            columns = ["年份", "月份", "日期", "文件夹", "文件名", "时间", "URL"]
            
            if not self.selected_months:
                years = list(range(2020, 2031))
                years.sort(reverse=True)
                
                for year in years:
                    if self.is_cancelled:
                        break
                    self._collect_year_data(str(year))
            else:
                for year, months in self.selected_months.items():
                    if self.is_cancelled:
                        break
                    self._collect_year_data(year, months)
            
            self.progress_signal.emit(f"采集完成，共 {len(self.catalog_data)} 条数据，正在生成表格...")
            df = pd.DataFrame(self.catalog_data, columns=columns)
            self.completed_signal.emit(df)
            
        except Exception as e:
            self.error_signal.emit(f"采集目录时出错: {str(e)}")
            import traceback
            self.progress_signal.emit(f"错误详情: {traceback.format_exc()}")
    
    def _collect_year_data(self, year, months=None):
        """采集指定年份的数据"""
        if self.is_cancelled:
            return
            
        year_url = urllib.parse.urljoin(self.base_url, f"{year}/")
        self.progress_signal.emit(f"正在采集 {year} 年的数据...")
        
        try:
            max_retries = 3
            for retry in range(max_retries):
                try:
                    year_response = requests.get(year_url, timeout=30)
                    break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if retry < max_retries - 1:
                        self.progress_signal.emit(f"连接超时，正在重试 ({retry+1}/{max_retries})...")
                        time.sleep(2)
                    else:
                        raise e
            
            if year_response.status_code != 200:
                self.progress_signal.emit(f"无法访问 {year} 年数据，跳过...")
                return
            
            year_soup = BeautifulSoup(year_response.text, 'html.parser')
            
            for month_link in year_soup.find_all('a'):
                if self.is_cancelled:
                    break
                    
                month_href = month_link.get('href')
                if not month_href or not month_href.strip('/').isdigit():
                    continue
                
                month = month_href.strip('/')
                
                if months and month not in months:
                    continue
                    
                self._collect_month_data(year, month)
                
        except Exception as e:
            self.progress_signal.emit(f"采集年份 {year} 时出错: {str(e)}")
    
    def _collect_month_data(self, year, month):
        """采集指定年份和月份的数据"""
        if self.is_cancelled:
            return
            
        month_url = urllib.parse.urljoin(self.base_url, f"{year}/{month}/")
        self.progress_signal.emit(f"正在采集 {year} 年 {month} 月的数据...")
        
        try:
            max_retries = 3
            for retry in range(max_retries):
                try:
                    month_response = requests.get(month_url, timeout=30)
                    break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if retry < max_retries - 1:
                        self.progress_signal.emit(f"连接超时，正在重试 ({retry+1}/{max_retries})...")
                        time.sleep(2)
                    else:
                        raise e
            
            if month_response.status_code != 200:
                self.progress_signal.emit(f"无法访问 {year} 年 {month} 月数据，跳过...")
                return
            
            month_soup = BeautifulSoup(month_response.text, 'html.parser')
            
            for day_link in month_soup.find_all('a'):
                if self.is_cancelled:
                    break
                    
                day_href = day_link.get('href')
                if not day_href or not day_href.strip('/').isdigit():
                    continue
                
                day = day_href.strip('/')
                self._collect_day_data(year, month, day)
                
        except Exception as e:
            self.progress_signal.emit(f"采集月份 {month} 时出错: {str(e)}")
    
    def _collect_day_data(self, year, month, day):
        """采集指定年份、月份和日期的数据"""
        if self.is_cancelled:
            return
            
        day_url = urllib.parse.urljoin(self.base_url, f"{year}/{month}/{day}/")
        self.progress_signal.emit(f"正在采集 {year} 年 {month} 月 {day} 日的数据...")
        
        try:
            max_retries = 3
            for retry in range(max_retries):
                try:
                    day_response = requests.get(day_url, timeout=30)
                    break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if retry < max_retries - 1:
                        self.progress_signal.emit(f"连接超时，正在重试 ({retry+1}/{max_retries})...")
                        time.sleep(2)
                    else:
                        raise e
            
            if day_response.status_code != 200:
                self.progress_signal.emit(f"无法访问 {year} 年 {month} 月 {day} 日数据，跳过...")
                return
            
            day_soup = BeautifulSoup(day_response.text, 'html.parser')
            
            for folder_link in day_soup.find_all('a'):
                if self.is_cancelled:
                    break
                    
                folder_href = folder_link.get('href')
                if not folder_href or folder_href == '../':
                    continue
                
                folder_name = folder_href.strip('/')
                self._collect_folder_data(year, month, day, folder_name)
                
        except Exception as e:
            self.progress_signal.emit(f"采集日期 {day} 时出错: {str(e)}")
    
    def _collect_folder_data(self, year, month, day, folder_name):
        """采集指定文件夹的数据"""
        if self.is_cancelled:
            return
            
        folder_url = urllib.parse.urljoin(self.base_url, f"{year}/{month}/{day}/{folder_name}/")
        self.progress_signal.emit(f"正在采集文件夹 {year}/{month}/{day}/{folder_name}/...")
        
        try:
            max_retries = 3
            for retry in range(max_retries):
                try:
                    folder_response = requests.get(folder_url, timeout=30)
                    break
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                    if retry < max_retries - 1:
                        self.progress_signal.emit(f"连接超时，正在重试 ({retry+1}/{max_retries})...")
                        time.sleep(2)
                    else:
                        raise e
            
            if folder_response.status_code != 200:
                self.progress_signal.emit(f"无法访问 {folder_url}，跳过...")
                return
            
            folder_soup = BeautifulSoup(folder_response.text, 'html.parser')
            
            files_found = 0
            for file_link in folder_soup.find_all('a'):
                if self.is_cancelled:
                    break
                    
                file_href = file_link.get('href')
                if not file_href or file_href == '../':
                    continue
                
                file_name = urllib.parse.unquote(file_href)
                
                file_time = ""
                
                next_sibling = file_link.next_sibling
                if next_sibling and isinstance(next_sibling, str):
                    file_time = next_sibling.strip()
                elif next_sibling and hasattr(next_sibling, 'string') and next_sibling.string:
                    file_time = next_sibling.string.strip()
                
                file_url = urllib.parse.urljoin(folder_url, file_href)
                
                self.catalog_data.append([
                    year, month, day, folder_name, file_name, file_time, file_url
                ])
                
                files_found += 1
                
                if files_found % 10 == 0:
                    self.progress_signal.emit(f"已采集 {files_found} 个文件...")
            
            self.progress_signal.emit(f"文件夹 {folder_name} 采集完成，共 {files_found} 个文件")
                
        except Exception as e:
            self.progress_signal.emit(f"采集文件夹 {folder_name} 时出错: {str(e)}")
            import traceback
            self.progress_signal.emit(f"错误详情: {traceback.format_exc()}")


class CatalogCollectionDialog(QDialog):
    """目录采集对话框，用于选择要采集的年份和月份"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("目录采集设置")
        self.resize(500, 400)
        self.selected_months = {}
        self.parent = parent
        
        self.create_widgets()
        self.load_years()
        self.deselect_all_btn.setEnabled(False)
        
        if parent and hasattr(parent, 'config') and parent.config.has_section("Catalog") and "last_selected_year" in parent.config["Catalog"]:
            last_year = parent.config["Catalog"]["last_selected_year"]
            for i in range(self.year_list.count()):
                if self.year_list.item(i).text() == last_year:
                    self.year_list.setCurrentRow(i)
                    break
    
    def create_widgets(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel("请选择要采集的年份和月份：")
        layout.addWidget(info_label)
        
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
        
        year_widget = QWidget()
        year_layout = QVBoxLayout(year_widget)
        year_label = QLabel("年份")
        year_layout.addWidget(year_label)
        self.year_list = QListWidget()
        self.year_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.year_list.currentItemChanged.connect(self.on_year_selected)
        year_layout.addWidget(self.year_list)
        splitter.addWidget(year_widget)
        
        month_widget = QWidget()
        month_layout = QVBoxLayout(month_widget)
        month_label = QLabel("月份")
        month_layout.addWidget(month_label)
        self.month_list = QListWidget()
        self.month_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.month_list.itemSelectionChanged.connect(self.on_month_selection_changed)
        month_layout.addWidget(self.month_list)
        splitter.addWidget(month_widget)
        
        select_buttons = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all_months)
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all_months)
        select_buttons.addWidget(self.select_all_btn)
        select_buttons.addWidget(self.deselect_all_btn)
        month_layout.addLayout(select_buttons)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_years(self):
        """加载年份列表"""
        current_date = QDateTime.currentDateTime().date()
        current_year = current_date.year()
        
        years = list(range(2020, 2031))
        years.sort(reverse=True)
        
        for year in years:
            item = QListWidgetItem(str(year))
            self.year_list.addItem(item)
            self.selected_months[str(year)] = []
        
        if self.year_list.count() > 0:
            self.year_list.setCurrentRow(0)
            self.ok_button.setEnabled(False)
    
    def on_year_selected(self, current, previous):
        """当选择年份时，加载对应的月份列表"""
        if not current:
            return
            
        self.month_list.clear()
        year = current.text()
        
        for month in range(1, 13):
            month_str = f"{month:02d}"
            item = QListWidgetItem(month_str)
            self.month_list.addItem(item)
            
            if month_str in self.selected_months.get(year, []):
                item.setSelected(True)
    
    def on_month_selection_changed(self):
        """当月份选择变化时，更新选中的月份列表"""
        current_year = self.year_list.currentItem().text()
        selected_months = []
        
        for i in range(self.month_list.count()):
            item = self.month_list.item(i)
            if item.isSelected():
                selected_months.append(item.text())
        
        self.selected_months[current_year] = selected_months
        
        has_selection = len(selected_months) > 0
        self.deselect_all_btn.setEnabled(has_selection)
        self.ok_button.setEnabled(has_selection)
    
    def select_all_months(self):
        """选择所有月份"""
        for i in range(self.month_list.count()):
            self.month_list.item(i).setSelected(True)
    
    def deselect_all_months(self):
        """取消选择所有月份"""
        for i in range(self.month_list.count()):
            self.month_list.item(i).setSelected(False)
    
    def get_selected_months(self):
        """获取所有选中的年份和月份"""
        result = {}
        for year, months in self.selected_months.items():
            if months:
                result[year] = months
        return result
    
    def accept(self):
        """确认选择，保存选中的月份"""
        if not any(self.get_selected_months().values()):
            QMessageBox.warning(self, "警告", "请至少选择一个月份！")
            return
            
        if self.year_list.currentItem():
            year = self.year_list.currentItem().text()
            
            if self.parent and hasattr(self.parent, 'config'):
                if not self.parent.config.has_section("Catalog"):
                    self.parent.config.add_section("Catalog")
                self.parent.config["Catalog"]["last_selected_year"] = year
                self.parent.save_config()
        
        super().accept()


class CatalogCollectorWindow(QMainWindow):
    """目录采集工具主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read('catalog_collector_config.ini')
        if not self.config.has_section('Settings'):
            self.config.add_section('Settings')
        
        self.catalog_thread = None
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("目录采集工具")
        self.resize(900, 600)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        title_label = QLabel("PSP-HMT 数据目录采集工具")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        info_label = QLabel("数据源: https://download.china-vo.org/psp/hmt/PSP-HMT-DATA/data/")
        layout.addWidget(info_label)
        
        settings_group = QGroupBox("保存设置")
        settings_layout = QFormLayout()
        
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText(self.config.get('Settings', 'save_path', fallback=os.path.join(os.getcwd(), "catalogs")))
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_save_path)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.save_path_edit)
        path_layout.addWidget(self.browse_button)
        settings_layout.addRow("保存路径:", path_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        button_layout = QHBoxLayout()
        self.collect_button = QPushButton("开始采集")
        self.collect_button.clicked.connect(self.start_collection)
        self.collect_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 8px; }")
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_collection)
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 8px; }")
        
        button_layout.addWidget(self.collect_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        progress_group = QGroupBox("采集进度")
        progress_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        progress_layout.addWidget(self.log_text)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        self.log_text.append("欢迎使用目录采集工具！")
        self.log_text.append("请设置保存路径，然后点击'开始采集'按钮。")
        self.log_text.append("")
    
    def browse_save_path(self):
        """浏览保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择保存目录", self.save_path_edit.text())
        if path:
            self.save_path_edit.setText(path)
    
    def start_collection(self):
        """开始采集"""
        save_path = self.save_path_edit.text()
        if not save_path:
            QMessageBox.warning(self, "警告", "请设置保存路径！")
            return
        
        self.config.set('Settings', 'save_path', save_path)
        self.save_config()
        
        dialog = CatalogCollectionDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        
        selected_months = dialog.get_selected_months()
        if not selected_months:
            QMessageBox.warning(self, "警告", "请至少选择一个月份")
            return
        
        if os.path.exists(os.path.join(save_path, "catalog.csv")):
            reply = QMessageBox.question(
                self, 
                "确认覆盖", 
                "已存在采集表格，是否覆盖？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.log_text.clear()
        self.log_text.append("开始采集...")
        self.collect_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        
        base_url = "https://download.china-vo.org/psp/hmt/PSP-HMT-DATA/data/"
        self.catalog_thread = CatalogCollectionThread(base_url, selected_months)
        
        self.catalog_thread.progress_signal.connect(self.update_progress)
        self.catalog_thread.completed_signal.connect(self.on_collection_completed)
        self.catalog_thread.error_signal.connect(self.on_collection_error)
        
        self.catalog_thread.start()
    
    def cancel_collection(self):
        """取消采集"""
        if self.catalog_thread and self.catalog_thread.isRunning():
            self.catalog_thread.cancel()
            self.log_text.append("正在取消采集...")
    
    def update_progress(self, message):
        """更新采集进度"""
        self.log_text.append(message)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def on_collection_completed(self, df):
        """采集完成处理"""
        try:
            save_path = self.save_path_edit.text()
            os.makedirs(save_path, exist_ok=True)
            
            if df.empty:
                self.log_text.append("采集完成，但未找到任何数据")
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(100)
                self.collect_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                return
            
            monthly_files = {}
            for _, row in df.iterrows():
                year = row['年份']
                month = row['月份']
                folder_name = f"{year}{month}"
                
                if folder_name not in monthly_files:
                    month_path = os.path.join(save_path, folder_name)
                    os.makedirs(month_path, exist_ok=True)
                    monthly_files[folder_name] = []
                
                monthly_files[folder_name].append(row)
            
            saved_files = []
            for folder_name, rows in monthly_files.items():
                month_df = pd.DataFrame(rows)
                month_path = os.path.join(save_path, folder_name)
                month_csv_path = os.path.join(month_path, f"{folder_name}.csv")
                month_df.to_csv(month_csv_path, index=False, encoding="utf-8-sig")
                saved_files.append(month_csv_path)
            
            self.log_text.append(f"采集完成，共 {len(df)} 条数据")
            self.log_text.append("数据已保存到：")
            for file_path in saved_files:
                self.log_text.append(f"- {file_path}")
            
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(100)
            self.collect_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            
            QMessageBox.information(self, "完成", f"采集完成！\n共采集 {len(df)} 条数据，保存到 {len(saved_files)} 个文件")
                
        except Exception as e:
            self.log_text.append(f"保存数据时出错: {str(e)}")
            import traceback
            self.log_text.append(f"错误详情: {traceback.format_exc()}")
            self.collect_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
    
    def on_collection_error(self, error_msg):
        """采集错误处理"""
        self.log_text.append(f"错误: {error_msg}")
        self.progress_bar.setVisible(False)
        self.collect_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
    
    def save_config(self):
        """保存配置"""
        with open('catalog_collector_config.ini', 'w') as f:
            self.config.write(f)
    
    def closeEvent(self, event):
        """关闭窗口事件"""
        if self.catalog_thread and self.catalog_thread.isRunning():
            reply = QMessageBox.question(
                self, 
                "确认退出", 
                "采集正在进行中，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.catalog_thread.cancel()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = CatalogCollectorWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
