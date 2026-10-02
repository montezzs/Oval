"""
Gera o oval.ico (ícone do Oval.exe) a partir de Img/personagem/P_verde.png,
usando só o pygame (o Pillow não é necessário).

    python tools/gerar_icone.py
"""
import io
import os
import struct
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAMANHOS = (16, 24, 32, 48, 64, 128, 256)


def main():
    pygame.init()
    img = pygame.image.load(os.path.join(RAIZ, "Img", "personagem", "P_verde.png"))
    recorte = img.subsurface(img.get_bounding_rect()).copy()
    lado = max(recorte.get_size())
    quadrado = pygame.Surface((lado, lado), pygame.SRCALPHA)
    quadrado.blit(recorte, recorte.get_rect(center=(lado // 2, lado // 2)))

    pngs = []
    for t in TAMANHOS:
        sup = pygame.transform.smoothscale(quadrado, (t, t))
        buf = io.BytesIO()
        pygame.image.save(sup, buf, "x.png")
        pngs.append((t, buf.getvalue()))

    # ICO com PNGs embutidos (aceito desde o Windows Vista)
    cabecalho = struct.pack("<HHH", 0, 1, len(pngs))
    entradas = b""
    dados = b""
    deslocamento = 6 + 16 * len(pngs)
    for t, png in pngs:
        lado_b = 0 if t >= 256 else t
        entradas += struct.pack("<BBBBHHII", lado_b, lado_b, 0, 0, 1, 32, len(png), deslocamento)
        dados += png
        deslocamento += len(png)
    destino = os.path.join(RAIZ, "oval.ico")
    with open(destino, "wb") as f:
        f.write(cabecalho + entradas + dados)
    print("ícone gravado em", destino)


if __name__ == "__main__":
    sys.exit(main())
