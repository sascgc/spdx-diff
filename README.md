SPDX3 Diff Tool
===============

Overview
--------
This tool compares two SPDX3 JSON documents and reports differences in:
- Software packages (name + version)
- Kernel configuration parameters (CONFIG_*)
- PACKAGECONFIG entries per package

The application separates human-readable and machine-readable outputs to improve automation and pipeline integration.

- **stderr** is used for human-readable (text) output intended for debugging.
- **stdout** always emits structured **JSON output**, making it suitable for consumption by scripts and CI/CD pipelines.
- When a JSON filename parameter is provided, the JSON result is also written to the specified file.

Usage
-----
```bash
./spdx-diff reference.json new.json [OPTIONS]
```

Required arguments:
  - `reference`: Path to the baseline SPDX3 JSON file.
  - `new`: Path to the newer SPDX3 JSON file.

Optional arguments:
  - `--json-output <file>`: Save diff results to the given JSON file.

Text output filtering - category :
  - `--[no-]packages`: show|hide package differences.
  - `--[no-]kernel-config`: show|hide kernel config differences.
  - `--[no-]packageconfig`: show|hide PACKAGECONFIG differences.
  - `--[no-]packages-proprietary`: show|hide packages with LicenseRef-Proprietary.

Output
------
The script prints differences grouped into three sections:

1. Packages
   - Added packages
   - Removed packages
   - Changed versions

2. Kernel Config (CONFIG_*)
   - Added options
   - Removed options
   - Modified options

3. PACKAGECONFIG (per package)
   - Packages with added PACKAGECONFIG entries
   - Packages with removed PACKAGECONFIG entries
   - Packages with changed feature configurations
   - Shows package name and associated features

Symbols:
  + added
  - removed
  ~ changed

```

JSON Diff File
--------------
The output file (default: spdx_diff_<timestamp>.json) contains a structured diff:

```json
{
  "package_diff": {
    "added": { "pkgA": "1.2.3" },
    "removed": { "pkgB": "4.5.6" },
    "changed": { "pkgC": { "from": "1.0", "to": "2.0" } }
  },
  "kernel_config_diff": {
    "added": { "CONFIG_XYZ": "y" },
    "removed": { "CONFIG_ABC": "n" },
    "changed": { "CONFIG_DEF": { "from": "m", "to": "y" } }
  },
  "packageconfig_diff": {
    "added": {
      "xz": { "doc": "enabled" }
    },
    "removed": {
      "old-package": { "feature1": "disabled" }
    },
    "changed": {
      "zstd-native": {
        "added": { "zlib": "enabled" },
        "removed": { "lz4": "disabled" },
        "changed": {
          "doc": { "from": "disabled", "to": "enabled" }
        }
      }
    }
  }
}
```

PACKAGECONFIG Structure
-----------------------
PACKAGECONFIG entries are tracked per package, showing which features are
enabled/disabled for each specific package:

Console output example:
```
PACKAGECONFIG - Changed Packages:
 ~ xz:
     + doc: enabled
 ~ zstd-native:
     ~ lz4: disabled -> enabled
     - lzma: disabled
```

This shows:
- xz package: doc feature was added and enabled
- zstd-native package: lz4 changed from disabled to enabled, lzma was removed

Logging
-------
The script uses Python's logging module:
```
  INFO     Normal operations (file opened, counts, etc.)
  WARNING  Missing sections (no build_Build objects found)
  ERROR    Invalid input or format issues
```

Examples
--------

### Basic comparison with both console(stderr) and JSON(stdout) output:
    ./spdx-diff reference.json new.json

### Full details with proprietary packages excluded:
    ./spdx-diff reference.json new.json --no-packages-proprietary

### Console output for CI/CD:
    ./spdx-diff reference.json new.json --quiet

### Console and JSON output with JSON file generated:
    ./spdx-diff reference.json new.json --quiet --json-output result.json

### Show on console no PACKAGECONFIG differences:
    ./spdx-diff reference.json new.json --no-packageconfig

Console output(stderr) example:
```
Packages - Added:
 + libfoo: 2.0

Packages - Changed:
 ~ zlib: 1.2.11 -> 1.2.13

Kernel Config - Removed:
 - CONFIG_OLD_FEATURE

PACKAGECONFIG - Added Packages:
 + newpkg:
     gtk: enabled
     doc: disabled

PACKAGECONFIG - Changed Packages:
 ~ xz:
     + lzma: enabled
```
