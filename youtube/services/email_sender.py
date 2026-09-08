import logging
from email.message import EmailMessage

import aiosmtplib

from youtube.settings import CoreEmailSettingsSchema


class EmailSender:
    def __init__(self, settings: CoreEmailSettingsSchema):
        self.host = settings.host
        self.port = settings.port
        self.user = settings.user
        self.password = settings.password
        self.sender = settings.sender

    async def send_verification_code(self, to_email: str, code: str, verify_link: str | None = None) -> None:
        """Отправляет письмо с кодом подтверждения."""
        msg = EmailMessage()
        msg['Subject'] = 'Подтверждение регистрации'
        msg['From'] = self.sender
        msg['To'] = to_email

        msg.set_content(
            f""" Your verification code: {code}\n
            {(f'Or go to the link: {verify_link}\n\n') if verify_link else ''}
            Code is valid for 15 minutes."""
        )

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                start_tls=True,  # Если порт 587 (или use_tls=True для 465)
                timeout=10,
            )
        except Exception as e:
            logging.error(f'Error sending email: {e}')
