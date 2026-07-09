import json
import os
import time
import requests
import base64
import hashlib
import hmac
import logging
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import padding
import OpenSSL
from plogical import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
import socket


class CustomACME:
    def __init__(self, domain, admin_email, staging=False, provider='letsencrypt'):
        """Initialize CustomACME"""
        logging.CyberCPLogFileWriter.writeToFile(
            f'Initializing CustomACME for domain: {domain}, email: {admin_email}, staging: {staging}, provider: {provider}')
        self.domain = domain
        self.admin_email = admin_email
        self.staging = staging
        self.provider = provider

        # Set the ACME directory URL based on provider and staging flag
        if provider == 'zerossl':
            if staging:
                self.acme_directory = "https://acme-staging.zerossl.com/v2/DV90"
                logging.CyberCPLogFileWriter.writeToFile('Using ZeroSSL staging ACME directory')
            else:
                self.acme_directory = "https://acme.zerossl.com/v2/DV90"
                logging.CyberCPLogFileWriter.writeToFile('Using ZeroSSL production ACME directory')
        else:  # letsencrypt
            if staging:
                self.acme_directory = "https://acme-staging-v02.api.letsencrypt.org/directory"
                logging.CyberCPLogFileWriter.writeToFile('Using Let\'s Encrypt staging ACME directory')
            else:
                self.acme_directory = "https://acme-v02.api.letsencrypt.org/directory"
                logging.CyberCPLogFileWriter.writeToFile('Using Let\'s Encrypt production ACME directory')

        self.account_key = None
        self.account_url = None
        self.directory = None
        self.nonce = None
        self.order_url = None
        self.authorizations = []
        self.finalize_url = None
        self.certificate_url = None

        # Initialize paths
        self.cert_path = f'/etc/letsencrypt/live/{domain}'
        self.challenge_path = '/usr/local/lsws/Example/html/.well-known/acme-challenge'
        self.account_key_path = f'/etc/letsencrypt/accounts/{domain}.key'
        logging.CyberCPLogFileWriter.writeToFile(
            f'Certificate path: {self.cert_path}, Challenge path: {self.challenge_path}')

        # Create accounts directory if it doesn't exist
        os.makedirs('/etc/letsencrypt/accounts', exist_ok=True)

    def _generate_account_key(self):
        """Generate RSA account key"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Generating RSA account key...')
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            self.account_key = key
            logging.CyberCPLogFileWriter.writeToFile('Successfully generated RSA account key')
            return True
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error generating account key: {str(e)}')
            return False

    def _get_directory(self):
        """Get ACME directory"""
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Fetching ACME directory from {self.acme_directory}')
            response = requests.get(self.acme_directory)
            self.directory = response.json()
            logging.CyberCPLogFileWriter.writeToFile(
                f'Successfully fetched ACME directory: {json.dumps(self.directory)}')
            return True
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error getting directory: {str(e)}')
            return False

    def _get_nonce(self):
        """Get new nonce from ACME server"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Getting new nonce...')
            response = requests.head(self.directory['newNonce'])

            # Check for nonce in headers (case-insensitive)
            nonce_header = None
            for header_name in ['Replay-Nonce', 'replay-nonce', 'REPLAY-NONCE']:
                if header_name in response.headers:
                    nonce_header = header_name
                    break

            if not nonce_header:
                # Log all available headers for debugging
                logging.CyberCPLogFileWriter.writeToFile(f'Available headers: {list(response.headers.keys())}')
                raise KeyError('Replay-Nonce header not found in response')

            self.nonce = response.headers[nonce_header]
            logging.CyberCPLogFileWriter.writeToFile(f'Successfully got nonce: {self.nonce}')
            return True
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error getting nonce: {str(e)}')
            return False

    def _create_jws(self, payload, url):
        """Create JWS (JSON Web Signature)"""
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Creating JWS for URL: {url}')
            if payload is not None:
                logging.CyberCPLogFileWriter.writeToFile(f'Payload: {json.dumps(payload)}')

            # Get a fresh nonce for this request
            if not self._get_nonce():
                logging.CyberCPLogFileWriter.writeToFile('Failed to get fresh nonce')
                return None

            # Get the private key numbers
            logging.CyberCPLogFileWriter.writeToFile('Getting private key numbers...')
            private_numbers = self.account_key.private_numbers()
            public_numbers = private_numbers.public_numbers

            # Convert numbers to bytes
            logging.CyberCPLogFileWriter.writeToFile('Converting RSA numbers to bytes...')
            n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
            e_bytes = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')

            # Create JWK
            logging.CyberCPLogFileWriter.writeToFile('Creating JWK...')
            jwk_key = {
                "kty": "RSA",
                "n": base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('='),
                "e": base64.urlsafe_b64encode(e_bytes).decode('utf-8').rstrip('='),
                "alg": "RS256"
            }
            logging.CyberCPLogFileWriter.writeToFile(f'Created JWK: {json.dumps(jwk_key)}')

            # Create protected header
            protected = {
                "alg": "RS256",
                "url": url,
                "nonce": self.nonce
            }

            # Add either JWK or Key ID based on whether we have an account URL
            if self.account_url and url != self.directory['newAccount']:
                protected["kid"] = self.account_url
                logging.CyberCPLogFileWriter.writeToFile(f'Using Key ID: {self.account_url}')
            else:
                protected["jwk"] = jwk_key
                logging.CyberCPLogFileWriter.writeToFile('Using JWK for new account')

            # Encode protected header
            logging.CyberCPLogFileWriter.writeToFile('Encoding protected header...')
            protected_b64 = base64.urlsafe_b64encode(
                json.dumps(protected).encode('utf-8')
            ).decode('utf-8').rstrip('=')

            # For POST-as-GET requests, payload_b64 should be empty string
            if payload is None:
                payload_b64 = ""
                logging.CyberCPLogFileWriter.writeToFile('Using empty payload for POST-as-GET request')
            else:
                # Encode payload
                logging.CyberCPLogFileWriter.writeToFile('Encoding payload...')
                payload_b64 = base64.urlsafe_b64encode(
                    json.dumps(payload).encode('utf-8')
                ).decode('utf-8').rstrip('=')

            # Create signature input
            logging.CyberCPLogFileWriter.writeToFile('Creating signature input...')
            signature_input = f"{protected_b64}.{payload_b64}".encode('utf-8')

            # Sign the input
            logging.CyberCPLogFileWriter.writeToFile('Signing input...')
            signature = self.account_key.sign(
                signature_input,
                padding.PKCS1v15(),
                hashes.SHA256()
            )

            # Encode signature
            logging.CyberCPLogFileWriter.writeToFile('Encoding signature...')
            signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

            # Create final JWS
            logging.CyberCPLogFileWriter.writeToFile('Creating final JWS...')
            jws = {
                "protected": protected_b64,
                "payload": payload_b64,  # Always include payload field, even if empty
                "signature": signature_b64
            }

            # Ensure the JWS is properly formatted
            jws_str = json.dumps(jws, separators=(',', ':'))
            logging.CyberCPLogFileWriter.writeToFile(f'Final JWS: {jws_str}')

            return jws_str
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error creating JWS: {str(e)}')
            return None

    def _load_account_key(self):
        """Load existing account key if available"""
        try:
            if os.path.exists(self.account_key_path):
                logging.CyberCPLogFileWriter.writeToFile('Loading existing account key...')
                with open(self.account_key_path, 'rb') as f:
                    key_data = f.read()
                self.account_key = serialization.load_pem_private_key(
                    key_data,
                    password=None,
                    backend=default_backend()
                )
                logging.CyberCPLogFileWriter.writeToFile('Successfully loaded existing account key')
                return True
            return False
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error loading account key: {str(e)}')
            return False

    def _save_account_key(self):
        """Save account key for future use"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Saving account key...')
            key_data = self.account_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.account_key_path, 'wb') as f:
                f.write(key_data)
            logging.CyberCPLogFileWriter.writeToFile('Successfully saved account key')
            return True
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error saving account key: {str(e)}')
            return False

    def _create_account(self):
        """Create new ACME account"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Creating new ACME account...')
            payload = {
                "termsOfServiceAgreed": True,
                "contact": [f"mailto:{self.admin_email}"]
            }

            # Check if External Account Binding is required (for ZeroSSL)
            if self.provider == 'zerossl' and 'meta' in self.directory and 'externalAccountRequired' in self.directory[
                'meta']:
                if self.directory['meta']['externalAccountRequired']:
                    logging.CyberCPLogFileWriter.writeToFile(
                        'ZeroSSL requires External Account Binding, getting EAB credentials...')

                    # Get EAB credentials from ZeroSSL
                    eab_kid, eab_hmac_key = self._get_zerossl_eab_credentials()
                    if not eab_kid or not eab_hmac_key:
                        logging.CyberCPLogFileWriter.writeToFile(
                            'Failed to get ZeroSSL EAB credentials, falling back to Let\'s Encrypt')
                        # Fallback to Let's Encrypt
                        self.provider = 'letsencrypt'
                        self.acme_directory = "https://acme-v02.api.letsencrypt.org/directory"
                        if not self._get_directory():
                            return False
                        if not self._get_nonce():
                            return False
                        return self._create_account()

                    # Add EAB to payload
                    payload['externalAccountBinding'] = self._create_eab(eab_kid, eab_hmac_key)

            jws = self._create_jws(payload, self.directory['newAccount'])
            if not jws:
                logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for account creation')
                return False

            logging.CyberCPLogFileWriter.writeToFile('Sending account creation request...')
            headers = {
                'Content-Type': 'application/jose+json'
            }
            response = requests.post(self.directory['newAccount'], data=jws, headers=headers)
            logging.CyberCPLogFileWriter.writeToFile(f'Account creation response status: {response.status_code}')
            logging.CyberCPLogFileWriter.writeToFile(f'Account creation response: {response.text}')

            if response.status_code == 201:
                self.account_url = response.headers['Location']
                logging.CyberCPLogFileWriter.writeToFile(
                    f'Successfully created account. Account URL: {self.account_url}')
                # Save the account key for future use
                self._save_account_key()
                return True
            elif response.status_code == 429:
                logging.CyberCPLogFileWriter.writeToFile(
                    'Rate limit hit for account creation. Using staging environment...')
                self.staging = True
                self.acme_directory = "https://acme-staging-v02.api.letsencrypt.org/directory"
                # Get new directory and nonce for staging
                if not self._get_directory():
                    return False
                if not self._get_nonce():
                    return False
                # Try one more time with staging
                return self._create_account()
            elif response.status_code == 400 and "badNonce" in response.text:
                logging.CyberCPLogFileWriter.writeToFile('Bad nonce, getting new nonce and retrying...')
                if not self._get_nonce():
                    return False
                return self._create_account()
            return False
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error creating account: {str(e)}')
            return False

    def _get_zerossl_eab_credentials(self):
        """Get External Account Binding credentials from ZeroSSL"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Getting ZeroSSL EAB credentials...')

            # Request EAB credentials from ZeroSSL API
            eab_url = 'https://api.zerossl.com/acme/eab-credentials-email'
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            data = {
                'email': self.admin_email
            }

            response = requests.post(eab_url, headers=headers, data=data)
            logging.CyberCPLogFileWriter.writeToFile(f'ZeroSSL EAB response status: {response.status_code}')
            logging.CyberCPLogFileWriter.writeToFile(f'ZeroSSL EAB response: {response.text}')

            if response.status_code == 200:
                eab_data = response.json()
                if 'eab_kid' in eab_data and 'eab_hmac_key' in eab_data:
                    return eab_data['eab_kid'], eab_data['eab_hmac_key']

            return None, None
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error getting ZeroSSL EAB credentials: {str(e)}')
            return None, None

    def _create_eab(self, eab_kid, eab_hmac_key):
        """Create External Account Binding for ZeroSSL"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Creating External Account Binding...')

            # Get the private key numbers
            private_numbers = self.account_key.private_numbers()
            public_numbers = private_numbers.public_numbers

            # Convert numbers to bytes
            n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
            e_bytes = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')

            # Create JWK
            jwk = {
                "kty": "RSA",
                "n": base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('='),
                "e": base64.urlsafe_b64encode(e_bytes).decode('utf-8').rstrip('=')
            }

            # Create protected header for EAB
            protected = {
                "alg": "HS256",
                "kid": eab_kid,
                "url": self.directory['newAccount']
            }

            # Encode protected header
            protected_b64 = base64.urlsafe_b64encode(
                json.dumps(protected).encode('utf-8')
            ).decode('utf-8').rstrip('=')

            # Encode JWK payload
            payload_b64 = base64.urlsafe_b64encode(
                json.dumps(jwk).encode('utf-8')
            ).decode('utf-8').rstrip('=')

            # Create signature using HMAC-SHA256
            signature_input = f"{protected_b64}.{payload_b64}".encode('utf-8')
            hmac_key = base64.urlsafe_b64decode(eab_hmac_key + '==')  # Add padding if needed
            signature = hmac.new(hmac_key, signature_input, hashlib.sha256).digest()
            signature_b64 = base64.urlsafe_b64encode(signature).decode('utf-8').rstrip('=')

            # Create EAB object
            eab = {
                "protected": protected_b64,
                "payload": payload_b64,
                "signature": signature_b64
            }

            logging.CyberCPLogFileWriter.writeToFile('Successfully created External Account Binding')
            return eab
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error creating External Account Binding: {str(e)}')
            return None

    def _create_order(self, domains):
        """Create new order for domains"""
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Creating new order for domains: {domains}')
            identifiers = [{"type": "dns", "value": domain} for domain in domains]
            payload = {
                "identifiers": identifiers
            }

            jws = self._create_jws(payload, self.directory['newOrder'])
            if not jws:
                logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for order creation')
                return False

            logging.CyberCPLogFileWriter.writeToFile('Sending order creation request...')
            headers = {
                'Content-Type': 'application/jose+json'
            }
            response = requests.post(self.directory['newOrder'], data=jws, headers=headers)
            logging.CyberCPLogFileWriter.writeToFile(f'Order creation response status: {response.status_code}')
            logging.CyberCPLogFileWriter.writeToFile(f'Order creation response: {response.text}')

            if response.status_code == 201:
                self.order_url = response.headers['Location']
                self.authorizations = response.json()['authorizations']
                self.finalize_url = response.json()['finalize']
                logging.CyberCPLogFileWriter.writeToFile(f'Successfully created order. Order URL: {self.order_url}')
                logging.CyberCPLogFileWriter.writeToFile(f'Authorizations: {self.authorizations}')
                logging.CyberCPLogFileWriter.writeToFile(f'Finalize URL: {self.finalize_url}')
                return True
            return False
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error creating order: {str(e)}')
            return False

    def _handle_http_challenge(self, challenge):
        """Handle HTTP-01 challenge"""
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Handling HTTP challenge: {json.dumps(challenge)}')

            # Get key authorization
            key_auth = self._get_key_authorization(challenge)
            if not key_auth:
                logging.CyberCPLogFileWriter.writeToFile('Failed to get key authorization')
                return False

            # Create challenge directory if it doesn't exist
            if not os.path.exists(self.challenge_path):
                logging.CyberCPLogFileWriter.writeToFile(f'Creating challenge directory: {self.challenge_path}')
                os.makedirs(self.challenge_path)

            # Write challenge file
            challenge_file = os.path.join(self.challenge_path, challenge['token'])
            logging.CyberCPLogFileWriter.writeToFile(f'Writing challenge file: {challenge_file}')

            # Write only the key authorization to the file
            with open(challenge_file, 'w') as f:
                f.write(key_auth)

            logging.CyberCPLogFileWriter.writeToFile('Successfully handled HTTP challenge')
            return True
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error handling HTTP challenge: {str(e)}')
            return False

    def _handle_dns_challenge(self, challenge):
        """Handle DNS-01 challenge (Cloudflare)"""
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Handling DNS challenge: {json.dumps(challenge)}')
            # This is a placeholder - implement Cloudflare API integration
            # You'll need to add your Cloudflare API credentials and implementation
            pass
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error handling DNS challenge: {str(e)}')
            return False

    def _get_key_authorization(self, challenge):
        """Get key authorization for challenge"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Getting key authorization...')

            # Get the private key numbers
            private_numbers = self.account_key.private_numbers()
            public_numbers = private_numbers.public_numbers

            # Convert numbers to bytes
            n_bytes = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, 'big')
            e_bytes = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, 'big')

            # Create JWK without alg field
            jwk_key = {
                "kty": "RSA",
                "n": base64.urlsafe_b64encode(n_bytes).decode('utf-8').rstrip('='),
                "e": base64.urlsafe_b64encode(e_bytes).decode('utf-8').rstrip('=')
            }

            # Calculate the JWK thumbprint according to RFC 7638
            # The thumbprint is a hash of the JWK (JSON Web Key) in a specific format
            # First, we create a dictionary with the required JWK parameters
            jwk = {
                "e": base64.urlsafe_b64encode(public_numbers.e.to_bytes(3, 'big')).decode('utf-8').rstrip('='),
                "kty": "RSA",  # Key type
                "n": base64.urlsafe_b64encode(public_numbers.n.to_bytes(256, 'big')).decode('utf-8').rstrip('=')
            }

            # Sort the JWK parameters alphabetically by key name
            # This ensures consistent thumbprint calculation regardless of parameter order
            sorted_jwk = json.dumps(jwk, sort_keys=True, separators=(',', ':'))

            # Calculate the SHA-256 hash of the sorted JWK
            # Example of what sorted_jwk might look like:
            # {"e":"AQAB","kty":"RSA","n":"tVKUtcx_n9rt5afY_2WFNVAu9fjD4xqX4Xm3dJz3XYb"}
            # The thumbprint will be a 32-byte SHA-256 hash of this string
            # For example, it might look like: b'x\x9c\x1d\x8f\x8b\x1b\x1e\x8b\x1b\x1e\x8b\x1b\x1e\x8b\x1b\x1e'
            thumbprint = hashlib.sha256(sorted_jwk.encode('utf-8')).digest()

            # Encode the thumbprint in base64url format (RFC 4648)
            # This removes padding characters (=) and replaces + and / with - and _
            # Example final thumbprint: "xJ0dj8sbHosbHosbHosbHos"
            thumbprint = base64.urlsafe_b64encode(thumbprint).decode('utf-8').rstrip('=')

            # Combine token and key authorization
            key_auth = f"{challenge['token']}.{thumbprint}"
            logging.CyberCPLogFileWriter.writeToFile(f'Key authorization: {key_auth}')
            return key_auth
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error getting key authorization: {str(e)}')
            return None

    def _verify_challenge(self, challenge_url):
        """Verify challenge completion with the ACME server

        This function sends a POST request to the ACME server to verify that the challenge
        has been completed successfully. The challenge URL is provided by the ACME server
        when the challenge is created.

        Example challenge_url:
        "https://acme-v02.api.letsencrypt.org/acme/challenge/example.com/123456"

        The verification process:
        1. Creates an empty payload (POST-as-GET request)
        2. Creates a JWS (JSON Web Signature) with the payload
        3. Sends the request to the ACME server
        4. Checks the response status

        Returns:
            bool: True if challenge is verified successfully, False otherwise
        """
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Verifying challenge at URL: {challenge_url}')

            # Create empty payload for POST-as-GET request
            # This is a special type of request where we want to GET a resource
            # but need to include a signature, so we use POST with an empty payload
            payload = {}

            # Create JWS (JSON Web Signature) for the request
            # Example JWS might look like:
            # {
            #   "protected": "eyJhbGciOiJSUzI1NiIsIm5vbmNlIjoiMTIzNDU2Nzg5MCIsInVybCI6Imh0dHBzOi8vYWNtZS12MDIuYXBpLmxldHNlbmNyeXB0Lm9yZy9hY21lL2NoYWxsZW5nZS9leGFtcGxlLmNvbS8xMjM0NTYifQ",
            #   "signature": "c2lnbmF0dXJlX2hlcmU",
            #   "payload": ""
            # }
            jws = self._create_jws(payload, challenge_url)
            if not jws:
                logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for challenge verification')
                return False

            logging.CyberCPLogFileWriter.writeToFile('Sending challenge verification request...')

            # Set headers for the request
            # Content-Type: application/jose+json indicates we're sending a JWS
            headers = {
                'Content-Type': 'application/jose+json'
            }

            # Send the verification request to the ACME server
            # Example response might look like:
            # {
            #   "type": "http-01",
            #   "status": "valid",
            #   "validated": "2024-03-20T12:00:00Z",
            #   "url": "https://acme-v02.api.letsencrypt.org/acme/challenge/example.com/123456"
            # }
            response = requests.post(challenge_url, data=jws, headers=headers)
            logging.CyberCPLogFileWriter.writeToFile(f'Challenge verification response status: {response.status_code}')
            logging.CyberCPLogFileWriter.writeToFile(f'Challenge verification response: {response.text}')

            # Check if the challenge was verified successfully
            # Status code 200 indicates success
            # The response will contain the challenge status and validation time
            if response.status_code == 200:
                logging.CyberCPLogFileWriter.writeToFile('Successfully verified challenge')
                return True
            return False
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error verifying challenge: {str(e)}')
            return False

    def _finalize_order(self, csr):
        """Finalize order and get certificate"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Finalizing order...')
            payload = {
                "csr": base64.urlsafe_b64encode(csr).decode('utf-8').rstrip('=')
            }

            jws = self._create_jws(payload, self.finalize_url)
            if not jws:
                logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for order finalization')
                return False

            logging.CyberCPLogFileWriter.writeToFile('Sending order finalization request...')
            headers = {
                'Content-Type': 'application/jose+json'
            }
            response = requests.post(self.finalize_url, data=jws, headers=headers)
            logging.CyberCPLogFileWriter.writeToFile(f'Order finalization response status: {response.status_code}')
            logging.CyberCPLogFileWriter.writeToFile(f'Order finalization response: {response.text}')

            if response.status_code == 200:
                # Wait for order to be processed
                max_attempts = 10
                delay = 2
                for attempt in range(max_attempts):
                    if not self._get_nonce():
                        logging.CyberCPLogFileWriter.writeToFile('Failed to get nonce for order status check')
                        return False

                    # Use POST-as-GET for order status check
                    jws = self._create_jws(None, self.order_url)
                    if not jws:
                        logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for order status check')
                        return False

                    response = requests.post(self.order_url, data=jws, headers=headers)
                    logging.CyberCPLogFileWriter.writeToFile(f'Order status check response: {response.text}')

                    if response.status_code == 200:
                        order_status = response.json().get('status')
                        if order_status == 'valid':
                            self.certificate_url = response.json().get('certificate')
                            logging.CyberCPLogFileWriter.writeToFile(
                                f'Successfully finalized order. Certificate URL: {self.certificate_url}')
                            return True
                        elif order_status == 'invalid':
                            logging.CyberCPLogFileWriter.writeToFile('Order validation failed')
                            return False
                        elif order_status == 'processing':
                            logging.CyberCPLogFileWriter.writeToFile(
                                f'Order still processing, attempt {attempt + 1}/{max_attempts}')
                            time.sleep(delay)
                            continue

                    logging.CyberCPLogFileWriter.writeToFile(
                        f'Order status check failed, attempt {attempt + 1}/{max_attempts}')
                    time.sleep(delay)

                logging.CyberCPLogFileWriter.writeToFile('Order processing timed out after 20 seconds')
                return False
            return False
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error finalizing order: {str(e)}')
            return False

    def _download_certificate(self):
        """Download certificate from ACME server"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Downloading certificate...')
            logging.CyberCPLogFileWriter.writeToFile(f'Certificate URL: {self.certificate_url}')

            # Get a fresh nonce for the request
            if not self._get_nonce():
                logging.CyberCPLogFileWriter.writeToFile('Failed to get nonce for certificate download')
                return None

            # Use POST-as-GET for certificate download (ACME v2 requirement)
            jws = self._create_jws(None, self.certificate_url)
            if not jws:
                logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for certificate download')
                return None

            headers = {
                'Content-Type': 'application/jose+json'
            }
            response = requests.post(self.certificate_url, data=jws, headers=headers)
            logging.CyberCPLogFileWriter.writeToFile(f'Certificate download response status: {response.status_code}')
            logging.CyberCPLogFileWriter.writeToFile(f'Certificate download response headers: {response.headers}')

            if response.status_code == 200:
                logging.CyberCPLogFileWriter.writeToFile('Successfully downloaded certificate')
                # The response should be the PEM-encoded certificate chain
                return response.text.encode('utf-8') if isinstance(response.text, str) else response.content
            else:
                logging.CyberCPLogFileWriter.writeToFile(f'Certificate download failed: {response.text}')
            return None
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error downloading certificate: {str(e)}')
            return None

    def _wait_for_challenge_validation(self, challenge_url, max_attempts=10, delay=2):
        """Wait for challenge to be validated by the ACME server"""
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Waiting for challenge validation at URL: {challenge_url}')
            for attempt in range(max_attempts):
                if not self._get_nonce():
                    logging.CyberCPLogFileWriter.writeToFile('Failed to get nonce for challenge status check')
                    return False

                # Use POST-as-GET for challenge status check
                jws = self._create_jws(None, challenge_url)
                if not jws:
                    logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for challenge status check')
                    return False

                headers = {
                    'Content-Type': 'application/jose+json'
                }
                response = requests.post(challenge_url, data=jws, headers=headers)
                logging.CyberCPLogFileWriter.writeToFile(f'Challenge status check response: {response.text}')

                if response.status_code == 200:
                    challenge_status = response.json().get('status')
                    if challenge_status == 'valid':
                        logging.CyberCPLogFileWriter.writeToFile('Challenge validated successfully')
                        return True
                    elif challenge_status == 'invalid':
                        # Check for DNS-related errors in the response
                        response_data = response.json()
                        error_detail = response_data.get('error', {}).get('detail', '')

                        # Common DNS-related error patterns
                        dns_errors = [
                            'NXDOMAIN',
                            'DNS problem',
                            'No valid IP addresses',
                            'could not be resolved',
                            'DNS resolution',
                            'Timeout during connect',
                            'Connection refused',
                            'no such host'
                        ]

                        is_dns_error = any(err.lower() in error_detail.lower() for err in dns_errors)
                        if is_dns_error:
                            logging.CyberCPLogFileWriter.writeToFile(
                                f'Challenge validation failed due to DNS issue: {error_detail}')
                        else:
                            logging.CyberCPLogFileWriter.writeToFile(
                                f'Challenge validation failed: {error_detail}')
                        return False

                logging.CyberCPLogFileWriter.writeToFile(
                    f'Challenge still pending, attempt {attempt + 1}/{max_attempts}')
                time.sleep(delay)

            logging.CyberCPLogFileWriter.writeToFile('Challenge validation timed out after 20 seconds')
            return False
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error waiting for challenge validation: {str(e)}')
            return False

    def _check_dns_record(self, domain):
        """Check if a domain has valid DNS records

        This function performs multiple DNS checks to ensure the domain has valid DNS records.
        It includes:
        1. A record (IPv4) check
        2. AAAA record (IPv6) check
        3. DNS caching prevention
        4. Multiple DNS server checks

        Args:
            domain (str): The domain to check

        Returns:
            bool: True if valid DNS records are found, False otherwise
        """
        try:
            logging.CyberCPLogFileWriter.writeToFile(f'Checking DNS records for domain: {domain}')

            # List of public DNS servers to check against (reduced to 2 for faster checks)
            dns_servers = [
                '8.8.8.8',  # Google DNS
                '1.1.1.1'   # Cloudflare DNS
            ]

            # Use system's DNS resolver as primary check (faster and respects local config)
            a_record_found = False
            aaaa_record_found = False

            try:
                # Try to resolve A record (IPv4) with timeout
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(3)  # 3 second timeout
                socket.gethostbyname(domain)
                a_record_found = True
                socket.setdefaulttimeout(old_timeout)
            except socket.gaierror:
                socket.setdefaulttimeout(old_timeout)
                pass
            except socket.timeout:
                socket.setdefaulttimeout(old_timeout)
                pass

            try:
                # Try to resolve AAAA record (IPv6) with timeout
                old_timeout = socket.getdefaulttimeout()
                socket.setdefaulttimeout(3)  # 3 second timeout
                socket.getaddrinfo(domain, None, socket.AF_INET6)
                aaaa_record_found = True
                socket.setdefaulttimeout(old_timeout)
            except socket.gaierror:
                socket.setdefaulttimeout(old_timeout)
                pass
            except socket.timeout:
                socket.setdefaulttimeout(old_timeout)
                pass

            # If system resolver fails, try public DNS servers as fallback
            if not a_record_found and not aaaa_record_found:
                # Function to check DNS record with specific DNS server
                def check_with_dns_server(server, record_type='A'):
                    try:
                        # Create a new socket for each check
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.settimeout(2)  # 2 second timeout

                        # Set the DNS server
                        sock.connect((server, 53))

                        # Create DNS query
                        query = bytearray()
                        # DNS header
                        query += b'\x00\x01'  # Transaction ID
                        query += b'\x01\x00'  # Flags: Standard query
                        query += b'\x00\x01'  # Questions: 1
                        query += b'\x00\x00'  # Answer RRs: 0
                        query += b'\x00\x00'  # Authority RRs: 0
                        query += b'\x00\x00'  # Additional RRs: 0

                        # Domain name
                        for part in domain.split('.'):
                            query.append(len(part))
                            query.extend(part.encode())
                        query += b'\x00'  # End of domain name

                        # Query type and class
                        if record_type == 'A':
                            query += b'\x00\x01'  # Type: A
                        else:  # AAAA
                            query += b'\x00\x1c'  # Type: AAAA
                        query += b'\x00\x01'  # Class: IN

                        # Send query
                        sock.send(query)

                        # Receive response
                        response = sock.recv(1024)

                        # Check if we got a valid response
                        if len(response) > 12:  # Minimum DNS response size
                            # Check if there are answers in the response
                            answer_count = int.from_bytes(response[6:8], 'big')
                            if answer_count > 0:
                                return True

                        return False
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f'Error checking DNS with server {server}: {str(e)}')
                        return False
                    finally:
                        try:
                            sock.close()
                        except:
                            pass

                # Check A records (IPv4) with first available DNS server only
                for server in dns_servers:
                    if check_with_dns_server(server, 'A'):
                        a_record_found = True
                        break

                # Only check AAAA if A record wasn't found and we still have time
                if not a_record_found:
                    for server in dns_servers:
                        if check_with_dns_server(server, 'AAAA'):
                            aaaa_record_found = True
                            break

            # Log the results
            if a_record_found:
                logging.CyberCPLogFileWriter.writeToFile(f'IPv4 DNS record found for domain: {domain}')
            if aaaa_record_found:
                logging.CyberCPLogFileWriter.writeToFile(f'IPv6 DNS record found for domain: {domain}')

            # Return True if either A or AAAA record is found
            return a_record_found or aaaa_record_found

        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error checking DNS records: {str(e)}')
            return False

    def _wait_for_order_processing(self, max_attempts=10, delay=2):
        """Wait for order to be processed"""
        try:
            logging.CyberCPLogFileWriter.writeToFile('Waiting for order processing...')
            for attempt in range(max_attempts):
                if not self._get_nonce():
                    logging.CyberCPLogFileWriter.writeToFile('Failed to get nonce for order status check')
                    return False

                # Use POST-as-GET for order status check
                jws = self._create_jws(None, self.order_url)
                if not jws:
                    logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for order status check')
                    return False

                headers = {
                    'Content-Type': 'application/jose+json'
                }
                response = requests.post(self.order_url, data=jws, headers=headers)
                logging.CyberCPLogFileWriter.writeToFile(f'Order status check response: {response.text}')

                if response.status_code == 200:
                    order_status = response.json().get('status')
                    if order_status == 'valid':
                        self.certificate_url = response.json().get('certificate')
                        logging.CyberCPLogFileWriter.writeToFile('Order validated successfully')
                        return True
                    elif order_status == 'invalid':
                        logging.CyberCPLogFileWriter.writeToFile('Order validation failed')
                        return False
                    elif order_status == 'processing':
                        logging.CyberCPLogFileWriter.writeToFile(
                            f'Order still processing, attempt {attempt + 1}/{max_attempts}')
                        time.sleep(delay)
                        continue

                logging.CyberCPLogFileWriter.writeToFile(
                    f'Order status check failed, attempt {attempt + 1}/{max_attempts}')
                time.sleep(delay)

            logging.CyberCPLogFileWriter.writeToFile('Order processing timed out after 20 seconds')
            return False
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error waiting for order processing: {str(e)}')
            return False

    def issue_certificate(self, domains, use_dns=False):
        """Main method to issue certificate"""
        try:
            logging.CyberCPLogFileWriter.writeToFile(
                f'Starting certificate issuance for domains: {domains}, use_dns: {use_dns}')

            # Try to load existing account key first
            if self._load_account_key():
                logging.CyberCPLogFileWriter.writeToFile('Using existing account key')
            else:
                logging.CyberCPLogFileWriter.writeToFile('No existing account key found, will create new one')

            # Filter domains to only include those with valid DNS records
            valid_domains = []
            for domain in domains:
                if self._check_dns_record(domain):
                    valid_domains.append(domain)
                else:
                    logging.CyberCPLogFileWriter.writeToFile(f'Skipping domain {domain} due to missing DNS records')

            if not valid_domains:
                logging.CyberCPLogFileWriter.writeToFile('No valid domains found with DNS records')
                return False

            # Initialize ACME
            logging.CyberCPLogFileWriter.writeToFile('Step 1: Generating account key')
            if not self._generate_account_key():
                logging.CyberCPLogFileWriter.writeToFile('Failed to generate account key')
                return False

            logging.CyberCPLogFileWriter.writeToFile('Step 2: Getting ACME directory')
            if not self._get_directory():
                logging.CyberCPLogFileWriter.writeToFile('Failed to get ACME directory')
                return False

            logging.CyberCPLogFileWriter.writeToFile('Step 3: Getting nonce')
            if not self._get_nonce():
                logging.CyberCPLogFileWriter.writeToFile('Failed to get nonce')
                return False

            logging.CyberCPLogFileWriter.writeToFile('Step 4: Creating account')
            if not self._create_account():
                logging.CyberCPLogFileWriter.writeToFile('Failed to create account')
                # If we failed to create account and we're not in staging, try staging
                if not self.staging:
                    logging.CyberCPLogFileWriter.writeToFile('Switching to staging environment...')
                    self.staging = True
                    self.acme_directory = "https://acme-staging-v02.api.letsencrypt.org/directory"
                    if not self._get_directory():
                        return False
                    if not self._get_nonce():
                        return False
                    if not self._create_account():
                        return False
                else:
                    return False

            # Create order with only valid domains
            logging.CyberCPLogFileWriter.writeToFile('Step 5: Creating order')
            if not self._create_order(valid_domains):
                logging.CyberCPLogFileWriter.writeToFile('Failed to create order')
                return False

            # Handle challenges
            logging.CyberCPLogFileWriter.writeToFile('Step 6: Handling challenges')
            for auth_url in self.authorizations:
                logging.CyberCPLogFileWriter.writeToFile(f'Processing authorization URL: {auth_url}')
                if not self._get_nonce():
                    logging.CyberCPLogFileWriter.writeToFile('Failed to get nonce for authorization')
                    return False

                # Get authorization details with POST-as-GET request
                # ACME protocol requires POST with empty payload for fetching resources
                logging.CyberCPLogFileWriter.writeToFile(f'Fetching authorization details for: {auth_url}')
                jws = self._create_jws(None, auth_url)  # None payload for POST-as-GET
                if not jws:
                    logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for authorization request')
                    return False

                headers = {
                    'Content-Type': 'application/jose+json'
                }
                response = requests.post(auth_url, data=jws, headers=headers)
                logging.CyberCPLogFileWriter.writeToFile(f'Authorization response status: {response.status_code}')
                logging.CyberCPLogFileWriter.writeToFile(f'Authorization response: {response.text}')

                if response.status_code != 200:
                    logging.CyberCPLogFileWriter.writeToFile('Failed to get authorization')
                    return False

                challenges = response.json()['challenges']
                for challenge in challenges:
                    logging.CyberCPLogFileWriter.writeToFile(f'Processing challenge: {json.dumps(challenge)}')

                    # Only handle the challenge type we're using
                    if use_dns and challenge['type'] == 'dns-01':
                        if not self._handle_dns_challenge(challenge):
                            logging.CyberCPLogFileWriter.writeToFile('Failed to handle DNS challenge')
                            return False
                        if not self._verify_challenge(challenge['url']):
                            logging.CyberCPLogFileWriter.writeToFile('Failed to verify DNS challenge')
                            return False
                        if not self._wait_for_challenge_validation(challenge['url']):
                            logging.CyberCPLogFileWriter.writeToFile('DNS challenge validation failed')
                            return False
                    elif not use_dns and challenge['type'] == 'http-01':
                        if not self._handle_http_challenge(challenge):
                            logging.CyberCPLogFileWriter.writeToFile('Failed to handle HTTP challenge')
                            return False
                        if not self._verify_challenge(challenge['url']):
                            logging.CyberCPLogFileWriter.writeToFile('Failed to verify HTTP challenge')
                            return False
                        if not self._wait_for_challenge_validation(challenge['url']):
                            logging.CyberCPLogFileWriter.writeToFile('HTTP challenge validation failed')
                            return False
                    else:
                        logging.CyberCPLogFileWriter.writeToFile(f'Skipping {challenge["type"]} challenge')

            # Generate CSR
            logging.CyberCPLogFileWriter.writeToFile('Step 7: Generating CSR')
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Get the domain from the order response
            # Use POST-as-GET to get order details
            jws = self._create_jws(None, self.order_url)
            if not jws:
                logging.CyberCPLogFileWriter.writeToFile('Failed to create JWS for order details')
                return False
            order_response = requests.post(self.order_url, data=jws, headers=headers).json()
            order_domains = [identifier['value'] for identifier in order_response['identifiers']]
            logging.CyberCPLogFileWriter.writeToFile(f'Order domains: {order_domains}')

            # Create CSR with exactly the domains from the order
            csr = x509.CertificateSigningRequestBuilder().subject_name(
                x509.Name([
                    x509.NameAttribute(x509.NameOID.COMMON_NAME, order_domains[0])
                ])
            ).add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(domain) for domain in order_domains
                ]),
                critical=False
            ).sign(key, hashes.SHA256(), default_backend())

            # Finalize order
            logging.CyberCPLogFileWriter.writeToFile('Step 8: Finalizing order')
            if not self._finalize_order(csr.public_bytes(serialization.Encoding.DER)):
                logging.CyberCPLogFileWriter.writeToFile('Failed to finalize order')
                return False

            # Wait for order processing
            logging.CyberCPLogFileWriter.writeToFile('Step 9: Waiting for order processing')
            if not self._wait_for_order_processing():
                logging.CyberCPLogFileWriter.writeToFile('Failed to process order')
                return False

            # Download certificate
            logging.CyberCPLogFileWriter.writeToFile('Step 10: Downloading certificate')
            certificate = self._download_certificate()
            if not certificate:
                logging.CyberCPLogFileWriter.writeToFile('Failed to download certificate')
                return False

            # Save certificate
            logging.CyberCPLogFileWriter.writeToFile('Step 11: Saving certificate')
            if not os.path.exists(self.cert_path):
                logging.CyberCPLogFileWriter.writeToFile(f'Creating certificate directory: {self.cert_path}')
                os.makedirs(self.cert_path)

            cert_file = os.path.join(self.cert_path, 'fullchain.pem')
            key_file = os.path.join(self.cert_path, 'privkey.pem')

            logging.CyberCPLogFileWriter.writeToFile(f'Saving certificate to: {cert_file}')
            with open(cert_file, 'wb') as f:
                f.write(certificate)

            logging.CyberCPLogFileWriter.writeToFile(f'Saving private key to: {key_file}')
            with open(key_file, 'wb') as f:
                f.write(key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            logging.CyberCPLogFileWriter.writeToFile('Successfully completed certificate issuance')
            return True
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Error issuing certificate: {str(e)}')
            return False 