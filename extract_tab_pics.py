import os
import cv2
import numpy as np
from collections import Counter
from region_selector import prompt_coords
from cv_io import imread, imwrite

def extract_tab(main_directory, select_region=None):
    # `select_region(image_path) -> (y1, x1, y2, x2)` lets a caller (e.g. the GUI)
    # supply its own region picker; defaults to the OpenCV drag window.
    if select_region is None:
        select_region = prompt_coords

    directory = main_directory + "/frames"
    count = 0
    imp_files = []
    for filename in os.listdir(directory):
        if filename.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff')):
            image_path = os.path.join(directory, filename)
            imp_files.append(image_path)

    all_bounds = []
    if len(imp_files) == 0:
        raise FileNotFoundError("No images found in frames directory, video was likely not downloaded correctly")

    imp_files = sorted(imp_files)
    med_path = imp_files[len(imp_files) // 2]
    bounds = select_region(med_path)

    # Normalize the corners so dragging in any direction (e.g. right-to-left or
    # bottom-to-top) still yields a valid top-left -> bottom-right crop.
    y1, x1, y2, x2 = bounds
    top, bottom = sorted((y1, y2))
    left, right = sorted((x1, x2))
    bounds = (top, left, bottom, right)

    for image_path in imp_files:
        if count > 0:
            image = imread(image_path)
            if image is None:
                continue
            image_section = image[bounds[0]:bounds[2], bounds[1]:bounds[3]]
            imwrite(main_directory + f"/tabs/tab{count:04d}.png", image_section);

        count += 1
