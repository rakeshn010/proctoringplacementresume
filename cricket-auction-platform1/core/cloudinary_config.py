"""
Cloudinary configuration for image uploads
"""
import cloudinary
import cloudinary.uploader
import cloudinary.api
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", ""),
    api_key=os.getenv("CLOUDINARY_API_KEY", ""),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", ""),
    secure=True
)

def upload_image(file_content, filename: str, folder: str = "cricket_auction/players"):
    """
    Upload image to Cloudinary
    
    Args:
        file_content: File content (bytes or file object)
        filename: Original filename
        folder: Cloudinary folder path
        
    Returns:
        dict: Upload result with 'url' and 'public_id'
    """
    try:
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file_content,
            folder=folder,
            resource_type="image",
            allowed_formats=["jpg", "jpeg", "png", "gif"],
            transformation=[
                {"width": 500, "height": 500, "crop": "limit"},
                {"quality": "auto:good"}
            ]
        )
        
        return {
            "success": True,
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "format": result.get("format"),
            "width": result.get("width"),
            "height": result.get("height")
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def delete_image(public_id: str):
    """
    Delete image from Cloudinary
    
    Args:
        public_id: Cloudinary public ID
        
    Returns:
        dict: Deletion result
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return {
            "success": result.get("result") == "ok",
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def is_cloudinary_configured():
    """Check if Cloudinary is properly configured"""
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    api_key = os.getenv("CLOUDINARY_API_KEY", "")
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "")
    
    is_configured = bool(cloud_name and api_key and api_secret and 
                cloud_name != "your_cloud_name")
    
    # Log configuration status
    if is_configured:
        print(f"✅ Cloudinary configured: {cloud_name}")
    else:
        print(f"⚠️ Cloudinary NOT configured")
        print(f"   CLOUDINARY_CLOUD_NAME: {cloud_name if cloud_name else 'NOT SET'}")
        print(f"   CLOUDINARY_API_KEY: {'SET' if api_key else 'NOT SET'}")
        print(f"   CLOUDINARY_API_SECRET: {'SET' if api_secret else 'NOT SET'}")
    
    return is_configured
