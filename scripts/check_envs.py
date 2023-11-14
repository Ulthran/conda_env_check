# Parse command line arguments from sys.argv and use the first arg as a comma-separted list of directories in which
# to find conda environment files.

import glob
import json
import os
import requests
import subprocess as sp
import sys
import yaml
from bs4 import BeautifulSoup
from pathlib import Path
from typing import List, Tuple


class Version:
    def __init__(self, version_str: str) -> None:
        """Takes in a string of the form "1" or "1.2.3" or "1.2.3-456abc" and parses it into major, minor, patch, and build attributes"""
        if "-" in version_str:
            self.version = version_str.split("-")[0]
        else:
            self.version = version_str
        if not set(self.version).issubset(set("0123456789.")):
            raise ValueError(
                f"Version string must only contain numbers and periods (other than anything after a dash)\n{version_str}"
            )

        self.major = self.version.split(".")[0]
        try:
            self.minor = self.version.split(".")[1]
        except IndexError:
            self.minor = None
        try:
            self.patch = self.version.split(".")[2]
        except IndexError:
            self.patch = None
        try:
            self.build = version_str.split("-")[1]
        except IndexError:
            self.build = None

    def __str__(self) -> str:
        return self.version


def get_latest_package_version(channel: str, package: str) -> Version | None:
    # Create the URL for the Anaconda channel/package page
    url = f"https://anaconda.org/{channel}/{package}"

    # Send an HTTP GET request to the URL
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the HTML content of the page
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the element containing package version information
        version_element = soup.find("small", class_="subheader")

        if version_element:
            # Extract the version information
            version = version_element.text.strip()
            return Version(version)

    # If the request was not successful or version information was not found, return None
    return None


class EnvFile:
    def __init__(self, fp: Path) -> None:
        self.fp = fp
        self.name = fp.stem
        print(f"EnvFile: {self.name}")

        self.env_created = lite
        with open(fp, "r") as f:
            env_dict = yaml.safe_load(f)
            self.channels = env_dict.get("channels", [])
            self.dependencies = env_dict.get("dependencies", [])
            self.env_name = env_dict.get("name", "")

        self.should_have_pin = (
            len(
                [
                    d
                    for d in [d for d in self.dependencies if type(d) == dict]
                    if "pip" in d.keys()
                ]
            )
            > 0
        )
        self.dependencies = [
            self.parse_dependecy(dep) for dep in self.dependencies if type(dep) == str
        ]
        self.dependencies = {d[0]: d[1] for d in self.dependencies}
        print({k: str(v) for k, v in self.dependencies.items()})
        self.dependencies = {d: v for d, v in self.dependencies.items() if d != "python"}
        # End up with a dictionary of dependencies and their max versions (as specified in the env file)

        self.updated_env = None

        self.should_have_pin = len(self.dependencies) > 0 or self.should_have_pin

    def check_env_create(self) -> bool:
        args = [
            "conda",
            "env",
            "create",
            "--file",
            self.fp,
            "--name",
            self.name,
            "--dry-run",
            "--json",
        ]
        try:
            output = sp.check_output(args)
            self.updated_env = json.loads(output.decode("utf-8"))
            try:
                self.updated_env["dependencies"] = {
                    s.split("::")[1].split("==")[0]: (
                        s.split("/")[0],
                        Version(s.split("==")[1].split("=")[0]),
                    )
                    for s in self.updated_env["dependencies"]
                }  # Gives a dictionary with {Dependency: (Channel, Version)}
            except KeyError:
                print(f"No dependencies found for {self.name}")
                self.updated_env["dependencies"] = {}
            self.env_created = True
            return True
        except sp.CalledProcessError as e:
            print(f"Could not create environment {self.name}")
            return False

    @staticmethod
    def parse_dependecy(d: str) -> Tuple[str, Version | None]:
        """Parse a dependency string and return a tuple of the dependency name and the max version is it allowed to be by the env file (or None if there is no max version)"""
        dependency = d.split("=")[0].split("<")[0].split(">")[0].strip()
        max = None
        v = None
        if "<" in d or "=" in d:
            if "<" in d:
                v = d.split("<")[1]
            if "=" in d:
                v = d.split("=")[1]
            # This will be off by one if given a version like 3.0.0 (returns 3, should be 2) but I'm just gonna ignore that for now
            try:
                max = Version(v.strip())
            except ValueError:
                pass

        return (dependency, max)


class PinFile:
    def __init__(self, fp: Path, env_file: EnvFile) -> None:
        self.fp = fp
        self.name = fp.stem
        print(f"PinFile: {self.name}")

        self.env_file = env_file
        self.pin_created = lite

        self.pins = {}
        with open(fp, "r") as f:
            for line in f.readlines():
                if any((d := dep) in line for dep in self.env_file.dependencies):
                    self.pins[d] = (
                        line.split("/")[3],
                        Version(line.split("/")[5].split("-")[1]),
                    )  # Dictionary of form {Dependency: (Channel, Version)}
        
        print({k: str(v[1]) for k, v in self.pins.items()})

        self.updated_pins = None

    def check_pin_env_create(self) -> bool:
        args = [
            "conda",
            "env",
            "create",
            "--file",
            self.fp,
            "--name",
            self.name,
            "--dry-run",
            "--json",
        ]
        try:
            output = sp.check_output(args)
            self.pin_created = True
            return True
        except sp.CalledProcessError as e:
            print(f"Could not create environment {self.name} from pin")
            return False

    def pin_env(self) -> bool:
        args = [
            "snakedeploy",
            "pin-conda-envs",
            f"{self.env_file.fp}",
        ]
        try:
            output = sp.check_output(args)

            with open(self.fp, "r") as f:
                self.updated_pins = {}
                for line in f.readlines():
                    if any((d := dep) in line for dep in self.env_file.dependencies):
                        self.updated_pins[d] = (
                            line.split("/")[3],
                            Version(line.split("/")[5].split("-")[1]),
                        )  # Dictionary of form {Dependency: (Channel, Version)}

            return True
        except sp.CalledProcessError as e:
            print(f"Could not pin environment {self.name}")
            return False

    def check_latest_versions(self) -> bool:
        for dep in self.env_file.dependencies.keys():
            if dep in self.pins.keys():
                channel, version = self.pins[dep]
                latest_version = get_latest_package_version(channel, dep)
                if latest_version:
                    if (
                        version.major != latest_version.major
                        and self.env_file.dependencies[dep]
                        and version.major != self.env_file.dependencies[dep].major
                    ):
                        print(
                            f"Major version mismatch for {dep}"
                            f"Current: {version}, Latest: {latest_version}"
                        )
                        return False
                else:
                    print(f"Could not find latest version for {dep}")
            else:
                print(f"Could not find pin for {dep}")
                return False
        return True


def parse_args() -> List[str | bool]:
    if len(sys.argv) < 3:
        print("Usage: python check_envs.py <env_dirs> <lite>")
        sys.exit(1)
    return (sys.argv[1].split(","), bool(sys.argv[2]))


def find_env_files(env_dirs: List[str]) -> List[EnvFile]:
    env_files = []
    for env_dir in env_dirs:
        for filename in os.listdir(env_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                env_files.append(EnvFile(Path(env_dir) / filename))
    return env_files


def find_pin_files(env_files: List[EnvFile]) -> List[PinFile]:
    pin_files = []
    for env_file in env_files:
        for filename in glob.glob(
            f"{str(env_file.fp).replace('.yml', '.').replace('.yaml', '.')}*.pin.txt"
        ):
            pin_files.append(PinFile(Path(filename), env_file))
    return pin_files


print("Starting...")
env_dirs, lite = parse_args()
percentage = 100

# Create EnvFiles for all available env files
env_files = find_env_files(env_dirs)

if not env_files:
    print("No environment files found")
    print(f"Percentage: {percentage}%")
    sys.exit(0)

# Create PinFiles for all available pin files (every PinFile should be linked to an EnvFile)
pin_files = find_pin_files(env_files)

# Designate percentages
lite_factor = 1 if lite else 3
total_files = len(env_files) + len(pin_files) * lite_factor

if not pin_files:
    print(f"No pin files found")
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
                    print(f"PR: {pin_file.name}")
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
        print(f"FAIL: Could not create any env for {pin_file.name}")

print(f"Percentage: {percentage}%")
