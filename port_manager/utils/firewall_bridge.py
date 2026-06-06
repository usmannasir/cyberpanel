from plogical.firewallUtilities import FirewallUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from .validation import parse_port, parse_proto

def open_port(proto, port, ip='0.0.0.0/0'):
    proto = parse_proto(proto)
    port_i = parse_port(port)
    if not proto or port_i is None:
        return False, 'invalid port or proto'
    if ip != '0.0.0.0/0':
        return False, 'unsupported ip scope'
    try:
        res = FirewallUtilities.addRule(proto, str(port_i), ip)
        if res:
            return True, 'ok'
        return False, 'firewall rule failed'
    except Exception as msg:
        logging.writeToFile('Port Manager firewall open error: ' + str(msg))
        return False, 'error'
