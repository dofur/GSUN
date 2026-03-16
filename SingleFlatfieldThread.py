"""
单张伪平场处理线程 - Single Flatfield Thread

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

class SingleFlatfieldThread(QThread):
    """单张伪平场处理线程"""
    complete_signal = pyqtSignal(str, np.ndarray)  # 处理完成信号，返回输出路径和处理后的图像数据
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self, input_path, output_folder):
        super().__init__()
        self.input_path = input_path
        self.output_folder = output_folder
        self.filename = os.path.basename(input_path)
        self.processed_data = None  # 存储处理后的数据
    
    @staticmethod
    def _detect_hot_pixels_improved(data, threshold=3.0, kernel_size=5):
        """改进的热噪点检测算法"""
        # 使用5x5中值滤波获取更稳定的局部背景
        local_median = cv2.medianBlur(data, kernel_size)
        
        # 计算像素与局部中值的差值（绝对值）
        diff = np.abs(data - local_median)
        
        # 计算局部标准差作为噪声水平估计
        local_std = cv2.blur(np.square(data - local_median), (kernel_size, kernel_size))
        local_std = np.sqrt(local_std)
        
        # 检测条件：差值超过阈值倍标准差，且像素值明显高于背景
        noise_threshold = local_std * threshold
        
        # 检测热噪点（亮噪点）
        hot_pixels = (diff > noise_threshold) & (data > local_median)
        
        # 改进：增加孤立性检查，防止误删星点
        # 如果一个"热噪点"的邻域内还有其他"亮像素"（即使没达到热噪点阈值），则很可能是星点
        if np.any(hot_pixels):
            # 定义较宽松的阈值来检测星点的"裙边"（wings）
            # 比如 2.0 倍标准差
            signal_threshold = local_std * 2.0
            bright_pixels = (diff > signal_threshold) & (data > local_median)
            
            mask_bright = bright_pixels.astype(np.uint8)
            kernel = np.ones((3,3), dtype=np.uint8)
            kernel[1,1] = 0
            
            # 计算每个热噪点周围有多少个"亮像素"
            bright_neighbor_count = cv2.filter2D(mask_bright, -1, kernel, borderType=cv2.BORDER_CONSTANT)
            
            # 只有当它是完全孤立的（周围连微弱的亮像素都没有）时，才认为是真正的热噪点
            true_hot_pixels = hot_pixels & (bright_neighbor_count == 0)
        else:
            true_hot_pixels = hot_pixels

        # 检测坏点（暗噪点）- 暗噪点通常不需要像亮噪点那样小心，因为星点是亮的
        dead_pixels = (diff > noise_threshold) & (data < local_median)
        
        # 合并所有噪点
        all_noise_pixels = true_hot_pixels | dead_pixels
        
        return all_noise_pixels
    
    @staticmethod
    def _repair_noise_pixels_robust(data, noise_mask):
        """鲁棒的噪点修复算法 (Vectorized for speed)"""
        # 使用5x5中值滤波图像作为修复源
        # 这样比逐像素修复快得多
        median_filtered = cv2.medianBlur(data, 5)
        
        repaired = data.copy()
        # 向量化替换
        repaired[noise_mask] = median_filtered[noise_mask]
        
        return repaired
    
    @staticmethod
    def _process_channel(data):
        """处理单通道数据（包含改进的噪点去除）"""
        # 转换为float32以进行处理
        data_float = data.astype(np.float32)
        h, w = data_float.shape
        
        # 1. 改进的噪点检测与修复
        # 使用较低的阈值以确保检测到热噪
        # 但为了保护星点，我们可以结合拉普拉斯算子或仅针对单像素
        
        # 简单有效的方法：
        # 检测热噪点：值远大于邻域中值
        noise_mask = SingleFlatfieldThread._detect_hot_pixels_improved(data_float, threshold=4.0)
        
        # 强制执行修复，移除比例检查，因为热噪可能很少但很明显
        if np.any(noise_mask):
            data_float = SingleFlatfieldThread._repair_noise_pixels_robust(data_float, noise_mask)
        
        # 2. 背景估计 (使用降采样加速)
        scale = max(1, w // 500)
        
        if scale > 1:
            small_w = w // scale
            small_h = h // scale
            # 降采样
            small_img = cv2.resize(data_float, (small_w, small_h), interpolation=cv2.INTER_AREA)
            
            # 计算对应的小图核大小
            ksize = int(20 / scale)
            if ksize % 2 == 0: ksize += 1
            if ksize < 3: ksize = 3
            
            # 在小图上应用中值滤波
            background_small = cv2.medianBlur(small_img, max(5, ksize))
            
            # 上采样回原尺寸
            background = cv2.resize(background_small, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            background = cv2.medianBlur(data_float, 21)
            
        # 避免除零
        background[background == 0] = 1e-10
        
        # 3. 伪平场校正
        processed = data_float / background
        
        return processed

    def run(self):
        try:
            from astropy.io import fits
            
            # 确保输出目录存在
            os.makedirs(self.output_folder, exist_ok=True)
            
            # 构建输出路径
            output_filename = f"FW_{self.filename}"
            output_path = os.path.join(self.output_folder, output_filename)
            
            try:
                if self.filename.lower().endswith(('.fits', '.fit', '.fts')):
                    with fits.open(self.input_path) as hdul:
                        image = hdul[0].data
                        header = hdul[0].header
                        
                        # 处理单通道FITS
                        if len(image.shape) == 2:
                            processed_image = self._process_channel(image)
                        elif len(image.shape) == 3: # 处理多通道FITS (如RGB)
                             # 假设是 (C, H, W) 或 (H, W, C) ? FITS通常是 (C, H, W)
                             # 但这里为了安全，如果是3维，我们假设它是多帧或多通道
                             # astropy fits通常是 (Plane, Row, Col) -> (C, H, W)
                             processed_image = np.zeros_like(image, dtype=np.float32)
                             for i in range(image.shape[0]):
                                 processed_image[i] = self._process_channel(image[i])
                        else:
                             # 简单的fallback或者报错，这里假设是2D
                             processed_image = self._process_channel(image)
                        
                        self.processed_data = processed_image.copy()
                        
                        fits.writeto(output_path, processed_image, header, overwrite=True)
                        
                else:
                    img = Image.open(self.input_path)
                    img_array = np.array(img)
                    
                    if len(img_array.shape) == 3:
                        processed_image = np.zeros_like(img_array, dtype=np.float32)
                        for channel in range(img_array.shape[2]):
                            processed_image[:,:,channel] = self._process_channel(img_array[:,:,channel])
                    else:
                        processed_image = self._process_channel(img_array)
                    
                    min_val = np.min(processed_image)
                    max_val = np.max(processed_image)
                    
                    if max_val > min_val:
                        processed_image = 255 * (processed_image - min_val) / (max_val - min_val)
                    
                    self.processed_data = processed_image.astype(np.uint8).copy()
                    
                    result_img = Image.fromarray(processed_image.astype(np.uint8))
                    result_img.save(output_path)
                
                self.complete_signal.emit(output_path, self.processed_data)
                
            except Exception as e:
                self.error_signal.emit(f"处理图像 {self.filename} 时出错: {e}")
                
        except Exception as e:
            # 如果有未捕获的异常，发送错误信号
            self.error_signal.emit(str(e))