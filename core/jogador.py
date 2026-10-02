import math

import pygame

from core import assets
from core.ui import escurecer, clarear

# ============================================================
# JOGADOR
# ============================================================
# Guarda o nome e a aparência do ovo, e monta o "avatar"
# (todas as partes empilhadas) com cache, para os mini jogos
# poderem usar o personagem em qualquer tamanho sem custo.


# Use no lugar do índice da boca para desenhar uma boca triste
BOCA_TRISTE = "triste"
# Use no lugar do índice do olho para olhos fechados (dormindo / piscando)
OLHO_FECHADO = "fechado"
# Use no lugar do índice da boca para a boca "aberta" (comendo / susto).
# Desenha assets.BOCAS[2] mesmo quando o jogador usa uma BOCA EXTRA.
BOCA_ABERTA = "aberta"
_INDICE_BOCA_ABERTA = 2


class IndiceOvo(int):
    """
    Índice da cor base do ovo (0..3) que "carrega" a COR EXTRA equipada
    (core/visual_extra.py). Continua sendo um int normal (compara,
    soma, indexa assets.OVOS, vai para o JSON), mas cor_do_ovo(ap[0])
    devolve a cor extra, então os jogos que pintam coisas com a cor do
    ovo do jogador acompanham a cor comprada.
    """

    def __new__(cls, valor, cor_x=None):
        obj = super().__new__(cls, valor)
        obj.cor_x = cor_x
        return obj

    def __getnewargs__(self):
        return (int(self), self.cor_x)


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
        # False = ignora cabelo/olhos/boca/cor EXTRA (ex: no criador,
        # para ver as partes base que estão sendo escolhidas)
        self.usar_extras = True

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
            else:
                setattr(self, parte, int(valor))    # tira o IndiceOvo

    def _extra(self, slot):
        if not self.usar_extras:
            return None
        try:
            return self.save["equipado"].get(slot) or None
        except (KeyError, TypeError, AttributeError):
            return None

    def aparencia(self):
        """
        Índices BASE (ovo, cabelo, olho, boca) do criador. Os extras
        comprados na loja entram no desenho pelos cosméticos equipados;
        o ovo vira IndiceOvo quando há uma cor extra equipada.
        """
        ovo = self.ovo
        cor_x = self._extra("cor_x")
        if cor_x:
            ovo = IndiceOvo(ovo, cor_x)
        return (ovo, self.cabelo, self.olho, self.boca)

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
        from core import visual_extra as vx

        # Aparência extra (cabelo/olhos/boca/cor comprados na loja)
        ext = vx.extras_de(cosmeticos) if cosmeticos else {}
        cor_x = ext.get("cor_x")
        cab_x = ext.get("cabelo_x")
        olho_x = ext.get("olhos_x")
        boca_x = ext.get("boca_x")
        ovo_cos = vx.ovo_para_cosmeticos(ovo, cor_x) if cor_x else ovo
        escuro = vx.escuro(cor_x)

        def linhas(img):
            # Rosto base (traço preto) fica claro em ovo escuro
            return vx.linhas_claras(img) if escuro else img

        sup = pygame.Surface((100, 100), pygame.SRCALPHA)
        cos.aplicar(sup, cosmeticos, "atras", ovo_cos)
        cab_escondido = bool(cab_x) and vx.cabelo_escondido(cab_x, cosmeticos)
        if cab_x:
            sup.blit(vx.cabelo(cab_x, "atras", cab_escondido), (0, 0))
        sup.blit(vx.corpo(cor_x) if cor_x else assets.OVOS[ovo], (0, 0))
        cos.aplicar(sup, cosmeticos, "corpo", ovo_cos)
        if cab_x:
            sup.blit(vx.cabelo(cab_x, "frente", cab_escondido), (0, 0))
        else:
            # Chapéus grandes escondem os cabelos "de topo"
            esconde = getattr(cos, "esconde_cabelo", None)
            if not (cosmeticos and esconde and esconde(cosmeticos, cabelo)):
                sup.blit(assets.CABELOS[cabelo], (0, 0))

        if olho == OLHO_FECHADO:
            # Dois risquinhos curvos no lugar dos olhos (os olhos 1 como guia)
            r = assets.OLHOS[0].get_bounding_rect()
            larg = max(10, int(r.w * 0.34))
            cor = vx.CLARO_LINHA if escuro else (25, 20, 25)
            for cx in (r.x + r.w * 0.2, r.right - r.w * 0.2):
                arco = pygame.Rect(0, 0, larg, larg)
                arco.center = (round(cx), round(r.centery - r.h * 0.05))
                pygame.draw.arc(sup, cor, arco, math.pi * 1.15, math.pi * 1.85, 2)
        elif olho_x:
            sup.blit(vx.olhos(olho_x, escuro), (0, 0))
        else:
            sup.blit(linhas(assets.OLHOS[olho]), (0, 0))

        if boca == BOCA_TRISTE:
            # Boquinha triste (necessidades baixas / despedida)
            r = assets.BOCAS[0].get_bounding_rect()
            r = pygame.Rect(0, 0, max(12, r.w), max(8, r.h))
            r.center = assets.BOCAS[0].get_bounding_rect().center
            cor = vx.CLARO_LINHA if escuro else (40, 30, 30)
            pygame.draw.arc(sup, cor, r.move(0, r.h // 3), 0.35, 2.8, 3)
        elif boca == BOCA_ABERTA:
            sup.blit(linhas(assets.BOCAS[_INDICE_BOCA_ABERTA]), (0, 0))
        elif boca_x:
            sup.blit(vx.boca(boca_x, escuro), (0, 0))
        else:
            sup.blit(linhas(assets.BOCAS[boca]), (0, 0))
        cos.aplicar(sup, cosmeticos, "frente", ovo_cos)
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
        if tuple(apar[:2]) != self.aparencia()[:2]:
            return ()
        ids = []
        for slot, v in self.chave_visual():
            if not self.usar_extras and slot in ("cabelo_x", "olhos_x", "boca_x", "cor_x"):
                continue
            # Olhos/boca EXTRA só valem com os olhos/boca do próprio
            # jogador: um jogo que troca a expressão (boca de susto,
            # olhos de outro ovo) mostra a expressão pedida.
            if slot == "olhos_x" and apar[2] != self.olho and apar[2] != OLHO_FECHADO:
                continue
            if slot == "boca_x" and apar[3] != self.boca and apar[3] not in (BOCA_TRISTE,
                                                                             BOCA_ABERTA):
                continue
            ids.append(v)
        return tuple(ids)

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
                 angulo=0.0, esticar=(1.0, 1.0)):
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
        if esticar != (1.0, 1.0):
            # Squash & stretch (amassar / esticar o ovo)
            w, h = sup.get_size()
            sup = pygame.transform.smoothscale(sup, (max(1, round(w * esticar[0])),
                                                     max(1, round(h * esticar[1]))))

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
        """
        Cor de um índice de ovo. Com o ovo de aparencia() do jogador
        (IndiceOvo) devolve a COR EXTRA equipada.
        """
        cor_x = getattr(indice, "cor_x", None)
        if cor_x:
            from core import visual_extra
            cor = visual_extra.rgb(cor_x)
            if cor:
                return cor
        img = assets.OVOS[indice]
        c = img.get_at((50, 55))
        return (c.r, c.g, c.b)

    @property
    def cor(self):
        """Cor do ovo (a COR EXTRA equipada, se houver)."""
        return self.cor_do_ovo(self.aparencia()[0])

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
