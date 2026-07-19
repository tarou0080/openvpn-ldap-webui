FROM rockylinux:9

# Install required packages
RUN dnf update -y && \
    dnf install -y epel-release && \
    dnf install -y \
    openvpn \
    easy-rsa \
    openssl \
    iptables \
    wget \
    python3 \
    python3-pip \
    openldap-clients \
    --allowerasing \
    && dnf clean all

# Install Python packages for Certificate API and LDAP auth
RUN pip3 install --no-cache-dir flask requests ldap3

# Create directories
RUN mkdir -p /etc/openvpn/{server,ccd,logs} && \
    mkdir -p /var/log/openvpn

# Copy easy-rsa to OpenVPN directory
RUN cp -r /usr/share/easy-rsa /etc/openvpn/

# Handle openvpn user (already created by package)
RUN id openvpn || useradd --system --shell /bin/false --home-dir /var/lib/openvpn --create-home openvpn

# Create scripts directory
RUN mkdir -p /scripts

# Expose ports
EXPOSE 1194/udp 8080/tcp

# Set ownership
RUN chown -R openvpn:openvpn /var/log/openvpn

ENTRYPOINT ["/usr/local/bin/start-openvpn.sh"]
