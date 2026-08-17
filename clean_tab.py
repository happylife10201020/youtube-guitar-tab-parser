
import os
import cv2
import numpy as np
from PIL import Image
from cv_io import imread

# Every crop is scaled to this width before analysis so filters and comparisons
# behave identically across videos (matches the A4 content width used for the
# PDF: 2480 - 2*100 margin).
TARGET_WIDTH = 2280

# Structuring element (sized for images scaled to TARGET_WIDTH) used to isolate
# notation strokes: larger than a note/staff-line stroke, smaller than the large
# smooth regions we want to discard (page background, video footage, highlight
# box).
NOTATION_SE = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))

def display(image):
    """Helper function to display an image for debugging."""
    cv2.namedWindow('image', cv2.WINDOW_AUTOSIZE)
    cv2.imshow('image', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def error(prv, cur):
    """Calculates the mean squared error between two (already aligned) images."""
    prv = np.array(prv, dtype=np.float64) / 255.0
    cur = np.array(cur, dtype=np.float64) / 255.0
    return np.sum((prv - cur) ** 2)

def notation(gray_image):
    """Isolates the tab notation from its background.

    Tablature is thin, high-contrast ink -- notes, staff lines, numbers -- that
    may be dark-on-light (printed sheets) or light-on-dark (a tab overlaid on
    video footage). A morphological top-hat keeps thin strokes of *either*
    polarity while suppressing large smooth regions, so this discards the page
    background, an outro fading to black, a moving 'now-playing' highlight box,
    and the video playing behind an overlaid tab alike. Comparing frames on this
    representation ignores everything but the notation, so two frames showing the
    same line match even when the background moves.
    """
    white = cv2.morphologyEx(gray_image, cv2.MORPH_TOPHAT, NOTATION_SE)
    black = cv2.morphologyEx(gray_image, cv2.MORPH_BLACKHAT, NOTATION_SE)
    return np.maximum(white, black)

def notation_energy(notation_image):
    """Fraction (0-1) of the crop covered by notation strokes.

    Near-zero for frames that hold no real tab -- an intro/outro, a fade to
    black, or footage before the tab appears -- which should be dropped instead
    of emitted as empty pages.
    """
    return np.mean(notation_image > 30)

def ncc(a, b):
    """Normalized cross-correlation of two equally shaped arrays, in [-1, 1]."""
    a = a.ravel().astype(np.float64)
    b = b.ravel().astype(np.float64)
    a -= a.mean()
    b -= b.mean()
    na = np.sqrt(np.dot(a, a))
    nb = np.sqrt(np.dot(b, b))
    if na < 1e-6 or nb < 1e-6:
        return 0.0
    return float(np.dot(a, b) / (na * nb))

def detect_overlap_fraction(notations, min_confidence=0.45, min_prominence=0.15):
    """Estimates the horizontal overlap between consecutive tab lines.

    Scrolling tab videos often re-show the last measures of one line as the
    first measures of the next so the player never loses their place. That makes
    the same measures appear twice in the compiled PDF. The repeat is a
    horizontal overlap: the left ``f`` fraction of a line duplicates the right
    ``f`` fraction of the line before it, and a given video uses a *consistent*
    ``f``.

    We estimate ``f`` once for the whole video: for each candidate fraction we
    take the median notation correlation between every line's head and the
    previous line's tail, then pick the sharp peak. Aggregating over all
    transitions cancels the ambiguity of self-similar tab content that defeats
    per-transition matching. Returns 0.0 when no consistent overlap clears
    ``min_confidence`` -- most videos page cleanly and are left untouched.

    A high best score alone is not proof of overlap: a repetitive song (the same
    groove bar after bar) correlates fairly well at *every* candidate fraction,
    producing a flat, uniformly-high curve whose maximum can drift past
    ``min_confidence`` -- and whether it does can hinge on where the user happened
    to drag the crop box, wrongly chopping the head off every line. A genuine
    overlap instead shows a sharp peak at the true fraction. So we also require
    the best score to stand out from the curve's median by ``min_prominence``.
    """
    if len(notations) < 3:
        return 0.0

    best_fraction, best_score = 0.0, -1.0
    medians = []
    for fraction in np.arange(0.05, 0.60, 0.01):
        width = int(TARGET_WIDTH * fraction)
        scores = [ncc(notations[k - 1][:, TARGET_WIDTH - width:], notations[k][:, :width])
                  for k in range(1, len(notations))]
        median = float(np.median(scores))
        medians.append(median)
        if median > best_score:
            best_fraction, best_score = float(fraction), median

    if best_score < min_confidence:
        return 0.0
    if best_score - float(np.median(medians)) < min_prominence:
        return 0.0   # flat curve: self-similar content, not a real overlap
    return best_fraction

def _scaled(image_path, flag):
    """Reads an image and scales it to TARGET_WIDTH, or returns None."""
    img = imread(image_path, flag)
    if img is None:
        return None
    h, w = img.shape[:2]
    return cv2.resize(img, (TARGET_WIDTH, int(h * TARGET_WIDTH / w)), interpolation=cv2.INTER_AREA)

def _paginate(images, output_pdf_path):
    """Stacks PIL images top-to-bottom onto A4 pages, starting a new page on overflow."""
    A4_WIDTH, A4_HEIGHT = 2480, 3508  # A4 size in pixels at 300 DPI
    MARGIN = 100
    target_width = A4_WIDTH - 2 * MARGIN

    if not images:
        print("No images to generate PDF.")
        return

    pages = []
    current_height = MARGIN
    current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')

    for img in images:
        # Scale to the page content width, keeping aspect ratio.
        if img.width != target_width:
            scale = target_width / img.width
            img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)

        if current_height + img.height > A4_HEIGHT - MARGIN:
            pages.append(current_page)
            current_page = Image.new('RGB', (A4_WIDTH, A4_HEIGHT), 'white')
            current_height = MARGIN

        current_page.paste(img, (MARGIN, current_height))
        current_height += img.height

    pages.append(current_page)
    pages[0].save(output_pdf_path, save_all=True, append_images=pages[1:])

def images_to_pdf_a4(image_paths, output_pdf_path, left_crop_fraction=0.0):
    """
    Loads tab-line images and stacks them vertically into an A4 PDF.

    ``left_crop_fraction`` trims that fraction off the left of every image except
    the first, removing measures a scrolling video repeats from the previous line
    (see ``detect_overlap_fraction``).
    """
    images = []
    for index, image_path in enumerate(image_paths):
        img = Image.open(image_path)
        # Drop the overlapping head of each subsequent line so repeated measures
        # are not shown twice. The first line is always kept whole.
        if left_crop_fraction > 0 and index > 0:
            cut = int(img.width * left_crop_fraction)
            img = img.crop((cut, 0, img.width, img.height))
        images.append(img)
    _paginate(images, output_pdf_path)

def horizontal_shift(prev_notation, cur_notation):
    """Pixels the tab scrolled left between two frames, plus a match confidence.

    The current frame is the previous one slid left, so the current frame's left
    portion reappears further right in the previous frame. Locating that portion
    (on the background-suppressed notation) gives the scroll distance.
    """
    template_width = int(TARGET_WIDTH * 0.4)
    template = cur_notation[:, :template_width]
    scores = cv2.matchTemplate(prev_notation, template, cv2.TM_CCOEFF_NORMED)[0]
    dx = int(np.argmax(scores))
    return dx, float(scores[dx])

def is_scrolling(notations, min_fraction=0.5, max_samples=40):
    """True when the tab slides sideways continuously rather than paging.

    Almost every consecutive pair of a scrolling video is a confident, sizeable
    horizontal slide; paged videos hold each line still (dx = 0) and jump between
    lines, so almost no pair looks like a steady slide. We sample a bounded number
    of pairs so the check stays fast on long videos.
    """
    n = len(notations)
    if n < 4:
        return False
    if n - 1 > max_samples:
        step = (n - 1) / max_samples
        indices = sorted({int(1 + i * step) for i in range(max_samples)})
    else:
        indices = range(1, n)

    scrolling = tested = 0
    for k in indices:
        if 1 <= k < n:
            dx, peak = horizontal_shift(notations[k - 1], notations[k])
            tested += 1
            if peak > 0.8 and 0.1 * TARGET_WIDTH < dx < 0.85 * TARGET_WIDTH:
                scrolling += 1
    return tested > 0 and scrolling / tested >= min_fraction

def make_scrolling_pdf(frames, output_pdf_path):
    """Stitches a continuously-scrolling tab into one long strip, then slices it
    into page-width lines. ``frames`` is a list of (path, notation, energy)."""
    paths = [f[0] for f in frames]
    notations = [f[1] for f in frames]

    # Cumulative left-scroll offset of each frame within the whole-song strip.
    offsets = [0]
    for k in range(1, len(notations)):
        dx, _ = horizontal_shift(notations[k - 1], notations[k])
        offsets.append(offsets[-1] + dx)

    first = _scaled(paths[0], cv2.IMREAD_COLOR)
    height = first.shape[0]
    panorama = np.zeros((height, offsets[-1] + TARGET_WIDTH, 3), dtype=np.uint8)
    for k, path in enumerate(paths):
        frame = first if k == 0 else _scaled(path, cv2.IMREAD_COLOR)
        if frame is None:
            continue
        rows = min(height, frame.shape[0])
        x = offsets[k]
        panorama[:rows, x:x + TARGET_WIDTH] = frame[:rows, :TARGET_WIDTH]

    # Slice the long strip into page-width lines, in reading order.
    lines = []
    for start in range(0, panorama.shape[1], TARGET_WIDTH):
        segment = panorama[:, start:start + TARGET_WIDTH]
        if segment.shape[1] < TARGET_WIDTH:
            pad = np.zeros((height, TARGET_WIDTH - segment.shape[1], 3), dtype=np.uint8)
            segment = np.hstack([segment, pad])
        lines.append(Image.fromarray(cv2.cvtColor(segment, cv2.COLOR_BGR2RGB)))
    _paginate(lines, output_pdf_path)

def _notation_mse(a, b):
    """MSE between two notation images, zero-padded to a common height."""
    h = max(a.shape[0], b.shape[0])
    comp1 = np.zeros((h, TARGET_WIDTH), dtype=np.uint8)
    comp2 = np.zeros((h, TARGET_WIDTH), dtype=np.uint8)
    comp1[0:a.shape[0], 0:a.shape[1]] = a
    comp2[0:b.shape[0], 0:b.shape[1]] = b
    return error(comp1, comp2)

def dedup_threshold(notations):
    """Per-video threshold separating 'same line still on screen' from 'new line'.

    A fixed value can't serve both a video whose held frames still differ a fair
    amount (a moving 'now-playing' highlight leaves a residual) and a very
    repetitive song whose consecutive *distinct* lines differ only by a small
    measure number. So we derive it from each video's own noise floor: the
    40th-percentile consecutive difference (the typical 'held' level) times a
    margin. Clamped so a pristine, static video still splits near-identical
    repeated lines, and a noisy one never merges everything into one page.
    """
    if len(notations) < 3:
        return 4000.0
    diffs = [_notation_mse(notations[i - 1], notations[i]) for i in range(1, len(notations))]
    floor = float(np.percentile(diffs, 40))
    return min(8000.0, max(400.0, floor * 4.0))

def make_paged_pdf(frames, output_pdf_path, overlap_fraction):
    """De-duplicates page-style tab lines and compiles them into a PDF.
    ``frames`` is a list of (path, notation, energy)."""
    MIN_NOTATION_ENERGY = 0.03

    # Skip blank frames (intros, fades) up front so they neither become pages nor
    # skew the noise floor used to pick the de-duplication threshold.
    content = [(path, nt) for path, nt, energy in frames if energy >= MIN_NOTATION_ENERGY]

    # De-duplication compares the notation-only image (see `notation`): identical
    # lines score ~0 and genuine line changes score far above this threshold,
    # which adapts per video (see `dedup_threshold`) so repetitive songs whose
    # distinct lines differ only by a measure number are not wrongly merged.
    threshold = dedup_threshold([nt for _, nt in content])

    use_files = []
    use_notations = []
    prv_notation = None
    for path, cur_notation in content:
        if prv_notation is None or _notation_mse(prv_notation, cur_notation) > threshold:
            use_files.append(path)
            use_notations.append(cur_notation)
        prv_notation = cur_notation   # compare against the previous frame

    # Trim the repeated head of each line (measures the video re-shows from the
    # previous line). Auto-detected unless the caller overrides it.
    if overlap_fraction is None:
        overlap_fraction = detect_overlap_fraction(use_notations)
    if overlap_fraction > 0:
        print(f"Trimming {overlap_fraction * 100:.0f}% overlap from the start of each line")

    images_to_pdf_a4(use_files, output_pdf_path, left_crop_fraction=overlap_fraction)

def make_pdf(main_directory, overlap_fraction=None):
    """
    Extracts the unique tablature from the cropped frames and compiles a PDF.

    Handles two video styles automatically: pages that flip line-by-line (kept
    unique and de-overlapped) and tabs that scroll sideways continuously (stitched
    into one strip and re-sliced into lines).

    ``overlap_fraction`` only affects paged videos: ``None`` auto-detects the
    repeated overlap, ``0`` disables trimming, and a value in (0, 1) forces it.
    """
    directory = os.path.join(main_directory, "tabs")
    output_pdf_path = os.path.join(main_directory, 'output.pdf')

    imp_files = sorted([os.path.join(directory, f) for f in os.listdir(directory) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))])

    if not imp_files:
        print("No image files found in the 'tabs' directory.")
        return

    MIN_NOTATION_ENERGY = 0.03

    # Analyse every frame once: background-suppressed notation + how much tab it holds.
    frames = []
    for path in imp_files:
        gray = _scaled(path, cv2.IMREAD_GRAYSCALE)
        if gray is None:
            continue
        cur_notation = notation(gray)
        frames.append((path, cur_notation, notation_energy(cur_notation)))

    # Drop blank frames at the very start/end (intro, outro, fade to black) so
    # they neither become pages nor break scroll-shift measurement.
    content = [i for i, f in enumerate(frames) if f[2] >= MIN_NOTATION_ENERGY]
    if not content:
        print("No tab content found in the frames.")
        return
    frames = frames[content[0]: content[-1] + 1]

    if is_scrolling([f[1] for f in frames]):
        print("Detected a continuously-scrolling tab; stitching frames into lines...")
        make_scrolling_pdf(frames, output_pdf_path)
    else:
        make_paged_pdf(frames, output_pdf_path, overlap_fraction)

    print(f"Output is at {output_pdf_path}")
