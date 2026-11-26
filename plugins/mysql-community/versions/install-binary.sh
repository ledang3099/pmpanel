install_mysql_binary() (
    set -eu
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
    filename="mysql-${SUFFIX_NAME}.tar.${extension}"
    curl --proto '=https' --proto-redir '=https' -fsSL --retry 2 \
        "https://cdn.mysql.com/Downloads/MySQL-${series}/${filename}" -o "$staging/$filename"
    tar -xf "$staging/$filename" -C "$staging"
    source_dir="$staging/mysql-${SUFFIX_NAME}"
    test -x "$source_dir/bin/mysqld"
    mkdir -p "$target"
    cp -R "$source_dir"/. "$target/"
    printf '%s\n' "$series" > "$target/version.pl"
)
