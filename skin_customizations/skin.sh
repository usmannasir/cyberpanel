# CUSTOM PANEL CYBERPANEL 
# Author: Patrick Oliveira | patricknasci@cenathost.com
# CenatHost © 2019 | support@cenathost.com
# English Version

#CUSTOM_NAME='Web <i>Panel</i>'
SERVER_NAME=Cyber

#LOGIN PAGE
#DEFAULT:#fafafa
BACKGROUND_OLD=#fafafa
BACKGROUND_NEW=#293a4a
#FLAG HEADER PANEL

#DEFAULT:#008fe2
flag_oldprimary=#008fe2
flag_newprimary=#39386e

#DEFAULT:#00b29c
flag_oldsecondary=#00b29c
flag_newsecondary=#b31c31

# COLORS

#DEFAULT:#8da0aa
div_selector_color_old=#8da0aa
div_selector_color=#000000


#DEFAULT: ##00bca4
background_tileold_color=#00bca4
background_tilenew_color=#1a2b3c

#DEFAULT:#00ceb4
background_tileoldselected_color=#00ceb4
background_tilenewselected_color=#293a4a

#DEFAULT:#00bca4
border_tileold_color=#00a792
border_tilenew_color=#000

#DEFAULT:#00b19b
border_tileoldselected_color=#00b19b
border_tilenewselected_color=#293a4a


#DEFAULT:#4b5056
header_tableold_color=#4b5056
header_tablenew_color=#fff

#DEFAULT:#f9fafe
background_tableold_color=#f9fafe
background_tablenew_color=#293a4a

#DEFAULT:#4b5056
textheader_launchold_color=#4b5056
textheader_launchnew_color=#fff

#DEFAULT:#3498db
header_launchold_color=#3498db
header_launchnew_color=#293a4a

#DEFAULT: #3498db
table_launch_panelold=#3498db
table_launch_panelnew=#293a4a


#========================================================================
#LOGIN PAGE CHANGE
echo 'Updating Login Page Background...'
sed -i 's|        background: '$BACKGROUND_OLD';|        background: '$BACKGROUND_NEW';|g' /usr/local/CyberCP/loginSystem/templates/loginSystem/login.html

echo 'Updating Colors Header Flag...'
# COLOR HEADER
sed -i 's|'$flag_oldprimary'|'$flag_newprimary'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBase.css
sed -i 's|'$flag_oldsecondary'|'$flag_newsecondary'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBase.css

echo 'Updating button colors..'
#COLORS BUTTONS
sed -i 's|'$border_tileold_color'|'$border_tilenew_color'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBaseTheme.css
sed -i 's|'$background_tileold_color'|'$background_tilenew_color'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBaseTheme.css
sed -i 's|'$border_tileoldselected_color'|'$border_tilenewselected_color'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBaseTheme.css
sed -i 's|'$background_tileoldselected_color'|'$background_tilenewselected_color'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBaseTheme.css

#Table
echo 'Updating Table Colors...'
sed -i 's|.table>thead>tr>th{color:'$header_tableold_color';background-color:'$background_tableold_color'}|.table>thead>tr>th{color:'$header_tablenew_color';background-color:'$background_tablenew_color'}|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBaseTheme.css
sed -i 's|'$div_selector_color_old'|'$div_selector_color'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBaseTheme.css
sed -i 's|'$table_launch_panelold'|'$table_launch_panelnew'|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBase.css

#Header launch
echo 'Upgrading Header launch...'
sed -i 's|span.checked{color:'$textheader_launchold_color';border-color:#308dcc;background:'$header_launchold_color'}|span.checked{color:'$textheader_launchnew_color';border-color:#308dcc;background:'$header_launchnew_color'}|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBase.css

echo 'Menu counter removed...'
#HIDE BADGE
sed -i 's|.bs-badge.badge-absolute{position:absolute;z-index:5;top:-10px;left:-15px}|.bs-badge.badge-absolute{position:absolute;z-index:5;top:-10px;left:-15px;display:none;}|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalBase/finalBase.css


#CHANGE NAME
sed -i 's|Cyber <i>Panel</i>|'$CUSTOM_NAME'|g' /usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html
sed -i 's:Login - CyberPanel:'$SERVER_NAME' | PANEL - LOGIN:g' /usr/local/CyberCP/loginSystem/templates/loginSystem/login.html

#LOGIN MODIFY CENTER
sed -i '69,89d' /usr/local/CyberCP/loginSystem/templates/loginSystem/login.html
sed -i '/row">/a <div class="col-md-2"></div>' /usr/local/CyberCP/loginSystem/templates/loginSystem/login.html
sed -i '/"col-md-7">/a <center><h2 class="text-transform-upr font-size-17">'$SERVER_NAME' | PANEL - LOGIN</h2></center><div class="divider"></div>'  /usr/local/CyberCP/loginSystem/templates/loginSystem/login.html
sed -i 's|body,label{color:#3e4855}|body,label{color:#ffffff}|g' /usr/local/lscp/cyberpanel/static/baseTemplate/assets/finalLoginPageCSS/allCss.css

echo 'COMPLETE!'
#LOGO PANEL 





#RESTART AGENT PANEL
service gunicorn restart
