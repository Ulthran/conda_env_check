import json
import subprocess as sp
import yaml
from pathlib import Path
from typing import Tuple

from .Version import Version

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