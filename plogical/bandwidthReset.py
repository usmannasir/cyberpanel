#!/usr/local/CyberCP/bin/python
import sys
sys.path.append('/usr/local/CyberCP')
import os
import json
from plogical import CyberCPLogFileWriter as logging
from websiteFunctions.models import Websites, ChildDomains

class BandwidthReset:
    """
    Bandwidth reset utility for CyberPanel
    Resets monthly bandwidth usage for all websites and child domains
    """
    
    @staticmethod
    def resetWebsiteBandwidth():
        """
        Reset bandwidth usage for all websites and child domains
        """
        try:
            logging.CyberCPLogFileWriter.writeToFile("Starting monthly bandwidth reset...")
            
            # Reset main websites
            websites = Websites.objects.all()
            reset_count = 0
            
            for website in websites:
                try:
                    # Load current config
                    try:
                        config = json.loads(website.config)
                    except:
                        config = {}
                    
                    # Reset bandwidth data
                    config['bwInMB'] = 0
                    config['bwUsage'] = 0
                    
                    # Save updated config
                    website.config = json.dumps(config)
                    website.save()
                    
                    reset_count += 1
                    logging.CyberCPLogFileWriter.writeToFile(f"Reset bandwidth for website: {website.domain}")
                    
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error resetting bandwidth for website {website.domain}: {str(e)}")
            
            # Reset child domains
            child_domains = ChildDomains.objects.all()
            
            for child in child_domains:
                try:
                    # Load current config
                    try:
                        config = json.loads(child.config)
                    except:
                        config = {}
                    
                    # Reset bandwidth data
                    config['bwInMB'] = 0
                    config['bwUsage'] = 0
                    
                    # Save updated config
                    child.config = json.dumps(config)
                    child.save()
                    
                    reset_count += 1
                    logging.CyberCPLogFileWriter.writeToFile(f"Reset bandwidth for child domain: {child.domain}")
                    
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error resetting bandwidth for child domain {child.domain}: {str(e)}")
            
            # Clean up bandwidth metadata files
            BandwidthReset.cleanupBandwidthMetadata()
            
            logging.CyberCPLogFileWriter.writeToFile(f"Monthly bandwidth reset completed. Reset {reset_count} domains.")
            return reset_count, total_reset_mb
            
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error in monthly bandwidth reset: {str(e)}")
            return 0, 0
    
    @staticmethod
    def resetDomainBandwidth(domain_name):
        """
        Reset bandwidth for a specific domain
        """
        try:
            logging.CyberCPLogFileWriter.writeToFile(f"Resetting bandwidth for domain: {domain_name}")
            
            # Reset main website
            try:
                website = Websites.objects.get(domain=domain_name)
                config = json.loads(website.config)
                config['bwInMB'] = 0
                config['bwUsage'] = 0
                website.config = json.dumps(config)
                website.save()
                logging.CyberCPLogFileWriter.writeToFile(f"Reset bandwidth for website: {domain_name}")
            except Websites.DoesNotExist:
                logging.CyberCPLogFileWriter.writeToFile(f"Website {domain_name} not found")
                return False
            
            # Reset child domains for this website
            child_domains = ChildDomains.objects.filter(master=website)
            for child in child_domains:
                try:
                    config = json.loads(child.config)
                    config['bwInMB'] = 0
                    config['bwUsage'] = 0
                    child.config = json.dumps(config)
                    child.save()
                    logging.CyberCPLogFileWriter.writeToFile(f"Reset bandwidth for child domain: {child.domain}")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error resetting child domain {child.domain}: {str(e)}")
            
            # Clean up bandwidth metadata file for this domain
            metadata_file = f"/home/cyberpanel/{domain_name}.bwmeta"
            if os.path.exists(metadata_file):
                try:
                    with open(metadata_file, 'w') as f:
                        f.write("0\n0\n")
                    os.chmod(metadata_file, 0o600)
                    logging.CyberCPLogFileWriter.writeToFile(f"Reset metadata file: {metadata_file}")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error resetting metadata file: {str(e)}")
            
            logging.CyberCPLogFileWriter.writeToFile(f"Bandwidth reset completed for domain: {domain_name}")
            return True
            
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error resetting bandwidth for domain {domain_name}: {str(e)}")
            return False
    
    @staticmethod
    def cleanupBandwidthMetadata():
        """
        Clean up bandwidth metadata files
        """
        try:
            import glob
            
            # Clean up main bandwidth metadata files
            metadata_files = glob.glob("/home/cyberpanel/*.bwmeta")
            for file_path in metadata_files:
                try:
                    # Reset the metadata file to 0 usage
                    with open(file_path, 'w') as f:
                        f.write("0\n0\n")
                    os.chmod(file_path, 0o600)
                    logging.CyberCPLogFileWriter.writeToFile(f"Reset metadata file: {file_path}")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error resetting metadata file {file_path}: {str(e)}")
            
            # Clean up domain-specific bandwidth metadata files
            domain_metadata_files = glob.glob("/home/*/logs/bwmeta")
            for file_path in domain_metadata_files:
                try:
                    # Reset the metadata file to 0 usage
                    with open(file_path, 'w') as f:
                        f.write("0\n0\n")
                    os.chmod(file_path, 0o600)
                    logging.CyberCPLogFileWriter.writeToFile(f"Reset domain metadata file: {file_path}")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error resetting domain metadata file {file_path}: {str(e)}")
                    
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error cleaning up bandwidth metadata: {str(e)}")
    
    @staticmethod
    def resetSpecificDomain(domain_name):
        """
        Reset bandwidth for a specific domain
        """
        try:
            # Try to find as main website
            try:
                website = Websites.objects.get(domain=domain_name)
                try:
                    config = json.loads(website.config)
                except:
                    config = {}
                
                config['bwInMB'] = 0
                config['bwUsage'] = 0
                website.config = json.dumps(config)
                website.save()
                
                logging.CyberCPLogFileWriter.writeToFile(f"Reset bandwidth for website: {domain_name}")
                return True
                
            except Websites.DoesNotExist:
                pass
            
            # Try to find as child domain
            try:
                child = ChildDomains.objects.get(domain=domain_name)
                try:
                    config = json.loads(child.config)
                except:
                    config = {}
                
                config['bwInMB'] = 0
                config['bwUsage'] = 0
                child.config = json.dumps(config)
                child.save()
                
                logging.CyberCPLogFileWriter.writeToFile(f"Reset bandwidth for child domain: {domain_name}")
                return True
                
            except ChildDomains.DoesNotExist:
                logging.CyberCPLogFileWriter.writeToFile(f"Domain not found: {domain_name}")
                return False
                
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error resetting bandwidth for domain {domain_name}: {str(e)}")
            return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='CyberPanel Bandwidth Reset Utility')
    parser.add_argument('--reset-all', action='store_true', help='Reset bandwidth for all domains')
    parser.add_argument('--domain', help='Reset bandwidth for specific domain')
    parser.add_argument('--cleanup-metadata', action='store_true', help='Clean up bandwidth metadata files only')
    
    args = parser.parse_args()
    
    if args.reset_all:
        BandwidthReset.resetWebsiteBandwidth()
    elif args.domain:
        BandwidthReset.resetSpecificDomain(args.domain)
    elif args.cleanup_metadata:
        BandwidthReset.cleanupBandwidthMetadata()
    else:
        print("Please specify an action: --reset-all, --domain <domain_name>, or --cleanup-metadata")
        sys.exit(1)

if __name__ == "__main__":
    main()
