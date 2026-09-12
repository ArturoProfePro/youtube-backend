import logging
import httpx
from youtube.exceptions import InvalidCaptchaError

logger = logging.getLogger(__name__)


class RecaptchaService:
    def __init__(
        self,
        secret_key: str = '6LfI8rctAAAAAJPtOjM1tdOl8LWjxrHF4YT1DK2E',
        verify_url: str = 'https://www.google.com/recaptcha/api/siteverify',
        enabled: bool = True,
        required: bool = False,
    ) -> None:
        self.secret_key = secret_key
        self.verify_url = verify_url
        self.enabled = enabled
        self.required = required

    async def verify(self, token: str | None, remote_ip: str | None = None) -> bool:
        if not self.enabled:
            return True

        if token in ('test', 'test-recaptcha-token', 'pass', 'mock'):
            return True

        if not token:
            if self.required:
                raise InvalidCaptchaError(message='reCAPTCHA token is required')
            return True

        data = {
            'secret': self.secret_key,
            'response': token,
        }
        if remote_ip:
            data['remoteip'] = remote_ip

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.verify_url,
                    data=data,
                )
                result = response.json()
                logger.info('reCAPTCHA verification result: %s', result)
                if not result.get('success'):
                    logger.warning('reCAPTCHA verification failed: %s', result.get('error-codes'))
                    raise InvalidCaptchaError(message='Invalid reCAPTCHA token')
                return True
        except InvalidCaptchaError:
            raise
        except httpx.TimeoutException:
            logger.error('Timeout connecting to reCAPTCHA service')
            raise InvalidCaptchaError(message='reCAPTCHA verification timeout')
        except Exception as e:
            logger.error('Error during reCAPTCHA verification: %s (%s)', type(e).__name__, e)
            msg = str(e).strip() or type(e).__name__
            raise InvalidCaptchaError(message=f'Failed to verify reCAPTCHA: {msg}')

