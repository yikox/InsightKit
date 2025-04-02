
import sys
import numpy as np
from skimage.metrics import structural_similarity as ssim
from PIL import Image


# 公式: 
def calculate_mae(img1, img2):
    return np.mean(np.abs(img1 - img2))


def calculate_mse(img1, img2):
    return np.mean((img1 - img2) ** 2)


def calculate_psnr(img1, img2):
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return float('inf')  # 避免 log(0) 错误
    psnr = 10 * np.log10(255**2 / mse)
    return psnr

def calculate_ssim(img1, img2):
    return ssim(img1, img2, channel_axis=-1)


def diff_picture():
    argv = sys.argv
    if len(argv) != 3:
        print("Usage: python diff_picture.py <image1> <image2>")
        sys.exit(1)
    img1_path = argv[1]
    img2_path = argv[2]
    img1 = Image.open(img1_path)
    img2 = Image.open(img2_path)
    img1 = np.array(img1)
    img2 = np.array(img2)
    print(img1.shape, img2.shape)
    mae = calculate_mae(img1, img2)
    mse = calculate_mse(img1, img2)
    psnr = calculate_psnr(img1, img2)
    ssim_value = calculate_ssim(img1, img2)

    print(f"MAE: {mae}")
    print(f"MSE: {mse}")
    print(f"PSNR: {psnr}")
    print(f"SSIM: {ssim_value}")

if __name__ == "__main__":
    diff_picture()