import docker

# Create a Docker client
client = docker.from_env()

# Define the label to filter containers
label_filter = {'name': 'cyberplanner-new'}

# List containers matching the label filter
containers = client.containers.list(filters=label_filter)

# Print container information
for container in containers:
    print(f"Container ID: {container.id}, Name: {container.name}, Status: {container.status}")

    # Get volume information for the container
    volumes = container.attrs['HostConfig']['Binds'] if 'HostConfig' in container.attrs else []
    for volume in volumes:
        print(f"Volume: {volume}")

    # # Fetch last 50 logs for the container
    # logs = container.logs(tail=50).decode('utf-8')
    # print(f"Last 50 Logs:\n{logs}")

    # Get exposed ports for the container
    ports = container.attrs['HostConfig']['PortBindings'] if 'HostConfig' in container.attrs else {}
    for port in ports:
        print(f"Exposed Port: {port}")
