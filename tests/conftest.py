"""Isolate tests from application credentials and persistent state."""
import os
import tempfile
import shutil
import atexit

_test_data = tempfile.mkdtemp(prefix="studio-tests-")
os.environ["STUDIO_DATA_DIR"] = _test_data
os.environ["STUDIO_CONFIG_FILE"] = os.path.join(_test_data, "config.json")
os.environ["STUDIO_API_TOKEN"] = "test-suite-token"
os.environ["STUDIO_SECURE_COOKIES"] = "false"
atexit.register(shutil.rmtree, _test_data, ignore_errors=True)
