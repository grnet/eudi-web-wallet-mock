#!/usr/bin/env bash

if [ "$1" == "-h" ]; then
    echo "Usage:"
    echo "install.sh [HOSTNAME]"
    echo
    echo "    HOSTNAME     the IP or host name to use to start the callback server"
    echo "                 (example: snf-895798.vm.okeanos.grnet.gr)"
    exit
fi

curl -sSL https://install.python-poetry.org | python3 -
echo 'export PATH="/home/ubuntu/.local/bin:$PATH"' >> ~/.bash_profile
. ~/.bash_profile
poetry self add poetry-plugin-shell
# poetry shell
poetry install

./setup-cert.sh $1

echo
echo "Installation complete. Run 'poetry shell' to activate the virtual "
echo "environment, then one of the following commands:"
echo "* 'python wallet_issuer.py' to run an issuance flow"
echo "* 'python wallet_verifier.py' to present a credential"
echo
