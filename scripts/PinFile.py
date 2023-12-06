import subprocess as sp
from pathlib import Path

from . import get_latest_package_version
from .EnvFile import EnvFile
from .Version import Version

class PinFile:
    def __init__(self, fp: Path, env_file: EnvFile, lite: bool = False) -> None:
        self.fp = fp
        self.name = fp.stem
        print(f"PinFile: {self.name}")

        self.env_file = env_file
        self.pin_created = lite

        self.pins = {}
        with open(fp, "r") as f:
            for line in f.readlines():
                if any((d := f"/{dep}-") in line for dep in self.env_file.dependencies):
                    self.pins[d[1:][:-1]] = (
                        line.split("/")[3],
                        Version(line.split(d)[1].split("-")[0]),
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