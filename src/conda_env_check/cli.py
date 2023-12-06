import argparse
import glob
import os
import sys
from pathlib import Path
from typing import List

from .EnvFile import EnvFile
from .PinFile import PinFile


def find_env_files(env_dirs: List[str], lite: bool) -> List[EnvFile]:
    env_files = []
    for env_dir in env_dirs:
        for filename in os.listdir(env_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                env_files.append(EnvFile(Path(env_dir) / filename, lite))
    return env_files


def find_pin_files(env_files: List[EnvFile], lite: bool) -> List[PinFile]:
    pin_files = []
    for env_file in env_files:
        for filename in glob.glob(
            f"{str(env_file.fp).replace('.yml', '.').replace('.yaml', '.')}*.pin.txt"
        ):
            pin_files.append(PinFile(Path(filename), env_file, lite))
    return pin_files


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--envs", type=str, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--lite", action="store_true")

    args = p.parse_args(argv)

    print("Starting...")
    env_dirs = args.envs.split(",")
    lite = args.lite
    out = open(args.out, "w")
    percentage = 100

    # Create EnvFiles for all available env files
    env_files = find_env_files(env_dirs, lite)

    if not env_files:
        out.write("No environment files found")
        out.write(f"Percentage: {percentage}%")
        sys.exit(0)

    # Create PinFiles for all available pin files (every PinFile should be linked to an EnvFile)
    pin_files = find_pin_files(env_files, lite)

    # Designate percentages
    lite_factor = 1 if lite else 3
    total_files = len(env_files) + len(pin_files) * lite_factor

    if not pin_files:
        out.write(f"No pin files found")
    else:
        # Iterate over PinFiles
        for pin_file in pin_files:
            # Check that pinned envs can be created
            if not lite:
                try_pin = pin_file.check_pin_env_create()
                if not try_pin:
                    percentage -= 1 / total_files
            # Check that snakedeploy pin-conda-envs doesn't update major versions of packages and PR if it does
            if not lite:
                try_pin = pin_file.pin_env()
                if try_pin:
                    compare = pin_file.compare_updated_pins()
                    if compare:
                        out.write(f"PR: {pin_file.name}")
                else:
                    percentage -= 1 / total_files
            # Check that created envs major versions are up to date with latest
            compare = pin_file.check_latest_versions()
            if not compare:
                percentage -= 1 / total_files

    # Iterate over EnvFiles and check that envs can be created
    for env_file in env_files:
        # Check that created envs major versions are up to date with latest
        if not lite:
            # Only run if no pin file (redundant with pin_file.pin_env())
            if not env_file.should_have_pin:
                try_solve = env_file.check_env_create()
                if not try_solve:
                    percentage -= 1 / total_files

    # Check that at least one env create method was successful for each env/platform
    for pin_file in pin_files:
        if not (pin_file.pin_created and pin_file.env_file.env_created):
            out.write(f"FAIL: Could not create any env for {pin_file.name}")

    out.write(f"Percentage: {percentage}%")
    out.close()
