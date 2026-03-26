import os
import django
import re
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend

# No setup here, will run via manage.py shell

from apps.certificates.models import DigitalCertificate

def main():
    with open('/app/cert_inspect_extensions.txt', 'w') as out:
        try:
            dc = DigitalCertificate.objects.get(id=3) 
            password = dc.get_password()
            p12_data = dc.certificate_file.read()
            
            pk, cert, extra = pkcs12.load_key_and_certificates(
                p12_data, password.encode(), default_backend()
            )
            
            out.write(f"Parsed Cert for {dc.company.business_name}\n")
            
            for ext in cert.extensions:
                out.write(f"Extension OID: {ext.oid.dotted_string}\n")
                try:
                    # Some extensions contain UTF8Strings or octet strings with the RUC
                    val = ext.value
                    out.write(f"  Value Type: {type(val)}\n")
                    out.write(f"  Value Representation: {repr(val)}\n")
                except:
                    out.write("  Could not read value\n")
            
            out.write("\nChecking Subject Attributes again:\n")
            for attr in cert.subject:
                out.write(f"OID: {attr.oid.dotted_string}, Value: {attr.value}\n")
                
        except Exception as e:
            out.write(f"ERROR: {str(e)}\n")

main()
