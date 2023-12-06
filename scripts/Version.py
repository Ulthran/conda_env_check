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