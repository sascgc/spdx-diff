# SPDX-License-Identifier: GPL-2.0

import json
import os
import pathlib
import subprocess
from typing import Any


def exec_tool(tmp_dir: pathlib.Path, args: list[str]) -> None:
    cmd = ["spdx-diff"]
    cmd.extend(args)

    subprocess.run(
        cmd,
        input="",
        capture_output=True,
        check=True,
        cwd=tmp_dir,
        encoding="utf-8",
    )


class ExpectedDiff:
    def __init__(self) -> None:
        self._json: dict[str, Any] = {
            "package_diff": {"added": {}, "removed": {}, "changed": {}},
            "kernel_config_diff": {"added": {}, "removed": {}, "changed": {}},
            "packageconfig_diff": {"added": {}, "removed": {}, "changed": {}},
        }

        self.same_expect_ignore_proprietary = False

    def package_added(self, name: str, version: str) -> None:
        self._json["package_diff"]["added"][name] = version

    def package_removed(self, name: str, version: str) -> None:
        self._json["package_diff"]["removed"][name] = version

    def package_changed(self, name: str, old_version: str, new_version: str) -> None:
        self._json["package_diff"]["changed"][name] = {
            "from": old_version,
            "to": new_version,
        }

    def kernel_config_added(self, name: str, module_state: str) -> None:
        self._json["kernel_config_diff"]["added"][name] = module_state

    def kernel_config_removed(self, name: str, module_state: str) -> None:
        self._json["kernel_config_diff"]["removed"][name] = module_state

    def kernel_config_changed(self, name: str, old_state: str, new_state: str) -> None:
        self._json["kernel_config_diff"]["changed"][name] = {
            "from": old_state,
            "to": new_state,
        }

    def packageconfig_added_pkg(self, name: str, features: dict[str, str]) -> None:
        self._json["packageconfig_diff"]["added"][name] = features

    def packageconfig_removed_pkg(self, name: str, features: dict[str, str]) -> None:
        self._json["packageconfig_diff"]["removed"][name] = features

    def packageconfig_changed_add(self, name: str, features: dict[str, str]) -> None:
        d = self._json["packageconfig_diff"]["changed"].setdefault(name, {})
        d["added"] = features

    def packageconfig_changed_rm(self, name: str, features: dict[str, str]) -> None:
        d = self._json["packageconfig_diff"]["changed"].setdefault(name, {})
        d["removed"] = features

    def packageconfig_changed_mod(
        self, name: str, feature: str, old_state: str, new_state: str
    ) -> None:
        d = self._json["packageconfig_diff"]["changed"].setdefault(
            name, {"added": {}, "removed": {}, "changed": {}}
        )
        d["changed"][feature] = {
            "from": old_state,
            "to": new_state,
        }

    def check(self, json_data: dict[str, Any]) -> None:
        assert json_data == self._json, (
            f"tested: {json.dumps(json_data, indent=4)}\n\n"
            f"expected: {json.dumps(self._json, indent=4)}\n"
        )


def _run_spdx_diff_check(
    tmp_dir: pathlib.Path,
    out_name: str,
    sbom_data_path: pathlib.Path,
    sbom_ref: str,
    sbom_new: str,
    exp_diff: ExpectedDiff,
    extra_args: list[str],
) -> None:
    out_path = tmp_dir.joinpath(out_name)
    exec_tool(
        tmp_dir,
        [
            os.fspath(sbom_data_path.joinpath(sbom_ref).resolve(strict=True)),
            os.fspath(sbom_data_path.joinpath(sbom_new).resolve(strict=True)),
            "--json-output",
            os.fspath(out_path),
            *extra_args,
        ],
    )

    with out_path.open(encoding="utf-8") as f:
        ret_diff = json.load(f)

    exp_diff.check(ret_diff)


def run_spdx_diff_check(
    tmp_dir: pathlib.Path,
    sbom_data_path: pathlib.Path,
    sbom_ref: str,
    sbom_new: str,
    exp_diff: ExpectedDiff,
    extra_args: list[str] | None = None,
) -> None:
    if extra_args is None:
        extra_args = []

    _run_spdx_diff_check(
        tmp_dir,
        "diff.json",
        sbom_data_path,
        sbom_ref,
        sbom_new,
        exp_diff,
        extra_args,
    )

    if exp_diff.same_expect_ignore_proprietary:
        _run_spdx_diff_check(
            tmp_dir,
            "diff2.json",
            sbom_data_path,
            sbom_ref,
            sbom_new,
            exp_diff,
            ["--no-packages-proprietary", *extra_args],
        )
