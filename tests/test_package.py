# SPDX-License-Identifier: GPL-2.0

import pathlib

import pytest
from helper import ExpectedDiff, run_spdx_diff_check

testdata1 = [
    ("test-new-package.spdx.json", "4.3"),
    ("test-new-package-version.spdx.json", "4.4"),
]


@pytest.mark.parametrize("sbom_new_name,i2c_tools_version", testdata1)
def test_new_pkg_with_proprietary(
    tmp_dir: pathlib.Path,
    sbom_data: pathlib.Path,
    sbom_new_name: str,
    i2c_tools_version: str,
) -> None:
    exp = ExpectedDiff()
    exp.package_added("example", "0.1")
    exp.package_added("i2c-tools", i2c_tools_version)
    exp.package_added("libacl1", "2.3.2")
    exp.package_added("libattr1", "2.5.1")
    exp.package_added("libpopt0", "1.19")
    exp.package_added("rsync", "3.2.7")
    exp.package_removed("libgcc1", "13.4.0")
    exp.package_removed("libstdc++6", "13.4.0")
    exp.package_removed("zstd", "1.5.5")

    run_spdx_diff_check(
        tmp_dir,
        sbom_data,
        "reference-sbom.spdx.json",
        sbom_new_name,
        exp,
    )


@pytest.mark.parametrize("sbom_new_name,i2c_tools_version", testdata1)
def test_new_pkg_ign_proprietary(
    tmp_dir: pathlib.Path,
    sbom_data: pathlib.Path,
    sbom_new_name: str,
    i2c_tools_version: str,
) -> None:
    exp = ExpectedDiff()
    exp.package_added("i2c-tools", i2c_tools_version)
    exp.package_added("libacl1", "2.3.2")
    exp.package_added("libattr1", "2.5.1")
    exp.package_added("libpopt0", "1.19")
    exp.package_added("rsync", "3.2.7")
    exp.package_removed("libgcc1", "13.4.0")
    exp.package_removed("libstdc++6", "13.4.0")
    exp.package_removed("zstd", "1.5.5")

    run_spdx_diff_check(
        tmp_dir,
        sbom_data,
        "reference-sbom.spdx.json",
        sbom_new_name,
        exp,
        ["--no-packages-proprietary"],
    )


def test_version_updated(tmp_dir: pathlib.Path, sbom_data: pathlib.Path) -> None:
    exp = ExpectedDiff()
    exp.same_expect_ignore_proprietary = True
    exp.package_changed("i2c-tools", "4.3", "4.4")

    run_spdx_diff_check(
        tmp_dir,
        sbom_data,
        "test-new-package.spdx.json",
        "test-new-package-version.spdx.json",
        exp,
    )
