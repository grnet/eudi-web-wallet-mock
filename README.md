# EUDI Mock Wallet

This is a simple web application that imitates the role of a EUDI wallet in its interactions with a credential issuer as per the OIDC4VC standard and with a verifier of the presentation of credentials as per the OIDC4VP standard.
Since the wallet's interactions with an issuer are independent of the wallet's interactions with a verifier in two separate workflows specified by the two different standards mentioned above, this segmentation is followed in the implementation of the mock wallet as well.
The script [wallet-issuer.py](https://github.com/mfragkoulis/eudi-web-wallet-mock/blob/main/wallet-issuer.py) first registers the mock wallet with the registration endpoint of the issuer assuming that the issuer also plays the role of a wallet provider. Then, the script implements the wallet's functionality as per the OIDC4VC standard. It also starts a simple Flask application in a separate process to expose an authorization endpoint required for the workflow.
Respectively, the script [wallet-verifier.py](https://github.com/mfragkoulis/eudi-web-wallet-mock/blob/main/wallet-verifier.py) implements the wallet's functionality as per the OIDC4VP standard.
The documentation that follows also discusses these two implementations and workflows separately.

## Common installation instructions

Install required packages in the system.

```bash
sudo apt-get install -y python3.11 curl
```

Setup poetry for dependency management, install dependencies and create certificate.

```bash
./install.sh
```

Note that the certificate is bound to the current IP (or the optional hostname argument to install.sh) and thus setup must run again if the IP or the hostname changes.

* [Mock Wallet - Issuer](#mock-wallet---issuer)
* [Mock Wallet - Verifier](#mock-wallet---verifier)

# Mock Wallet - Issuer

## Execution instructions

The execution instructions assume that there is an [issuer web application](https//github.com/gfour/eudi-srv-web-issuing-eudiw-py) running at the `issuer_url` configured in the `wallet_issuer_config.json` configuration file.

```python
python wallet_issuer.py
```

## Types of credentials supported

Supported credential configurations are defined in configuration file `wallet_issuer_config.json`:

```json
"credential_configurations": {
  "<configuration name>": {
    "credential_offer_file": "<credential offer>",
    "credential_data_file": "<credential data to use to fill in interactive UI form>"
  },
  ...
}
```

Currently, the following credential configurations are supported (and can be selected with the `--configuration` command-line parameter):

| Credential configuration | Description | Notes |
| ------------------------ | ----------- | ----- |
| `pid_mdoc`               | PID in mdoc format  | |
| `pid_sd_jwt`             | PID in SD-JWT-VC format | |
| `mdl_mdoc`               | mDL in mdoc format | The issuer does not support the loading of an image for an mDL, which is provided in the `portrait` field. Instead it only accepts the symbolic values "Port1" and "Port2", which correspond to sample image files stored internally in the issuer in base64 JPEG format. For an example of an image in base64 JPEG format see `data/credential_data_mdl_image.json`. |

## Wallet registration with issuer/wallet provider

In the context of this mock wallet, we take advantage of the fact that the issuer features a registration endpoint that listens to OpenID Connect Registration. Accordingly, to implement wallet registration in this mock context, we assume that the issuer also plays the role of a wallet provider and use its registration endpoint to register the wallet.

- _Method_: GET
- _URL_: https://0.0.0.0/registration
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k -G -X GET \
  -d redirect_uris=https://83.212.99.99:6000/auth \
  'https://83.212.99.99:5000/registration'
```

**Returns:**
```json
{
  "client_id": "ih16zFwfHKohboszRuYKsQ",
  "registration_access_token": "VjqJO-VX94RRY3iYl6jJzAhssaWuOpUmz_I89wVHV4o",
  "registration_client_uri": "https://83.212.99.99/registration_api?client_id=ih16zFwfHKohboszRuYKsQ",
  "client_id_issued_at": 1728550458,
  "client_secret": "d23551af11a57f2b2c156aea9bc8c4cbc5cd050af0899f0b5701157f",
  "client_secret_expires_at": 1731142458,
  "application_type": "web",
  "response_types": ["code"],
  "redirect_uris": ["https://83.212.99.99:6000/auth"]
}
```

## Workflow and endpoints

[OpenID4VC specification published in 1 October 2024](https://openid.github.io/OpenID4VCI/openid-4-verifiable-credential-issuance-wg-draft.html)
![OpenID4VC specification 1 October 2024](figures/openid4vc-spec-2024Oct1.png)

### 1b. Create and receive Credential Offer (Diagram Step 1b, Document Section 4)

In an issuer-initiated credential offer, the issuer shares a URI via a QR code that the wallet can scan and receive. To simplify the flow for the mock wallet at hand, it is assumed that the wallet has scanned the QR code and possesses it. In practice, the Wallet reads from file a credential offer URI that has been offered by the issuer. The URI has been transformed to a JSON file for readability and practicality. The credential offer regards a PID document in mdoc format. See [data/credential_offer.json]().

The credential offer URI looks like this:
```
https://dev.tester.issuer.eudiw.dev/credential_offer?credential_offer={%22credential_issuer%22:%20%22https://snf-895798.vm.okeanos.grnet.gr:5000%22,%20%22credential_configuration_ids%22:%20[%22eu.europa.ec.eudi.pid_mdoc%22],%20%22grants%22:%20{%22authorization_code%22:%20{}}}
```

### 2. Retrieve issuer metadata (Diagram Step 2, Document Section 10.2)

The wallet requires the following issuer metadata to carry out the OpenID4VC workflow.
- `pushed_authorization_request_endpoint` (.well-known/openid-configuration)
- `authorization_endpoint` (.well-known/openid-configuration)
- `token_endpoint` (.well-known/openid-configuration)
- `credential_endpoint` (.well-known/openid-configuration)
- `credential_configurations_supported` (.well-known/openid-credential-issuer)
  - `credential_configuration_ids` (provided in the credential offer)
    - `scope`
    - `format`
    - `doctype`

#### Credential metadata

- _Method_: GET
- _URL_: https://0.0.0.0/.well-known/openid-credential-issuer
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k -X GET 'https://snf-895798.vm.okeanos.grnet.gr:5000/.well-known/openid-credential-issuer'
```

**Returns:**
```json
{
  "batch_credential_endpoint": "https://snf-895798.vm.okeanos.grnet.gr:5000/batch_credential",
  "credential_configurations_supported": {
    "eu.europa.ec.eudi.pid_mdoc": {
      "claims": {
        "eu.europa.ec.eudi.pid.1": {
          "age_birth_year": {
            "mandatory": false
          },
          "age_over_18": {
            "display": [
              {
                "locale": "en",
                "name": "Adult or minor"
              }
            ],
            "mandatory": true
          },
          ...
        }
      }
      "credential_alg_values_supported": [
        -7
      ],
      "credential_crv_values_supported": [
        1
      ],
      "credential_signing_alg_values_supported": [
        "ES256"
      ],
      "cryptographic_binding_methods_supported": [
        "jwk",
        "cose_key"
      ],
      "doctype": "eu.europa.ec.eudi.pid.1",
      "format": "mso_mdoc",
      "proof_types_supported": {
        "cwt": {
          "proof_alg_values_supported": [
            -7
          ],
          "proof_crv_values_supported": [
            1
          ],
          "proof_signing_alg_values_supported": [
            "ES256"
          ]
        },
        "jwt": {
          "proof_signing_alg_values_supported": [
            "ES256"
          ]
        }
      },
      "scope": "eu.europa.ec.eudi.pid.1"
    }
  }
}
```

#### Credential issuer metadata

- _Method_: GET
- _URL_: https://0.0.0.0/.well-known/openid-configuration
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k -X GET 'https://snf-895798.vm.okeanos.grnet.gr:5000/.well-known/openid-configuration'
```

**Returns:**
```json
{
  "authorization_endpoint": "https://snf-895798.vm.okeanos.grnet.gr:5000/authorizationV3",
  "claims_parameter_supported": true,
  "code_challenge_methods_supported": [
    "S256"
  ],
  "credential_endpoint": "https://snf-895798.vm.okeanos.grnet.gr:5000/credential",
  "grant_types_supported": [
    "authorization_code",
    "implicit",
    "urn:ietf:params:oauth:grant-type:jwt-bearer",
    "refresh_token"
  ],
  "issuer": "https://snf-895798.vm.okeanos.grnet.gr:5000",
  "jwks_uri": "https://snf-895798.vm.okeanos.grnet.gr:5000/static/jwks.json",
  "pushed_authorization_request_endpoint": "https://snf-895798.vm.okeanos.grnet.gr:5000/pushed_authorizationv2",
  "registration_endpoint": "https://snf-895798.vm.okeanos.grnet.gr:5000/registration",
  "request_object_signing_alg_values_supported": [
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "HS256",
    "HS384",
    "HS512",
    "PS256",
    "PS384",
    "PS512"
  ],
  "response_types_supported": [
    "code"
  ],
  "scopes_supported": [
    "openid"
  ],
  "token_endpoint": "https://snf-895798.vm.okeanos.grnet.gr:5000/token",
  "userinfo_endpoint": "https://snf-895798.vm.okeanos.grnet.gr:5000/userinfo",
  "userinfo_signing_alg_values_supported": [
    "RS256",
    "RS384",
    "RS512",
    "ES256",
    "ES384",
    "ES512",
    "PS256",
    "PS384",
    "PS512",
    "HS256",
    "HS384",
    "HS512"
  ],
  "version": "3.0"
  ...
}
```

### 3. Perform pushed authorization request (Diagram Step 3, Document Section 5)

- _Method_: POST
- _URL_: https://0.0.0.0/pushed_authorizationv2
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k --cookie-jar cookies.txt \
     -X POST 'https://snf-895798.vm.okeanos.grnet.gr:5000/pushed_authorizationv2' \
     -H "Accept: application/json" \
     -H "Accept-Charset: UTF-8" \
     -H "Content-Type: application/x-www-form-urlencoded; charset=utf-8" \
     -H "Connection: Keep-Alive" \
     --data-urlencode "response_type=code" \
     --data-urlencode "code_challenge_method=S256" \
     --data-urlencode "code_challenge=4ZsRAi29Ozxi-mYotUZHqbOFlM9Z4VQ886C0FKhYd-c" \
     --data-urlencode "client_id=mock-wallet" \
     --data-urlencode "scope=eu.europa.ec.eudi.pid.1" \
     --data-urlencode "state=QusipItJDU1Fb3FCK3dZPZOi3N50QE0xtppB334S36U" \
     --data-urlencode "redirect_uri=https://snf-895798.vm.okeanos.grnet.gr:6000/auth"
```

**Returns:**
```json
{
  "expires_in": 3600,
  "request_uri": "urn:uuid:65207d6c-3fd4-470b-813c-8cc23f51af36"
}
```

### Perform authorization request

We use the returned `request_uri` to perform an authorization request.

- _Method_: GET
- _URL_: https://0.0.0.0/authorizationV3
- _Actor_: [Wallet]()

The -G option of curl ensures that the parameters are added to the URL instead of composing a body.

**Usage:**
```bash
curl -k -G --cookie cookies.txt -X GET \
  -d client_id=mock-wallet \
  -d state=QusipItJDU1Fb3FCK3dZPZOi3N50QE0xtppB334S36U \
  -d request_uri=urn:uuid:65207d6c-3fd4-470b-813c-8cc23f51af36 \
  'https://snf-895798.vm.okeanos.grnet.gr:5000/authorizationV3'
```

**Returns:**
```html
<!doctype html>
<html lang=en>
<title>Redirecting...</title>
<h1>Redirecting...</h1>
<p>You should be redirected automatically to the target URL: <a href="https://snf-895798.vm.okeanos.grnet.gr:5000/auth_choice">https://snf-895798.vm.okeanos.grnet.gr:5000/auth_choice</a>. If not, click the link.
```

At this point, the flow would open a UI page in the browser to select authentication method.

### Select authentication method

We choose to authenticate based on country by submitting a form with the suitable radio button selected: link2 corresponds to country selection.

- _Method_: GET
- _URL_: https://0.0.0.0/dynamic/auth_method
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k --cookie cookies.txt -X GET \
  -d optionsRadios=link2 \
  'https://snf-895798.vm.okeanos.grnet.gr:5000/dynamic/auth_method'
```

**Returns:** HTML page

At this point, the flow would open a UI page in the browser to request credentials for our EUDI wallet and select our country of origin.

### Select country of origin

We select a country of origin and pass the authorization details of the credential. The country FC corresponds to the FormEU country shown in the UI.

- _Method_: POST
- _URL_: https://0.0.0.0/dynamic/
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k --cookie cookies.txt -X POST \
  -d country=FC \
  -d proceed=Submit \
  --data-urlencode 'authorization_details={
  "type": "openid_credential"
  "credential_configuration_id": "eu.europa.ec.eudi.pid_mdoc"}' \
  'https://snf-895798.vm.okeanos.grnet.gr:5000/dynamic/'
```

**Returns:** HTML page

At this point, the flow would open a UI page in the browser to enter data for our EUDI wallet and select our basic information.

### Enter credential data

We enter the data required for the credential type we chose.

- _Method_: GET
- _URL_: https://0.0.0.0/dynamic/form
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k --cookie cookies.txt -X GET \
  -d given_name=John \
  -d family_name=Doe \
  -d birth_date=2024-10-03 \
  -d age_over_18=off \
  -d proceed=Submit \
  'https://snf-895798.vm.okeanos.grnet.gr:5000/dynamic/form'
```

**Returns:** HTML page

At this point, the flow would open a UI page in the browser to authorize data for our EUDI wallet and confirm the elements of information we entered.

### Authorize data from EUDI wallet

We authorize the data that we input in the previous step.

Note that we need to pass a user id when submitting the request.
This user id is generated by the issuer and passed internally to the source of the HTML page that is displayed to the device holding the wallet application.
So, we need to extract it from there.

The redirection leads to the wallet's auth endpoint, which in the case of this mock wallet returns a json structure composed of the parameters of the URL string it receives.

- _Method_: GET
- _URL_: https://0.0.0.0/dynamic/redirect_wallet
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k --cookie cookies.txt -X GET \
  -d user_id=FC.4858c36d-98d8-417a-bc17-3f529da8000e \
  'https://snf-895798.vm.okeanos.grnet.gr:5000/dynamic/redirect_wallet'
```

**Returns:**
```json
{
  "state": "QusipItJDU1Fb3FCK3dZPZOi3N50QE0xtppB334S36U",
  "iss": "https://snf-895798.vm.okeanos.grnet.gr",
  "client_id": "mock-wallet",
  "code": "Z0FBQUFBQm5BLWhsZzYzbW90Z0xrWUE4UHBtWHhLOUNQSU05d1FwN3RYRUp5X2dxV051Mjluc2Z5NnpzRTJHSmRidER0UWJUNWRreS1rcFJVaDg5elhmZTVwU0RtNXBhS1Fzcl95ZVlrdmFKVWpWZDZTV3AzVC1RVDIwem0xZGdVd3E0WmY3aWRqOFBkXzRGbXlzYjktRksxVjFWRF84OTA5Q1E5ZkZ6Q245b000d082cWZLMTRkamI4SmY4UFlHT1M4VEFTTm5oaWF5aUxMeEh1R201MVdfaFltZXlHaV9QNG80cFFJSkRXOTdtYzJZQ1lyS2VQaFlsZFNzb1JYV3lOMm1Edk1jSjN1RnRKSlhGTWxoVkNMX1lQNG1kRnBvei1sYThSUk82blRPUk5kMkE3NTRwOGhCdnRPWllXX0I4WjVGRmxQazVZTEJxSDliUTdXUUdMb0hXek1DZWotdUlwd2pJR0ZuZ0RrZTZJenVyRWM3NFVYM2VCOGRycVlhbUFCelRsU0NLTGJBaFFWS3YxRW5hQVB6RDJVbmQyUlFYVHA0Y2F1WmZLTWQ0WVpvZjY1SW1IaFVveEJaQ3lsajNySVpBQ0FhZWYza19nVnE0WWpsRW92Ym1XbGU5eENUVzRvTkwzQXRNVnkwZzhldk9EeGxiR3JRb3FMbGZBelFUNFdJSG9SbFJscXowbW11clBRaEY5akRCYjlKX2s3TjVyT1BReUNDZUFZVElYZmtKUXlLX1BZZWRXdlMxSG51djRlRkRVRW5wY1FWUzRVZ1hwYXN4d3huLTY0UkxHNTBCLVl0cTRoRlBVQ2RfVm1LcFU5RGVDX0xMd21fYlBmbHY3Q2VtNG1ZSFBSb01fYW5VOEZVeFJDRHFZcXZoYXJ2bEdyT0pXb1FEMXRiODdoMVRFa1NRRkZTcnNtWGhOTTVZNHlSX1pZM0ZtQ1h1VkhZZTBNNDJ6NGM5QV9PZkptck93PT0%3D"
}
```

### 5. Request token (Diagram Step 5, Document Section 6)

At this tep, we use the code returned by the previous request to receive an access token.

- _Method_: POST
- _URL_: https://0.0.0.0/token
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k --cookie cookies.txt -X POST \
  -d grant_type=authorization_code \
  -d client_id=mock-wallet \
  -d redirect_uri=https://snf-895798.vm.okeanos.grnet.gr:6000/auth \
  -d code_verifier=IPWeeA04h_i604EY_U3WUUabCi5cf3qrI4-iynOAwbY \
  -d code=Z0FBQUFBQm1fdXk3ZHVRNS16eFZZQ3FOdmRDTXdBVW1hNlR1dnVadGlJTjlkZ2xic3cwNEM2Wktub3FQSThKMktBdl9GdlFqRHZ2V3B1SVlKVk9kb2hBMjlDeFUwbGJoM0RjWUctV1JvdEFjWXdzUmVoNWVYUlN1M3dEWmRCZHZWMnB2cmJva2psUXh1bEQ0TGJuaG9JOGJCekRFYjczY1pLY18yMi1wYUtCUzFIUUkybWs2SGotTUFrTW9POC15YVNBQkU0NloxSjQtYnJiZUdSeE8wTzdUYnNWTUh1U1BJWTdRLUdwbVFhRnlFaW1hU1RjSjVOSGIzWkR1aXBUNlRrZ2s3UC11Ti1ZSTQtQmZlWUZmZUxhUUFtRUpGQ0I3RlNFN1FBLUY0S05qdG9iVzd3T01BdmlKZ1dyT3hiTmtlNTZ3TERtVmlDWGtYMG01cmNyME4tYlNYNXFGYVdySzdCTENmMFIyaWJZQVpoX1FZVVlMY3gyUzRLcTJEbXBHVjRnTl93LVd3bmRNSFdULXZtV044dGlmdkNxbHpOamV2YTkwaTJSaGJaY3dLSkctN0prWG15RzlCMHJ3T3o3Mk1sTzNKUlJpR0l3QnhfQ3BDQ044cVhQeVVTOEozTkg2eG9mYnpSUk53bHRxNE92NHlabGh1cGVlX2NtbW5uWGZ2eFBadzk1WkowbEZvemNDLWhsVlNVT2NQVVNCZ1V6SXhkYndzWVJieEluRGxlME1hT1BvU2liandRalJTeHdCZTRUencxQ2l6cDZCaXREZzc2NlFyanJtVG5MYnFsLV83d3lGU0Y4X3BMUkpaeHVCU194MHJOQTJrV0Z3WTNqT3BYSFNnb3BFQllMY2twV3lLN1g5WGdNeW9nVlhtcUR1V19wUTB0Sm1MTUtrTS1fSlR4RnBCb2ZCSVVKYV9QdlZOU2J6WWY4Rk5Zb19CX3ZJS21SbUNmV2Zoem9sRUJLUlRRPT0= \
  'https://snf-895798.vm.okeanos.grnet.gr:5000/token'
```

**Returns:**
```json
{
  "token_type": "Bearer",
  "scope": "eu.europa.ec.eudi.pid.1",
  "access_token": "eyJhbGciOiJFUzI1NiIsImtpZCI6Ik1tWkhTQzE0UlhwNVRUQjVkMHR1UTE5a1FYVnJTVlZLUldKelVWSTVlREJ6UWkxd1ZuQXdVMGgyYncifQ.eyJhdWQiOiBbIndhbGxldC1kZXYiXSwgImp0aSI6ICIwZGNmZmExYjdiNmI0MjFmYTllZTEzMWM2YjM3ZjBmMyIsICJjbGllbnRfaWQiOiAid2FsbGV0LWRldiIsICJzdWIiOiAiZmQ4YTAwYTFjZTZhZTliNzdmNmU0NWRmMzE0NzYxMTk4ODJhNDIxM2I1YTc0ZTJhYWUwNWQ2YjE1MmQ1NDY5OCIsICJzaWQiOiAiWjBGQlFVRkJRbTFmZFhrM2JuVjJMVWRvWjFaaGFHRllZMGRZYlZJMlNXVlplRVozZVRKRVRXNXFkV3RhU25aemNuQkVUblpMYjBoZmQzRlhSMU5pU3kweldWQlZMVmh6YUV3MmRXeGZlbWd3TW5wWmJWSm1aRTh0ZGtSMllVSXhZVlZXVldnNVVtUlpSbTlPVjNKbFIyVlpjemRYZUdGWlIyUmpjVzlrU0RrNGQyaGxOWGRmWjIxT2NHeEJkMTl5TVZOb01tcExWVkpaYkMxSk9GRmxaMGhmUjFveVVFNUNjRm8yT1VoT2VEVnhjVVUxVDI5V1gxSldTMUZFZUhGWmNFb3lSRmw0YWpkeU1VMWlWVmxETmxKUlgwWjNjM1J0YlVkZk9HdEpXalo1U1RSRk5qVmZiMjVMYWpKUVkzSnJOMjlqTTJ4WGRYSmtWakU1VjFkTmJuWldRbXRUV0RGTFNqTjJiV0YxWjBoMlpFNWFjV0l4Y1U5eFZUazFaemhITjJjOVBRPT0iLCAidG9rZW5fY2xhc3MiOiAiYWNjZXNzX3Rva2VuIiwgImlzcyI6ICJodHRwczovLzgzLjIxMi45OS45OSIsICJpYXQiOiAxNzI3OTgyNzgyLCAiZXhwIjogMTcyNzk4NjM4Mn0.pTaSzgfl-WHAPOfU5UqaNnuE94vHVnxjbxIWxIlTaRrcLuQZCiFhncXprTIThcAJI7J1_Ck5uvU2Jb_0r54BNA", 
  "expires_in": 3600,
  "refresh_token": "Z0FBQUFBQm1fdXktNGdWQm1EMzNvb0htQVdKWkZVZktIOG8zVEg1bTlOblJyMGc2MlNoNkFuN215Sk15WmJkWnFhVklWMTZLM1pmeVJtNXNlQ1pGTHREQ05ZWTRNWGFQX0tDTk5aTldod1lFdGZXSnNvRDR6aGtQOS1ydWZMRFF6SlJ6anhaSEdleDlQRXc0OFJUVWdpS1V4TE1tQm04Zjl5NXNBTVdDakFQMGEtQXhNcHRKX1RQZTFYRmMyU3dSYlcyOXNPQ21vUEgzVklNcmJxUEdicFpWWE9WTXBYWFJkQi1oWlREZHhVUHhzM2ZUVVdFRXpZTjVpRjBFNzBaQUxrUHQ3RE42a0NhbXl1aXJ6NU01emxfQWhGNE5fRGFtWjFkdFFTNEFCNFlPRFM0Mm1MUDdnSzJRRU5YUlVBS1hFd093LXdQaU5KOGVFa2hMRVlaUVdtdjFzdW1EZEtvYm5wS1B4VG9WeU1NLWNpMnZENXVYblpPR2dZS0lmS242d2hIZTM0ZkszUHRrck1RVzRmemRkWmM4UUp5WUtaby1kcmFLQXc5ZDkyUElKbklIVFpmd0xCVXJHU2VCOXNMcm15Y3A1LWVRX1Y5ZkI1OTRwVHdkY3NVOFEzcXJiMzFVa0Fpeks1ZW9SVUwwNE1wZUFwRkktMDlLZVBjeUFORERGcURabVBZM2lMRUpWYVd6U3l5RmZOblNHUzhKZTZKUGdRX19sNjBqY0hFcXpGMVEtREFJQWs2SDZkSXVnOHNqS2w0WWVsbjAzbnI4NFdWdHhlQ3NaTTgyTG91VFk3cnMwMWk1alR2U09QV21pRzJTWXlTUFMyVTRXMTJESTlvd0JtMWtfLXl1M2xQUFdZclB3TzRPbE1DT0pwRXR5Rk5HeEpCMEt5VUhBUGFQX0k5X2dQRGVhX0l6bkw2Sm1tSG9BMFJscnJOZWs3ajhaN2p4eDNRandkNnZ2OU5iY3hLNzV3PT0=",
  "id_token": "eyJhbGciOiJFUzI1NiIsImtpZCI6Ik1tWkhTQzE0UlhwNVRUQjVkMHR1UTE5a1FYVnJTVlZLUldKelVWSTVlREJ6UWkxd1ZuQXdVMGgyYncifQ.eyJzdWIiOiAiZmQ4YTAwYTFjZTZhZTliNzdmNmU0NWRmMzE0NzYxMTk4ODJhNDIxM2I1YTc0ZTJhYWUwNWQ2YjE1MmQ1NDY5OCIsICJzaWQiOiAiWjBGQlFVRkJRbTFmZFhrM2JuVjJMVWRvWjFaaGFHRllZMGRZYlZJMlNXVlplRVozZVRKRVRXNXFkV3RhU25aemNuQkVUblpMYjBoZmQzRlhSMU5pU3kweldWQlZMVmh6YUV3MmRXeGZlbWd3TW5wWmJWSm1aRTh0ZGtSMllVSXhZVlZXVldnNVVtUlpSbTlPVjNKbFIyVlpjemRYZUdGWlIyUmpjVzlrU0RrNGQyaGxOWGRmWjIxT2NHeEJkMTl5TVZOb01tcExWVkpaYkMxSk9GRmxaMGhmUjFveVVFNUNjRm8yT1VoT2VEVnhjVVUxVDI5V1gxSldTMUZFZUhGWmNFb3lSRmw0YWpkeU1VMWlWVmxETmxKUlgwWjNjM1J0YlVkZk9HdEpXalo1U1RSRk5qVmZiMjVMYWpKUVkzSnJOMjlqTTJ4WGRYSmtWakU1VjFkTmJuWldRbXRUV0RGTFNqTjJiV0YxWjBoMlpFNWFjV0l4Y1U5eFZUazFaemhITjJjOVBRPT0iLCAiYXV0aF90aW1lIjogMTcyNzk4Mjc3OSwgImFjciI6ICJ1cm46b2FzaXM6bmFtZXM6dGM6U0FNTDoyLjA6YWM6Y2xhc3NlczpJbnRlcm5ldFByb3RvY29sUGFzc3dvcmQiLCAianRpIjogIjgyYjMwNDBiODFiYjExZWZhMzBlNDUxYzIzYzg2ZTU0IiwgInNjb3BlIjogW10sICJpc3MiOiAiaHR0cHM6Ly84My4yMTIuOTkuOTkiLCAiaWF0IjogMTcyNzk4Mjc4MiwgImV4cCI6IDE3Mjc5ODMwODIsICJhdWQiOiBbIndhbGxldC1kZXYiXX0.X4hPsEf46UsZz8mwSgaHBFxfUvL9-tXSfwJBwLXJ5qy9mx9QyvKR7TLQf_TXRcdYbG7oo22jFtZGoiieMuUNPQ"
}
```

### 6. Request credential (Diagram Step 6, Document Section 7)

Finally, we request the credential using the access token returned by the token endpoint in the Authorization header.

- _Method_: POST
- _URL_: https://0.0.0.0/credential
- _Actor_: [Wallet]()

**Usage:**
```bash
curl -k --cookie cookies.txt -X POST \
  -H "Accept: application/json" \
  -H "Accept-Charset: UTF-8" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer yJhbGciOiJFUzI1NiIsImtpZCI6Ik1tWkhTQzE0UlhwNVRUQjVkMHR1UTE5a1FYVnJTVlZLUldKelVWSTVlREJ6UWkxd1ZuQXdVMGgyYncifQ.eyJhdWQiOiBbIndhbGxldC1kZXYiXSwgImp0aSI6ICIwZGNmZmExYjdiNmI0MjFmYTllZTEzMWM2YjM3ZjBmMyIsICJjbGllbnRfaWQiOiAid2FsbGV0LWRldiIsICJzdWIiOiAiZmQ4YTAwYTFjZTZhZTliNzdmNmU0NWRmMzE0NzYxMTk4ODJhNDIxM2I1YTc0ZTJhYWUwNWQ2YjE1MmQ1NDY5OCIsICJzaWQiOiAiWjBGQlFVRkJRbTFmZFhrM2JuVjJMVWRvWjFaaGFHRllZMGRZYlZJMlNXVlplRVozZVRKRVRXNXFkV3RhU25aemNuQkVUblpMYjBoZmQzRlhSMU5pU3kweldWQlZMVmh6YUV3MmRXeGZlbWd3TW5wWmJWSm1aRTh0ZGtSMllVSXhZVlZXVldnNVVtUlpSbTlPVjNKbFIyVlpjemRYZUdGWlIyUmpjVzlrU0RrNGQyaGxOWGRmWjIxT2NHeEJkMTl5TVZOb01tcExWVkpaYkMxSk9GRmxaMGhmUjFveVVFNUNjRm8yT1VoT2VEVnhjVVUxVDI5V1gxSldTMUZFZUhGWmNFb3lSRmw0YWpkeU1VMWlWVmxETmxKUlgwWjNjM1J0YlVkZk9HdEpXalo1U1RSRk5qVmZiMjVMYWpKUVkzSnJOMjlqTTJ4WGRYSmtWakU1VjFkTmJuWldRbXRUV0RGTFNqTjJiV0YxWjBoMlpFNWFjV0l4Y1U5eFZUazFaemhITjJjOVBRPT0iLCAidG9rZW5fY2xhc3MiOiAiYWNjZXNzX3Rva2VuIiwgImlzcyI6ICJodHRwczovLzgzLjIxMi45OS45OSIsICJpYXQiOiAxNzI3OTgyNzgyLCAiZXhwIjogMTcyNzk4NjM4Mn0.pTaSzgfl-WHAPOfU5UqaNnuE94vHVnxjbxIWxIlTaRrcLuQZCiFhncXprTIThcAJI7J1_Ck5uvU2Jb_0r54BNA" \
  -d '{
    "format": "mso_mdoc",
    "doctype": "eu.europa.ec.eudi.pid.1",
    "proof": {
      "proof_type": "jwt",
      "jwt": "eyJ0eXAiOiJvcGVuaWQ0dmNpLXByb29mK2p3dCIsImFsZyI6IkVTMjU2IiwiandrIjp7Imt0eSI6IkVDIiwiY3J2IjoiUC0yNTYiLCJ4IjoiNDk2aUlQOU5HWWFCQU1EdkpTazgzY1NVSkhsT1liMkJDMHhyOXRJcXJtVSIsInkiOiJ3YWtYNGNaQ2Ytemp0YTc4YVFuSmZhd1VOUzNoaHN6UEFWTVFGTEgtZGJNIn19.eyJpc3MiOiJ3YWxsZXQtZGV2IiwiYXVkIjoiaHR0cHM6Ly84My4yMTIuOTkuOTk6NTAwMCIsIm5vbmNlIjoiTTN0Rm5SUTljSnZadlUxU1FieDc0ZyIsImlhdCI6MTcyNzk4Mjc4NH0.l-iC7Xzgm2sWLlaDXx3GODh4gKhP7CjwLZkRfHJNWWSbaqA8gnz5D3DlVc8T7VdfGSEWfcY9qVPRkVo6wgRkOQ"
    }
  }' 'https://snf-895798.vm.okeanos.grnet.gr:5000/credential'
```

**Returns:**
```json
{
  "c_nonce": "TDRvnU1JPXQZ65DdwNJLYQ",
  "c_nonce_expires_in": 86400,
  "notification_id": "wwbikRg30JtQa9xPpDJY0Q",
  "credential": "omppc3N1ZXJBdXRohEOhASahGCFZAukwggLlMIICaqADAgECAhRoQu0mnaibjqEFrDO7g1RxBIyzBDAKBggqhkjOPQQDAjBcMR4wHAYDVQQDDBVQSUQgSXNzdWVyIENBIC0gVVQgMDExLTArBgNVBAoMJEVVREkgV2FsbGV0IFJlZmVyZW5jZSBJbXBsZW1lbnRhdGlvbjELMAkGA1UEBhMCVVQwHhcNMjQwNzAxMTAwMzA2WhcNMjUwOTI0MTAwMzA1WjBUMRYwFAYDVQQDDA1QSUQgRFMgLSAwMDAyMS0wKwYDVQQKDCRFVURJIFdhbGxldCBSZWZlcmVuY2UgSW1wbGVtZW50YXRpb24xCzAJBgNVBAYTAlVUMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE66T6UUJ8d2wrkB_g0zroSJ_boX3LL1wToHmFgFCaVQoS5OQ6gx64rPFJ36iBrfXBZbWUOvORiayYAE6H1XXyVKOCARAwggEMMB8GA1UdIwQYMBaAFLNsuJEXHNekGmYxh0Lhi8BAzJUbMBYGA1UdJQEB_wQMMAoGCCuBAgIAAAECMEMGA1UdHwQ8MDowOKA2oDSGMmh0dHBzOi8vcHJlcHJvZC5wa2kuZXVkaXcuZGV2L2NybC9waWRfQ0FfVVRfMDEuY3JsMB0GA1UdDgQWBBQEfQ5D1-0ZE9VvaFJOS-fzBhMSyjAOBgNVHQ8BAf8EBAMCB4AwXQYDVR0SBFYwVIZSaHR0cHM6Ly9naXRodWIuY29tL2V1LWRpZ2l0YWwtaWRlbnRpdHktd2FsbGV0L2FyY2hpdGVjdHVyZS1hbmQtcmVmZXJlbmNlLWZyYW1ld29yazAKBggqhkjOPQQDAgNpADBmAjEAkfm_P8cc8y1BtYvC4tH1-iB1spuGpMRpYvxZZxpbhoMZ10fyDDwXC-knmtzkP0p7AjEA2l-9N2LXnG-vqaO2rCgylMXMV8L_HHB-fW_WThZoljQc5_XuOihslQXdIyY-BTvbWQJZ2BhZAlSmZ2RvY1R5cGV3ZXUuZXVyb3BhLmVjLmV1ZGkucGlkLjFndmVyc2lvbmMxLjBsdmFsaWRpdHlJbmZvo2ZzaWduZWTAdDIwMjQtMTAtMDNUMTk6MTM6MDZaaXZhbGlkRnJvbcB0MjAyNC0xMC0wM1QxOToxMzowNlpqdmFsaWRVbnRpbMB0MjAyNS0wMS0wMVQwMDowMDowMFpsdmFsdWVEaWdlc3RzoXdldS5ldXJvcGEuZWMuZXVkaS5waWQuMagAWCAL2G1o2_uvarxduf17AWtoINBqAyB0J0cksCrwqWsb7wFYIC6Fo7NJODDAH1fMuVdzuvfmVmYNoXUszg3QbXlI029oAlggobvh_nXDea6V10znbO4i82eWNvL3yHeQW85OoC-UGp8DWCA7jEkWp_R9QLOI6DWTuraXODQh8_Yvf4wjshl_4yk_iARYINunF85UM-JmU2ljdVnWmB_7CXNJW-_tjk8EMOw6X277BVggG8Y-C2e5QQXGDgSRoSDWnjWBI4p3STgAc7LabbTABGMGWCAw16-IEc5YVebHrHhoIu7nm5GkqpVSB3tQw_4fzkgtGwdYINAfuLyTNdoP9qLnTFlwpd4Etb6fr5eIqyz87RAKHyqCbWRldmljZUtleUluZm-haWRldmljZUtleaQBAiABIVgg496iIP9NGYaBAMDvJSk83cSUJHlOYb2BC0xr9tIqrmUiWCDBqRfhxkJ_7OO1rvxpCcl9rBQ1LeGGzM8BUxAUsf51s29kaWdlc3RBbGdvcml0aG1nU0hBLTI1NlhAdqGsy4V0LzNc6drVRcXZv_x_ar39REJVdBGnh6fKPV0g5CYi1QDPk-4DZG0NrwUjqXrwr-VCCn2GzjysjtvAsGpuYW1lU3BhY2VzoXdldS5ldXJvcGEuZWMuZXVkaS5waWQuMYjYGFhmpGZyYW5kb21YIFYo7uH3oNbEBClZXdL8-nor4ETHMbnQ3MSoESU4j-oqaGRpZ2VzdElEAGxlbGVtZW50VmFsdWViRkNxZWxlbWVudElkZW50aWZpZXJvaXNzdWluZ19jb3VudHJ52BhYb6RmcmFuZG9tWCAvyHCqo-lvjwjmQxf6uQi5qG7shesLDtZgfJr3fBuVS2hkaWdlc3RJRAFsZWxlbWVudFZhbHVl2QPsajIwMjQtMTAtMDNxZWxlbWVudElkZW50aWZpZXJtaXNzdWFuY2VfZGF0ZdgYWGykZnJhbmRvbVgg1UyFZqKVJ0NLLexPtsaeQ-Rg51LiBJJHQykm9H13dN9oZGlnZXN0SUQCbGVsZW1lbnRWYWx1ZdkD7GoyMDI0LTEwLTAzcWVsZW1lbnRJZGVudGlmaWVyamJpcnRoX2RhdGXYGFhtpGZyYW5kb21YIGjL982ucROF9NZ2_dZ-GiqZajcBeV_DuDO0gQ_25mdiaGRpZ2VzdElEA2xlbGVtZW50VmFsdWXZA-xqMjAyNS0wMS0wMXFlbGVtZW50SWRlbnRpZmllcmtleHBpcnlfZGF0ZdgYWHWkZnJhbmRvbVggpYkSRrpFx2H4TqHJTKgvufh0lKF5kWcRPcy-9dMhk2FoZGlnZXN0SUQEbGVsZW1lbnRWYWx1ZW9UZXN0IFBJRCBpc3N1ZXJxZWxlbWVudElkZW50aWZpZXJxaXNzdWluZ19hdXRob3JpdHnYGFhgpGZyYW5kb21YIECW5jxe1W-2Bm_-Tf46tW68DUT2N6xaX2iWg7ssGSsxaGRpZ2VzdElEBWxlbGVtZW50VmFsdWVhTXFlbGVtZW50SWRlbnRpZmllcmpnaXZlbl9uYW1l2BhYYaRmcmFuZG9tWCAIFQ2kwTyUAglEeb2fJ88WrM3o0FsHhdXqru9ZExbK8mhkaWdlc3RJRAZsZWxlbWVudFZhbHVlYUZxZWxlbWVudElkZW50aWZpZXJrZmFtaWx5X25hbWXYGFhgpGZyYW5kb21YICDGSsQCiiE3dyeCqnki9LTsrXol1x5h2dSn5WTz8UAZaGRpZ2VzdElEB2xlbGVtZW50VmFsdWX0cWVsZW1lbnRJZGVudGlmaWVya2FnZV9vdmVyXzE4" 
}
```

# Mock Wallet - Verifier

## Execution instructions

The execution instructions assume that there is a [Verifier backend](https://github.com/grnet/eudi-srv-web-verifier-endpoint-23220-4-kt) running at the `verifier_url` configured in the `wallet_verifier_config.json` configuration file.

The following command runs the happy day presentation flow scenario for a valid vp token.

```python
python wallet_verifier.py
```

Instead if set the `vp_token_valid` configuration flag to False in the `wallet_verifier_config.json` configuration file, the execution runs the presentation flow scenario for a revoked vp token.

```json
{
  "vp_token_valid": false
}
```

Both scenarios use a hardcoded vpToken stored in files in this directory as binary hex strings in CBOR format.

If we want to contact the revocation service and get new (URI, index) pairs, we set the `want_new_revocation_data` to True in the `wallet_verifier_config.json` configuration file as follows.

```json
{
  "want_new_revocation_data": true
}
```

## Workflow and endpoints

[OpenID4VP specification published in 9 August 2024 (Draft 21)](https://openid.net/specs/openid-4-verifiable-presentations-1_0.html)
![OpenID4VP specification 9 August 2024](figures/openid4vp-spec-2024Aug9.png)



### Presentation Flows

#### Same device

```mermaid
sequenceDiagram    
    participant UA as User Agent
    participant W as Wallet
    participant V as Verifier
    participant VE as Verifier Endpoint
    UA->>V: Trigger presentation 
    
    V->>+VE: Initiate transaction
    VE-->>-V: Authorization request as request_url
    
    V->>UA: Render request as deep link
    UA->>W: Trigger wallet and pass request
    
    W->>+VE: Get authorization request via request_uri 
    VE-->>-W: authorization_request
    
    W->>W: Parse authorization request
    
    W->>+VE: Get presentation definition 
    VE-->>-W: presentation_definition
    
    W->>W: Prepare response     
    
    W->>+VE: Post vp_token response 
    VE->>VE: Validate response and prepare response_code
    VE-->>-W: Return redirect_uri with response_code
    
    W->>UA: Refresh user agent to follow redirect_uri
    UA->>V: Follow redirect_uri passing response_code
    
    V->>+VE: Get wallet response passing response_code 
    VE->>VE: Validate response_code matches wallet response
    VE-->>-V: Return wallet response
    
    V->>UA: Render wallet response 
```

### Cross device

```mermaid
sequenceDiagram    
    participant UA as User Agent
    participant W as Wallet
    participant V as Verifier
    participant VE as Verifier Endpoint
    UA->>V: Trigger presentation 
    
    V->>+VE:  Initiate transaction
    VE-->>-V: Authorization request as request_url
    
    V->>UA: Render request as QR Code

    loop
    V->>+VE: Get wallet response
    VE-->>-V: Return wallet response
    Note over V,VE: Verifier starts polling Verifier Endpoint for Wallet Response
    end

    UA->>W: Scan QR Code, trigger wallet, and pass request
    
    W->>+VE: Get authorization request via request_uri 
    VE-->>-W: authorization_request
    
    W->>W: Parse authorization request
    
    W->>+VE: Get presentation definition 
    VE-->>-W: presentation_definition
    
    W->>W: Prepare response     
    
    W->>+VE: Post vp_token response 
    VE->>VE: Validate response

    loop
    V->>+VE: Get wallet response
    VE-->>-V: Return wallet response
    end
    
    V->>UA: Render wallet response
```

## Wallet - Verifier Endpoints

### Initialize transaction endpoint

- _Method_: POST
- _URL_: http://localhost:8080/ui/presentations
- _Actor_: [Verifier](src/main/kotlin/eu/europa/ec/eudi/verifier/endpoint/adapter/input/web/VerifierApi.kt)

An endpoint to control the content of the authorization request that will be prepared from the verifier backend service. Payload of this request is a json object with the following acceptable attributes:
- `type`: The type of the response to the authorization request. Allowed values are one of: `id_token`, `vp_token` or `vp_token id_token`.
- `id_token_type`: In case type is `id_token` controls the type of id_token that will be requested from wallet. Allowed values are one of `subject_signed_id_token` or `attester_signed_id_token`. 
- `presentation_definition`: A json object that depicting the presentation definition to be included in the OpenId4VP authorization request in case `type` is 'vp_token'. 
- `nonce`: Nonce value to be included in the OpenId4VP authorization request.
- `response_mode`: Controls the `response_mode` attribute of the OpenId4VP authorization request. Allowed values are one of `direct_post` or `direct_post.jwt`.  
- `jar_mode`: Controls the way the generated authorization request will be passed. If 'by_value' the request will be passed inline to the wallet upon request, if `by_reference` a `request_uri` url will be returned.  
- `presentation_definition_mode`: Controls how the presentation definition will be embedded in the request. If 'by_value' it will be embedded inline, if `by_reference` a `presentation_definition_uri` url will be embedded in the request.
- `wallet_response_redirect_uri_template`: If provided will be used to construct the response to wallet, when it posts its response to the authorization request.   

**Usage:**
```bash
curl -X POST -H "Content-type: application/json" -d '{
  "type": "vp_token",  
  "presentation_definition": {
        "id": "32f54163-7166-48f1-93d8-ff217bdb0653",
        "input_descriptors": [
            {
                "constraints": {
                    "fields": [
                        {
                            "intent_to_retain": false,
                            "path": [
                                "$['eu.europa.ec.eudiw.pid.1']['family_name']"
                            ]
                        }
                    ]
                },
                "id": "eu.europa.ec.eudiw.pid.1",
                "format": {
                  "mso_mdoc": {
                    "alg": [
                      "ES256",
                      "ES384",
                      "ES512",
                      "EdDSA"
                    ]
                  }
                }
                "name": "EUDI PID",
                "purpose": "We need to verify your identity"
            }
        ]
    },
  "nonce": "nonce"
}' 'http://localhost:8080/ui/presentations'
```

**Returns:**
```json
{
  "presentation_id": "STMMbidoCQTtyk9id5IcoL8CqdC8rxgks5FF8cqqUrHvw0IL3AaIHGnwxvrvcEyUJ6uUPNdoBQDa7yCqpjtKaw",
  "client_id": "dev.verifier-backend.eudiw.dev",
  "request_uri": "https://localhost:8080/wallet/request.jwt/5N6E7VZsmwXOGLz1Xlfi96MoyZVC3FZxwdAuJ26DnGcan-vYs-VAKErioQ58BWEsKlVw2_X49jpZHyp0Mk9nKw"
}
```

You can also try it out in [Swagger UI](http://localhost:8080/swagger-ui#/verifier%20api/initializeTransaction).

### Get authorization request

- _Method_: GET
- _URL_: http://localhost:8080/wallet/request.jwt/{requestId}
- _Parameters_
  - `requestId`: The identifier of the authorization request
- _Actor_: [Wallet](src/main/kotlin/eu/europa/ec/eudi/verifier/endpoint/adapter/input/web/WalletApi.kt)

An endpoint to be used by wallet when the OpenId4VP authorization request is passed to wallet by reference as a request_uri.
In essence this is the endpoint that responds to the url included as the `request_uri` attribute of the [Initialize transaction endpoint](#initialize-transaction-endpoint)'s response.

**Usage:**
```bash
curl https://localhost:8080/wallet/request.jwt/5N6E7VZsmwXOGLz1Xlfi96MoyZVC3FZxwdAuJ26DnGcan-vYs-VAKErioQ58BWEsKlVw2_X49jpZHyp0Mk9nKw
```
**Returns:** The authorization request payload as a signed JWT.

### Get presentation definition

- _Method_: GET
- _URL_: http://localhost:8080/wallet/pd/{requestId}
- _Parameters_
    - `requestId`: The identifier of the authorization request
- _Actor_: [Wallet](src/main/kotlin/eu/europa/ec/eudi/verifier/endpoint/adapter/input/web/WalletApi.kt)

An endpoint to be used by wallet when the presentation definition of the OpenId4VP authorization request is not embedded inline in the request but by reference as a `presentation_definition_uri`.

**Usage:**
```bash
curl https://localhost:8080/wallet/pd/5N6E7VZsmwXOGLz1Xlfi96MoyZVC3FZxwdAuJ26DnGcan-vYs-VAKErioQ58BWEsKlVw2_X49jpZHyp0Mk9nKw
```

**Returns:** The presentation definition of the authorization request as JSON.

### Send wallet response

- _Method_: POST
- _URL_: http://localhost:8080/wallet/direct_post
- _Actor_: [Wallet](src/main/kotlin/eu/europa/ec/eudi/verifier/endpoint/adapter/input/web/WalletApi.kt)

An endpoint available to wallet to post its response. Based on the `response_mode` of the OpenId4VP authorization request this endpoint can 
accept 2 type of payloads:

_**response_mode = direct_post**_

A form post (application/x-www-form-urlencoded encoding) with the following form parameters:
- `state`: The state claim included in the authorization request JWT. Its value matches the authorization request identifier.  
- `id_token`: The requested id_token if authorization request 'response_type' attribute contains `id_token`.
- `vp_token`: The requested vp_token if authorization request 'response_type' attribute contains `vp_token`.
- `presentation_submission`: The presentation submission accompanying the vp_token in case 'response_type' attribute of authorization request contains `vp_token`.

_**response_mode = direct_post.jwt**_

A form post (application/x-www-form-urlencoded encoding) with the following form parameters:
- `state`: The state claim included in the authorization request JWT. Its value matches the authorization request identifier.
- `response`: A string representing an encrypted JWT (JWE) that contains as claims the form parameters mentioned in the case above    

**Usage:**
```bash
STATE=5N6E7VZsmwXOGLz1Xlfi96MoyZVC3FZxwdAuJ26DnGcan-vYs-VAKErioQ58BWEsKlVw2_X49jpZHyp0Mk9nKw
curl -v -X POST 'http://localhost:8080/wallet/direct_post' \
  -H "Content-type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  --data-urlencode "state=$STATE" \
  --data-urlencode 'vp_token={"id": "123456"}' \
  --data-urlencode presentation_submission@- << EOF
{
  "id": "a30e3b91-fb77-4d22-95fa-871689c322e2",
  "definition_id": "32f54163-7166-48f1-93d8-ff217bdb0653",
  "descriptor_map": [
    {
      "id": "employment_input",
      "format": "jwt_vc",
      "path": "$.verifiableCredential[0]"
    }
  ]
}
EOF
```
**Returns:**

* Same device case
```HTTP
HTTP/1.1 200 OK
{
  "redirect_uri" : "https://dev.verifier.eudiw.dev/get-wallet-code?response_code=5272d373-ebab-40ec-b44d-0a9909d0da69"
}
```
* Cross device case
```HTTP
HTTP/1.1 200 OK
```

For this call to return a `redirect_uri`, it entails a `wallet_response_redirect_uri_template` to be provided in the initial call to [Initialize transaction endpoint](#initialize-transaction-endpoint). The format of this template is quite specific in form and can be sneakpeaked in [openapi.json](src/main/resources/public/openapi.json:944) and in [CreateQueryWalletResponseRedirectUri.kt](src/main/kotlin/eu/europa/ec/eudi/verifier/endpoint/port/out/cfg/CreateQueryWalletResponseRedirectUri.kt:32).

### Get wallet response

- Method: GET
- URL: http://localhost:8080/ui/presentations/{presentationId}?response_code={responseCode}
- Parameters
  - `presentationId`: The `presentation_id` identifier returned by the [transaction initialization](#initialize-transaction-endpoint) call.
  - `responseCode`: (OPTIONAL) Response code generated in case of 'same device' case 
- _Actor_: [Verifier](src/main/kotlin/eu/europa/ec/eudi/verifier/endpoint/adapter/input/web/VerifierApi.kt)

```bash
curl http://localhost:8080/ui/presentations/STMMbidoCQTtyk9id5IcoL8CqdC8rxgks5FF8cqqUrHvw0IL3AaIHGnwxvrvcEyUJ6uUPNdoBQDa7yCqpjtKaw?response_code=5272d373-ebab-40ec-b44d-0a9909d0da69
```

**Returns:** The wallet submitted response as JSON.

You can also try it out in [Swagger UI](http://localhost:8080/swagger-ui#/verifier%20api/getWalletResponse).

### Get presentation event log

- Method: GET
- URL: http://localhost:8080/ui/presentations/{presentationId}/events
- Parameters
  - `presentationId`: The `presentation_id` identifier returned by the [transaction initialization](#initialize-transaction-endpoint) call.
- _Actor_: [Verifier](src/main/kotlin/eu/europa/ec/eudi/verifier/endpoint/adapter/input/web/VerifierApi.kt)

```bash
curl http://localhost:8080/ui/presentations/STMMbidoCQTtyk9id5IcoL8CqdC8rxgks5FF8cqqUrHvw0IL3AaIHGnwxvrvcEyUJ6uUPNdoBQDa7yCqpjtKaw/events
```

**Returns:** The log of notable events for the specific presentation.

You can also try it out in [Swagger UI](http://localhost:8080/swagger-ui#/verifier%20api/getPresentationEvents).
