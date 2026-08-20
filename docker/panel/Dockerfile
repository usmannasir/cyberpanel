# CyberPanel panel image (build from repo root)
# Example:
#   docker build -f docker/panel/Dockerfile --build-arg BASE_IMAGE=almalinux:10 --build-arg OS_FAMILY=rhel --build-arg OS_TAG=almalinux10 -t master3395/cyberpanel:almalinux10 .

ARG BASE_IMAGE=almalinux:10
ARG OS_FAMILY=rhel
ARG OS_TAG=almalinux10

FROM ${BASE_IMAGE}

# Re-declare build args after FROM (pre-FROM ARGs do not persist into the image stage).
ARG OS_FAMILY=rhel
ARG OS_TAG=almalinux10

LABEL org.opencontainers.image.title="CyberPanel"
LABEL org.opencontainers.image.vendor="News Targeted"
LABEL org.opencontainers.image.source="https://github.com/master3395/cyberpanel"
LABEL cyberpanel.os.tag="${OS_TAG}"

ENV container=docker
ENV CYBERPANEL_CONTAINER=1
ENV CYBERPANEL_OS_TAG=${OS_TAG}
ENV LANG=C.UTF-8
ENV OS_FAMILY=${OS_FAMILY}

STOPSIGNAL SIGRTMIN+3

# systemd in container
RUN if [ "$OS_FAMILY" = "debian" ]; then \
      export DEBIAN_FRONTEND=noninteractive && \
      apt-get update && \
      apt-get install -y --no-install-recommends systemd systemd-sysv dbus curl git ca-certificates openssh-server sudo iproute2 procps hostname && \
      apt-get clean && rm -rf /var/lib/apt/lists/* ; \
    else \
      (command -v dnf >/dev/null && dnf -y install systemd systemd-sysv dbus curl git ca-certificates openssh-server sudo iproute procps-ng hostname) || \
      (command -v yum >/dev/null && yum -y install systemd systemd-sysv dbus curl git ca-certificates openssh-server sudo iproute procps-ng hostname) ; \
      (command -v dnf >/dev/null && dnf clean all) || (command -v yum >/dev/null && yum clean all) || true ; \
    fi

RUN systemctl set-default multi-user.target 2>/dev/null || true

COPY docker/panel/entrypoint.sh /usr/local/cyberpanel-docker/entrypoint.sh
COPY docker/panel/first-boot.sh /usr/local/cyberpanel-docker/first-boot.sh
COPY docker/panel/healthcheck.sh /usr/local/cyberpanel-docker/healthcheck.sh
COPY docker/panel/systemd/cyberpanel-firstboot.service /etc/systemd/system/cyberpanel-firstboot.service
COPY . /usr/local/cyberpanel-installer/

RUN chmod +x /usr/local/cyberpanel-docker/entrypoint.sh \
    /usr/local/cyberpanel-docker/first-boot.sh \
    /usr/local/cyberpanel-docker/healthcheck.sh \
    && ln -sf /usr/local/cyberpanel-installer/cyberpanel.sh /usr/local/bin/cyberpanel.sh \
    && systemctl enable cyberpanel-firstboot.service 2>/dev/null || true

VOLUME ["/home", "/var/lib/mysql", "/etc/cyberpanel", "/var/lib/docker", "/var/mail", "/root/.acme.sh"]

EXPOSE 8090 80 443 7080 53 21 25 587 465 993 995 40100-40200

HEALTHCHECK --interval=60s --timeout=30s --start-period=900s --retries=3 \
  CMD ["/usr/local/cyberpanel-docker/healthcheck.sh"]

ENTRYPOINT ["/usr/local/cyberpanel-docker/entrypoint.sh"]
CMD ["/sbin/init"]
