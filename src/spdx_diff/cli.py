#
# SPDX-License-Identifier: GPL-2.0

import json
import logging
import pathlib
import re
from argparse import ArgumentParser, ArgumentTypeError
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from . import __version__

_logger = logging.getLogger(__name__)


class Spdx3Sbom:
    """
    Class that allow to parse SPDX3 JSON files.

    :ivar packages: mapping of package names to versions
    :ivar config: mapping of CONFIG_* keys to their values
    :ivar packageconfig: mapping of package names to their PACKAGECONFIG features
    """

    def __init__(self, json_path: pathlib.Path) -> None:
        """
        Constructor for Spdx3Sbom class.

        :param json_path: Path the JSON file to parse.
        """
        self._graph: list[dict[str, Any]] = []
        self._map_id_node: dict[str, dict[str, Any]] = {}
        self._map_rel_license: dict[str, set[str]] = defaultdict(set)

        self.packages: dict[str, str] = {}
        self.config: dict[str, Any] = {}
        self.packageconfig: dict[str, dict[str, str]] = defaultdict(dict)

        self._parse(json_path)

    def _parse(self, json_path: pathlib.Path) -> None:
        """
        Parse SPDX3 JSON files.

        :param json_path: Path the JSON file.
        """
        _logger.info("Opening SPDX file: %s", json_path)
        try:
            with json_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as e:
            raise ValueError("Failed to read or parse %s", json_path) from e

        graph = data.get("@graph")
        if not isinstance(graph, list):
            raise TypeError("SPDX3 file format is not recognized.")

        _logger.debug("Found %d elements in the SPDX3 document.", len(graph))
        self._graph = graph

        # Index each nodes
        for item in graph:
            # Update map between spdxId and node object
            spdx_id: str | None = item.get("spdxId")
            if not spdx_id:
                continue

            self._map_id_node[spdx_id] = item

            # Update map between element spdxId and one or multiple license spdxId
            if (
                item.get("type") == "Relationship"
                and item.get("relationshipType") == "hasConcludedLicense"
            ):
                self._map_rel_license[item["from"]].update(item["to"])

    def is_package_proprietary(self, pkg: dict[str, Any]) -> bool:
        """
        Check if the software_Package is a proprietary package.

        :param pkg: The JSON graph node representing a package.
        :return: True if this is a proprietary package, False otherwise.
        """
        spdx_id: str | None = pkg.get("spdxId")
        if not spdx_id:
            return False

        license_ids = self._map_rel_license.get(spdx_id)
        if not license_ids:
            return False

        for license_id in license_ids:
            license_node = self._map_id_node.get(license_id)
            if not license_node:
                continue

            if license_node.get("type") != "simplelicensing_LicenseExpression":
                continue

            if (
                license_node.get("simplelicensing_licenseExpression")
                == "LicenseRef-Proprietary"
            ):
                return True

        return False

    @staticmethod
    def normalize_package_name(name: str) -> str:
        """
        Normalize package names, especially for kernel and kernel-modules.

        :return: The normalized package name

        Examples:
            "kernel-6.12.43-00469-g647daef97a89" -> "kernel"
            "kernel-module-8021q-6.12.43-00469-g647daef97a89" -> "kernel-module-8021q"

        """
        # Pattern to match kernel version suffixes
        # Matches: X.Y.Z followed by any combination of alphanumeric, dots, underscores,
        # hyphens
        # Examples:
        #   - 6.12.43-linux-00469-g647daef97a89 (git-based)
        #   - 6.6.111-yocto-standard (branch-based)
        #   - 6.1.38-rt13 (RT kernel)
        kernel_version_pattern = r"-(\d+\.\d+(?:\.\d+)?[a-zA-Z0-9._-]*)$"

        match = re.search(kernel_version_pattern, name)
        return name[: match.start()] if match else name

    def extract_spdx_data(self, ignore_proprietary: bool = False) -> None:
        """
        Extract SPDX information (packages, kernel CONFIG, and PACKAGECONFIG).

        Extract SPDX package data, kernel CONFIG options, and PACKAGECONFIG entries from
        the SPDX JSON file. Kernel packages are automatically normalized.

        :param ignore_proprietary: Whether to skip proprietary packages
        """
        build_count = 0

        for item in self._graph:
            # Extract packages
            if item.get("type") == "software_Package":
                pkg_name: str | None = item.get("name")
                version: str | None = item.get("software_packageVersion")
                if not pkg_name or not version:
                    continue

                if ignore_proprietary and self.is_package_proprietary(item):
                    _logger.info("Ignoring proprietary package: %s", pkg_name)
                    continue

                sw_primary_purpose: str | None = item.get("software_primaryPurpose")
                if sw_primary_purpose != "install":
                    continue

                # Always normalize kernel package names
                if pkg_name.startswith("kernel-") or pkg_name == "kernel":
                    normalized_name = self.normalize_package_name(pkg_name)
                    self.packages[normalized_name] = version
                else:
                    self.packages[pkg_name] = version

            # Extract kernel config and PACKAGECONFIG
            if item.get("type") == "build_Build":
                build_count += 1

                build_name = item.get("name", "")
                recipe_name: str | None = None
                if ":" in build_name:
                    recipe_name, _ = build_name.split(":", maxsplit=1)

                for param in item.get("build_parameter", []):
                    if not isinstance(param, dict):
                        continue
                    key = param.get("key")
                    value = param.get("value")
                    if not key or value is None:
                        continue

                    if key.startswith("CONFIG_"):
                        self.config[key] = value
                    elif key.startswith("PACKAGECONFIG:") and recipe_name:
                        _, feature = key.split(":", maxsplit=1)
                        self.packageconfig[recipe_name][feature] = value

        if build_count == 0:
            _logger.warning("No build_Build objects found.")

        _logger.debug(
            "Extracted %d packages, %d CONFIG_*, "
            "and %d packages with PACKAGECONFIG entries.",
            len(self.packages),
            len(self.config),
            len(self.packageconfig),
        )


def compare_dicts(
    ref: dict[str, Any], new: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """
    Compare two dictionaries and return added, removed, and changed items.

    Args:
        ref: Reference dictionary
        new: New dictionary to compare

    Returns:
        tuple[dict, dict, dict]: added, removed, changed items

    """
    added = {k: v for k, v in new.items() if k not in ref}
    removed = {k: v for k, v in ref.items() if k not in new}
    changed = {
        k: {"from": ref[k], "to": new[k]} for k in ref if k in new and ref[k] != new[k]
    }
    return added, removed, changed


def compare_packageconfig(
    ref_pcfg: dict[str, dict[str, str]], new_pcfg: dict[str, dict[str, str]]
) -> tuple[
    dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, Any]]
]:
    """
    Compare PACKAGECONFIG dictionaries.

    Args:
        ref_pcfg: Reference PACKAGECONFIG mapping
        new_pcfg: New PACKAGECONFIG mapping

    Returns:
        tuple: added packages, removed packages, changed features per package

    """
    added_pkgs = {k: v for k, v in new_pcfg.items() if k not in ref_pcfg}
    removed_pkgs = {k: v for k, v in ref_pcfg.items() if k not in new_pcfg}

    changed_pkgs = {}
    for pkg, ref_features in ref_pcfg.items():
        new_features = new_pcfg.get(pkg)
        if new_features is None:
            continue

        added_features = {
            k: v for k, v in new_features.items() if k not in ref_features
        }
        removed_features = {
            k: v for k, v in ref_features.items() if k not in new_features
        }
        changed_features = {
            k: {"from": ref_features[k], "to": new_features[k]}
            for k in ref_features
            if k in new_features and ref_features[k] != new_features[k]
        }

        if added_features or removed_features or changed_features:
            changed_pkgs[pkg] = {
                "added": added_features,
                "removed": removed_features,
                "changed": changed_features,
            }

    return added_pkgs, removed_pkgs, changed_pkgs


def print_diff(
    title: str,
    added: dict[str, Any],
    removed: dict[str, Any],
    changed: dict[str, Any],
    *,
) -> None:
    """
    Print differences between items.

    Args:
        title: Section title
        added: Added items
        removed: Removed items
        changed: Changed items
    """
    if added:
        print(f"\n{title} - Added:")
        for k in sorted(added):
            print(f" + {k}" if isinstance(added, list) else f" + {k}: {added[k]}")

    if removed:
        print(f"\n{title} - Removed:")
        for k in sorted(removed):
            print(f" - {k}" if isinstance(removed, list) else f" - {k}: {removed[k]}")

    if changed:
        print(f"\n{title} - Changed:")
        for k in sorted(changed):
            print(f" ~ {k}: {changed[k]['from']} -> {changed[k]['to']}")


def print_packageconfig_diff(
    added: dict[str, dict[str, str]],
    removed: dict[str, dict[str, str]],
    changed: dict[str, dict[str, Any]],
    *,
) -> None:
    """
    Print PACKAGECONFIG differences.

    Args:
        added: Added packages with their features
        removed: Removed packages with their features
        changed: Changed packages with feature differences

    """
    if added:
        print("\nPACKAGECONFIG - Added Packages:")
        for pkg in sorted(added):
            print(f" + {pkg}:")
            for feature, value in sorted(added[pkg].items()):
                print(f"     {feature}: {value}")

    if removed:
        print("\nPACKAGECONFIG - Removed Packages:")
        for pkg in sorted(removed):
            print(f" - {pkg}:")
            for feature, value in sorted(removed[pkg].items()):
                print(f"     {feature}: {value}")

    if changed:
        print("\nPACKAGECONFIG - Changed Packages:")
        for pkg in sorted(changed):
            print(f" ~ {pkg}:")
            pkg_changes = changed[pkg]
            if pkg_changes.get("added"):
                for feature, value in sorted(pkg_changes["added"].items()):
                    print(f"     + {feature}: {value}")
            if pkg_changes.get("removed"):
                for feature, value in sorted(pkg_changes["removed"].items()):
                    print(f"     - {feature}: {value}")
            if pkg_changes.get("changed"):
                for feature, change in sorted(pkg_changes["changed"].items()):
                    print(f"     ~ {feature}: {change['from']} -> {change['to']}")


def write_diff_to_json(
    pkg_diff: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    cfg_diff: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    pcfg_diff: tuple[
        dict[str, dict[str, str]], dict[str, dict[str, str]], dict[str, dict[str, Any]]
    ],
    output_file: pathlib.Path,
) -> None:
    """
    Write diff results to a JSON file.

    Args:
        pkg_diff: Differences for packages
        cfg_diff: Differences for kernel config
        pcfg_diff: Differences for PACKAGECONFIG
        output_file: File path to write JSON

    """
    _logger.info("Writing diff results to %s", output_file)
    delta = {
        "package_diff": {
            "added": dict(sorted(pkg_diff[0].items())),
            "removed": dict(sorted(pkg_diff[1].items())),
            "changed": dict(sorted(pkg_diff[2].items())),
        },
        "kernel_config_diff": {
            "added": dict(sorted(cfg_diff[0].items())),
            "removed": dict(sorted(cfg_diff[1].items())),
            "changed": dict(sorted(cfg_diff[2].items())),
        },
        "packageconfig_diff": {
            "added": dict(sorted(pcfg_diff[0].items())),
            "removed": dict(sorted(pcfg_diff[1].items())),
            "changed": dict(sorted(pcfg_diff[2].items())),
        },
    }
    with output_file.open("w", encoding="utf-8") as f:
        json.dump(delta, f, indent=2, ensure_ascii=False)


def path_is_file(value: str) -> pathlib.Path:
    """Ensures value is an existing Path or raises and argparse error."""
    if (path := pathlib.Path(value)).is_file():
        return path
    raise ArgumentTypeError(f"{value} is not a path to an existing file!")


def main() -> None:
    """
    Main entry point.

    Parse arguments, extract SPDX data, compare, and print/write diffs.
    """
    parser = ArgumentParser(description="Compare SPDX3 JSON files")
    parser.add_argument(
        "--version", action="version", version=f"spdx-diff {__version__}"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG)",
    )
    parser.add_argument(
        "reference",
        type=path_is_file,
        help="Reference SPDX3 JSON file",
    )
    parser.add_argument(
        "new",
        type=path_is_file,
        help="New SPDX3 JSON file",
    )
    timestamp = datetime.now(tz=timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    default_output = f"spdx_diff_{timestamp}.json"
    parser.add_argument(
        "--output",
        "-o",
        metavar="PATH",
        type=pathlib.Path,
        default=default_output,
        help="Optional output file name (JSON)",
    )
    parser.add_argument(
        "--ignore-proprietary",
        action="store_true",
        help="Ignore packages with LicenseRef-Proprietary",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "both"],
        default="both",
        help="Output format: text (console only), json (file only), or both (default)",
    )

    # Output filtering options
    parser.add_argument(
        "--show-packages",
        action="store_true",
        help="Show only package differences",
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show only kernel config differences",
    )
    parser.add_argument(
        "--show-packageconfig",
        action="store_true",
        help="Show only PACKAGECONFIG differences",
    )

    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbose >= 2:
        log_level = logging.DEBUG
    elif args.verbose == 1:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    # Determine what to show based on flags
    # If no specific show flags are set, show everything
    show_all_category = not (
        args.show_packages or args.show_config or args.show_packageconfig
    )
    show_packages = args.show_packages or show_all_category
    show_config = args.show_config or show_all_category
    show_packageconfig = args.show_packageconfig or show_all_category

    try:
        sbom_ref = Spdx3Sbom(args.reference)
        sbom_ref.extract_spdx_data(args.ignore_proprietary)

        sbom_new = Spdx3Sbom(args.new)
        sbom_new.extract_spdx_data(args.ignore_proprietary)
    except (ValueError, TypeError) as e:
        parser.error(str(e))

    pkg_diff = compare_dicts(sbom_ref.packages, sbom_new.packages)
    cfg_diff = compare_dicts(sbom_ref.config, sbom_new.config)
    pcfg_diff = compare_packageconfig(sbom_ref.packageconfig, sbom_new.packageconfig)
    pcfg_light_diff = (
        {k: v for k, v in pcfg_diff[0].items() if k not in pkg_diff[0]},
        {k: v for k, v in pcfg_diff[1].items() if k not in pkg_diff[1]},
        pcfg_diff[2],
    )

    # Print summary or full output
    if show_packages:
        print_diff(
            "Packages",
            *pkg_diff,
        )
    if show_config:
        print_diff(
            "Kernel Config",
            *cfg_diff,
        )
    if show_packageconfig:
        print_packageconfig_diff(
            *pcfg_light_diff,
        )

    if args.format in ["json", "both"]:
        write_diff_to_json(pkg_diff, cfg_diff, pcfg_light_diff, args.output)


if __name__ == "__main__":
    main()
