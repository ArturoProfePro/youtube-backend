from .auth import AuthService as AuthService
from .verification import EmailVerificationService as EmailVerificationService
from .user import UserService as UserService

all = [AuthService, EmailVerificationService, UserService]
