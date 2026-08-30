import os
import json
import logging

LICENSE_FILE = "license.json"

def get_license():
    """Reads the local license file."""
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error reading license file: {e}")
    return None

def save_license(key, status, details=None):
    """Saves the license locally."""
    data = {
        "key": key,
        "status": status,
        "details": details or {}
    }
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f)
    return True

def delete_license():
    """Removes the local license file."""
    if os.path.exists(LICENSE_FILE):
        os.remove(LICENSE_FILE)
        return True
    return False

def is_activated():
    """Checks if the software is currently activated."""
    lic = get_license()
    if lic and lic.get("status") == "active":
        return True
    return False

def validate_key(key):
    """
    Validates a license key against a mock API.
    For V1, accepts 'BETA-TEST-KEY' or any key starting with 'NULLPK-'.
    """
    key = key.strip()
    if key == "BETA-TEST-KEY" or key.startswith("NULLPK-"):
        # Mock successful validation
        save_license(key, "active", {"tier": "pro", "features": ["all"]})
        return True, "Activation Successful! Welcome to AI Content Studio."
    
    return False, "Invalid License Key. Please check your purchase email."
