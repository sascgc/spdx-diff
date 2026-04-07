SPDX3 Diff Tool
===============

Overview
--------
This tool compares two SPDX3 JSON documents and reports differences in:
- Software packages (name + version)
- Kernel configuration parameters (CONFIG_*)
- PACKAGECONFIG entries per package

It produces both human-readable output (console) and a structured JSON diff file.

Usage
-----
```bash
./spdx-diff reference.json new.json [OPTIONS]
```

Required arguments:
  - `reference`: Path to the baseline SPDX3 JSON file.
  - `new`: Path to the newer SPDX3 JSON file.

Optional arguments:
  - `--output <file>`: Save diff results to the given JSON file.
    Default: `spdx_diff_<timestamp>.json`
  - `--ignore-proprietary`: Ignore packages with LicenseRef-Proprietary.
  - `--format {text,json,both}`: Control output format:
    - `text`: Console output only (no JSON file)
    - `json`: JSON file only (silent mode for automation)
    - `both`: Both console and JSON output (**default**)

Output filtering - category:
  - `--show-packages`: Show only package differences.
  - `--show-config`: Show only kernel config differences.
  - `--show-packageconfig`: Show only PACKAGECONFIG differences.

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

### Basic comparison with both console and JSON output:
    ./spdx-diff reference.json new.json

### Full details with proprietary packages excluded:
    ./spdx-diff reference.json new.json --ignore-proprietary

### Quick summary check:
    ./spdx-diff reference.json new.json --summary

### Silent mode for CI/CD (JSON output only):
    ./spdx-diff reference.json new.json --format json --output results.json

### Console output only (no JSON file):
    ./spdx-diff reference.json new.json --format text

### Show only PACKAGECONFIG differences:
    ./spdx-diff reference.json new.json --show-packageconfig

Console output example:
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
