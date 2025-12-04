# runner/paths.py
import os
import uuid

ARTIFACTS_ROOT = os.getenv("BM_ARTIFACTS_ROOT", "/tmp/browser_runner_artifacts")

def make_session_dir(session_id: str = None) -> str:
    session_id = session_id or uuid.uuid4().hex
    path = os.path.join(ARTIFACTS_ROOT, session_id)
    os.makedirs(path, exist_ok=True)
    return path

def session_screenshot_path(session_dir: str, filename: str = "screenshot.png") -> str:
    return os.path.join(session_dir, filename)

def session_video_path(session_dir: str, filename: str = "session_video.webm") -> str:
    return os.path.join(session_dir, filename)
