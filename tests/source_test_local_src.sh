
# Check if the file was sourced
_is_sourced() {
    if [ -n "$ZSH_VERSION" ]; then
        case $ZSH_EVAL_CONTEXT in *:file:*) return 0;; esac
    elif [ -n "$BASH_VERSION" ]; then
        [ "$BASH_SOURCE" != "$0" ] && return 0
    else
        case ${0##*/} in dash|-dash|bash|-bash|ksh|-ksh|sh|-sh) return 0;; esac
    fi
    return 1
}

if ! _is_sourced ; then
    echo "ERROR: This script must be sourced, not executed." >&2
    echo "Usage: source $0" >&2
    exit 1
fi

# Get directory of the source folder
if [ -n "$BASH_SOURCE" ]; then
    _tmp_src_path="${BASH_SOURCE[0]}"
elif [ -n "$ZSH_VERSION" ]; then
    _tmp_src_path="${(%):-%x}"
else
    _tmp_src_path="./source_test_local_src.sh"
fi

_tmp_src_path="$(cd "$(dirname "$_tmp_src_path")" && pwd)"
_tmp_src_path="$(dirname "$_tmp_src_path")"
_tmp_src_path="$_tmp_src_path/src"

# Set PYTHONPATH and update PATH
if [ ! -d "$_tmp_src_path" ]; then
    echo "WARNING: Source directory not found: $_tmp_src_path" >&2
else
    export PYTHONPATH="${_tmp_src_path}${PYTHONPATH:+:}${PYTHONPATH}"
    PATH="$_tmp_src_path:$PATH"
fi

# Cleanup
unset _tmp_src_path
unset -f _is_sourced
