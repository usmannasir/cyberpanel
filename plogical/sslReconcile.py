#!/usr/bin/env python3
"""
SSL Reconciliation Module for CyberPanel
Integrates the acme_reconcile_all.sh functionality into CyberPanel core
"""

import os
import re
import subprocess
import shlex
import hashlib
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from plogical import installUtilities


class SSLReconcile:
    """SSL Certificate Reconciliation and Management"""
    
    VHOSTS_DIR = "/usr/local/lsws/conf/vhosts"
    VHROOT_BASE = "/home"
    ACME_HOME = "/root/.acme.sh"
    RELOAD_CMD = "systemctl restart lsws"
    
    @staticmethod
    def trim(text):
        """Trim whitespace from text"""
        return text.strip()
    
    @staticmethod
    def pick_lineage_conf(vhost):
        """Pick the appropriate acme.sh lineage configuration file"""
        ecc_conf = f"{SSLReconcile.ACME_HOME}/{vhost}_ecc/{vhost}.conf"
        reg_conf = f"{SSLReconcile.ACME_HOME}/{vhost}/{vhost}.conf"
        
        if os.path.exists(ecc_conf):
            return ecc_conf
        elif os.path.exists(reg_conf):
            return reg_conf
        else:
            # Create ECC lineage directory and file
            os.makedirs(f"{SSLReconcile.ACME_HOME}/{vhost}_ecc", exist_ok=True)
            with open(ecc_conf, 'w') as f:
                f.write('')
            return ecc_conf
    
    @staticmethod
    def set_kv(config_file, key, value):
        """Set key-value pair in configuration file"""
        try:
            # Read existing content
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # Check if key exists and update or add
            key_found = False
            for i, line in enumerate(lines):
                if line.startswith(f"{key}="):
                    lines[i] = f"{key}='{value}'\n"
                    key_found = True
                    break
            
            if not key_found:
                lines.append(f"{key}='{value}'\n")
            
            # Write back to file
            with open(config_file, 'w') as f:
                f.writelines(lines)
                
        except Exception as e:
            logging.writeToFile(f"Error setting {key}={value} in {config_file}: {str(e)}")
            raise
    
    @staticmethod
    def issuer_cn(pem_file):
        """Get issuer CN from certificate"""
        if not os.path.exists(pem_file):
            return ""
        
        try:
            cmd = f"openssl x509 -in {pem_file} -noout -issuer"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                issuer_line = result.stdout.strip()
                # Extract CN from issuer line
                cn_match = re.search(r'CN=([^,]+)', issuer_line)
                if cn_match:
                    return cn_match.group(1)
        except Exception as e:
            logging.writeToFile(f"Error getting issuer CN from {pem_file}: {str(e)}")
        
        return ""
    
    @staticmethod
    def sha256fp(pem_file):
        """Get SHA256 fingerprint of certificate"""
        if not os.path.exists(pem_file):
            return ""
        
        try:
            cmd = f"openssl x509 -in {pem_file} -noout -fingerprint -sha256"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                fingerprint_line = result.stdout.strip()
                # Extract fingerprint value
                fp_match = re.search(r'=([A-F0-9:]+)', fingerprint_line)
                if fp_match:
                    return fp_match.group(1)
        except Exception as e:
            logging.writeToFile(f"Error getting SHA256 fingerprint from {pem_file}: {str(e)}")
        
        return ""
    
    @staticmethod
    def fix_context_location(vconf_path, docroot):
        """Fix ACME challenge context location in vhost configuration"""
        try:
            # Read current configuration
            with open(vconf_path, 'r') as f:
                content = f.read()
            
            want_uri = '/.well-known/acme-challenge/'
            want_loc = f"{docroot}/.well-known/acme-challenge/"
            
            # Create challenge directory
            os.makedirs(want_loc, exist_ok=True)
            os.chmod(docroot, 0o755)
            os.chmod(f"{docroot}/.well-known", 0o755)
            os.chmod(want_loc, 0o755)
            
            # Check if context already exists
            context_pattern = r'context\s+/.well-known/acme-challenge/?\s*{'
            if re.search(context_pattern, content):
                # Update existing context
                content = re.sub(
                    r'(context\s+)/.well-known/acme-challenge/?(\s*{)',
                    rf'\1{want_uri}\2',
                    content
                )
                content = re.sub(
                    r'(location\s+).*acme-challenge/?',
                    rf'\1{want_loc}',
                    content
                )
            else:
                # Add new context
                context_block = f"""

context {want_uri} {{
  location              {want_loc}
  addDefaultCharset     off
}}
"""
                content += context_block
            
            # Write updated configuration
            with open(vconf_path, 'w') as f:
                f.write(content)
                
            logging.writeToFile(f"Fixed ACME challenge context for {vconf_path}")
            return True
            
        except Exception as e:
            logging.writeToFile(f"Error fixing context location for {vconf_path}: {str(e)}")
            return False
    
    @staticmethod
    def needs_force_issue(vhost, dconf_path, docroot, live_fullchain):
        """Determine if certificate needs to be force re-issued"""
        try:
            # Read lineage configuration
            le_api = ""
            webroot = ""
            
            if os.path.exists(dconf_path):
                with open(dconf_path, 'r') as f:
                    for line in f:
                        if line.startswith("Le_API="):
                            le_api = line.split("'")[1] if "'" in line else ""
                        elif line.startswith("Le_Webroot="):
                            webroot = line.split("'")[1] if "'" in line else ""
            
            # Check for staging API
            if 'acme-staging' in le_api:
                return True
            
            # Check for wrong webroot
            if webroot and webroot != docroot:
                return True
            
            # Check if live files are missing
            if not os.path.exists(live_fullchain):
                return True
            
            # Check for fingerprint mismatch
            acme_chain = ""
            ecc_chain = f"{SSLReconcile.ACME_HOME}/{vhost}_ecc/fullchain.cer"
            reg_chain = f"{SSLReconcile.ACME_HOME}/{vhost}/fullchain.cer"
            
            if os.path.exists(ecc_chain):
                acme_chain = ecc_chain
            elif os.path.exists(reg_chain):
                acme_chain = reg_chain
            
            if acme_chain:
                acme_fp = SSLReconcile.sha256fp(acme_chain)
                live_fp = SSLReconcile.sha256fp(live_fullchain)
                if acme_fp and live_fp and acme_fp != live_fp:
                    return True
            
            return False
            
        except Exception as e:
            logging.writeToFile(f"Error checking force issue for {vhost}: {str(e)}")
            return True  # Force issue on error
    
    @staticmethod
    def reconcile_one(vconf_path):
        """Reconcile SSL configuration for a single vhost"""
        try:
            vhost = os.path.basename(os.path.dirname(vconf_path))
            
            # Read docRoot from vhost configuration
            docroot = ""
            with open(vconf_path, 'r') as f:
                for line in f:
                    if re.match(r'^\s*docRoot\s+', line):
                        docroot = SSLReconcile.trim(line.split()[1])
                        break
            
            if not docroot:
                logging.writeToFile(f"[skip] {vhost}: no docRoot")
                return False
            
            # Resolve $VH_ROOT variable
            if docroot.startswith('$VH_ROOT/'):
                docroot = docroot.replace('$VH_ROOT', f"{SSLReconcile.VHROOT_BASE}/{vhost}")
            
            # 1) Fix context location
            if not SSLReconcile.fix_context_location(vconf_path, docroot):
                return False
            
            # 2) Configure lineage
            dconf_path = SSLReconcile.pick_lineage_conf(vhost)
            SSLReconcile.set_kv(dconf_path, "Le_Webroot", docroot)
            SSLReconcile.set_kv(dconf_path, "Le_API", "https://acme-v02.api.letsencrypt.org/directory")
            
            # 3) Define live targets
            live_dir = f"/etc/letsencrypt/live/{vhost}"
            live_key = f"{live_dir}/privkey.pem"
            live_full = f"{live_dir}/fullchain.pem"
            live_cert = f"{live_dir}/cert.pem"
            os.makedirs(live_dir, exist_ok=True)
            
            # 4) Check if force issue is needed
            if SSLReconcile.needs_force_issue(vhost, dconf_path, docroot, live_full):
                # Build SAN set
                alt_domains = []
                if os.path.exists(dconf_path):
                    with open(dconf_path, 'r') as f:
                        for line in f:
                            if line.startswith("Le_Alt="):
                                alt = line.split("'")[1] if "'" in line else ""
                                if alt:
                                    alt_domains.append(alt)
                
                # Add www subdomain for base domains
                if not alt_domains and not vhost.startswith('www.'):
                    alt_domains.append(f"www.{vhost}")
                
                # Issue certificate
                cmd_parts = [f"{SSLReconcile.ACME_HOME}/acme.sh", "--issue", "-d", vhost]
                for alt in alt_domains:
                    cmd_parts.extend(["-d", alt])
                cmd_parts.extend(["-w", docroot, "--ecc", "--server", "letsencrypt", "--force"])
                
                result = subprocess.run(cmd_parts, capture_output=True, text=True)
                if result.returncode != 0:
                    logging.writeToFile(f"Certificate issuance failed for {vhost}: {result.stderr}")
                    return False
                
                logging.writeToFile(f"[issue] {vhost} certificate issued")
            
            # 5) Set installation targets
            SSLReconcile.set_kv(dconf_path, "Le_RealKeyPath", live_key)
            SSLReconcile.set_kv(dconf_path, "Le_RealFullChainPath", live_full)
            SSLReconcile.set_kv(dconf_path, "Le_RealCertPath", live_cert)
            
            # 6) Install certificate if needed
            if (not os.path.exists(live_full) or not os.path.exists(live_key) or 
                os.path.getsize(live_full) == 0 or os.path.getsize(live_key) == 0):
                
                cmd_parts = [
                    f"{SSLReconcile.ACME_HOME}/acme.sh", "--install-cert", "-d", vhost, "--ecc",
                    "--key-file", live_key,
                    "--fullchain-file", live_full,
                    "--cert-file", live_cert,
                    "--reloadcmd", SSLReconcile.RELOAD_CMD
                ]
                
                result = subprocess.run(cmd_parts, capture_output=True, text=True)
                if result.returncode == 0:
                    logging.writeToFile(f"[install] {vhost} -> {live_dir}")
                else:
                    logging.writeToFile(f"Certificate installation failed for {vhost}: {result.stderr}")
                    return False
            else:
                # Check if sync is needed
                acme_chain = ""
                ecc_chain = f"{SSLReconcile.ACME_HOME}/{vhost}_ecc/fullchain.cer"
                reg_chain = f"{SSLReconcile.ACME_HOME}/{vhost}/fullchain.cer"
                
                if os.path.exists(ecc_chain):
                    acme_chain = ecc_chain
                elif os.path.exists(reg_chain):
                    acme_chain = reg_chain
                
                if acme_chain:
                    acme_fp = SSLReconcile.sha256fp(acme_chain)
                    live_fp = SSLReconcile.sha256fp(live_full)
                    if acme_fp and live_fp and acme_fp != live_fp:
                        # Sync needed
                        cmd_parts = [
                            f"{SSLReconcile.ACME_HOME}/acme.sh", "--install-cert", "-d", vhost, "--ecc",
                            "--key-file", live_key,
                            "--fullchain-file", live_full,
                            "--cert-file", live_cert,
                            "--reloadcmd", SSLReconcile.RELOAD_CMD
                        ]
                        
                        result = subprocess.run(cmd_parts, capture_output=True, text=True)
                        if result.returncode == 0:
                            logging.writeToFile(f"[sync] {vhost} live files updated")
                        else:
                            logging.writeToFile(f"Certificate sync failed for {vhost}: {result.stderr}")
                            return False
                    else:
                        logging.writeToFile(f"[ok] {vhost} unchanged")
            
            return True
            
        except Exception as e:
            logging.writeToFile(f"Error reconciling {vconf_path}: {str(e)}")
            return False
    
    @staticmethod
    def reconcile_all():
        """Reconcile SSL configuration for all vhosts"""
        try:
            changed = 0
            vhosts_dir = SSLReconcile.VHOSTS_DIR
            
            if not os.path.exists(vhosts_dir):
                logging.writeToFile(f"VHosts directory not found: {vhosts_dir}")
                return False
            
            # Process all vhost configurations
            for vhost_name in os.listdir(vhosts_dir):
                vconf_path = os.path.join(vhosts_dir, vhost_name, "vhost.conf")
                if os.path.exists(vconf_path):
                    if SSLReconcile.reconcile_one(vconf_path):
                        changed += 1
            
            # Restart LiteSpeed
            try:
                subprocess.run(SSLReconcile.RELOAD_CMD, shell=True, check=True)
                logging.writeToFile(f"LiteSpeed restarted successfully")
            except subprocess.CalledProcessError as e:
                logging.writeToFile(f"Failed to restart LiteSpeed: {str(e)}")
            
            logging.writeToFile(f"[done] processed={changed} vhosts")
            return True
            
        except Exception as e:
            logging.writeToFile(f"Error in reconcile_all: {str(e)}")
            return False
    
    @staticmethod
    def reconcile_domain(domain):
        """Reconcile SSL configuration for a specific domain"""
        try:
            vconf_path = os.path.join(SSLReconcile.VHOSTS_DIR, domain, "vhost.conf")
            
            if not os.path.exists(vconf_path):
                logging.writeToFile(f"VHost configuration not found for {domain}")
                return False
            
            if SSLReconcile.reconcile_one(vconf_path):
                # Restart LiteSpeed
                try:
                    subprocess.run(SSLReconcile.RELOAD_CMD, shell=True, check=True)
                    logging.writeToFile(f"LiteSpeed restarted successfully for {domain}")
                except subprocess.CalledProcessError as e:
                    logging.writeToFile(f"Failed to restart LiteSpeed for {domain}: {str(e)}")
                
                return True
            else:
                return False
                
        except Exception as e:
            logging.writeToFile(f"Error reconciling domain {domain}: {str(e)}")
            return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            SSLReconcile.reconcile_all()
        elif sys.argv[1] == "--domain" and len(sys.argv) > 2:
            SSLReconcile.reconcile_domain(sys.argv[2])
        else:
            print("Usage: python sslReconcile.py [--all|--domain <domain>]")
    else:
        SSLReconcile.reconcile_all()
