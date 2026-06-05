import os
import sys
import glob
import numpy as np
from PIL import Image

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
GROUPS_DIR = os.path.join(BASE_DIR, 'static', 'visitor_groups')

def fuse_portraits(group_name):
    group_path = os.path.join(GROUPS_DIR, group_name)
    portrait_dir = os.path.join(group_path, 'portraits')
    out_dir = os.path.join(group_path, 'outputs')
    
    portrait_files = glob.glob(os.path.join(portrait_dir, '*'))
    if not portrait_files:
        print(f"[{group_name}] No portraits found to fuse.")
        return False

    min_pixels = float('inf')
    target_size = None
    
    # Find smallest resolution to use as baseline
    for p in portrait_files:
        try:
            with Image.open(p) as img:
                pixels = img.width * img.height
                if pixels < min_pixels:
                    min_pixels = pixels
                    target_size = (img.width, img.height)
        except Exception:
            pass

    if not target_size:
        return False

    fused_array = np.zeros((target_size[1], target_size[0], 3), dtype=np.float32)
    valid_count = 0
    
    for p in portrait_files:
        try:
            with Image.open(p) as img:
                resized = img.resize(target_size, Image.Resampling.LANCZOS).convert('RGB')
                fused_array += np.array(resized, dtype=np.float32)
                valid_count += 1
        except Exception:
            pass
            
    if valid_count > 0:
        fused_array /= valid_count
        fused_img = Image.fromarray(np.uint8(fused_array))
        fused_img.save(os.path.join(out_dir, 'fused.jpg'), quality=90)
        print(f"[{group_name}] Fused portrait saved successfully.")
        return True
    return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        fuse_portraits(sys.argv[1])
    else:
        print("Usage: python fuse_images.py <group_name>")