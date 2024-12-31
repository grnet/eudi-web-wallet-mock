#!/usr/bin/env bash
python wallet_issuer.py --issuer-type GRNET --verbose \
                        --wallet-auth-endpoint https://localhost:6000/auth \
                        --issuer-url https://localhost \
                        --registration-endpoint https://localhost/oidc/registration
