import io
from PIL import Image
from fastapi import UploadFile
from youtube.exceptions import ValidationError

ALLOWED_AVATAR_MIMETYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5MB

def validate_and_convert_avatar(file: UploadFile) -> bytes:
    """
    Validates file format, mimetype, size and converts it to WebP format, resizing it to 256x256.
    """
    if file.content_type not in ALLOWED_AVATAR_MIMETYPES:
         raise ValidationError(field="avatar", custom_message="Only JPEG, PNG and WebP images are allowed")

    # Read content
    content = file.file.read()
    if len(content) > MAX_AVATAR_SIZE:
         raise ValidationError(field="avatar", custom_message="Avatar size must be less than 5MB")
    
    # Reset file pointer just in case
    file.file.seek(0)
    
    try:
        image = Image.open(io.BytesIO(content))
        image.verify() # Verify it's a valid image
        
        # Re-open because verify() closes the file/invalidates it for further operations
        image = Image.open(io.BytesIO(content))
        
        # Convert RGBA/P to RGB if converting to webp (standardizes transparency Handling)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            # Keep alpha channel for WebP since WebP supports transparency
            pass
        else:
            image = image.convert("RGB")
            
        # Resize to thumbnail to optimize size (e.g., 256x256)
        image.thumbnail((256, 256))
        
        output_buffer = io.BytesIO()
        image.save(output_buffer, format="WEBP", quality=85)
        return output_buffer.getvalue()
        
    except Exception as e:
         raise ValidationError(field="avatar", custom_message="Invalid image file or corrupted content") from e
