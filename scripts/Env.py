import json
import requests
import subprocess as sp
import yaml
from bs4 import BeautifulSoup
from pathlib import Path

from .Version import Version

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