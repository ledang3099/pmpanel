install_mysql_binary() (
    set -euo pipefail
    action=$1
    series=$2
    extension=$3
    target="$serverPath/mysql-community"

    case "$action" in
        uninstall) rm -rf -- "$target"; return ;;
        install) ;;
        *) return 1 ;;
    esac

    mkdir -p "$myDir"
    staging=$(mktemp -d "$myDir/install.XXXXXX")
    trap 'rm -rf -- "$staging"' EXIT
    archive_name="mysql-${SUFFIX_NAME}"
    case "$SUFFIX_NAME" in
        *-linux-glibc2.28-x86_64) archive_name="$archive_name-minimal" ;;
    esac
    filename="$archive_name.tar.$extension"
    url="https://cdn.mysql.com/Downloads/MySQL-${series}/${filename}"
    status=$(curl --proto '=https' --proto-redir '=https' -fsSL --retry 2 \
        --write-out '%{http_code}' "$url" -o "$staging/$filename")
    if [ "$status" != 200 ]; then
        echo "Unexpected HTTP status for the MySQL archive: $status" >&2
        return 1
    fi
    case "$extension" in
        xz) xz --threads=1 -dc "$staging/$filename" | tar -xf - -C "$staging" ;;
        gz) tar -xzf "$staging/$filename" -C "$staging" ;;
    esac
    source_dir="$staging/$archive_name"
    test -x "$source_dir/bin/mysqld"
    mkdir -p "$target"
    cp -R "$source_dir"/. "$target/"
    printf '%s\n' "$series" > "$target/version.pl"
)
