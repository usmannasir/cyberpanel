# Use Debian as the base image
FROM debian:11.0

# Install required dependencies
RUN apt-get update && \
    apt-get install -y wget gnupg ca-certificates

# Install OpenLiteSpeed
RUN wget -O - http://rpms.litespeedtech.com/debian/enable_lst_debian_repo.sh | bash

RUN apt-get install -y openlitespeed

# Install PHP and required PHP extensions for WordPress
RUN apt-get install -y lsphp82*

###

RUN rm -rf /usr/local/lsws/Example/html/*

# Install WP CLI

RUN wget https://github.com/wp-cli/wp-cli/releases/download/v2.7.1/wp-cli-2.7.1.phar
RUN chmod +x wp-cli-2.7.1.phar
RUN mv wp-cli-2.7.1.phar /usr/bin/wp

## set up vh conf

RUN rm -f /usr/local/lsws/conf/vhosts/Example/vhconf.conf
COPY ./vhconf.conf /usr/local/lsws/conf/vhosts/Example/vhconf.conf

# Expose necessary ports
EXPOSE 8088

# Copy entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# Set execute permissions
RUN chmod +x /usr/local/bin/entrypoint.sh

# Define entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
