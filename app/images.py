from dotenv import load_dotenv
from imagekitio import ImageKit
import os

load_dotenv()

imagekit = ImageKit(
    private_key=os.getenv("PRIVATE_KEY") or os.getenv("IMAGE_PRIVATE_KEY") or os.getenv("IMAGEKIT_PRIVATE_KEY")
)
