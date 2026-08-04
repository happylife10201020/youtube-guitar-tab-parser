import os
import re
import time
import cv2
import yt_dlp
from urllib.parse import urlparse, parse_qs
from cv_io import imread, imwrite

_VIDEO_ID = re.compile(r'^[A-Za-z0-9_-]{11}$')

# Limits so the app fails clearly instead of making the user wait forever.
MAX_VIDEO_SECONDS = 20 * 60      # refuse videos longer than this
MAX_DOWNLOAD_SECONDS = 5 * 60    # abort a download that runs longer than this

def _mmss(seconds):
    seconds = int(seconds)
    return f"{seconds // 60}m {seconds % 60}s"

def _validate_video(info, max_video_seconds):
    """Raises ValueError with a clear message if the video can't be handled."""
    if info.get('is_live'):
        raise ValueError("This is a live stream, which is not supported. Please use a normal video.")
    duration = info.get('duration')
    if max_video_seconds and duration and duration > max_video_seconds:
        raise ValueError(
            f"This video is {_mmss(duration)} long, but the limit is "
            f"{max_video_seconds // 60} minutes. Please use a shorter video.")

def normalize_youtube_url(url):
    """Reduces any YouTube link to a clean single-video watch URL.

    The link copied from the browser address bar often carries a playlist
    (`&list=...`), an index, a start time, or tracking parameters, which can make
    yt-dlp grab the whole playlist or fail -- while "Share -> Copy link" gives a
    clean one. We pull out the 11-character video id from any common form
    (watch?v=, youtu.be/, shorts/, embed/, live/) and rebuild the canonical URL.
    If we cannot find an id we return the input unchanged and let yt-dlp try.
    """
    url = (url or "").strip()
    if _VIDEO_ID.match(url):
        return f"https://www.youtube.com/watch?v={url}"

    try:
        parsed = urlparse(url)
    except ValueError:
        return url

    host = (parsed.netloc or "").lower()
    video_id = None
    if "youtu.be" in host:
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif "youtube" in host:
        query = parse_qs(parsed.query)
        if "v" in query:
            video_id = query["v"][0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "v", "live"):
                video_id = parts[1]

    if video_id and _VIDEO_ID.match(video_id):
        return f"https://www.youtube.com/watch?v={video_id}"
    return url

class _YtdlpLogger:
    """Routes yt-dlp's own messages to our log callback.

    Needed for the packaged (windowed) app, where sys.stdout/stderr are absent
    and yt-dlp printing directly would crash.
    """
    def __init__(self, log):
        self._log = log
    def debug(self, msg):
        pass
    def info(self, msg):
        pass
    def warning(self, msg):
        self._log(str(msg))
    def error(self, msg):
        self._log(str(msg))

def download_youtube_video(url, output_path, log=print, on_progress=None,
                           max_video_seconds=MAX_VIDEO_SECONDS,
                           max_download_seconds=MAX_DOWNLOAD_SECONDS):
    # Single-file formats only (no "+"), so yt-dlp never needs ffmpeg to merge.
    # We only need the video track; audio is irrelevant for tab extraction.
    url = normalize_youtube_url(url)
    last = {'pct': -1.0}
    start = {'t': None}
    timed_out = {'v': False}
    def hook(d):
        if d.get('status') == 'downloading':
            if start['t'] is None:
                start['t'] = time.time()
            if max_download_seconds and time.time() - start['t'] > max_download_seconds:
                timed_out['v'] = True
                raise TimeoutError("download time limit exceeded")
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            done = d.get('downloaded_bytes', 0)
            if total and on_progress:
                pct = done * 100.0 / total
                if pct >= last['pct'] + 1:   # feed the progress bar, not the log
                    last['pct'] = pct
                    on_progress(pct)
        elif d.get('status') == 'finished':
            log("Video downloaded.")

    ydl_opts = {
        # Cap at 720p: frames are downscaled to <=1000px wide before use anyway,
        # so higher resolution only wastes download time and (much more) frame
        # decoding time. Prefer single-file mp4 so no ffmpeg merge is needed.
        'format': ('bestvideo[height<=720][ext=mp4]/best[height<=720][ext=mp4]/'
                   'best[height<=720]/bestvideo[ext=mp4]/best[ext=mp4]/best'),
        'outtmpl': os.path.join(output_path, 'video.%(ext)s'),
        'postprocessors': [],
        'noplaylist': True,   # a stray &list=... must not pull the whole playlist
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'socket_timeout': 30,   # fail fast on a dead/stalled connection
        'retries': 5,
        'fragment_retries': 5,
        # Pull formats from several YouTube player clients. When one client's
        # media URL is blocked (HTTP 403, PO-token gated, throttled), others
        # often still serve the video, so this avoids many "Forbidden" failures.
        'extractor_args': {'youtube': {'player_client': ['tv', 'ios', 'web_safari', 'android', 'web']}},
        'logger': _YtdlpLogger(log),
        'progress_hooks': [hook],
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # 1) Probe metadata (no download) to enforce the length limit up front.
        try:
            info = ydl.extract_info(url, download=False)
        except yt_dlp.utils.DownloadError as e:
            log(f"Could not read video info: {e}")
            raise
        _validate_video(info, max_video_seconds)

        # 2) Download, aborting if it runs past the time limit.
        try:
            info = ydl.extract_info(url, download=True)
        except Exception as e:
            if timed_out['v']:
                raise TimeoutError(
                    f"The download took longer than {max_download_seconds // 60} minutes and was "
                    f"stopped. Try a shorter video or check your internet connection.")
            log(f"Download error: {e}")
            raise
        video_path = ydl.prepare_filename(info)
        return video_path, info.get('title')

def download(main_directory, youtube_url, log=print, on_progress=None):
    video_path, title = download_youtube_video(youtube_url, main_directory, log=log, on_progress=on_progress)

    if on_progress:
        on_progress(None)   # switch the bar to "busy" (indeterminate) for extraction
    log("Extracting frames...")
    frames_folder = os.path.join(main_directory, "frames")
    extract_frames(video_path, frames_folder, log=log)
    return title

MAX_FRAME_HEIGHT = 500
MAX_FRAME_WIDTH = 1000

def _downscale(image):
    """Shrinks a frame to fit within MAX_FRAME_WIDTH x MAX_FRAME_HEIGHT."""
    h, w = image.shape[:2]
    scale = min(1.0, MAX_FRAME_WIDTH / w, MAX_FRAME_HEIGHT / h)
    if scale < 1.0:
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return image

def extract_frames(video_path, output_folder, interval=2, log=print):
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")

    fps = video.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        raise ValueError("FPS value is zero, unable to extract frames.")
    total_frames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = total_frames / fps if total_frames else 0

    # Seek straight to one frame every `interval` seconds instead of decoding
    # every frame and throwing ~98% away. Frames are downscaled here too, so no
    # second resize pass over the folder is needed. Exact frames are irrelevant
    # for choosing/cropping the tab region.
    frame_count = 0
    timestamp = 0.0
    while True:
        video.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        success, frame = video.read()
        if not success:
            break
        frame_filename = os.path.join(output_folder, f"frame_{frame_count:04d}.jpg")
        imwrite(frame_filename, _downscale(frame))
        frame_count += 1
        timestamp += interval
        if duration and timestamp >= duration:
            break

    video.release()
    log(f"Extracted {frame_count} frames.")

