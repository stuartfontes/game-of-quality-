import pygame

from src.core import settings


class _SilentSound:
    """Substituto de som: aceita as mesmas chamadas e não faz nada."""

    def play(self, *args, **kwargs):
        pass

    def stop(self):
        pass

    def set_volume(self, volume):
        pass


class Assets:
    def __init__(self):
        self._images = {}
        self._fonts = {}
        self._sounds = {}
        self._warned = set()

    def _warn(self, kind, path):
        key = (kind, str(path))
        if key not in self._warned:
            self._warned.add(key)
            print(f"[assets] {kind} não encontrado: {path}")

    @staticmethod
    def _placeholder(size):
        surf = pygame.Surface(size)
        surf.fill((255, 0, 255))
        pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 1)
        pygame.draw.line(surf, (0, 0, 0), (0, 0), (size[0] - 1, size[1] - 1))
        pygame.draw.line(surf, (0, 0, 0), (size[0] - 1, 0), (0, size[1] - 1))
        return surf

    def image(self, folder, name, size=None):
        key = (folder, name, size)
        if key in self._images:
            return self._images[key]

        path = settings.ASSETS_DIR / folder / name
        if path.exists():
            surf = pygame.image.load(str(path)).convert_alpha()
        else:
            self._warn("imagem", path)
            surf = self._placeholder(size or (settings.TILE_SIZE, settings.TILE_SIZE))

        self._images[key] = surf
        return surf

    def font(self, name, size):
        key = (name, size)
        if key in self._fonts:
            return self._fonts[key]

        path = settings.FONTS_DIR / name
        if path.exists():
            font = pygame.font.Font(str(path), size)
        else:
            self._warn("fonte", path)
            font = pygame.font.Font(None, size)

        self._fonts[key] = font
        return font

    def sound(self, name):
        if name in self._sounds:
            return self._sounds[name]

        path = settings.SOUNDS_DIR / name
        sound = _SilentSound()
        if path.exists():
            try:
                sound = pygame.mixer.Sound(str(path))
            except pygame.error as err:
                print(f"[assets] erro ao carregar som {path}: {err}")
        else:
            self._warn("som", path)

        self._sounds[name] = sound
        return sound