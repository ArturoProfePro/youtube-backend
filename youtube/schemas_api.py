from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, EmailStr


class IUser(BaseModel):
    id: str
    username: Optional[str] = None
    email: EmailStr


class IAuthData(BaseModel):
    email: EmailStr
    password: str


class IAuthResponse(BaseModel):
    user: IUser
    accessToken: str


class ISettings(BaseModel):
    email: EmailStr
    username: str
    password: Optional[str] = None
    channel: dict  # avatar, banner, slug, description


class IEmailVerificationRequest(BaseModel):
    token: str


class IResendEmailRequest(BaseModel):
    email: EmailStr


class IResponseUser(BaseModel):
    id: str
    username: Optional[str] = None
    email: EmailStr
    channel: Optional[dict] = None
    subscriptions: List[dict] = []
    watchHistory: List[dict] = []
    likes: List[dict] = []
    subscribedVideos: List['IVideo'] = []


class IPaginationParams(BaseModel):
    searchTerm: Optional[str] = None
    page: int = 1
    limit: int = 10


class IVideoFormData(BaseModel):
    title: str
    description: Optional[str] = None
    thumbnailUrl: str
    videoFileName: str
    maxResolution: str  # '480p' | '720p' | '1080p' | '4K'
    tags: List[str] = []


class IVideo(BaseModel):
    id: str
    publicId: str
    title: str
    description: Optional[str] = None
    thumbnailUrl: str
    videoFileName: str
    maxResolution: str
    views: int
    isPublic: bool
    createdAt: datetime
    channel: dict


class IVideoFull(IVideo):
    likes: List[dict] = []
    comments: List[dict] = []


class IVideoSingleResponse(IVideoFull):
    similarVideos: List[IVideo] = []


class IVideoStudioResponse(IVideoFull):
    tags: List[str] = []


class IVideosPagination(BaseModel):
    page: int
    limit: int
    totalCount: int
    totalPages: int
    videos: List[IVideoFull]


class IChannel(BaseModel):
    id: str
    slug: str
    description: str = ''
    isVerified: bool = False
    avatar: str = ''
    banner: str = ''
    owner: Optional[dict] = None
    videos: List[IVideo] = []
    subscriptions: List[dict] = []
    createdAt: datetime


class ICommentData(BaseModel):
    text: str
    videoId: str


class IComment(BaseModel):
    id: str
    text: str
    createdAt: datetime
    videoId: str
    user: dict


class IPlaylistData(BaseModel):
    title: str
    videoPublicId: str


class IPlaylist(BaseModel):
    id: str
    name: str
    userId: str
    videos: List[IVideo]
    createdAt: datetime


class IFileResponse(BaseModel):
    url: str
    name: str
    maxResolution: Optional[str] = None


class IToggleLikeRequest(BaseModel):
    videoId: str


class IToggleVideoRequest(BaseModel):
    videoId: str


class IWatchHistoryRequest(BaseModel):
    videoId: str


# Resolve forward refs
IResponseUser.model_rebuild()
