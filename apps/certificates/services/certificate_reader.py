# -*- coding: utf-8 -*-
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import hashes

class CertificateReader:
    @staticmethod
    def read_p12_file(file_path, password):
        try:
            with open(file_path, 'rb') as f:
                p12_data = f.read()
            
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                p12_data, password.encode('utf-8')
            )
            
            if not certificate:
                raise ValueError('No certificate found')
            
            # Extract info
            subject = certificate.subject
            issuer = certificate.issuer
            
            return {
                'subject_name': ', '.join([f'{attr.oid._name.upper()}={attr.value}' for attr in subject]),
                'issuer_name': ', '.join([f'{attr.oid._name.upper()}={attr.value}' for attr in issuer]),
                'serial_number': str(certificate.serial_number),
                'valid_from': certificate.not_valid_before,
                'valid_to': certificate.not_valid_after,
                'fingerprint': certificate.fingerprint(hashes.SHA256()).hex()[:32]
            }
        except Exception as e:
            raise Exception(f'Error reading P12: {str(e)}')
