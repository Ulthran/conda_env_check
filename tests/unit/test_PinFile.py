from src.conda_env_check.PinFile import PinFile
from src.conda_env_check.EnvFile import EnvFile
from src.conda_env_check.Version import Version
from pathlib import Path
import pytest


envs_fp = Path(__file__).parent.parent / "envs"


@pytest.fixture
def uptodate_env_file():
    env_file = EnvFile(envs_fp / "uptodate.yml")
    return env_file


@pytest.fixture
def outofdate_env_file():
    env_file = EnvFile(envs_fp / "outofdate.yml")
    return env_file


@pytest.fixture
def rotten_env_file():
    env_file = EnvFile(envs_fp / "rotten.yml")
    return env_file


def test_pinfile_init(uptodate_env_file):
    fp = envs_fp / "uptodate.linux-64.pin.txt"
    pinfile = PinFile(fp, uptodate_env_file)
    assert pinfile.fp == fp
    assert pinfile.name == "uptodate.linux-64.pin"
    assert pinfile.env_file == uptodate_env_file
    assert pinfile.pin_created == False
    assert pinfile.pins["pandas"][0] == "anaconda"
    assert pinfile.pins["pandas"][1].same_major(Version("2"))


def test_check_latest_versions_uptodate(uptodate_env_file):
    fp = envs_fp / "uptodate.linux-64.pin.txt"
    pinfile = PinFile(fp, uptodate_env_file)
    assert pinfile.check_latest_versions() == True


def test_check_latest_versions_outofdate(outofdate_env_file):
    fp = envs_fp / "outofdate.linux-64.pin.txt"
    pinfile = PinFile(fp, outofdate_env_file)
    assert pinfile.check_latest_versions() == False
