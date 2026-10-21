# run with: python -m pytest
import json

from playblast_publisher import versioning

def test_first_version_is_1(tmp_path):
    assert versioning.next_version(tmp_path / "sh010" / "anim") == 1

def test_next_version_ignores_gaps(tmp_path):
    dept_folder = tmp_path / "sh010" / "anim"
    for name in ["v001", "v004", "notes", "v002"]:
        (dept_folder / name).mkdir(parents=True)
    assert versioning.next_version(dept_folder) == 5

def test_never_reuses_version(tmp_path):
    first = versioning.build_publish_paths(tmp_path, "sh010", "anim")
    second = versioning.build_publish_paths(tmp_path, "sh010", "anim")
    assert first["media_prefix"].name == "sh010_anim_v001"
    assert second["media_prefix"].name == "sh010_anim_v002"
    
def test_shot_names():
    assert versioning.validate_shot("sh010") == ""
    assert versioning.validate_shot("shot10") != ""

def test_guess_shot():
    assert versioning.guess_shot("C:/proj/sh020_anim.ma") == "sh020"
    assert versioning.guess_shot("untitled.ma") == ""

def test_metadata_file(tmp_path):
    path = tmp_path / "meta.json"
    versioning.write_metadata(path, {"shot": "sh010"})
    saved = json.loads(path.read_text())
    assert saved["shot"] == "sh010"
    assert "created" in saved