# Docker Command Execution Feature for CyberPanel

## Overview
This feature adds the ability to execute commands inside running Docker containers directly from the CyberPanel web interface. This is particularly useful for applications like Honeygain that require specific command-line arguments to function properly.

## Features Added

### 1. Backend Components
- **New View Function**: `executeContainerCommand` in `dockerManager/views.py`
- **New Container Method**: `executeContainerCommand` in `dockerManager/container.py`
- **New URL Pattern**: `/docker/executeContainerCommand` in `dockerManager/urls.py`

### 2. Frontend Components
- **New Action Button**: "Run Command" button in Container Actions section
- **Command Execution Modal**: Interactive modal for executing commands
- **Command History**: Tracks last 10 executed commands
- **Real-time Output**: Displays command output with proper formatting

### 3. Security Features
- **Permission Checks**: Only admin users can execute commands
- **Container Ownership**: Users can only execute commands on containers they own
- **Input Validation**: Commands are properly sanitized using `shlex.split()`
- **Error Handling**: Comprehensive error handling for various failure scenarios

## How to Use

### 1. Access the Feature
1. Navigate to your Docker container in CyberPanel
2. Ensure the container is running (the "Run Command" button is disabled for stopped containers)
3. Click the "Run Command" button in the Container Actions section

### 2. Execute Commands
1. Enter your command in the input field (e.g., `-tou-accept`, `ls -la`, `ps aux`)
2. Press Enter or click the "Execute" button
3. View the output in the terminal-style output area
4. Use command history to quickly re-run previous commands

### 3. Common Use Cases
**For applications requiring command-line arguments:**
1. Start your container
2. Click "Run Command"
3. Enter the required command (e.g., `-tou-accept`, `--help`, `--version`)
4. Click "Execute"
5. View the output to confirm successful execution

**For debugging and maintenance:**
- `ls -la` - List files and directories
- `ps aux` - Show running processes
- `whoami` - Display current user
- `env` - Show environment variables
- `df -h` - Display disk usage

## Technical Details

### Command Execution Process
1. **Validation**: Check if container exists and user has permissions
2. **Status Check**: Ensure container is running
3. **Command Parsing**: Use `shlex.split()` to properly parse command arguments
4. **Execution**: Use Docker's `exec_run()` method to execute command
5. **Response**: Return output, exit code, and any errors

### Error Handling
- Container not found
- Container not running
- Permission denied
- Command execution failures
- Network connectivity issues

### Security Considerations
- Commands are executed with the same user as the container's default user
- No privileged execution (unless container is privileged)
- Input is sanitized to prevent injection attacks
- Only admin users can execute commands

## Files Modified

### Backend Files
- `dockerManager/container.py` - Added `executeContainerCommand` method
- `dockerManager/views.py` - Added `executeContainerCommand` view function
- `dockerManager/urls.py` - Added URL pattern for command execution

### Frontend Files
- `dockerManager/templates/dockerManager/viewContainer.html` - Added UI components
- `dockerManager/static/dockerManager/dockerManager.js` - Added JavaScript functionality

## API Endpoint

**POST** `/docker/executeContainerCommand`

**Request Body:**
```json
{
    "name": "container_name",
    "command": "command_to_execute"
}
```

**Response:**
```json
{
    "commandStatus": 1,
    "error_message": "None",
    "output": "command_output",
    "exit_code": 0,
    "command": "executed_command"
}
```

## Troubleshooting

### Common Issues
1. **"Container must be running"** - Start the container first
2. **"Permission denied"** - Ensure you have admin access
3. **"Command not found"** - Check if the command exists in the container
4. **Empty output** - Some commands may not produce visible output

### Debugging
- Check container logs for additional information
- Verify the container's base image supports the command
- Ensure proper command syntax for the container's shell

## Future Enhancements
- Interactive terminal mode
- Command templates for common tasks
- Output filtering and search
- Command scheduling
- Multi-container command execution

## Security Notes
- This feature should only be used by trusted administrators
- Commands are executed with the container's user permissions
- Consider implementing additional logging for audit purposes
- Monitor command execution for security compliance

## Testing with Various Applications
1. Pull any Docker image (e.g., `ubuntu:latest`, `alpine:latest`, `nginx:latest`)
2. Create a container with the image
3. Start the container
4. Use the "Run Command" feature to execute various commands:
   - `ls -la` - List files
   - `ps aux` - Show processes
   - `whoami` - Check user
   - `env` - View environment
5. Verify commands execute properly and output is displayed correctly

This feature provides a secure and user-friendly way to execute commands in Docker containers directly from the CyberPanel interface, making it easy to manage applications like Honeygain that require specific command-line arguments.
