import os
from collections import deque

from PIL import Image

SRC = r"C:\Users\Administrator\Desktop\新建文件夹 (2)\02f347f382f4aab78b48f5452c4cc136.jpg"
OUT = r"C:\Users\Administrator\Desktop\oka passwd\assets"
TOL = 54
PAD = 1.08
SOLID = (74, 50, 32, 255)


def isolate(img):
    img = img.convert("RGB")
    w, h = img.size
    px = img.load()
    bg = px[0, 0]
    visited = bytearray(w * h)
    q = deque()

    def try_push(x, y):
        if x < 0 or y < 0 or x >= w or y >= h:
            return
        i = y * w + x
        if visited[i]:
            return
        r, g, b = px[x, y]
        if abs(r - bg[0]) <= TOL and abs(g - bg[1]) <= TOL and abs(b - bg[2]) <= TOL:
            visited[i] = 1
            q.append((x, y))

    for x in range(w):
        try_push(x, 0)
        try_push(x, h - 1)
    for y in range(h):
        try_push(0, y)
        try_push(w - 1, y)
    while q:
        x, y = q.popleft()
        try_push(x + 1, y)
        try_push(x - 1, y)
        try_push(x, y + 1)
        try_push(x, y - 1)

    out = img.convert("RGBA")
    op = out.load()
    for y in range(h):
        base = y * w
        for x in range(w):
            if visited[base + x]:
                r, g, b, _ = op[x, y]
                op[x, y] = (r, g, b, 0)
    return out


def square(img):
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    w, h = img.size
    side = int(max(w, h) * PAD)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - w) // 2, (side - h) // 2), img)
    return canvas


def silhouette(img):
    mask = img.split()[3]
    solid = Image.new("RGBA", img.size, SOLID)
    solid.putalpha(mask)
    return solid


def main():
    os.makedirs(OUT, exist_ok=True)
    src = Image.open(SRC)

    color = square(isolate(src))
    color.save(os.path.join(OUT, "logo_color.png"))
    color.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT, "logo_color.ico"),
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    sil = square(silhouette(isolate(src)))
    sil.save(os.path.join(OUT, "logo_silhouette.png"))
    sil.resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT, "logo_silhouette.ico"),
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("done", color.size, sil.size)


if __name__ == "__main__":
    main()
