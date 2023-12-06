from pathlib import Path


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