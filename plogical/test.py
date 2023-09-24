import re


def extract_domain_parts(domain):
    # Use a regular expression to extract the domain parts
    pattern = r'(?:\w+\.)?(\w+)\.(\w+)'
    match = re.match(pattern, domain)

    if match:
        subdomain = match.group(1)
        top_level_domain = match.group(2)
        return subdomain, top_level_domain
    else:
        return None, None


# Example usage
domain = "sub.example.ae"
subdomain, top_level_domain = extract_domain_parts(domain)
print("Subdomain:", subdomain)
print("Top-Level Domain:", top_level_domain)
