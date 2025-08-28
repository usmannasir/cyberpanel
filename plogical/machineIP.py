import os


def get_machine_ip():
    """
    Get machine IP from /etc/cyberpanel/machineIP or fallback locations.
    Used for development and production environments.
    """
    # Try production location first
    ip_file = "/etc/cyberpanel/machineIP"
    if not os.path.exists(ip_file):
        # Try development location
        ip_file = "/tmp/cyberpanel/machineIP"
        if not os.path.exists(ip_file):
            # Create development fallback
            os.makedirs("/tmp/cyberpanel", exist_ok=True)
            with open(ip_file, "w") as f:
                f.write("127.0.0.1\n")

    try:
        with open(ip_file, "r") as f:
            ip_data = f.read().strip()
            return ip_data.split('\n', 1)[0] if ip_data else "127.0.0.1"
    except Exception:
        return "127.0.0.1"
