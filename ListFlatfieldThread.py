"""
列表伪平场处理线程 - List Flatfield Thread

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用
"""

from PyQt5.QtCore import QThread, pyqtSignal
import os
import numpy as np
from PIL import Image
import cv2
from astropy.io import fits

class ListFlatfieldThread(QThread):
    """列表伪平场处理线程"""
    progress_signal = pyqtSignal(int, int)  # 发送当前处理的索引和总数
    complete_signal = pyqtSignal()  # 处理完成信号
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self, image_list, apply_zscale_func):
        super().__init__()
        self.image_list = image_list
        self.apply_zscale_func = apply_zscale_func
        self.processed_images = []
        self.is_canceled = False
    
    def _detect_hot_pixels_improved(self, data, threshold=3.0, kernel_size=5):
        """改进的热噪点检测算法"""
        local_median = cv2.medianBlur(data, kernel_size)
        diff = np.abs(data - local_median)
        local_std = cv2.blur(np.square(data - local_median), (kernel_size, kernel_size))
        local_std = np.sqrt(local_std)
        noise_threshold = local_std * threshold
        hot_pixels = (diff > noise_threshold) & (data > local_median)
        dead_pixels = (diff > noise_threshold) & (data < local_median)
        all_noise_pixels = hot_pixels | dead_pixels
        return all_noise_pixels
    
    def _repair_noise_pixels_robust(self, data, noise_mask):
        """鲁棒的噪点修复算法"""
        median_filtered = cv2.medianBlur(data, 5)
        repaired = data.copy()
        repaired[noise_mask] = median_filtered[noise_mask]
        return repaired
    
    def _process_channel(self, data):
        """处理单通道数据（包含改进的噪点去除）"""
        data_float = data.astype(np.float32)
        h, w = data_float.shape
        
        # 1. 改进的噪点检测与修复
        noise_mask = self._detect_hot_pixels_improved(data_float, threshold=4.0)
        
        if np.any(noise_mask):
            data_float = self._repair_noise_pixels_robust(data_float, noise_mask)
        
        # 2. 背景估计 (使用降采样加速)
        scale = max(1, w // 500)
        
        if scale > 1:
            small_w = w // scale
            small_h = h // scale
            small_img = cv2.resize(data_float, (small_w, small_h), interpolation=cv2.INTER_AREA)
            ksize = int(20 / scale)
            if ksize % 2 == 0: ksize += 1
            if ksize < 3: ksize = 3
            background_small = cv2.medianBlur(small_img, max(5, ksize))
            background = cv2.resize(background_small, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            background = cv2.medianBlur(data_float, 21)
            
        background[background == 0] = 1e-10
        
        # 3. 伪平场校正
        processed = data_float / background
        
        return processed
    
    def run(self):
        try:
            for idx, image_dict in enumerate(self.image_list):
                if self.is_canceled:
                    break
                
                self.progress_signal.emit(idx, len(self.image_list))
                
                file_path = image_dict['filename']
                
                try:
                    with fits.open(file_path, memmap=False) as hdul:
                        image = hdul[0].data
                        header = hdul[0].header
                        
                        if len(image.shape) > 2:
                            if len(image.shape) == 3:
                                image = image[0]
                            elif len(image.shape) == 4:
                                image = image[0, 0]
                        
                        processed_image = self._process_channel(image)
                        
                        normalized_data = self.apply_zscale_func(processed_image)
                        
                        if len(normalized_data.shape) == 2:
                            height, width = normalized_data.shape
                            qimage = QImage(normalized_data.tobytes(), width, height, width, QImage.Format_Grayscale8)
                        else:
                            height, width = normalized_data.shape[:2]
                            qimage = QImage(normalized_data.tobytes(), width, height, width*3, QImage.Format_RGB888)
                        
                        from PyQt5.QtGui import QPixmap
                        pixmap = QPixmap.fromImage(qimage)
                        
                        time_info = image_dict.get('time_info', '')
                        sky_region_info = image_dict.get('sky_region', '')
                        
                        new_image_dict = {
                            'filename': file_path,
                            'pixmap': pixmap,
                            'time_info': time_info,
                            'sky_region': sky_region_info,
                            'header': header,
                            'original_data_shape': processed_image.shape,
                            'original_data': normalized_data
                        }
                        
                        self.processed_images.append(new_image_dict)
                        print(f"图像 {os.path.basename(file_path)} 已处理")
                        
                except Exception as e:
                    print(f"处理图像 {os.path.basename(file_path)} 时出错: {e}，跳过此图像。")
                    continue
            
            self.complete_signal.emit()
        
        except Exception as e:
            self.error_signal.emit(str(e))
    
    def cancel(self):
        """取消处理操作"""
        self.is_canceled = True
