from io import BytesIO

from PIL import Image
from django.core.files.base import ContentFile


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

    filename = image_field.name.rsplit(".", 1)[0] + ".webp"

    return ContentFile(output.read(), name=filename)