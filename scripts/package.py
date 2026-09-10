#!/usr/bin/env python3
"""Build and audit the documentation-only Agent Ultra composition package."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0-1"
DEPENDENCIES = {'redixs': None,
 'comm': None,
 'obsidian': '1.13.7',
 'mote-vault-sync': '1.1.0-3',
 'mote-vault-syncd': '1.1.0-3'}
DOC = "usr/share/doc/agent-ultra/"
PAYLOAD = {DOC + "README.md", DOC + "copyright"}


def git(*args):
    top = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "--show-toplevel"], text=True).strip()
    if Path(top).resolve() != ROOT:
        raise ValueError("source provenance requires this package's own Git repository")
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def fields(text):
    result = {}
    key = None
    for line in text.splitlines():
        if line.startswith(" ") and key:
            result[key] += "\n" + line
        elif line:
            key, value = line.split(":", 1)
            if key in result:
                raise ValueError("duplicate control field: " + key)
            result[key] = value.strip()
    return result


def control():
    return fields((ROOT / "packaging/control").read_text())


def check_control(meta):
    if meta != control():
        raise ValueError("package metadata differs from reviewed control")
    if meta["Package"] != "agent-ultra" or meta["Architecture"] != "all" or meta["Version"] != VERSION:
        raise ValueError("wrong package identity")
    if set(meta) != {"Package", "Version", "Architecture", "Section", "Priority",
                    "Maintainer", "Homepage", "Depends", "Description"}:
        raise ValueError("unexpected control fields")
    expected_depends = ", ".join(name + (f" (>= {version})" if version else "")
                                 for name, version in DEPENDENCIES.items())
    if meta["Depends"] != expected_depends:
        raise ValueError("dependency boundary or version floor violation")


def compatibility():
    check_control(control())
    contract = json.loads((ROOT / "dependency-contract.json").read_text())
    if (contract["version"] != VERSION or contract["dependencies"] != DEPENDENCIES or
            contract["package"] != "agent-ultra" or contract["recommends"] or contract["suggests"]):
        raise ValueError("Ultra dependency contract differs from control")
    unresolved = {name for name, version in DEPENDENCIES.items() if version is None}
    if set(contract["native_release_gates"]) != unresolved:
        raise ValueError("unbuilt native infrastructure dependencies must remain explicit")
    if contract["installable"] is not False or contract["readiness"] is not False:
        raise ValueError("composition metadata cannot establish installation or runtime readiness")
    if set(DEPENDENCIES) != {"redixs", "comm", "obsidian", "mote-vault-sync", "mote-vault-syncd"}:
        raise ValueError("wrong Ultra ownership boundary")
    external = contract["external_provisioning"]["obsidian"]
    if (external["version"] != "1.13.7" or external["architecture"] != "amd64" or
            external["sha256"] != "17dc33b49cb3e785ecc27edd2ea0c79e40207798b554fd2886e36ebee7af9ae0" or
            external["rehost_on_motebus"] is not False):
        raise ValueError("Obsidian requires the exact official upstream artifact")
    return contract


def archive(path, flag):
    return tarfile.open(fileobj=io.BytesIO(subprocess.check_output(["dpkg-deb", flag, str(path)])))


def verify(path):
    with archive(path, "--ctrl-tarfile") as arc:
        files = [m for m in arc if not m.isdir()]
        if len(files) != 1 or files[0].name.removeprefix("./") != "control" or not files[0].isfile():
            raise ValueError("control archive must contain only control; hooks are forbidden")
        check_control(fields(arc.extractfile(files[0]).read().decode()))
    with archive(path, "--fsys-tarfile") as arc:
        files = set()
        allowed_dirs = {"", "usr", "usr/share", "usr/share/doc", "usr/share/doc/agent-ultra"}
        for member in arc:
            name = member.name.removeprefix("./").rstrip("/")
            name = "" if name == "." else name
            if member.uid != 0 or member.gid != 0:
                raise ValueError("archive member is not root-owned")
            if member.isdir():
                if name not in allowed_dirs or member.mode != 0o755:
                    raise ValueError("unexpected directory or permission: " + name)
            else:
                if not member.isfile() or name not in PAYLOAD or member.mode != 0o644 or name in files:
                    raise ValueError("unexpected payload or permission: " + name)
                source = ROOT / ("README.md" if name.endswith("README.md") else "packaging/copyright")
                if arc.extractfile(member).read() != source.read_bytes():
                    raise ValueError("documentation bytes differ: " + name)
                files.add(name)
        if files != PAYLOAD:
            raise ValueError("incomplete documentation payload")


def build(out):
    meta = control()
    check_control(meta)
    out.mkdir(parents=True, exist_ok=True)
    (ROOT / "build").mkdir(exist_ok=True)
    epoch = int(os.environ.get("SOURCE_DATE_EPOCH") or git("log", "-1", "--format=%ct"))
    with tempfile.TemporaryDirectory(prefix="agent-ultra-", dir=ROOT / "build") as tmp:
        stage = Path(tmp) / "root"
        (stage / "DEBIAN").mkdir(parents=True)
        docs = stage / DOC
        docs.mkdir(parents=True)
        shutil.copyfile(ROOT / "packaging/control", stage / "DEBIAN/control")
        shutil.copyfile(ROOT / "README.md", docs / "README.md")
        shutil.copyfile(ROOT / "packaging/copyright", docs / "copyright")
        for path in [stage, *stage.rglob("*")]:
            path.chmod(0o755 if path.is_dir() else 0o644)
            os.utime(path, (epoch, epoch))
        result = out / ("agent-ultra_" + meta["Version"] + "_all.deb")
        subprocess.run(["dpkg-deb", "--build", "--root-owner-group", "-Zxz", "-z9",
                        str(stage), str(result)], check=True,
                       env={**os.environ, "SOURCE_DATE_EPOCH": str(epoch)})
    verify(result)
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(out):
    """Bind a local review artifact; this is not a publication or readiness gate."""
    contract = compatibility()
    if contract["native_release_gates"]:
        raise ValueError("release blocked: actual Redixs and Comm package artifacts and versions are required")
    path = out / ("agent-ultra_" + control()["Version"] + "_all.deb")
    verify(path)
    if git("status", "--porcelain"):
        raise ValueError("manifest requires clean committed source")
    commit = git("rev-parse", "HEAD")
    data = {"schema": "agent-ultra-release/v1", "package": "agent-ultra", "version": control()["Version"],
            "architecture": "all", "status": "unpublished-composition-review", "installable": False,
            "readiness": False, "native_release_gates": contract["native_release_gates"],
            "source": "https://github.com/motebus/agent-ultra-deb", "source_commit": commit,
            "asset": path.name, "sha256": digest(path), "dependency_contract": contract}
    record = out / "release-manifest.json"
    record.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    (out / "SHA256SUMS").write_text("".join(digest(p) + "  " + p.name + "\n" for p in (path, record)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "verify", "compatibility", "manifest"])
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    if args.action == "build":
        print(build(args.path.resolve()))
    elif args.action == "verify":
        verify(args.path.resolve())
        print("Package boundary audit passed")
    elif args.action == "compatibility":
        print(json.dumps(compatibility(), indent=2))
    else:
        manifest(args.path.resolve())
