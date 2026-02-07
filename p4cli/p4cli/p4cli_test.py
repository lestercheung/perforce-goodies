#!/usr/bin/env python3


from p4cli import P4CLI
import pytest

import socket
import os
import subprocess

def find_free_port() -> int|None:
    for port in range(1666, 65535):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                # s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(("127.0.0.1", port))
                p4port = s.getsockname()[1]
                s.close()
            break
        except OSError:
            continue
    if p4port:
        return p4port
    return None

import tempfile
import shutil
import time

def rm_rf(path, attempts=5):
    for _ in range(attempts):
        try:
            shutil.rmtree(path)
            return
        except OSError:
            print(f"Failed to remove {path}, retrying...")
            time.sleep(1)
    raise RuntimeError(f"Failed to remove {path} after {attempts} attempts.")
    # subprocess.check_call([shutil.which("rm"), "-rf", path])

@pytest.fixture(autouse=True, scope="module")
def p4d_instance():
    p4port = find_free_port()
    p4dbin = shutil.which("p4d")
    p4bin = shutil.which("p4")
    p4root = tempfile.mkdtemp(prefix="p4d_test_")
    print(f"Starting p4d on port {p4port} with root {p4root}\n")

    subprocess.check_call([p4dbin, "-p", str(p4port), "-r", p4root, "-L", os.path.join(p4root, "log"), "-d"])

    try:
        yield dict(p4dbin=p4bin, p4port=p4port, p4root=p4root)
    finally:
        # Cleanup code here (e.g., stop p4d, remove temp directory)
        subprocess.check_call([p4bin, "-p", str(p4port), "admin", "stop"])
        # time.sleep(1)  # Give p4d some time to shut down before removing the directory
        rm_rf(p4root)


def test_p4root(p4d_instance):
    assert type(p4d_instance["p4port"]) is int
    assert os.path.isdir(p4d_instance["p4root"])
    # time.sleep(1)
    # assert os.path.isfile(os.path.join(p4d_instance["p4root"], "db.job"))

def test_p4cli_connect(p4d_instance):
    p4 = P4CLI(port=p4d_instance["p4port"])
    info = p4.run_info()
    assert info[0]['serverAddress'].endswith(str(p4d_instance["p4port"]))