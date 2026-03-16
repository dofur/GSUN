"""
批量伪平场处理线程 - Batch Flatfield Thread

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

class BatchFlatfieldThread(QThread):
    """批量伪平场处理线程"""
    progress_signal = pyqtSignal(int, str)  # 发送当前处理的索引和文件名
    complete_signal = pyqtSignal()  # 处理完成信号
    error_signal = pyqtSignal(str)  # 错误信号
    
    def __init__(self, input_folder, output_folder, image_files):
        super().__init__()
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.image_files = image_files
        self.running = True
    
    def _detect_hot_pixels_improved(self, data, threshold=3.0, kernel_size=5):
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
        
        # 检测坏点（暗噪点）
        dead_pixels = (diff > noise_threshold) & (data < local_median)
        
        # 合并所有噪点
        all_noise_pixels = hot_pixels | dead_pixels
        
        return all_noise_pixels
    
    def _repair_noise_pixels_robust(self, data, noise_mask):
        """鲁棒的噪点修复算法 (Vectorized for speed)"""
        # 使用5x5中值滤波图像作为修复源
        # 这样比逐像素修复快得多
        median_filtered = cv2.medianBlur(data, 5)
        
        repaired = data.copy()
        # 向量化替换
        repaired[noise_mask] = median_filtered[noise_mask]
        
        return repaired
    
    def _process_channel(self, data):
        """处理单通道数据（包含改进的噪点去除）"""
        # 转换为float32以进行处理
        data_float = data.astype(np.float32)
        h, w = data_float.shape
        
        # 1. 改进的噪点检测与修复
        # 使用较低的阈值以确保检测到热噪
        # 但为了保护星点，我们可以结合拉普拉斯算子或仅针对单像素
        
        # 简单有效的方法：
        # 检测热噪点：值远大于邻域中值
        noise_mask = self._detect_hot_pixels_improved(data_float, threshold=4.0)
        
        # 强制执行修复，移除比例检查，因为热噪可能很少但很明显
        if np.any(noise_mask):
            data_float = self._repair_noise_pixels_robust(data_float, noise_mask)
        
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
            
            # 处理每个文件
            for idx, filename in enumerate(self.image_files):
                if not self.running:
                    break
                
                # 发送进度信号
                self.progress_signal.emit(idx, filename)
                
                # 构建输入和输出路径
                input_path = os.path.join(self.input_folder, filename)
                output_filename = f"FW_{filename}"
                output_path = os.path.join(self.output_folder, output_filename)
                
                try:
                    # 根据文件类型处理
                    if filename.lower().endswith(('.fits', '.fit', '.fts')):
                        # 处理FITS文件
                        with fits.open(input_path) as hdul:
                            image = hdul[0].data
                            header = hdul[0].header
                            
                            # 处理图像
                            if len(image.shape) == 2:
                                processed_image = self._process_channel(image)
                            elif len(image.shape) == 3:
                                processed_image = np.zeros_like(image, dtype=np.float32)
                                for i in range(image.shape[0]):
                                    processed_image[i] = self._process_channel(image[i])
                            else:
                                processed_image = self._process_channel(image)
                            
                            # 保存处理后的图像
                            fits.writeto(output_path, processed_image, header, overwrite=True)
                            
                        # 继续处理下一个文件
                        continue
                    
                    # 处理非FITS图像文件
                    img = Image.open(input_path)
                    img_array = np.array(img)
                    
                    # 根据图像类型进行处理
                    if len(img_array.shape) == 3:  # 彩色图像
                        processed_image = np.zeros_like(img_array, dtype=np.float32)
                        # 分别处理每个颜色通道
                        for channel in range(img_array.shape[2]):
                            processed_image[:,:,channel] = self._process_channel(img_array[:,:,channel])
                    else:
                        # 处理普通图像文件
                        processed_image = self._process_channel(img_array)
                    
                    # 处理后的图像可能有值超出0-255范围，需要重新映射到0-255
                    min_val = np.min(processed_image)
                    max_val = np.max(processed_image)
                    
                    # 重新映射到0-255范围
                    if max_val > min_val:
                        processed_image = 255 * (processed_image - min_val) / (max_val - min_val)
                    
                    # 保存处理后的图像
                    result_img = Image.fromarray(processed_image.astype(np.uint8))
                    result_img.save(output_path)
                    
                except Exception as e:
                    self.error_signal.emit(f"处理图像 {filename} 时出错: {e}")
                    print(f"处理图像 {filename} 时出错: {e}，跳过此图像。")
                    continue
            
            # 发送完成信号
            if self.running:
                self.complete_signal.emit()
        
        except Exception as e:
            # 如果有未捕获的异常，发送错误信号
            self.error_signal.emit(str(e))
    
    def cancel(self):
        """取消处理操作"""
        self.running = False