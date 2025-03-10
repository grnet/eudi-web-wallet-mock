#!/usr/bin/env bash
# Test against the reference implementation issuer, deployed locally (same IP).
set -e

IP=$(cat .config.ip)

python wallet_issuer.py --wallet-auth-endpoint https://${IP}:6000/auth --issuer-url https://${IP}:5000 --registration-endpoint https://${IP}:5000/registration --configuration pid_mdoc
