#!/usr/bin/env bash
# Download a pinned release using HTTPS and validate cached archives as well.
verified_download() (
    url=$1
    archive=$2
    expected=$3
    if command -v sha256sum >/dev/null; then
        checksum=(sha256sum)
    else
        checksum=(shasum -a 256)
    fi

    if [ -f "$archive" ] && printf '%s  %s\n' "$expected" "$archive" | "${checksum[@]}" -c - >/dev/null 2>&1; then
        return 0
    fi

    temporary=$(mktemp "${archive}.XXXXXX") || return 1
    trap 'rm -f -- "$temporary"' EXIT
    curl --proto '=https' --proto-redir '=https' --fail --silent --show-error --location --retry 2 -o "$temporary" "$url" || return 1
    printf '%s  %s\n' "$expected" "$temporary" | "${checksum[@]}" -c - || return 1
    mv -f -- "$temporary" "$archive"
)
