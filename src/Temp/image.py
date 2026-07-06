from uuid import uuid4
import os
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image

def optimize_image(image_field, max_size=(1600, 1600), quality=80):
    img = Image.open(image_field)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.thumbnail(max_size)

    output = BytesIO()

    img.save(
        output,
        format="WEBP",
        quality=quality,
        optimize=True,
    )

    output.seek(0)

    # ❌ فقط filename بدون path
    original_name = os.path.splitext(os.path.basename(image_field.name))[0]

    filename = f"{original_name}_{uuid4().hex[:8]}.webp"

    return ContentFile(output.read(), name=filename)