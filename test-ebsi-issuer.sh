#!/usr/bin/env bash
# Test against the EBSI issuer, deployed locally (same IP/hostname).
set -e

if [ "$1" == "-h" ]; then
    echo "Usage: test-ebsi-issuer.sh [HOSTNAME]"
    echo
    echo "    HOSTNAME   the hostname of this machine, empty to use local IP"
    exit
elif [ "$1" == "" ]; then
    LOCAL_ADDR=$(cat .config.ip)
else
    LOCAL_ADDR=$1
fi

python wallet_issuer.py --wallet-auth-endpoint https://${LOCAL_ADDR}:6000/auth --issuer-url https://${LOCAL_ADDR}:8000 --registration-endpoint https://${LOCAL_ADDR}:8000/registration --configuration pid_mdoc --verbose
