"""Verify the actual signed APK using Android SDK tools, without third-party modules."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import zipfile


def run(command):
    result = subprocess.run([str(x) for x in command], capture_output=True, text=True,
                            encoding="utf-8", errors="replace", check=False)
    if result.returncode:
        raise RuntimeError(f"Command failed ({result.returncode}): {command[0]}\n"
                           f"{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def load_alignments(data):
    if data[:4] != b"\x7fELF" or data[5] != 1:
        raise ValueError("Expected little-endian ELF library")
    is64 = data[4] == 2
    offset = struct.unpack_from("<Q" if is64 else "<I", data, 32 if is64 else 28)[0]
    size, count = struct.unpack_from("<HH", data, 54 if is64 else 42)
    return [
        struct.unpack_from("<Q" if is64 else "<I", data, offset + i * size + (48 if is64 else 28))[0]
        for i in range(count)
        if struct.unpack_from("<I", data, offset + i * size)[0] == 1
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apk", type=Path)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    args = parser.parse_args()
    apks = [args.apk] if args.apk else list(Path("app/build/outputs/apk/release").glob("*.apk"))
    if len(apks) != 1:
        raise ValueError(f"Expected one release APK, found {len(apks)}")
    apk = apks[0].resolve()
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if not sdk:
        raise ValueError("Set ANDROID_HOME to your Android SDK directory")
    tools = Path(sdk) / "build-tools/36.0.0"
    signature = run([tools / ("apksigner.bat" if os.name == "nt" else "apksigner"),
                     "verify", "--verbose", "--print-certs", apk])
    alignment = run([tools / ("zipalign.exe" if os.name == "nt" else "zipalign"), "-c", "-v", "4", apk])
    alignment16 = run([tools / ("zipalign.exe" if os.name == "nt" else "zipalign"),
                       "-c", "-P", "16", "-v", "4", apk])
    badging = run([tools / ("aapt.exe" if os.name == "nt" else "aapt"), "dump", "badging", apk])
    permissions = run([tools / ("aapt.exe" if os.name == "nt" else "aapt"), "dump", "permissions", apk])
    package = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging)
    minimum = re.search(r"sdkVersion:'(\d+)'", badging)
    target = re.search(r"targetSdkVersion:'(\d+)'", badging)
    if not package or package[1] != "com.pengxh.daily.app":
        raise ValueError("Unexpected application ID")
    if not minimum or int(minimum[1]) != 26 or not target or int(target[1]) != 36:
        raise ValueError("Unexpected Android API requirements; review before distributing")
    if "application-debuggable" in badging:
        raise ValueError("APK must be a non-debuggable release")
    with zipfile.ZipFile(apk) as archive:
        bad_entry = archive.testzip()
        if bad_entry:
            raise ValueError(f"ZIP integrity check failed: {bad_entry}")
        names = archive.namelist()
        if not {"classes.dex", "AndroidManifest.xml", "resources.arsc"}.issubset(names):
            raise ValueError("Missing application contents")
        native = {name: load_alignments(archive.read(name)) for name in names
                  if name.startswith("lib/") and name.endswith(".so")}
        abis = sorted({name.split("/")[1] for name in native})
        if set(abis) != {"armeabi-v7a", "arm64-v8a", "x86", "x86_64"}:
            raise ValueError(f"Unexpected CPU architectures: {abis}")
        if any(f"lib/{abi}/libdaily_task.so" not in native for abi in abis):
            raise ValueError("Missing native watermark library")
        if not all(values and min(values) >= 16384 for values in native.values()):
            raise ValueError("Native library LOAD segments are not aligned for 16 KB pages")
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / apk.name
    if dest.resolve() != apk:
        shutil.copy2(apk, dest)
    sha256 = hashlib.sha256(apk.read_bytes()).hexdigest()
    result = {
        "verified_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "apk": apk.name, "bytes": apk.stat().st_size, "sha256": sha256,
        "application_id": package[1], "version_code": int(package[2]), "version_name": package[3],
        "min_sdk": int(minimum[1]), "target_sdk": int(target[1]), "abis": abis,
        "release_non_debuggable": True, "zip_crc_verified": True,
        "signature_verified": True, "zip_alignment_4k_verified": True,
        "zip_alignment_16k_verified": True,
        "native_elf_load_alignments": native,
        "native_elf_16k_compatible": all(values and min(values) >= 16384 for values in native.values()),
        "device_install_tested": False, "functional_tested": False,
    }
    (args.out / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (args.out / "signature.txt").write_text(signature, encoding="utf-8")
    (args.out / "zipalign.txt").write_text(alignment, encoding="utf-8")
    (args.out / "zipalign-16k.txt").write_text(alignment16, encoding="utf-8")
    (args.out / "package.txt").write_text(badging, encoding="utf-8")
    (args.out / "permissions.txt").write_text(permissions, encoding="utf-8")
    (args.out / "SHA256SUMS.txt").write_text(f"{sha256}  {apk.name}\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(signature)


if __name__ == "__main__":
    main()
