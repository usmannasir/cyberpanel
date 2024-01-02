import psutil

def get_disk_usage():
    total_disk = psutil.disk_usage('/').total / (1024 * 1024)  # Total disk space in MB
    used_disk = psutil.disk_usage('/').used / (1024 * 1024)    # Used disk space in MB
    free_disk = psutil.disk_usage('/').free / (1024 * 1024)    # Free disk space in MB
    percent_used = psutil.disk_usage('/').percent              # Percentage of disk used

    return {
        "current_disk_usage_mb": used_disk,
        "current_disk_free_mb": free_disk,
        "percentage_disk_used": percent_used
    }

# Usage example:
disk_info = get_disk_usage()
print("Current disk usage (MB):", disk_info["current_disk_usage_mb"])
print("Current disk free (MB):", disk_info["current_disk_free_mb"])
print("Percentage of disk used:", disk_info["percentage_disk_used"], "%")
