import os
import cv2
import numpy as np

# OpenCV's cv2.imread / cv2.imwrite pass the path straight to the C++ layer,
# which on Windows cannot handle non-ASCII paths (for example a Desktop folder
# named in Korean). These wrappers do the file I/O in Python and only hand raw
# bytes to OpenCV, so any Unicode path works. Use them instead of
# cv2.imread / cv2.imwrite throughout the project.

def imread(path, flags=cv2.IMREAD_COLOR):
    """Unicode-safe replacement for cv2.imread.

    Returns the decoded image, or None if the file is missing or cannot be
    decoded (matching cv2.imread's behaviour).
    """
    try:
        data = np.fromfile(path, dtype=np.uint8)
    except (OSError, ValueError):
        return None
    if data.size == 0:
        return None
    return cv2.imdecode(data, flags)

def imwrite(path, image):
    """Unicode-safe replacement for cv2.imwrite.

    Returns True on success, False otherwise (matching cv2.imwrite).
    """
    ext = os.path.splitext(path)[1]
    if not ext:
        ext = ".png"
    success, buffer = cv2.imencode(ext, image)
    if not success:
        return False
    try:
        buffer.tofile(path)
    except (OSError, ValueError):
        return False
    return True
