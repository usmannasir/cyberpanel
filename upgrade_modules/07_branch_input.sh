#!/usr/bin/env bash
# CyberPanel upgrade – branch input prompt. Sourced by cyberpanel_upgrade.sh.

Pre_Upgrade_Branch_Input() {
  echo -e "\nPress the Enter key to continue with latest version, or enter specific version such as: \e[31m2.3.4\e[39m , \e[31m2.4.4\e[39m ...etc"
  echo -e "\nIf nothing is input in 10 seconds, script will proceed with the latest stable version. "
  echo -e "\nPlease press the Enter key or specify a version number, or wait for 10 seconds: "
  printf "%s" ""
  read -r -t 10 Tmp_Input
  if [[ $Tmp_Input = "" ]]; then
    echo -e "Branch name set to $Branch_Name"
  else
    Branch_Check "$Tmp_Input"
  fi
}

