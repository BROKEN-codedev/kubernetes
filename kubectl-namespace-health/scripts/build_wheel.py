"""Build this dependency-free package's wheel with Python's standard library.

The conventional setuptools build is also configured in pyproject.toml.
This small offline builder is specific to this pure-Python project.
"""
from pathlib import Path
import base64
import csv
import hashlib
import io
import tomllib
import zipfile


def build_wheel(destination: Path) -> Path:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    name, version = project["name"].replace("-", "_"), project["version"]
    info = f"{name}-{version}.dist-info"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"{name}-{version}-py3-none-any.whl"
    entries = {}
    for source in sorted((root / "ns_health").rglob("*")):
        if source.is_file() and source.suffix in (".py", ".json"):
            entries[source.relative_to(root).as_posix()] = source.read_bytes()
    entries[f"{info}/METADATA"] = (
        f"Metadata-Version: 2.1\nName: {project['name']}\nVersion: {version}\n"
        f"Summary: {project['description']}\nRequires-Python: >=3.11\n"
        "Author: Ayaan Jindal\nLicense: MIT\n\n"
        "Simulated Kubernetes namespace readiness, restart and event analysis.\n"
    ).encode()
    entries[f"{info}/WHEEL"] = b"Wheel-Version: 1.0\nGenerator: ns-health-offline-builder\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    entries[f"{info}/entry_points.txt"] = b"[console_scripts]\nkubectl-ns_health = ns_health.cli:main\n"
    if (root / "LICENSE").is_file():
        entries[f"{info}/LICENSE"] = (root / "LICENSE").read_bytes()
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for filename, content in entries.items():
        digest = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
        writer.writerow([filename, "sha256=" + digest, len(content)])
    writer.writerow([f"{info}/RECORD", "", ""])
    entries[f"{info}/RECORD"] = record.getvalue().encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in entries.items():
            archive.writestr(filename, content)
    return path


if __name__ == "__main__":
    print(build_wheel(Path(__file__).resolve().parents[1] / "dist"))
