from pathlib import Path
from scripts.EnvFile import EnvFile
from scripts.Version import Version


envs_fp = Path(__file__).parent.parent / "envs"


def test_env_file_init():
    fp = envs_fp / "uptodate.yml"
    env_file = EnvFile(fp)
    assert env_file.fp == fp
    assert env_file.name == "uptodate"
    assert env_file.env_created is False
    assert env_file.channels == ["conda-forge"]
    assert env_file.dependencies["cutadapt"].same_major(Version("4"))
    assert env_file.env_name == "uptodate"
    assert env_file.should_have_pin is True
    assert env_file.updated_env is None

def test_env_file_parse_dependency():
    dependency = "numpy=1.19.2"
    parsed_dependency = EnvFile.parse_dependency(dependency)
    assert parsed_dependency[0] == "numpy"
    assert parsed_dependency[1].same_version(Version("1.19.2")), f"{parsed_dependency[1]} != {Version('1.19.2')}"

    dependency = "pandas>=1.0.0"
    parsed_dependency = EnvFile.parse_dependency(dependency)
    assert parsed_dependency[0] == "pandas"
    assert parsed_dependency[1].same_version(Version("1.0.0")), f"{parsed_dependency[1]} != {Version('1.0.0')}"