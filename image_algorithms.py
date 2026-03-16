"""
图像算法模块 - Image Algorithms

作者：Guoyou Sun (孙国佑) - 天体收藏家
软件：星视 GSUN View V4.0
网站：sunguoyou.lamost.org
标识：546756
原创作品，禁止商业使用
"""

import numpy as np
from scipy.signal import fftconvolve
from scipy.ndimage import gaussian_filter
from scipy.stats import sigmaclip
import logging

def estimate_background_std(data):
    """Estimate background noise standard deviation using sigma clipping."""
    # Use a central crop to avoid edge artifacts
    h, w = data.shape
    crop = data[int(h*0.2):int(h*0.8), int(w*0.2):int(w*0.8)]
    if crop.size == 0:
        crop = data
    
    # Simple robust estimation: percentile or sigma clip
    # 3-sigma clipping
    c, low, high = sigmaclip(crop, low=3.0, high=3.0)
    return np.std(c), np.mean(c)

def estimate_psf_width(data, threshold_sigma=5.0):
    """
    Estimate PSF width (sigma) assuming Gaussian PSF.
    Uses a simplified moment analysis on bright spots.
    """
    bg_std, bg_mean = estimate_background_std(data)
    threshold = bg_mean + threshold_sigma * bg_std
    
    # Find peaks (simplified)
    # We use a maximum filter to find local peaks
    from scipy.ndimage import maximum_filter, label, center_of_mass
    
    local_max = maximum_filter(data, size=5) == data
    mask = (data > threshold) & local_max
    
    labeled, num_objects = label(mask)
    
    if num_objects < 5:
        return 2.0 # Default fallback
    
    # Extract small cutouts around peaks and measure width
    # This is expensive, let's use a simpler approximation:
    # Width ~ sqrt(Area / (2*pi)) ? No.
    # We can use second moments of the brightest stars.
    
    # Let's pick top 10 brightest peaks
    peaks = []
    indices = np.argwhere(mask)
    for y, x in indices:
        peaks.append((data[y, x], x, y))
    
    peaks.sort(key=lambda x: x[0], reverse=True)
    peaks = peaks[:20]
    
    sigmas = []
    
    for _, cx, cy in peaks:
        # Cutout 11x11
        y_start = max(0, cy - 5)
        y_end = min(data.shape[0], cy + 6)
        x_start = max(0, cx - 5)
        x_end = min(data.shape[1], cx + 6)
        
        cutout = data[y_start:y_end, x_start:x_end]
        if cutout.shape != (11, 11):
            continue
            
        cutout = cutout - bg_mean
        
        # Calculate moments
        total = np.sum(cutout)
        if total <= 0: continue
        
        # Grid
        Y, X = np.mgrid[0:cutout.shape[0], 0:cutout.shape[1]]
        x_centroid = np.sum(X * cutout) / total
        y_centroid = np.sum(Y * cutout) / total
        
        xx = np.sum((X - x_centroid)**2 * cutout) / total
        yy = np.sum((Y - y_centroid)**2 * cutout) / total
        
        sigma = np.sqrt((xx + yy) / 2.0)
        if 0.5 < sigma < 5.0: # Reasonable range
            sigmas.append(sigma)
            
    if not sigmas:
        return 2.0
        
    return np.median(sigmas)

def calculate_flux_scale(ref_data, new_data):
    """
    Calculate flux scaling factor (alpha) such that new_data ~ alpha * ref_data
    Using robust regression on bright pixels.
    """
    # Select bright pixels in both images
    bg_std_ref, bg_mean_ref = estimate_background_std(ref_data)
    bg_std_new, bg_mean_new = estimate_background_std(new_data)
    
    threshold_ref = bg_mean_ref + 5 * bg_std_ref
    threshold_new = bg_mean_new + 5 * bg_std_new
    
    mask = (ref_data > threshold_ref) & (new_data > threshold_new)
    
    if np.sum(mask) < 100:
        # Fallback to std dev ratio
        return np.std(new_data) / np.std(ref_data) if np.std(ref_data) > 0 else 1.0
        
    # Robust ratio
    ratios = new_data[mask] / ref_data[mask]
    # Filter infs/nans
    ratios = ratios[np.isfinite(ratios)]
    if len(ratios) == 0:
        return 1.0
        
    # Median ratio
    return np.median(ratios)

def zogy_subtract(new_data, ref_data, psf_new_sigma=None, psf_ref_sigma=None):
    """
    Perform ZOGY (Zackay, Ofek, Gal-Yam) optimal image subtraction.
    Assuming Gaussian PSFs.
    
    Returns:
        S_corr (Significance Image), Diff (Difference Image)
    """
    # 1. Background subtraction and noise estimation
    bg_std_n, bg_mean_n = estimate_background_std(new_data)
    bg_std_r, bg_mean_r = estimate_background_std(ref_data)
    
    N = new_data - bg_mean_n
    R = ref_data - bg_mean_r
    
    # 2. Flux matching
    # We want to match Reference to New or vice versa. 
    # ZOGY assumes R and N are flux calibrated.
    # Let's scale R to match N.
    # F_n * Scale = F_r ? No. 
    # Let N ~ alpha * R. 
    # We can treat (alpha * R) as the reference with adjusted noise.
    
    flux_scale = calculate_flux_scale(R, N) # N / R
    # R_scaled = R * flux_scale
    # But for ZOGY formula, it's better to keep R and N separate and handle scaling in PSF or formula.
    # Simplified: Scale R to match N, then subtract.
    
    R_scaled = R * flux_scale
    sigma_r_scaled = bg_std_r * flux_scale
    sigma_n = bg_std_n
    
    # 3. PSF Estimation
    if psf_new_sigma is None:
        psf_new_sigma = estimate_psf_width(N)
    if psf_ref_sigma is None:
        psf_ref_sigma = estimate_psf_width(R)
        
    logging.info(f"ZOGY: PSF New={psf_new_sigma:.2f}, PSF Ref={psf_ref_sigma:.2f}, Scale={flux_scale:.2f}")
    
    # 4. Construct PSF Kernels (in Fourier space)
    # Image size
    h, w = N.shape
    
    # Create Gaussian PSFs
    # We need coordinate grids centered at 0
    y, x = np.mgrid[-h//2:h//2, -w//2:w//2]
    # Shift if needed? No, standard FFT assumes origin at (0,0) which is corner. 
    # We should create kernel in center and fftshift, or just create analytically in freq domain.
    
    # Analytic Fourier Transform of Gaussian:
    # G(x) = exp(-x^2 / (2sigma^2))
    # FT(G)(k) = exp(-2 pi^2 sigma^2 k^2) (ignoring normalization constants for now)
    
    # Frequencies
    ky = np.fft.fftfreq(h)
    kx = np.fft.fftfreq(w)
    KX, KY = np.meshgrid(kx, ky)
    K2 = KX**2 + KY**2
    
    # Fourier Transforms of Images
    N_hat = np.fft.fft2(N)
    R_hat = np.fft.fft2(R_scaled)
    
    # Fourier Transforms of PSFs (normalized to sum=1 in real space -> value 1 at DC)
    # FT of Gaussian with sigma (in pixels): exp(-2 * pi^2 * sigma^2 * (u^2 + v^2))
    P_n_hat = np.exp(-2 * np.pi**2 * psf_new_sigma**2 * K2)
    P_r_hat = np.exp(-2 * np.pi**2 * psf_ref_sigma**2 * K2)
    
    # 5. Compute Difference (D) and Score (S)
    # ZOGY Eq 13:
    # D_hat = (P_r_hat * N_hat - P_n_hat * R_hat) / sqrt(sigma_n^2 * |P_r_hat|^2 + sigma_r^2 * |P_n_hat|^2)
    # Note: sigma_r here is the noise of the *scaled* reference, so sigma_r_scaled.
    
    # Denominator squared
    denom2 = sigma_n**2 * np.abs(P_r_hat)**2 + sigma_r_scaled**2 * np.abs(P_n_hat)**2
    
    # Avoid division by zero (should not happen with Gaussians and noise > 0)
    denom = np.sqrt(denom2)
    
    # Numerator
    numer = P_r_hat * N_hat - P_n_hat * R_hat
    
    # Result in Fourier Space
    D_hat = numer / denom
    
    # Inverse FFT
    # We need real part
    D = np.fft.ifft2(D_hat).real
    
    # D is the "Scorr" (Score image) in ZOGY terms if normalized correctly.
    # Actually, Eq 13 gives the "Optimal Statistic" (S).
    # The "Difference Image" is usually just the numerator transformed back (properly matched).
    # But the user wants "highlight residuals". The S image is best for detection.
    
    # However, D might have artifacts at edges due to FFT.
    # Let's mask edges.
    
    return D, flux_scale

def simple_psf_match_subtract(new_data, ref_data):
    """
    Simpler fallback: Match PSFs by convolution then subtract.
    """
    bg_std_n, bg_mean_n = estimate_background_std(new_data)
    bg_std_r, bg_mean_r = estimate_background_std(ref_data)
    
    N = new_data - bg_mean_n
    R = ref_data - bg_mean_r
    
    flux_scale = calculate_flux_scale(R, N)
    R_scaled = R * flux_scale
    
    psf_new = estimate_psf_width(N)
    psf_ref = estimate_psf_width(R)
    
    if psf_new > psf_ref:
        # New is blurrier. Convolve Ref to match.
        sigma_diff = np.sqrt(psf_new**2 - psf_ref**2)
        R_matched = gaussian_filter(R_scaled, sigma=sigma_diff)
        diff = N - R_matched
    elif psf_ref > psf_new:
        # Ref is blurrier. Convolve New to match.
        sigma_diff = np.sqrt(psf_ref**2 - psf_new**2)
        N_matched = gaussian_filter(N, sigma=sigma_diff)
        diff = N_matched - R_scaled
    else:
        diff = N - R_scaled
        
    return diff, flux_scale
