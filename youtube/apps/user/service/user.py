import uuid
from youtube.apps.user.repository import AuthSessionRepository, UserRepository
from youtube.apps.user.schemas import UserReadSchema, UserUpdateSchema
from youtube.repositories import StorageRepositoryProtocol


class UserService:
    def __init__(self, repository: UserRepository, storage_repository: StorageRepositoryProtocol) -> None:
        self.repository = repository
        self.storage_repository = storage_repository

    async def update_avatar(self, user_id: uuid.UUID, avatar_content: bytes, filename: str) -> str:
        user = await self.repository.get(user_id)
        if user.avatar:
            try:
                await self.storage_repository.delete(user.avatar)
            except Exception:
                pass
        unique_id = uuid.uuid4()
        avatar_path = f'avatars/{user_id}/{unique_id}.webp'

        await self.storage_repository.write(avatar_path, avatar_content)
        return avatar_path

    async def update_profile(
        self,
        user_id: uuid.UUID,
        username: str | None = None,
        email: str | None = None,
        avatar_content: bytes | None = None,
        avatar_filename: str | None = None,
        old_password: str | None = None,
        new_password: str | None = None,
    ) -> UserReadSchema:
        from youtube.services.cryptography.hasher import generate_hash, verify_hash
        import asyncio
        from youtube.apps.user.exceptions import InvalidCredentialsError, UserAlreadyExistsError

        if email:
            existing = await self.repository.get_by_login(email)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError(field='email')
        if username:
            existing = await self.repository.get_by_login(username)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError(field='username')

        update_data = {}
        if username is not None:
            update_data['username'] = username
        if email is not None:
            update_data['email'] = email

        if avatar_content is not None and avatar_filename is not None:
            avatar_path = await self.update_avatar(user_id, avatar_content, avatar_filename)
            update_data['avatar'] = avatar_path

        if new_password is not None:
            if not old_password:
                raise InvalidCredentialsError(custom_message='Old password is required to set a new password')

            hashed_password = await self.repository.get_hashed_password(user_id)
            try:
                await asyncio.to_thread(verify_hash, hash=hashed_password, data=old_password)
            except Exception:
                raise InvalidCredentialsError() from None

            new_hashed_password = generate_hash(new_password)
            update_data['hashed_password'] = new_hashed_password

        if update_data:
            update_data['id'] = user_id
            return await self.repository.update(UserUpdateSchema(**update_data))

        return await self.repository.get(user_id)
