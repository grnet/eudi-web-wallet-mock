import argparse
import base64
import hashlib
import json
import logging
import os
import pprint
import re
import requests
import time
import urllib
import urllib3
from datetime import datetime, timezone
from multiprocessing import Process, set_start_method
from typing import Optional
from urllib.parse import urlparse

import jwt
from cryptography.hazmat.primitives import serialization
from flask import Flask, jsonify, make_response, request, Response

logger = logging.getLogger("mock-wallet")
logging.basicConfig(level=logging.INFO)

ssl_verify = False
# Silence warning regarding the absence of SSL certificate check.
if not ssl_verify:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
config = {}
p: Optional[Process] = None

# Need to inherit unpicklable local objects and
# internal file descriptors from parent process.
set_start_method("fork")


# Run auth endpoint for wallet with Flask in separate process.
app = Flask(__name__)


DEFAULT_ISSUER="https://83.212.72.114:5000"
# DEFAULT_ISSUER="https://snf-895798.vm.okeanos.grnet.gr:5000"

def start_wallet_auth_endpoint(auth_endpoint: str) -> None:
    global p
    print(f"Starting authentication endpoint: {auth_endpoint}")
    parsed_endpoint = urlparse(auth_endpoint)
    host, port = parsed_endpoint.hostname, parsed_endpoint.port
    debug = config["auth_endpoint_debug"]
    context = (
        config["certificate_file"],
        config["certificate_private_key_file"],
    )
    kwargs = {
        "host": host,
        "port": port,
        "debug": debug,
        "ssl_context": context,
    }
    p = Process(target=app.run, kwargs=kwargs)
    p.start()


# It would be more polite to send a MultiProcessing.Event to exit.
def stop_wallet_auth_endpoint() -> None:
    p.terminate()
    while p.is_alive():
        time.sleep(1)
    p.close()


@app.route("/auth", methods=["GET"])
def auth() -> Response:
    logger.info(f"Wallet auth: Received URL: {request.url}")

    try:
        query_string = request.url.split("?")[1]
    except IndexError:
        return Response(status=400)

    json_query_string = urllib.parse.parse_qs(query_string)
    json_params = {(k, v[0]) for k, v in json_query_string.items()}

    logger.info(f"Json query string: {json_params}")

    return make_response(jsonify(json_query_string), 200)


# Issuer uses OpenID Connect Registration.
def register_wallet(wallet_auth_endpoint: str) -> dict[str, str]:
    params = {"redirect_uris": wallet_auth_endpoint}
    r = requests.get(
        config['registration_endpoint'], params=params, verify=ssl_verify
    )
    if r.status_code != requests.codes.created:  # 201
        logger.error(f"Wallet registration failed ({r.status_code}). Exit.")
        wallet_exit()
    registration_response = r.json()
    logger.info("Wallet registration response:")
    logger.info(json.dumps(registration_response, indent=4))

    return registration_response


# According to the OIDC4VC standard, the issuer can communicate a state
# identifier via the credential offer. The state can be included by the
# wallet in the following steps of the flow.
def get_credential_offer() -> tuple[str, list[str]]:
    with open(config["credential_offer_file"]) as f:
        credential_offer = json.load(f)

    issuer_state = credential_offer["grants"]["authorization_code"][
        "issuer_state"
    ]
    logger.info(
        f'Credential issuer: {config["issuer_url"]}, state: {issuer_state}'
    )
    credential_configuration_ids = credential_offer[
        "credential_configuration_ids"
    ]

    return issuer_state, credential_configuration_ids


# According to the OIDC4VC standard (Section 3.4-3.5 step 3), the
# wallet needs the Credential Issuer's metadata to learn four aspects:
# 1. Credential types   (/.well-known/openid-credential-issuer)
# 2. Credential formats (/.well-known/openid-credential-issuer)
# 3. Token endpoint at the OAuth 2.0 Authorization Server
#       (/.well-known/openid-configuration)
# 4. Credential endpoint required to start the request
#       (/.well-known/openid-credential-issuer)
def retrieve_issuer_metadata(
    credential_configuration_ids: list[str],
) -> tuple[str, str, str, str, tuple[str, str, str, str]]:
    issuer_url = config["issuer_url"]
    logger.info(f"Retrieve metadata from credential issuer: {issuer_url}")

    r = requests.get(
        f"{issuer_url}/.well-known/openid-credential-issuer", verify=ssl_verify
    )
    issuer_metadata = r.json()
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Issuer metadata failed ({r.status_code}). Exit.")
        wallet_exit()
    logger.info(f"Issuer metadata keys: {issuer_metadata.keys()}")
    # logger.debug(f'{pprint.pprint(issuer_metadata)}')

    auth_server = config["authentication_server"]
    r = requests.get(
        f"{auth_server}/.well-known/openid-configuration", verify=ssl_verify
    )
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Issuer config failed ({r.status_code}). Exit.")
        wallet_exit()
    auth_server_config = r.json()
    logger.info(f"Authentication server OpenID config keys: {auth_server_config.keys()}")
    # logger.debug(f'{pprint.pprint(auth_server_config)}')

    supported_cred_configs = issuer_metadata[
        "credential_configurations_supported"
    ]
    cred_configs = [
        (
            cred_config_id,
            supported_cred_configs[cred_config_id]["scope"],
            supported_cred_configs[cred_config_id]["format"],
            supported_cred_configs[cred_config_id]["doctype"],
        )
        for cred_config_id in credential_configuration_ids
    ]
    logger.info(f"cred_configs: {cred_configs}")
    if verbose:
        logger.info(f"auth_server_config: {auth_server_config}")

    return (
        auth_server_config["pushed_authorization_request_endpoint"],
        auth_server_config["authorization_endpoint"],
        auth_server_config["token_endpoint"],
        issuer_metadata["credential_endpoint"],
        cred_configs,
    )


def auth_request(
    pushed_auth_endpoint: str, auth_endpoint: str, wallet_auth_endpoint: str, state: str, scope: list[str]
) -> tuple[requests.Session, str]:
    logger.info(
        f"Authorize using auth endpoints: {pushed_auth_endpoint}, "
        f"{auth_endpoint}, {wallet_auth_endpoint}"
    )
    http_headers = {
        "Accept": "application/json",
        "Accept-Charset": "UTF-8",
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    }
    client_id = config["client_id"]
    redirect_uri = wallet_auth_endpoint

    code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")

    s = requests.Session()

    params = {
        "response_type": "code",
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
        "client_id": client_id,
        "scope": scope,
        "state": state,
        "redirect_uri": redirect_uri,
    }
    r = s.post(
        pushed_auth_endpoint,
        data=params,
        headers=http_headers,
        verify=ssl_verify,
    )
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Pushed authorization failed ({r.status_code}). Exit.")
        if verbose:
            logger.error(params)
            logger.error(r.json())
        wallet_exit()
    logger.info(f"{r}, {r.reason}, {r.json()}, {r.headers}")
    request_uri = r.json()["request_uri"]
    cookie = r.headers["Set-Cookie"]
    logger.info(f"Auth returned request_uri: {request_uri}, cookie: {cookie}")

    params = {
        "client_id": client_id,
        "state": state,
        "request_uri": request_uri,
    }
    r = s.get(auth_endpoint, params=params, verify=ssl_verify)
    if r.status_code != requests.codes.ok:  # 200
        if verbose:
            logger.info(r.json())
        logger.error(f"Authorization failed ({r.status_code}). Exit.")
        wallet_exit()

    return s, code_verifier


def fill_in_ui_forms(
    s: requests.Session, credential_configuration_id: str
) -> dict:

    # UI page: Authentication Method Selection
    #          Please select Authentication Method
    # app/templates/misc/auth_method.html
    select_auth_method_country(s)

    # UI page: Request credentials for your EUDI Wallet
    #          Please select your country of origin
    # app/templates/dynamic/dynamic-countries.html
    country = "FC"
    select_country_origin(s, credential_configuration_id, country)

    # UI page: Enter the data for your EUDI Wallet
    #          Please select your basic information
    # app/templates/dynamic/dynamic-form.html
    user_id = enter_credential_data(s, country)

    # UI page: Authorize data from your EUDI Wallet
    #          Please confirm your information
    # app/templates/dynamic/form-authorize.html
    return confirm_credential_data(s, user_id)


def select_auth_method_country(s: requests.Session) -> None:
    # link2 corresponds to country selection.
    params = {"optionsRadios": "link2"}

    r = s.get(
        f"{config['issuer_url']}/dynamic/auth_method",
        data=params,
        verify=ssl_verify,
    )
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Auth method selection failed ({r.status_code}). Exit.")
        wallet_exit()
    logger.info(f"{r}, {r.headers}")


def select_country_origin(
    s: requests.Session, credential_configuration_id: str, country: str
) -> None:
    # FC corresponds to the FormEU country selection shown in the UI.
    params = {"country": country, "proceed": "Submit"}

    auth_details = [
        {
            "type": "openid_credential",
            "credential_configuration_id": credential_configuration_id,
        }
        for credential_configuration_id in credential_configuration_ids
    ]
    parsed_auth_details = urllib.parse.quote(json.dumps(auth_details))
    url_query = f"authorization_details={parsed_auth_details}"
    r = s.post(
        f"{config['issuer_url']}/dynamic/?{url_query}",
        data=params,
        verify=ssl_verify,
    )
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Country selection failed ({r.status_code}). Exit.")
        wallet_exit()


def enter_credential_data(s: requests.Session, country: str) -> str:
    with open(config["credential_data_file"]) as f:
        params = json.load(f)

    params = params | {"proceed": "Submit"}
    logger.info(f"Credential data: {params}")
    r = s.get(
        f"{config['issuer_url']}/dynamic/form", data=params, verify=ssl_verify
    )
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Data entry failed ({r.status_code}). Exit.")
        wallet_exit()

    # Extract user id of the form <country>.<uuid> from templated HTML
    # page.
    # Example user id: FC.dcb7aaec-fd30-44ad-b431-38769b17b424
    reg_match = re.search(
        rf'"({country}.[a-zA-Z0-9-]+)" name="user_id"', r.text
    )
    user_id = reg_match.group(1)

    return user_id


def confirm_credential_data(s: requests.Session, user_id: str) -> dict:
    params = {
        "user_id": user_id,
    }
    r = s.get(
        f"{config['issuer_url']}/dynamic/redirect_wallet",
        data=params,
        verify=ssl_verify,
    )
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Wallet redirection failed ({r.status_code}). Exit.")
        wallet_exit()
    auth_params = r.json()
    logger.info(f"auth params: {auth_params}")

    return auth_params


def request_token(
    token_endpoint: str,
    wallet_auth_endpoint: str,
    s: requests.Session,
    auth_params: dict,
    code_verifier: str,
) -> tuple[str, str]:
    params = {
        "grant_type": "authorization_code",
        "client_id": auth_params["client_id"],
        "code": auth_params["code"],
        "redirect_uri": wallet_auth_endpoint,
        "code_verifier": code_verifier,
    }
    r = s.post(token_endpoint, data=params, verify=ssl_verify)
    if r.status_code != requests.codes.ok:  # 200
        logger.error(f"Token request failed ({r.status_code}). Exit.")
        wallet_exit()
    token_data = r.json()
    token = token_data["access_token"]
    token_type = token_data["token_type"]

    return token, token_type


def request_credential(
    credential_endpoint: str,
    s: requests.Session,
    token: str,
    token_type: str,
    docformat: str,
    doctype: str,
) -> dict:
    http_headers = {
        "Accept": "application/json",
        "Accept-Charset": "UTF-8",
        "Content-Type": "application/json",
        "Authorization": f"{token_type} {token}",
    }
    params = {
        "format": docformat,
        "doctype": doctype,
    }
    if verbose:
        logger.info(f"credential request params: {params}")
    r = s.post(
        credential_endpoint,
        json=params,
        headers=http_headers,
        verify=ssl_verify,
    )
    bad_resp = r.json()
    nonce = bad_resp["c_nonce"]
    logger.info(f"nonce: {nonce}")

    jwk_args, private_key = create_jwk()
    client_id = config["client_id"]
    payload = {
        "iss": client_id,
        "aud": config["issuer_url"],
        "iat": datetime.now(tz=timezone.utc),
        "nonce": nonce,
    }
    jwt_token = jwt.encode(payload=payload, key=private_key, headers=jwk_args)
    logger.info(f"private key: {private_key}")
    logger.info(f"encoded_jwt: {jwt_token}")

    params["proof"] = {"proof_type": "jwt", "jwt": jwt_token}
    logger.info(f"params: {params}")
    r = s.post(
        credential_endpoint,
        json=params,
        headers=http_headers,
        verify=ssl_verify,
    )
    if r.status_code != requests.codes.ok:  # 200
        if verbose:
            logger.info(r.json())
        logger.error(f"Credential request failed ({r.status_code}). Exit.")
        wallet_exit()
    credential = r.json()

    return credential


def create_jwk() -> tuple[dict, str]:
    with open(config["certificate_private_key_file"], "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(), password=None
        )
    private_key_curve_identifier, private_key_x, private_key_y = KeyData(
        private_key, "private"
    )
    logger.info(f"curve: {private_key_curve_identifier}")
    jwk_args = {
        "typ": "openid4vci-proof+jwt",
        "alg": "ES256",
        "jwk": {
            "kty": "EC",
            "crv": private_key_curve_identifier,
            "x": jwt.utils.base64url_encode(private_key_x).decode("utf-8"),
            "y": jwt.utils.base64url_encode(private_key_y).decode("utf-8"),
        },
    }

    return jwk_args, private_key


# Pasted from issuer:
# eudi-srv-web-issuing-eudiw-py/app/formatter_func.py
def KeyData(key, type):
    curve_map = {
        "secp256r1": "P-256",  # NIST P-256
        "secp384r1": "P-384",  # NIST P-384
        "secp521r1": "P-521",  # NIST P-521
    }
    key_curve_name = key.curve.name
    curve_identifier = curve_map.get(key_curve_name)

    if type == "public":
        # Extract the x and y coordinates from the public key
        x = key.public_numbers().x.to_bytes(
            (key.public_numbers().x.bit_length() + 7)
            // 8,  # Number of bytes needed
            "big",  # Byte order
        )

        y = key.public_numbers().y.to_bytes(
            (key.public_numbers().y.bit_length() + 7)
            // 8,  # Number of bytes needed
            "big",  # Byte order
        )
    else:
        # Extract the x and y coordinates from the private key
        x = key.private_numbers().public_numbers.x.to_bytes(
            (key.private_numbers().public_numbers.x.bit_length() + 7)
            // 8,  # Number of bytes needed
            "big",  # Byte order
        )

        y = key.private_numbers().public_numbers.y.to_bytes(
            (key.private_numbers().public_numbers.y.bit_length() + 7)
            // 8,  # Number of bytes needed
            "big",  # Byte order
        )

    return curve_identifier, x, y


def wallet_exit() -> None:
    stop_wallet_auth_endpoint()
    exit(1)


def get_available_configurations():
    try:
        with open("wallet_issuer_config.json", "r") as f:
            config = json.load(f)
        if "credential_configurations" in config:
            return config["credential_configurations"].keys()
    except FileNotFoundError:
        pass
    return []

if __name__ == "__main__":
    try:
        with open(".config.ip") as local_ip_file:
            default_wallet_ip = local_ip_file.read().strip()
    except FileNotFoundError:
        default_wallet_ip = "snf-895798.vm.okeanos.grnet.gr"

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--credential-output",
        help="Output file for credential",
        default="credential.out",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Log more information",
    )
    parser.add_argument(
        "--wallet-auth-endpoint",
        type=str,
        help="Wallet authentication endpoint to start",
        default=f"https://{default_wallet_ip}:6000/auth",
    )
    parser.add_argument(
        "--issuer-url",
        help="The URL of the issuer",
        default=DEFAULT_ISSUER,
    )
    parser.add_argument(
        "--authentication-server",
        help="The hostname of the authentication server, defaults to the issuer",
    )
    parser.add_argument(
        "--registration-endpoint",
        help="The URL of the registration endpoint",
        default=f"{DEFAULT_ISSUER}/registration",
    )
    parser.add_argument(
        "--configuration",
        help="Credential configuration",
        choices=get_available_configurations(),
        default="pid_mdoc",
    )
    args = parser.parse_args()
    verbose = args.verbose

    logger.info("OIDC4VC draft 14, 1 October 2024")
    logger.info(
        "https://openid.github.io/OpenID4VCI/"
        "openid-4-verifiable-credential-issuance-wg-draft.html"
    )

    # Load wallet config
    with open("wallet_issuer_config.json") as f:
        config = json.load(f)

    config["issuer_url"] = args.issuer_url
    if args.authentication_server:
        config["authentication_server"] = args.authentication_server
    else:
        config["authentication_server"] = config["issuer_url"]
    config["registration_endpoint"] = args.registration_endpoint
    logger.info(f"Using credential configuration: {args.configuration}")
    config.update(config["credential_configurations"][args.configuration])

    logger.info("Start wallet auth endpoint in separate process.")
    start_wallet_auth_endpoint(args.wallet_auth_endpoint)

    # Assume issuer is also wallet provider. Register wallet.
    registration = register_wallet(args.wallet_auth_endpoint)

    # Credential offer: Diagram step 1b, document section 4
    state, credential_configuration_ids = get_credential_offer()

    # Issuer metadata: Diagram step 2, document section 10.2
    (
        pushed_auth_endpoint,
        auth_endpoint,
        token_endpoint,
        credential_endpoint,
        cred_configs,
    ) = retrieve_issuer_metadata(credential_configuration_ids)

    for credential_configuration_id, scope, docformat, doctype in cred_configs:
        logger.info(
            f"Auth - token - credential flow for credential:"
            f"\n  credential_config_id: {credential_configuration_id}"
            f"\n  scope: {scope}"
            f"\n  docformat: {docformat}"
            f"\n  doctype: {doctype}"
        )

        # Authorization: Diagram step 3, document section 5
        session, code_verifier = auth_request(
            pushed_auth_endpoint, auth_endpoint, args.wallet_auth_endpoint, state, scope
        )
        auth_params = fill_in_ui_forms(session, credential_configuration_id)

        # Token: Diagram step 5, document section 6
        token, token_type = request_token(
            token_endpoint, args.wallet_auth_endpoint, session, auth_params, code_verifier
        )

        # Credential: Diagram step 6, document section 7
        credential = request_credential(
            credential_endpoint, session, token, token_type, docformat, doctype
        )

        logger.info("Received credential")
        logger.info(f"{pprint.pprint(credential)}")

        with open(args.credential_output, "w") as f:
            f.write(credential["credential"])
        logger.info(f"Credential written to {args.credential_output}")

    stop_wallet_auth_endpoint()
