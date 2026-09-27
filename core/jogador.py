import pygame

from core import assets
from core.ui import escurecer, clarear

# ============================================================
# JOGADOR
# ============================================================
# Guarda o nome e a aparência do ovo, e monta o "avatar"
# (todas as partes empilhadas) com cache, para os mini jogos
# poderem usar o personagem em qualquer tamanho sem custo.


class Jogador:

    PARTES = ("ovo", "cabelo", "olho", "boca")

    def __init__(self, save):
        self.save = save
        self.nome = save["nome"]
        self.ovo = save["ovo"]
        self.cabelo = save["cabelo"]
        self.olho = save["olho"]
        self.boca = save["boca"]
        self._corrigir_indices()
        self._cache = {}

    # --------------------------------------------------------

    @staticmethod
    def listas():
        return {
            "ovo": assets.OVOS,
            "cabelo": assets.CABELOS,
            "olho": assets.OLHOS,
            "boca": assets.BOCAS,
        }

    def _corrigir_indices(self):
        for parte, lista in self.listas().items():
            valor = getattr(self, parte)
            if not isinstance(valor, int) or not 0 <= valor < len(lista):
                setattr(self, parte, 0)

    def aparencia(self):
        return (self.ovo, self.cabelo, self.olho, self.boca)

    def definir_aparencia(self, ovo, cabelo, olho, boca):
        self.ovo, self.cabelo, self.olho, self.boca = ovo, cabelo, olho, boca
        self._corrigir_indices()

    def salvar(self):
        self.save["nome"] = self.nome
        for parte in self.PARTES:
            self.save[parte] = getattr(self, parte)
        self.save.salvar()

    # --------------------------------------------------------
    # AVATAR
    # --------------------------------------------------------

    @staticmethod
    def compor(ovo, cabelo, olho, boca, cosmeticos=()):
        """
        Empilha as 4 partes numa Surface 100x100.
        `cosmeticos`: lista de ids (chapéu, óculos...) desenhados
        por cima (ou por trás, no caso das auras).
        """
        from core import cosmeticos as cos

        sup = pygame.Surface((100, 100), pygame.SRCALPHA)
        cos.aplicar(sup, cosmeticos, "atras", ovo)
        sup.blit(assets.OVOS[ovo], (0, 0))
        cos.aplicar(sup, cosmeticos, "corpo", ovo)
        # Chapéus grandes escondem os cabelos "de topo"
        esconde = getattr(cos, "esconde_cabelo", None)
        if not (cosmeticos and esconde and esconde(cosmeticos, cabelo)):
            sup.blit(assets.CABELOS[cabelo], (0, 0))
        sup.blit(assets.OLHOS[olho], (0, 0))
        sup.blit(assets.BOCAS[boca], (0, 0))
        cos.aplicar(sup, cosmeticos, "frente", ovo)
        return sup

    # --------------------------------------------------------
    # COSMÉTICOS EQUIPADOS
    # --------------------------------------------------------

    def chave_visual(self):
        """Muda sempre que o jogador troca de cosmético (para caches)."""
        equipado = self.save["equipado"]
        return tuple(sorted((k, v) for k, v in equipado.items() if v))

    def _cosmeticos_de(self, apar):
        # Só o próprio jogador usa os cosméticos. Olhos e boca podem
        # variar (dormindo, boca aberta comendo...), então comparamos
        # a cor do ovo e o cabelo. CPU/J2/família não usam.
        if tuple(apar[:2]) == self.aparencia()[:2]:
            return tuple(v for _, v in self.chave_visual())
        return ()

    # O corpo do ovo ocupa este retângulo dentro da imagem 100x100
    OVO_RECT = pygame.Rect(15, 14, 67, 74)

    def avatar(self, altura=None, aparencia=None):
        """
        Avatar do jogador (imagem quadrada, com as bordas).

        `altura` é a altura do CORPO DO OVO em pixels. Assim o ovo
        tem sempre o mesmo tamanho, não importa o cabelo escolhido.
        O centro da imagem fica praticamente no centro do ovo.

        `aparencia` permite montar outra combinação de partes
        (usado pela CPU do vôlei e pelas cartas da memória).
        """
        apar = tuple(aparencia or self.aparencia())
        cos = self._cosmeticos_de(apar)
        chave = (apar, cos, altura)
        sup = self._cache.get(chave)

        if sup is not None:
            return sup

        base = self._cache.get((apar, cos, None))

        if base is None:
            base = self.compor(*apar, cosmeticos=cos)
            self._cache[(apar, cos, None)] = base

        if altura is None:
            sup = base
        else:
            lado = max(1, round(100 * altura / self.OVO_RECT.h))

            if lado >= 100:
                sup = pygame.transform.scale(base, (lado, lado))
            else:
                sup = pygame.transform.smoothscale(base, (lado, lado))

        if len(self._cache) > 200:
            self._cache.clear()

        self._cache[chave] = sup
        return sup

    def desenhar(self, tela, centro, altura, aparencia=None, espelhar=False,
                 angulo=0.0):
        """
        Desenha o avatar com o CENTRO DO OVO em `centro`.
        Devolve o retângulo do corpo do ovo na tela (bom para colisão).
        """
        sup = self.avatar(altura, aparencia)
        escala = sup.get_width() / 100

        # Efeitos animados (auras) só em tamanhos que dá para ver
        efeitos = ()
        if altura >= 40:
            efeitos = self._cosmeticos_de(tuple(aparencia or self.aparencia()))
            if efeitos:
                self._efeito(tela, efeitos, centro, altura, "atras")

        if espelhar:
            sup = pygame.transform.flip(sup, True, False)
        if angulo:
            sup = pygame.transform.rotate(sup, angulo)

        # Diferença entre o centro do ovo e o centro da imagem
        dx = (self.OVO_RECT.centerx - 50) * escala * (-1 if espelhar else 1)
        dy = (self.OVO_RECT.centery - 50) * escala

        rect = sup.get_rect(center=(round(centro[0] - dx), round(centro[1] - dy)))
        tela.blit(sup, rect)

        if efeitos:
            self._efeito(tela, efeitos, centro, altura, "frente")

        largura = self.OVO_RECT.w * escala
        corpo = pygame.Rect(0, 0, round(largura), round(altura))
        corpo.center = (round(centro[0]), round(centro[1]))
        return corpo

    @staticmethod
    def _efeito(tela, ids, centro, altura, fase):
        from core import cosmeticos as cos
        desenhar = getattr(cos, "desenhar_efeito", None)
        if desenhar:
            import time
            desenhar(tela, ids, centro, altura, time.perf_counter(), fase)

    # --------------------------------------------------------
    # CORES DO OVO
    # --------------------------------------------------------

    @staticmethod
    def cor_do_ovo(indice):
        img = assets.OVOS[indice]
        c = img.get_at((50, 55))
        return (c.r, c.g, c.b)

    @property
    def cor(self):
        return self.cor_do_ovo(self.ovo)

    @property
    def cor_escura(self):
        return escurecer(self.cor, 60)

    @property
    def cor_clara(self):
        return clarear(self.cor, 60)

    @property
    def cor_contorno(self):
        """Contorno que aparece bem até no ovo branco."""
        r, g, b = self.cor
        if r + g + b > 600:
            return (150, 150, 170)
        return escurecer(self.cor, 70)
