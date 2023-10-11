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


class Version:
    def __init__(self, version_str: str) -> None:
        if "-" in version_str:
            self.version = version_str.split("-")[1]
        else:
            self.version = version_str
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
            self.build = version_str.split("-")[2].split(".")[0]
        except IndexError:
            self.build = None

    def __str__(self) -> str:
        return self.version


class Env:
    def __init__(self, env_fp: Path, pin_fp: Path) -> None:
        self.env_fp = env_fp
        self.pin_fp = pin_fp
        self.name = env_fp.stem
        with open(env_fp, "r") as f:
            env_dict = yaml.safe_load(f)
            self.channels = env_dict.get("channels")
            self.dependencies = env_dict.get("dependencies")

        self.dependencies = [
            dep.split("=")[0] for dep in self.dependencies if type(dep) == str
        ]
        self.dependencies = [
            dep.split("<")[0] for dep in self.dependencies if type(dep) == str
        ]
        self.dependencies = [
            dep.split(">")[0] for dep in self.dependencies if type(dep) == str
        ]

        self.updated_env = None

        with open(pin_fp, "r") as f:
            self.pins = {}
            for line in f.readlines():
                if any((d := dep) in line for dep in self.dependencies):
                    self.pins[d] = (
                        line.split("/")[3],
                        Version(line.split("/")[5]),
                    )  # (Channel, Version)

        self.warnings = []
        self.issues = []

    def check_pin_env_create(self) -> bool:
        args = [
            "conda",
            "env",
            "create",
            "--file",
            self.pin_fp,
            "--name",
            self.name,
            "--dry-run",
            "--json",
        ]
        try:
            output = sp.check_output(args)
            return True
        except sp.CalledProcessError as e:
            self.issues.append(
                [f"Could not create environment {self.name} from pin", e.output]
            )
            return False

    def check_env_create(self) -> bool:
        args = [
            "conda",
            "env",
            "create",
            "--file",
            self.env_fp,
            "--name",
            self.name,
            "--dry-run",
            "--json",
        ]
        try:
            output = sp.check_output(args)
            self.updated_env = json.loads(output.decode("utf-8"))
            self.updated_env["dependencies"] = {
                s.split("::")[1].split("==")[0]: (
                    s.split("/")[0],
                    Version(s.split("==")[1].split("=")[0]),
                )
                for s in self.updated_env["dependencies"]
            }  # Dependency: (Channel, Version)
            return True
        except sp.CalledProcessError as e:
            self.issues.append([f"Could not create environment {self.name}", e.output])
            return False

    def check_updated_versions(self) -> bool:
        if not self.updated_env:
            self.warnings.append("No updated environment found")
            return False
        for dep in self.dependencies:
            if dep in self.updated_env["dependencies"].keys():
                channel, version = self.updated_env["dependencies"][dep]
                current_channel, current_version = self.pins.get(dep)
                if version.major != current_version.major:
                    self.issues.append(
                        [
                            f"Major version mismatch for {dep}",
                            f"Current: {current_version}, Updated: {version}",
                        ]
                    )
                    return False
                if version.minor != current_version.minor:
                    self.warnings.append(
                        f"Minor version mismatch for {dep}. Current: {current_version}, Updated: {version}"
                    )
        return True

    def check_latest_versions(self) -> bool:
        for dep in self.dependencies:
            if dep in self.pins.keys():
                channel, version = self.pins[dep]
                latest_version = Version(self.get_latest_package_version(channel, dep))
                if latest_version:
                    if version.major != latest_version.major:
                        self.issues.append(
                            [
                                f"Major version mismatch for {dep}",
                                f"Current: {version}, Latest: {latest_version}",
                            ]
                        )
                        return False
                    if version.minor != latest_version.minor:
                        self.warnings.append(
                            f"Minor version mismatch for {dep}. Current: {version}, Latest: {latest_version}"
                        )
                else:
                    self.warnings.append(f"Could not find latest version for {dep}")
            else:
                self.warnings.append(f"Could not find pin for {dep}")
        return True

    @staticmethod
    def get_latest_package_version(channel, package):
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
                return version

        # If the request was not successful or version information was not found, return None
        return None


class EnvFile:
    def __init__(self, fp: Path) -> None:
        self.fp = fp
        self.name = fp.stem


class PinFile:
    def __init__(self, fp: Path) -> None:
        self.fp = fp
        self.name = fp.stem

        with open(fp, "r") as f:
            lines = f.readlines()
        with open(fp, "w") as f:
            for line in lines:
                if not (line.startswith("#") or line.startswith("@")):
                    f.write(line)


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
