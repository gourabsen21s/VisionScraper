import sys
import os
from pathlib import Path
import pytest

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner.browser_profile import BrowserProfile, ViewportSize

def test_browser_profile_defaults():
    profile = BrowserProfile()
    assert profile.headless is False  # Default depends on screen, but usually False if screen detected or None
    assert profile.user_data_dir is None
    
    # Check args generation
    # We need to set user_data_dir to get args
    profile.user_data_dir = Path("/tmp/test_profile")
    args = profile.get_args()
    assert "--no-first-run" in args
    assert f"--user-data-dir={profile.user_data_dir}" in args

def test_browser_profile_custom():
    profile = BrowserProfile(
        headless=False,
        user_data_dir="/tmp/custom_profile",
        window_size=ViewportSize(width=1280, height=720)
    )
    assert profile.headless is False
    assert Path(profile.user_data_dir).resolve() == Path("/tmp/custom_profile").resolve()
    
    args = profile.get_args()
    # assert "--headless=new" in args # Removed because headless=False
    assert "--window-size=1280,720" in args

if __name__ == "__main__":
    # Manual run if pytest not available or for quick check
    try:
        test_browser_profile_defaults()
        test_browser_profile_custom()
        print("BrowserProfile tests passed!")
    except Exception as e:
        print(f"BrowserProfile tests failed: {e}")
        import traceback
        traceback.print_exc()
