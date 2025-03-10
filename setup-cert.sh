#!/usr/bin/env bash

if [ "$1" == "-h" ]; then
    echo "Usage:"
    echo "setup-cert.sh [HOSTNAME]"
    echo
    echo "    HOSTNAME     the IP or host name to use to deploy the server"
    echo "                 (example: snf-895798.vm.okeanos.grnet.gr)"
    exit
elif [ "$1" == "" ]; then
    ./resolve-ip.sh > .config.ip
    HOSTNAME=$(cat .config.ip)
else
    HOSTNAME="$1"
fi
echo "Deploying at: ${HOSTNAME}"

echo "Generating TLS certificate..."
openssl ecparam -out data/ec_private_key.pem -name prime256v1 -genkey
openssl req -new -key data/ec_private_key.pem -x509 -nodes -days 365 -subj "/CN=${HOSTNAME}" -out data/mock_wallet_cert.pem
