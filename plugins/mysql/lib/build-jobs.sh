# Keep compiler processes within the memory budget of a Linux container.
mysql_build_jobs() {
    local jobs="$1"
    local memory_limit
    local memory_jobs

    if [ -n "${MYSQL_BUILD_JOBS:-}" ]; then
        printf '%s\n' "$MYSQL_BUILD_JOBS"
        return
    fi

    if [ -r /sys/fs/cgroup/memory.max ]; then
        read -r memory_limit < /sys/fs/cgroup/memory.max
        if [[ "$memory_limit" =~ ^[0-9]+$ ]]; then
            memory_jobs=$((memory_limit / (3 * 1024 * 1024 * 1024)))
            (( memory_jobs > 0 )) || memory_jobs=1
            (( jobs <= memory_jobs )) || jobs=$memory_jobs
        fi
    fi
    printf '%s\n' "$jobs"
}
