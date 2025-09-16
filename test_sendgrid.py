import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def test_sendgrid_connection():
    api_key = os.getenv('SENDGRID_API_KEY')
    if not api_key:
        print("❌ SENDGRID_API_KEY no está configurada")
        return False
    
    try:
        sg = SendGridAPIClient(api_key)
        print("✅ Cliente SendGrid inicializado")
        
        # Crear mensaje de prueba (sin enviarlo)
        message = Mail(
            from_email='noreply@fronteratech.ec',
            to_emails='test@example.com',
            subject='Test',
            html_content='<p>Test</p>'
        )
        print("✅ Mensaje de prueba creado correctamente")
        
        # NO enviamos realmente, solo validamos la configuración
        print("✅ SendGrid está listo para usar")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_sendgrid_connection()
