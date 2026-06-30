#!/usr/bin/env python3
"""Build PCM release zip and refresh packages-v1.json + repository.json."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

REPO_BASE = "https://raw.githubusercontent.com/peon374/ReactBOM/refs/heads/master"
IDENTIFIER = "com.github.peon374.ReactBOM"


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_last_tag(version_file: Path) -> str:
    text = version_file.read_text(encoding="utf-8")
    match = re.search(r"LAST_TAG\s*=\s*['\"]([^'\"]+)['\"]", text)
    if not match:
        raise SystemExit(f"LAST_TAG not found in {version_file}")
    return match.group(1)


def copy_plugin(src: Path, dst: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> set[str]:
        return {name for name in names if name == "__pycache__" or name.endswith(".ini")}

    shutil.copytree(src, dst, ignore=ignore)


def build_pcm_zip(root: Path, tag: str) -> tuple[Path, str, int, int]:
    releases = root / "releases"
    metadata_path = releases / "metadata.json"
    resources_path = releases / "resources"
    plugin_src = root / "InteractiveHtmlBom"

    if not metadata_path.exists():
        raise SystemExit(f"Missing {metadata_path}")

    icon_src = plugin_src / "icon.png"
    resources_path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(icon_src, resources_path / "icon.png")

    version_dir = releases / tag
    version_dir.mkdir(parents=True, exist_ok=True)
    zip_base = version_dir / f"ReactBOM_{tag}_pcm"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copytree(resources_path, tmp_path / "resources")
        copy_plugin(plugin_src, tmp_path / "plugins")
        shutil.copy2(metadata_path, tmp_path / "metadata.json")
        archive = Path(shutil.make_archive(str(zip_base), "zip", root_dir=tmp_path))

    zip_bytes = archive.read_bytes()
    download_sha256 = hashlib.sha256(zip_bytes).hexdigest()
    download_size = len(zip_bytes)
    with zipfile.ZipFile(archive) as zf:
        install_size = sum(info.file_size for info in zf.infolist())

    return archive, download_sha256, download_size, install_size


def write_packages_v1(
    root: Path,
    tag: str,
    download_sha256: str,
    download_size: int,
    install_size: int,
) -> Path:
    package_version = tag.lstrip("v")
    download_url = f"{REPO_BASE}/releases/{tag}/ReactBOM_{tag}_pcm.zip"
    packages_path = root / "packages-v1.json"

    packages = {
        "packages": [
            {
                "$schema": "https://go.kicad.org/pcm/schemas/v1",
                "author": {
                    "contact": {"web": "https://github.com/peon374/ReactBOM"},
                    "name": "David Middleton",
                },
                "description": "Export interactive BOM pcbdata for IBOMReact",
                "description_full": (
                    "KiCad plugin fork derived from InteractiveHtmlBom. Extracts pcbdata "
                    "(board geometry, footprints, BOM rows) as JSON or LZ-compressed base64 "
                    "for use with IBOMReact React components.\n\n"
                    "Based on InteractiveHtmlBom by openscopeproject (MIT)."
                ),
                "identifier": IDENTIFIER,
                "keep_on_update": [".*/config\\.ini", ".*/web/user.*"],
                "license": "MIT",
                "maintainer": {
                    "contact": {"web": "https://github.com/peon374/ReactBOM"},
                    "name": "David Middleton",
                },
                "name": "ReactBOM",
                "resources": {
                    "Github": "https://github.com/peon374/ReactBOM",
                    "Upstream": "https://github.com/openscopeproject/InteractiveHtmlBom",
                },
                "tags": ["bom", "pcbnew", "react", "assembly", "documentation"],
                "type": "plugin",
                "versions": [
                    {
                        "download_sha256": download_sha256,
                        "download_size": download_size,
                        "download_url": download_url,
                        "install_size": install_size,
                        "kicad_version": "6.0",
                        "kicad_version_max": "10",
                        "platforms": ["linux", "macos", "windows"],
                        "status": "stable",
                        "version": package_version,
                    }
                ],
            }
        ]
    }

    packages_path.write_text(
        json.dumps(packages, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return packages_path


def write_repository_json(root: Path, packages_path: Path) -> None:
    now = datetime.now(timezone.utc)
    repository = {
        "$schema": "https://go.kicad.org/pcm/schemas/v1#/definitions/Repository",
        "maintainer": {
            "contact": {"web": "https://github.com/peon374/ReactBOM"},
            "name": "David Middleton",
        },
        "name": "ReactBOM repository",
        "packages": {
            "sha256": sha256_of_file(packages_path),
            "update_time_utc": now.strftime("%Y-%m-%d %H:%M:%S"),
            "update_timestamp": int(now.timestamp()),
            "url": f"{REPO_BASE}/packages-v1.json",
        },
    }
    (root / "repository.json").write_text(
        json.dumps(repository, indent=4) + "\n",
        encoding="utf-8",
    )


def sync_metadata_version(root: Path, tag: str) -> None:
    metadata_path = root / "releases" / "metadata.json"
    if not metadata_path.exists():
        return
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    if data.get("versions"):
        data["versions"][0]["version"] = tag.lstrip("v")
        metadata_path.write_text(
            json.dumps(data, indent=4, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def main() -> None:
    root = Path(__file__).resolve().parent
    tag = read_last_tag(root / "InteractiveHtmlBom" / "version.py")
    sync_metadata_version(root, tag)

    archive, download_sha256, download_size, install_size = build_pcm_zip(root, tag)
    packages_path = write_packages_v1(
        root, tag, download_sha256, download_size, install_size
    )
    write_repository_json(root, packages_path)

    print(f"Built {archive}")
    print(f"Updated {packages_path.name} and repository.json")


if __name__ == "__main__":
    main()
