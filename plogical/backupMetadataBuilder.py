from xml.etree.ElementTree import Element, SubElement


def build_dns_records_xml(records):
    records_xml = Element("dnsrecords")
    for record in records or []:
        record_xml = Element("dnsrecord")
        SubElement(record_xml, "type").text = record.type
        SubElement(record_xml, "name").text = record.name
        SubElement(record_xml, "content").text = record.content
        SubElement(record_xml, "priority").text = str(record.prio)
        records_xml.append(record_xml)
    return records_xml


def build_email_accounts_xml(accounts):
    accounts_xml = Element("emails")
    for account in accounts or []:
        account_xml = Element("emailAccount")
        SubElement(account_xml, "email").text = account.email
        SubElement(account_xml, "password").text = account.password
        accounts_xml.append(account_xml)
    return accounts_xml
