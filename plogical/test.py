import os

def find_php_versions():
    import re
    import os
    php_versions = []
    lsws_directory = "/usr/local/lsws"

    if os.path.exists(lsws_directory):
        for dir_name in os.listdir(lsws_directory):
            full_path = os.path.join(lsws_directory, dir_name)
            if os.path.isdir(full_path) and dir_name.startswith("lsphp"):
                php_version = dir_name.replace("lsphp", "PHP ").replace("", ".")
                php_versions.append(php_version)

    result_list = []
    for item in sorted(php_versions):
        # Use regular expression to find numbers in the string
        numbers = re.findall(r'\d+', item)

        # Join the numbers with dots and add 'PHP' back to the string
        result = 'PHP ' + '.'.join(numbers)

        result_list.append(result)

    return result_list

if __name__ == "__main__":
    php_versions = find_php_versions()
    print(php_versions)
