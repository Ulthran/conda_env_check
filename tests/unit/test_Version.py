from src.conda_env_check.Version import Version


def test_version_with_major_minor_patch():
    version = Version("1.2.3")
    assert version.major == "1"
    assert version.minor == "2"
    assert version.patch == "3"
    assert version.build is None


def test_version_with_major_minor_patch_build():
    version = Version("1.2.3-456abc")
    assert version.major == "1"
    assert version.minor == "2"
    assert version.patch == "3"
    assert version.build == "456abc"


def test_version_with_major_only():
    version = Version("1")
    assert version.major == "1"
    assert version.minor is None
    assert version.patch is None
    assert version.build is None


def test_version_with_major_minor():
    version = Version("1.2")
    assert version.major == "1"
    assert version.minor == "2"
    assert version.patch is None
    assert version.build is None


def test_version_with_invalid_characters():
    try:
        version = Version("1.2.3a")
    except ValueError as e:
        assert (
            str(e)
            == "Version string must only contain numbers and periods (other than anything after a dash)\n1.2.3a"
        )


def test_version_with_underscore_separator():
    try:
        version = Version("1_2_3")
    except ValueError as e:
        assert (
            str(e)
            == "Version string must only contain numbers and periods (other than anything after a dash)\n1_2_3"
        )


def test_version_with_no_separator():
    version = Version("123")
    assert version.major == "123"
    assert version.minor is None
    assert version.patch is None
    assert version.build is None
