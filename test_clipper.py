import sys
import traceback

def mock_update(job_id, step, progress, result=None, error=None):
    print(f"[{job_id}] {step} - {progress}")
    if error:
        print(f"ERROR: {error}")
    if result:
        print(f"RESULT: {result}")

from pipeline_shorts import generate_shorts_from_youtube

if __name__ == "__main__":
    try:
        # Same URL user used
        generate_shorts_from_youtube("https://www.youtube.com/watch?v=7QDJL9c9qTI&pp=ygULZG9jdW1lbnRhcnk%3D", "test_job_123", mock_update, 3)
    except Exception as e:
        traceback.print_exc()
