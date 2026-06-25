#!/usr/bin/env python3
"""Download photos from a Ricoh GR IIIx via its Wi-Fi HTTP API.

Two modes:

  1) Manual: connect your computer to the camera's Wi-Fi yourself, then run
     the script with no Wi-Fi flags. By default the camera answers at
     192.168.0.1.

  2) Automatic (WSL2 -> Windows host or native Windows): pass --ssid and
     --password (or --password-env). The script asks Windows (via netsh.exe)
     to connect to the camera's Wi-Fi, downloads the photos, and optionally
     disconnects at the end.

History of downloaded files is kept in a small SQLite database, so running
the script multiple times only fetches what's new.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import requests

DEFAULT_HOST = "192.168.0.1"
DEFAULT_DEST = Path("./photos")
DEFAULT_DB = Path("./download_history.db")
LIST_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 120
CHUNK_SIZE = 64 * 1024
CAMERA_PROBE_TIMEOUT = 3
DEFAULT_CONNECT_TIMEOUT = 45


# ---------- Camera HTTP API ----------

def list_photos(host: str) -> list[tuple[str, str]]:
    url = f"http://{host}/v1/photos"
    r = requests.get(url, timeout=LIST_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    photos: list[tuple[str, str]] = []
    for d in data.get("dirs", []):
        dirname = d.get("name") or ""
        for fname in d.get("files", []):
            if dirname and fname:
                photos.append((dirname, fname))
    return photos


def download_photo(host: str, dirname: str, filename: str, dest: Path) -> int:
    url = f"http://{host}/v1/photos/{dirname}/{filename}"
    target_dir = dest / dirname
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    tmp = target.with_suffix(target.suffix + ".part")

    with requests.get(url, stream=True, timeout=DOWNLOAD_TIMEOUT) as r:
        r.raise_for_status()
        size = 0
        with tmp.open("wb") as f:
            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    size += len(chunk)
    tmp.replace(target)
    return size


def wait_for_camera(host: str, timeout: float) -> bool:
    deadline = time.time() + timeout
    url = f"http://{host}/v1/photos"
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=CAMERA_PROBE_TIMEOUT)
            if r.ok:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


# ---------- Wi-Fi (Windows / WSL2 -> Windows) ----------

def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def netsh_cmd() -> list[str]:
    if sys.platform == "win32":
        return ["netsh"]
    if is_wsl() and shutil.which("netsh.exe"):
        return ["netsh.exe"]
    raise RuntimeError(
        "Automatic Wi-Fi only supports Windows or WSL2 with access to netsh.exe. "
        "On other systems, connect to the camera Wi-Fi manually and omit --ssid."
    )


def _build_profile_xml(ssid: str, password: str) -> str:
    ssid_e = xml_escape(ssid)
    pwd_e = xml_escape(password)
    return (
        '<?xml version="1.0"?>\n'
        '<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">\n'
        f"  <name>{ssid_e}</name>\n"
        "  <SSIDConfig>\n"
        f"    <SSID><name>{ssid_e}</name></SSID>\n"
        "  </SSIDConfig>\n"
        "  <connectionType>ESS</connectionType>\n"
        "  <connectionMode>manual</connectionMode>\n"
        "  <MSM>\n"
        "    <security>\n"
        "      <authEncryption>\n"
        "        <authentication>WPA2PSK</authentication>\n"
        "        <encryption>AES</encryption>\n"
        "        <useOneX>false</useOneX>\n"
        "      </authEncryption>\n"
        "      <sharedKey>\n"
        "        <keyType>passPhrase</keyType>\n"
        "        <protected>false</protected>\n"
        f"        <keyMaterial>{pwd_e}</keyMaterial>\n"
        "      </sharedKey>\n"
        "    </security>\n"
        "  </MSM>\n"
        "</WLANProfile>\n"
    )


def _to_windows_path(p: Path) -> str:
    if sys.platform == "win32":
        return str(p)
    r = subprocess.run(["wslpath", "-w", str(p)], capture_output=True, text=True, check=True)
    return r.stdout.strip()


def wifi_connect(ssid: str, password: str | None, connect_timeout: float) -> None:
    """Add a WPA2-PSK profile (if password given) and connect to SSID."""
    netsh = netsh_cmd()

    if password is not None:
        xml = _build_profile_xml(ssid, password)
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-8") as tf:
            tf.write(xml)
            xml_path = Path(tf.name)
        try:
            win_path = _to_windows_path(xml_path)
            r = subprocess.run(
                netsh + ["wlan", "add", "profile", f"filename={win_path}", "user=current"],
                capture_output=True, text=True,
            )
            if r.returncode != 0:
                raise RuntimeError(f"netsh add profile failed: {r.stdout.strip()} {r.stderr.strip()}")
        finally:
            try:
                xml_path.unlink()
            except OSError:
                pass

    r = subprocess.run(
        netsh + ["wlan", "connect", f"name={ssid}", f"ssid={ssid}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"netsh connect failed: {r.stdout.strip()} {r.stderr.strip()}")

    deadline = time.time() + connect_timeout
    while time.time() < deadline:
        if _connected_to(ssid):
            return
        time.sleep(1)
    raise RuntimeError(f"Timed out waiting for Wi-Fi association to {ssid!r}.")


def _connected_to(ssid: str) -> bool:
    try:
        r = subprocess.run(
            netsh_cmd() + ["wlan", "show", "interfaces"],
            capture_output=True, text=True,
        )
    except (RuntimeError, FileNotFoundError):
        return False
    if r.returncode != 0:
        return False
    out = r.stdout
    in_ssid_line = False
    for line in out.splitlines():
        s = line.strip()
        if s.lower().startswith("ssid") and "bssid" not in s.lower():
            _, _, value = s.partition(":")
            if value.strip() == ssid:
                in_ssid_line = True
        if s.lower().startswith("state") and in_ssid_line:
            _, _, value = s.partition(":")
            return "connected" in value.strip().lower()
    return False


def wifi_disconnect() -> None:
    try:
        subprocess.run(netsh_cmd() + ["wlan", "disconnect"], capture_output=True, text=True)
    except (RuntimeError, FileNotFoundError):
        pass


# ---------- History (SQLite) ----------

def open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS downloads (
            dirname       TEXT NOT NULL,
            filename      TEXT NOT NULL,
            size_bytes    INTEGER NOT NULL,
            downloaded_at TEXT NOT NULL,
            PRIMARY KEY (dirname, filename)
        )
        """
    )
    conn.commit()
    return conn


def already_downloaded(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    cur = conn.execute("SELECT dirname, filename FROM downloads")
    return {(d, f) for d, f in cur.fetchall()}


def record_download(conn: sqlite3.Connection, dirname: str, filename: str, size: int) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO downloads (dirname, filename, size_bytes, downloaded_at) VALUES (?, ?, ?, ?)",
        (dirname, filename, size, datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    conn.commit()


def reset_history(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM downloads")
    conn.commit()


# ---------- CLI ----------

def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--host", default=DEFAULT_HOST, help=f"Camera IP (default: {DEFAULT_HOST})")
    p.add_argument("--dest", type=Path, default=DEFAULT_DEST, help=f"Destination folder (default: {DEFAULT_DEST})")
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help=f"SQLite history file (default: {DEFAULT_DB})")
    p.add_argument("--reset-history", action="store_true", help="Wipe history and re-download everything")
    p.add_argument("--dry-run", action="store_true", help="List what would be downloaded; don't download")
    p.add_argument("--ext", action="append", default=None, help="Only files with these extensions (e.g. --ext JPG --ext DNG)")

    g = p.add_argument_group("Wi-Fi (Windows or WSL2)")
    g.add_argument("--ssid", help="Camera Wi-Fi SSID. If given, connect automatically before download.")
    g.add_argument("--password", help="Wi-Fi password (WPA2-PSK). Avoid on shared machines; prefer --password-env.")
    g.add_argument("--password-env", help="Env var name to read the password from (e.g. RICOH_WIFI_PASS)")
    g.add_argument("--connect-timeout", type=float, default=DEFAULT_CONNECT_TIMEOUT, help=f"Seconds to wait for Wi-Fi (default: {DEFAULT_CONNECT_TIMEOUT})")
    g.add_argument("--camera-ready-timeout", type=float, default=15.0, help="Seconds to wait for the camera HTTP API after associating (default: 15)")
    g.add_argument("--no-disconnect", action="store_true", help="Don't disconnect the Wi-Fi when finished")

    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.dest.mkdir(parents=True, exist_ok=True)

    password: str | None = None
    if args.password and args.password_env:
        print("ERROR: use either --password or --password-env, not both.", file=sys.stderr)
        return 2
    if args.password:
        password = args.password
    elif args.password_env:
        password = os.environ.get(args.password_env)
        if not password:
            print(f"ERROR: environment variable {args.password_env!r} is empty or unset.", file=sys.stderr)
            return 2

    connected_by_us = False
    if args.ssid:
        try:
            if _connected_to(args.ssid):
                print(f"Already connected to {args.ssid!r}.")
            else:
                print(f"Connecting to Wi-Fi {args.ssid!r} ...")
                wifi_connect(args.ssid, password, args.connect_timeout)
                connected_by_us = True
                print("Wi-Fi associated. Waiting for camera HTTP to come up ...")
                if not wait_for_camera(args.host, args.camera_ready_timeout):
                    print(f"WARNING: camera at {args.host} not responding yet; continuing anyway.", file=sys.stderr)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print("Hints:", file=sys.stderr)
            print("  - On Windows, Location services may need to be ON (Privacy & security).", file=sys.stderr)
            print("  - Some operations require running the terminal as administrator.", file=sys.stderr)
            print("  - On WSL2, default NAT networking may not reach 192.168.0.1; enable mirrored networking", file=sys.stderr)
            print("    in %USERPROFILE%\\.wslconfig:  [wsl2]\\n networkingMode=mirrored", file=sys.stderr)
            return 1

    conn = open_db(args.db)
    if args.reset_history:
        reset_history(conn)

    print(f"Listing photos at http://{args.host} ...")
    try:
        photos = list_photos(args.host)
    except requests.RequestException as e:
        print(f"ERROR: could not reach the camera ({e}).", file=sys.stderr)
        if connected_by_us and not args.no_disconnect:
            wifi_disconnect()
        return 1

    if args.ext:
        wanted = {e.lower().lstrip(".") for e in args.ext}
        photos = [(d, f) for d, f in photos if f.rsplit(".", 1)[-1].lower() in wanted]

    done = already_downloaded(conn)
    pending = [(d, f) for d, f in photos if (d, f) not in done]
    print(f"Camera reports {len(photos)} photo(s); {len(pending)} new, {len(photos) - len(pending)} already downloaded.")

    rc = 0
    if pending and not args.dry_run:
        downloaded = 0
        failed = 0
        total_bytes = 0
        start = time.time()
        for i, (d, f) in enumerate(pending, 1):
            try:
                size = download_photo(args.host, d, f, args.dest)
                record_download(conn, d, f, size)
                total_bytes += size
                downloaded += 1
                print(f"[{i}/{len(pending)}] {d}/{f}  {human_size(size)}")
            except (requests.RequestException, OSError) as e:
                failed += 1
                print(f"[{i}/{len(pending)}] FAILED {d}/{f}: {e}", file=sys.stderr)
        elapsed = time.time() - start
        print(f"\nDone in {elapsed:.1f}s. Downloaded: {downloaded} ({human_size(total_bytes)}). Failed: {failed}.")
        rc = 0 if failed == 0 else 2
    elif args.dry_run:
        for d, f in pending:
            print(f"  would download: {d}/{f}")

    if connected_by_us and not args.no_disconnect:
        print("Disconnecting Wi-Fi.")
        wifi_disconnect()

    return rc


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)
