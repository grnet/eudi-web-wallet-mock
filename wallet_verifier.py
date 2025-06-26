import argparse
# import base64
# import chardet
#import cbor2
import json
import logging
# import os
import pprint
import requests
# import sys
import urllib3
from multiprocessing import Process, set_start_method
from urllib.parse import urlparse
from typing import Optional

from flask import Flask, jsonify, make_response, request, Response


logger = logging.getLogger("mock-wallet")
logging.basicConfig(level=logging.INFO)

config = {}

ssl_verify = False
# Silence warning regarding the absence of SSL certificate check.
if not ssl_verify:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
config = {}
p: Optional[Process] = None

# Need to inherit unpicklable local objects and
# internal file descriptors from parent process.
set_start_method("fork")

# Run wallet metadata endpoint with Flask in separate process.
app = Flask(__name__)


def start_wallet_metadata_endpoint() -> None:
    global p
    metadata_endpoint = config["metadata_endpoint"]
    parsed_endpoint = urlparse(metadata_endpoint)
    host, port = parsed_endpoint.hostname, parsed_endpoint.port
    context = (
        config["certificate_file"],
        config["certificate_private_key_file"],
    )
    kwargs = {
        "host": host,
        "port": port,
        "debug": False,
        "ssl_context": context,
    }
    p = Process(target=app.run, kwargs=kwargs)
    p.start()


def test_call_parameters(method: str, payload: dict, headers: dict):
    r = requests.post(
        f"{prot}://httpbin.org/{method}", data=payload, headers=headers
    )
    logger.info(r.json())


# Initialize transaction endpoint
def init_transaction() -> tuple[str, str]:
    with open(config["auth_request_file"]) as f:
        auth_request = json.load(f)

    r = requests.post(
        f"{config['verifier_url']}/ui/presentations",
        json=auth_request,
        verify=config["ssl_verify"],
    )
    #r = requests.post(f'{verifier_url}/ui/presentations',
    #                  json=auth_request, verify='../grnet_cert.pem')
    r_json = r.json()
    logger.info(f"#1. Auth request returned (status={r.status_code}):")
    logger.info(f"{pprint.pprint(r_json, compact=True)}")

    # request_id would be a more accurate parameter name than transaction_id.
    transaction_id = r_json["request_uri"].split("/")[-1]
    presentation_id = r_json["presentation_id"]
    logger.info(f"presentation_id: {presentation_id}")
    logger.info(f"transaction_id: {transaction_id}\n")

    return transaction_id, presentation_id


# Get authorization request
def get_auth_request(transaction_id: str) -> None:
    r = requests.get(
        f"{config['verifier_url']}/wallet/request.jwt/{transaction_id}",
        verify=config["ssl_verify"],
    )

    logger.info(f"#2. Get auth request returned (status={r.status_code}).")
    logger.info("  Authorization request payload as a signed JWT:")
    auth_request_payload = r.text
    logger.info(f"{auth_request_payload}\n")


# Get presentation definition
def get_presentation_def(transaction_d: str) -> None:
    r = requests.get(
        f"{config['verifier_url']}/wallet/pd/{transaction_id}",
        verify=config["ssl_verify"],
    )
    logger.info(
        f"#3. Get presentation definition returned (status={r.status_code})."
    )
    logger.info(
        "  Presentation definition of the authorization request as JSON:"
    )
    presentation_def = r.json()
    logger.info(f"{pprint.pprint(presentation_def, compact=True)}")
    logger.info("\n")


# Send wallet response
def send_wallet_response(transaction_id: str) -> str:
    logger.info("#4. Send the following wallet response.")
    with open(config["wallet_response_file"]) as f:
        wallet_response = json.load(f)
    logger.info(f"{pprint.pprint(wallet_response, compact=True)}")
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    # The reference implementation (RI) does not support VpTokens in CBOR format
    # at the moment. Hence, we cannot carry out the revocation check without
    # touching the rest of the implementation. We use a dummy JSON VpToken instead.
    # Ideally (future work), we would want to create the VpToken in this script rather
    # than read a CBOR object prepared in the RI of the Verifier backend
    #src/test/kotlin/eu/europa/ec/eudi/verifier/endpoint/adapter/input/web/MDocCBORTest.kt
    '''
    if config["vp_token_valid"]:
        with open(config["mdoc_status_list_valid_file"], "rb") as f:
            dumped_mdoc = f.read()
    else:
        with open(config["mdoc_status_list_revoked_file"], "rb") as f:
            dumped_mdoc = f.read()
    the_encoding = chardet.detect(dumped_mdoc)["encoding"]
    logger.info(f"Dumped mdoc: {dumped_mdoc}, encoding: {the_encoding}")

    urlencoded_mdoc = base64.urlsafe_b64encode(dumped_mdoc)
    logger.info(f"Urlencoded mdoc: {urlencoded_mdoc}")
    '''
    payload = {
        "state": transaction_id,
        #"vp_token": urlencoded_mdoc,
        "vp_token": json.dumps({"id": "123456"}),
        "presentation_submission": json.dumps(wallet_response),
    }

    # test_call_parameters('post', payload, headers)
    r = requests.post(
        f"{config['verifier_url']}/wallet/direct_post",
        data=payload,
        headers=headers,
        verify=config["ssl_verify"],
    )
    logger.info(f"Send wallet response returned (status={r.status_code}):")
    if r.status_code != 200:
        logger.info(r)
        exit(1)
    r_json = r.json()
    logger.info(f"{pprint.pprint(r_json, compact=True)}")
    redirect_uri = r_json["redirect_uri"]
    response_code = redirect_uri.split("response_code=")[-1]
    logger.info(f"response_code: {response_code}\n")

    return response_code


def get_wallet_response(presentation_id: str, response_code: str) -> None:
    r = requests.get(
        f"{config['verifier_url']}/ui/presentations/{presentation_id}?response_code={response_code}",
        verify=config["ssl_verify"],
    )
    logger.info(f"#5. Get wallet response returned (status={r.status_code}).")
    wallet_response = r.json()
    logger.info(f"{pprint.pprint(wallet_response)}")
    logger.info("\n")


def get_presentation_event_log(presentation_id: str) -> None:
    r = requests.get(
        f"{config['verifier_url']}/ui/presentations/{presentation_id}/events",
        verify=config["ssl_verify"],
    )
    logger.info(
        f"#6. Get presentation event log returned (status={r.status_code})."
    )
    presentation_events = r.json()
    logger.info(f"{pprint.pprint(presentation_events)}")


def get_new_revocation_data():
    headers = {"X-Api-Key": "305a4915-32b8-4ea4-ba5f-b1a867cd6728"}
    r = requests.post(
        f"https://issuer-openid4vc.ssi.tir.budru.de/status-list/api/lsp-hackathon/new-reference",
        headers=headers,
    )
    uri_index = r.json()
    logger.info(f"New status response: {uri_index}")

    headers = {"Content-type": "application/json", "Accept": "application/json"}
    payload = {
        "uri": uri_index["uri"],
        "index": uri_index["index"],
    }
    logger.info(f'POST uri={uri_index["uri"]}, index={uri_index["index"]}')


@app.route("/metadata", methods=["GET"])
def wallet_metadata() -> Response:
    metadata = {
        "authorization_endpoint": "eudi-openid4vp://",
        "client_id_schemes_supported": "x509_san_dns",
        "response_types_supported": ["vp_token"],
        "vp_formats_supported": {
            "mso_mdoc": {
                "alg_values_supported": ["ES256"]
            },
        },
    }
    return make_response(jsonify(metadata), 200)


if __name__ == "__main__":
    try:
        with open(".config.ip") as local_ip_file:
            default_wallet_ip = local_ip_file.read().strip()
    except FileNotFoundError:
        default_wallet_ip = "localhost"

    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "--wallet-metadata-endpoint",
        type=str,
        help="Wallet metadata endpoint to start",
        default=f"https://{default_wallet_ip}:7000/wallet_metadata",
    )
    parser.add_argument("--verifier-url",
        type=str,
        help="Verifier URL to connect to",
        default="http://83.212.99.99:8080",
    )
    parser.add_argument(
        "--auth-request-file",
        type=str,
        default="data/auth_request_mdoc_mdl.json",
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default="mock-wallet<->verifier",
    )
    parser.add_argument(
        "--wallet-response-file",
        type=str,
        default="data/wallet_response.json",
    )

    with open("wallet_verifier_config.json") as f:
        config = json.load(f)

    args = parser.parse_args()
    config["auth_request_file"] = args.auth_request_file
    config["client_id"] = args.client_id
    config["metadata_endpoint"] = args.wallet_metadata_endpoint
    config["verifier_url"] = args.verifier_url
    config["wallet_response_file"] = args.wallet_response_file

    logger.info(
        f"Verifier URL: {config['verifier_url']}\n"
        f"ssl_verify: {config['ssl_verify']}\n"
        f"vp_token_valid: {config['vp_token_valid']}\n"
        f"new_revocation_data: {config['want_new_revocation_data']}"
    )

    logger.info("Start wallet metadata endpoint in separate process.")
    start_wallet_metadata_endpoint()

    if config["want_new_revocation_data"]:
        get_new_revocation_data()
        exit(0)

    transaction_id, presentation_id = init_transaction()
    get_auth_request(transaction_id)
    get_presentation_def(transaction_id)
    response_code = send_wallet_response(transaction_id)
    get_wallet_response(presentation_id, response_code)
    get_presentation_event_log(presentation_id)
