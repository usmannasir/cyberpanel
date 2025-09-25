#!/bin/bash

# CyberPanel Installer UI Module
# Beautiful, interactive user interface for the installer
# Max 500 lines - Current: ~450 lines

# Colors and styling
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# UI Variables
TERMINAL_WIDTH=80
PROGRESS_WIDTH=50
CURRENT_STEP=0
TOTAL_STEPS=0

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [UI] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [UI] $1"
}

# Function to get terminal width
get_terminal_width() {
    TERMINAL_WIDTH=$(tput cols 2>/dev/null || echo 80)
    if [ $TERMINAL_WIDTH -lt 60 ]; then
        TERMINAL_WIDTH=60
    fi
    PROGRESS_WIDTH=$((TERMINAL_WIDTH - 30))
}

# Function to print centered text
print_center() {
    local text="$1"
    local color="$2"
    local width=$TERMINAL_WIDTH
    local padding=$(( (width - ${#text}) / 2 ))
    printf "%*s" $padding ""
    echo -e "${color}${text}${NC}"
}

# Function to print header
print_header() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    print_center "🚀 CYBERPANEL MODULAR INSTALLER 🚀" "${WHITE}${BOLD}"
    print_center "The Ultimate Web Hosting Control Panel" "${CYAN}"
    print_center "Powered by OpenLiteSpeed • Fast • Secure • Scalable" "${DIM}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to print section header
print_section() {
    local title="$1"
    local icon="$2"
    echo ""
    echo -e "${PURPLE}${BOLD}${icon} ${title}${NC}"
    echo -e "${PURPLE}$(printf '═%.0s' $(seq 1 $((TERMINAL_WIDTH - 3))))${NC}"
}

# Function to print step
print_step() {
    local step="$1"
    local description="$2"
    local status="$3"
    
    CURRENT_STEP=$((CURRENT_STEP + 1))
    
    case $status in
        "running")
            echo -e "${YELLOW}${BOLD}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} ${WHITE}${description}${NC} ${YELLOW}⏳ Running...${NC}"
            ;;
        "success")
            echo -e "${GREEN}${BOLD}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} ${WHITE}${description}${NC} ${GREEN}✅ Success${NC}"
            ;;
        "error")
            echo -e "${RED}${BOLD}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} ${WHITE}${description}${NC} ${RED}❌ Failed${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}${BOLD}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} ${WHITE}${description}${NC} ${YELLOW}⚠️  Warning${NC}"
            ;;
        "info")
            echo -e "${BLUE}${BOLD}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} ${WHITE}${description}${NC} ${BLUE}ℹ️  Info${NC}"
            ;;
        "pending")
            echo -e "${DIM}[${CURRENT_STEP}/${TOTAL_STEPS}]${NC} ${DIM}${description}${NC} ${DIM}⏸️  Pending${NC}"
            ;;
    esac
}

# Function to print progress bar
print_progress() {
    local current=$1
    local total=$2
    local description="$3"
    
    local percentage=$((current * 100 / total))
    local filled=$((current * PROGRESS_WIDTH / total))
    local empty=$((PROGRESS_WIDTH - filled))
    
    printf "\r${CYAN}${description}:${NC} ["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] ${percentage}%%"
    
    if [ $current -eq $total ]; then
        echo ""
    fi
}

# Function to print spinner
print_spinner() {
    local pid=$1
    local message="$2"
    local delay=0.1
    local spinstr='|/-\'
    
    while [ "$(ps a | awk '{print $1}' | grep $pid)" ]; do
        local temp=${spinstr#?}
        printf "\r${YELLOW}${message}${NC} [${spinstr:0:1}]"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
    done
    printf "\r${GREEN}${message}${NC} ✅"
    echo ""
}

# Function to print info box
print_info_box() {
    local title="$1"
    local content="$2"
    local color="$3"
    
    echo ""
    echo -e "${color}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${color}║${NC} ${WHITE}${BOLD}${title}${NC}"
    echo -e "${color}║${NC}"
    echo -e "${color}║${NC} ${content}"
    echo -e "${color}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to print warning box
print_warning_box() {
    local title="$1"
    local content="$2"
    
    print_info_box "$title" "$content" "$YELLOW"
}

# Function to print error box
print_error_box() {
    local title="$1"
    local content="$2"
    
    print_info_box "$title" "$content" "$RED"
}

# Function to print success box
print_success_box() {
    local title="$1"
    local content="$2"
    
    print_info_box "$title" "$content" "$GREEN"
}

# Function to print menu
print_menu() {
    local title="$1"
    shift
    local options=("$@")
    
    echo ""
    print_section "$title" "📋"
    
    for i in "${!options[@]}"; do
        local option_num=$((i + 1))
        echo -e "${BLUE}${option_num}.${NC} ${options[i]}"
    done
    echo ""
}

# Function to get user input
get_user_input() {
    local prompt="$1"
    local default="$2"
    
    if [ -n "$default" ]; then
        echo -e "${CYAN}${prompt}${NC} ${DIM}[${default}]${NC}: "
    else
        echo -e "${CYAN}${prompt}${NC}: "
    fi
}

# Function to get user choice
get_user_choice() {
    local prompt="$1"
    local max_choice="$2"
    local default="$3"
    
    while true; do
        get_user_input "$prompt" "$default"
        read -r choice
        
        if [ -z "$choice" ] && [ -n "$default" ]; then
            choice="$default"
        fi
        
        if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "$max_choice" ]; then
            echo "$choice"
            return
        else
            print_error_box "Invalid Choice" "Please enter a number between 1 and $max_choice"
        fi
    done
}

# Function to get yes/no input
get_yes_no() {
    local prompt="$1"
    local default="$2"
    
    while true; do
        get_user_input "$prompt (y/n)" "$default"
        read -r response
        
        if [ -z "$response" ] && [ -n "$default" ]; then
            response="$default"
        fi
        
        case $response in
            [yY]|[yY][eE][sS])
                return 0
                ;;
            [nN]|[nN][oO])
                return 1
                ;;
            *)
                print_error_box "Invalid Input" "Please enter 'y' for yes or 'n' for no"
                ;;
        esac
    done
}

# Function to print system info
print_system_info() {
    print_section "System Information" "💻"
    
    echo -e "${WHITE}Operating System:${NC} $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2 2>/dev/null || echo 'Unknown')"
    echo -e "${WHITE}Architecture:${NC} $(uname -m)"
    echo -e "${WHITE}Kernel:${NC} $(uname -r)"
    echo -e "${WHITE}Memory:${NC} $(free -h | grep 'Mem:' | awk '{print $2}' 2>/dev/null || echo 'Unknown')"
    echo -e "${WHITE}Disk Space:${NC} $(df -h / | tail -n1 | awk '{print $4}' 2>/dev/null || echo 'Unknown')"
    echo -e "${WHITE}CPU Cores:${NC} $(nproc 2>/dev/null || echo 'Unknown')"
}

# Function to print installation summary
print_installation_summary() {
    local status="$1"
    local message="$2"
    
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    
    case $status in
        "success")
            print_center "🎉 INSTALLATION COMPLETED SUCCESSFULLY! 🎉" "${GREEN}${BOLD}"
            ;;
        "error")
            print_center "❌ INSTALLATION FAILED ❌" "${RED}${BOLD}"
            ;;
        "warning")
            print_center "⚠️  INSTALLATION COMPLETED WITH WARNINGS ⚠️" "${YELLOW}${BOLD}"
            ;;
    esac
    
    if [ -n "$message" ]; then
        print_center "$message" "${WHITE}"
    fi
    
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to print footer
print_footer() {
    echo ""
    echo -e "${DIM}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${DIM}CyberPanel Modular Installer • Made with ❤️  for the community${NC}"
    echo -e "${DIM}For support: https://community.cyberpanel.net${NC}"
    echo -e "${DIM}Documentation: https://cyberpanel.net/KnowledgeBase/${NC}"
    echo -e "${DIM}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Function to initialize UI
init_ui() {
    get_terminal_width
    print_header
    print_system_info
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    init_ui
fi
