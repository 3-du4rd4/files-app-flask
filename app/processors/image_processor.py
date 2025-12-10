import io
from PIL import Image, ExifTags


def processar_imagem(file):
    img = Image.open(file)

    largura, altura = img.size

    profundidade = img.mode

    dpi = img.info.get("dpi", None)  

    exif_data = {}
    raw_exif = img.getexif()
    if raw_exif:
        for tag_id, value in raw_exif.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            exif_data[tag] = value

    thumbnail_size = (200, 200)
    thumbnail_img = img.copy()
    thumbnail_img.thumbnail(thumbnail_size)

    thumb_bytes_io = io.BytesIO()
    if thumbnail_img.mode in ("RGBA", "LA", "P"):
        thumbnail_img = thumbnail_img.convert("RGB")

    thumbnail_img.save(thumb_bytes_io, format="JPEG")
    thumb_bytes_io.seek(0)
    thumbnail_bytes = thumb_bytes_io.read()

    info = {
        "largura": largura,
        "altura": altura,
        "dimensao": f"{largura}x{altura}",
        "profundidade_cor": profundidade,
        "resolucao_dpi": dpi,
        "exif": exif_data
    }

    return info, thumbnail_bytes
