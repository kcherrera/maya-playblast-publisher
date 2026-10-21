import json
import re
from datetime import datetime
from pathlib import Path

DEPARTMENTS = ["story","layout", "anim", "previz"]

# checking shot names
def validate_shot(shot):
    """Check shot name. Returns an error message, or "" if the name is fine."""
    if re.match(r"^sh\d{3}", shot):     # ^ means "start", sh is literal, \d{3} means "three digits", $ means end
        return ""
    return "Shot must look like sh010 (sh + three digits)."
    
def guess_shot(scene_path):
    """Find a shot name like sh010 inside a scene filename. Returns "" if none."""
    file_name = Path(scene_path).stem   # ex: "C:/proj/sho010_anim.ma" -> "sho010_anim"
    match = re.search(r"sh\d{3}", file_name)
    if match:
        return match.group(0)
    return ""

# find next version number
def next_version(dept_folder):
    """Look at the v001, v002... folders and return the next free number."""
    dept_folder = Path(dept_folder)
    if not dept_folder.is_dir():
        return 1

    highest = 0
    for child in dept_folder.iterdir():
        match = re.match(r"v(\d{3})", child.name)
        if child.is_dir() and match:
            number = int(match.group(1))    # "v004" -> 4
            highest = max(highest, number)
    return highest + 1  # incrementing

# creating version folder
def build_publish_paths(root, shot, department):
    """Create the next version folder and return the paths the publish needs."""
    dept_folder = Path(root) / shot / department
    version = next_version(dept_folder)
    version_folder = dept_folder / f"v{version:03d}"
    
    # if folder already exists, raise an error
    version_folder.mkdir(parents=True, exist_ok=False)
    
    base_name = f"{shot}_{department}_v{version:03d}"
    return {
        "version": version,
        "folder": version_folder,
        "media_prefix": version_folder / base_name,
        "metadata": version_folder / f"{base_name}.json",
    }

# saving metadata    
def write_metadata(path, data):
    """Save a dictionary as a JSON file, adding date and time."""
    data["created"] = datetime.now().isoformat(timespec="seconds")
    text = json.dumps(data, indent=2)
    Path(path).write_text(text, encoding="utf-8")

