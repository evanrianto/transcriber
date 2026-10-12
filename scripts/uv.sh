#!/bin/sh
# Runs uv with the given arguments, installing uv first if it isn't available yet.
set -e

if command -v uv >/dev/null 2>&1; then
    UV=uv
else
    UV="$HOME/.local/bin/uv"
    if [ ! -x "$UV" ]; then
        echo "uv not found; installing it..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi
fi

exec "$UV" "$@"
