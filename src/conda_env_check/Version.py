class Version:
    def __init__(self, version_str: str) -> None:
        """Takes in a string of the form "1" or "1.2.3" or "1.2.3-456abc" and parses it into major, minor, patch, and build attributes"""
        if "-" in version_str:
            self.version = version_str.split("-")[0]
        elif "_" in version_str:
            self.version = version_str.split("_")[0]
        else:
            self.version = version_str

        try:
            self.major = int(self.version.split(".")[0])
        except ValueError:
            raise ValueError(
                f"The major version has to be parseable as an int\n{version_str}"
            )
        try:
            self.minor = int(self.version.split(".")[1])
        except (IndexError, ValueError):
            print(f"Minor version either doesn't exist or isn't parseable as an int\n{version_str}")
            self.minor = None
        try:
            self.patch = int(self.version.split(".")[2])
        except (IndexError, ValueError):
            print(f"Patch version either doesn't exist or isn't parseable as an int\n{version_str}")
            self.patch = None
        try:
            self.build = version_str.split("-")[1]
        except IndexError:
            self.build = None

    def __str__(self) -> str:
        return self.version

    def __equals__(self, other) -> bool:
        if not other:
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self.build == other.build
        )

    def same_major(self, other) -> bool:
        if not other:
            return False
        return self.major == other.major

    def same_version(self, other) -> bool:
        if not other:
            return False
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
        )
