# Parse command line arguments from sys.argv and use the first arg as a comma-separted list of directories in which
# to find conda environment files.

import glob
import os
import sys
from pathlib import Path

from .Env import Env
from .File import EnvFile, PinFile


def parse_args() -> list:
    if len(sys.argv) < 3:
        print("Usage: python check_envs.py <env_dirs> <lite>")
        sys.exit(1)
    return (sys.argv[1].split(","), bool(sys.argv[2]))


def find_env_files(env_dirs: list) -> list:
    env_files = []
    for env_dir in env_dirs:
        for filename in os.listdir(env_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                env_files.append(EnvFile(Path(env_dir) / filename))
    return env_files


def find_pin_files(env_files: list) -> list:
    pin_files = []
    for env_file in env_files:
        for filename in glob.glob(
            f"{str(env_file.fp).replace('.yml', '.').replace('.yaml', '.')}*.pin.txt"
        ):
            pin_files.append(PinFile(Path(filename)))
    return pin_files


env_dirs, lite = parse_args()
env_files = find_env_files(env_dirs)
pin_files = find_pin_files(env_files)
net_frac = 0
for env_file in env_files:
    env_pin_files = [
        pin_file for pin_file in pin_files if env_file.name in pin_file.name
    ]
    for pin_file in env_pin_files:
        env = Env(env_file.fp, pin_file.fp)

        if not lite:
            try_pin = env.check_pin_env_create()
            try_solve = env.check_env_create()
            if not (try_pin or try_solve):
                print(
                    f"FAIL: Could not create environment {env.name} with pin or solve"
                )

        env.check_updated_versions()
        env.check_latest_versions()
        print(f"Environment: {env.name}")
        print(f"Warnings: {env.warnings}")
        print(f"Issues: {env.issues}")

        frac = 1 - (0.9 * len(env.issues) + 0.1 * len(env.warnings)) / len(
            env.dependencies
        )
        print(f"Fraction: {frac}")
        net_frac += frac

try:
    print(f"Percentage: {round((net_frac / len(pin_files)) * 100)}%")
except ZeroDivisionError:
    pass
