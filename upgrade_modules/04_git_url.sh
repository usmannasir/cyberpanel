#!/usr/bin/env bash
# CyberPanel upgrade – set Git content and clone URLs (usmannasir or override).
# Sourced by cyberpanel_upgrade.sh.

Pre_Upgrade_Setup_Git_URL() {
  if [[ $Server_Country != "CN" ]] ; then
    if [[ -n "$Git_User_Override" ]]; then
      Git_User="$Git_User_Override"
      echo -e "\nUsing GitHub repo: ${Git_User}/cyberpanel\n"
    else
      Git_User="master3395"
    fi
    Git_Content_URL="https://raw.githubusercontent.com/${Git_User}/cyberpanel"
    Git_Clone_URL="https://github.com/${Git_User}/cyberpanel.git"
  else
    if [[ -n "$Git_User_Override" ]]; then
      Git_User="$Git_User_Override"
    else
      Git_User="qtwrk"
    fi
    Git_Content_URL="https://gitee.com/${Git_User}/cyberpanel/raw"
    Git_Clone_URL="https://gitee.com/${Git_User}/cyberpanel.git"
  fi
  if [[ "$Debug" = "On" ]] ; then
    Debug_Log "Git_URL" "$Git_Content_URL"
  fi
}
