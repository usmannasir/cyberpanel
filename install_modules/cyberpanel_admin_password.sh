# Admin password mode for fresh installs (sourced by cyberpanel.sh / 00_common.sh).
# CYBERPANEL_ADMIN_PASSWORD_MODE: default | random | custom
# CYBERPANEL_ADMIN_PASSWORD: resolved plain password for install.py / adminPass.py

_cyberpanel_generate_random_password() {
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 24 | tr -d '/+=' | head -c 20
        return
    fi
    tr -dc 'A-Za-z0-9' </dev/urandom 2>/dev/null | head -c 20
}

resolve_cyberpanel_admin_password() {
    local mode="${CYBERPANEL_ADMIN_PASSWORD_MODE:-}"
    local resolved=""

    case "$mode" in
        random|r)
            resolved="$(_cyberpanel_generate_random_password)"
            ;;
        custom|c)
            resolved="${CYBERPANEL_ADMIN_PASSWORD_CUSTOM:-}"
            if [ -z "$resolved" ]; then
                echo "ERROR: Custom admin password is empty."
                exit 1
            fi
            if [ "${#resolved}" -lt 8 ]; then
                echo "ERROR: Custom admin password must be at least 8 characters."
                exit 1
            fi
            ;;
        default|d|"")
            resolved="1234567"
            ;;
        *)
            echo "ERROR: Unknown admin password mode: $mode"
            exit 1
            ;;
    esac

    export CYBERPANEL_ADMIN_PASSWORD="$resolved"
    mkdir -p /root /etc/cyberpanel
    printf '%s\n' "$resolved" > /root/.cyberpanel_password
    printf '%s\n' "$resolved" > /etc/cyberpanel/adminPass
    chmod 600 /root/.cyberpanel_password /etc/cyberpanel/adminPass 2>/dev/null || true
}
