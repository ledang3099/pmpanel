# Install a single executable from an already authenticated release URL and digest.
install_release_binary() (
    url=$1
    digest=$2
    archive=$3
    destination=$4

    mkdir -p "$(dirname "$archive")" "$(dirname "$destination")" || return 1
    verified_download "$url" "$archive" "$digest" || return 1
    work=$(mktemp -d "$(dirname "$archive")/extract.XXXXXX") || return 1
    candidate=
    trap 'rm -rf -- "$work"; if [ -n "$candidate" ]; then rm -f -- "$candidate"; fi' EXIT
    tar -xf "$archive" -C "$work" || return 1
    executable=$(find "$work" -type f -name "${destination##*/}") || return 1
    [ -n "$executable" ] && [ -f "$executable" ] || return 1
    candidate=$(mktemp "${destination}.XXXXXX") || return 1
    install -m 0755 "$executable" "$candidate" || return 1
    mv -f -- "$candidate" "$destination"
)
