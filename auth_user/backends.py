from django.core.mail.backends.console import EmailBackend
import sys

class CleanConsoleEmailBackend(EmailBackend):
    """
    A custom email backend that prints only the email body to the console.
    Useful for getting clean URLs during development without MIME headers.
    """
    def write_message(self, message):
        msg = message.message()
        payload = msg.get_payload()
        if isinstance(payload, list):
            # For multipart, usually the first part is text/plain
            body = payload[0].get_payload()
        else:
            body = payload
        
        stream = self.stream
        stream.write('-------------------------------------------------------------------------------\n')
        # Decode quoted-printable if necessary, but msg.get_payload() often returns decoded string if straightforward.
        # If headers say Quoted-Printable, it might still have = signs if raw. 
        # However, getting 'body' from `message.body` attribute is often safer in Django's EmailMessage.
        
        # Prefer message.body if available (Django EmailMessage object)
        if hasattr(message, 'body'):
            stream.write(message.body)
        else:
             stream.write(str(body))
             
        stream.write('\n-------------------------------------------------------------------------------\n')
        stream.flush()
