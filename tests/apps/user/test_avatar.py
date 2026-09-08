import pytest
import io
from fastapi import UploadFile
from youtube.utils.avatar import validate_and_convert_avatar
from youtube.exceptions import ValidationError

def test_validate_and_convert_avatar_success():
    from PIL import Image as PILImage
    img_io = io.BytesIO()
    PILImage.new("RGB", (10, 10), color="red").save(img_io, format="PNG")
    png_data = img_io.getvalue()
    
    upload_file = UploadFile(
        file=io.BytesIO(png_data),
        filename="test.png",
        headers={"content-type": "image/png"}
    )
    
    result = validate_and_convert_avatar(upload_file)
    assert isinstance(result, bytes)
    assert len(result) > 0

def test_validate_and_convert_avatar_invalid_mimetype():
    upload_file = UploadFile(
        file=io.BytesIO(b"some raw text data"),
        filename="test.txt",
        headers={"content-type": "text/plain"}
    )
    
    with pytest.raises(ValidationError) as excinfo:
        validate_and_convert_avatar(upload_file)
    assert "Only JPEG, PNG and WebP images are allowed" in str(excinfo.value)

def test_validate_and_convert_avatar_invalid_image_content():
    upload_file = UploadFile(
        file=io.BytesIO(b"invalid image bytes but correct mime"),
        filename="test.png",
        headers={"content-type": "image/png"}
    )
    
    with pytest.raises(ValidationError) as excinfo:
        validate_and_convert_avatar(upload_file)
    assert "Invalid image file or corrupted content" in str(excinfo.value)
