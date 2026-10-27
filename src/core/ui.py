import pygame

from src.core import settings


def wrap_text(text, font, max_width):

    lines = []
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split(" "):
            test = word if not current else current + " " + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        lines.append(current)
    return lines


def draw_text(surface, text, font, color, pos, max_width=None, line_spacing=2):
    
    lines = wrap_text(text, font, max_width) if max_width else text.split("\n")
    x, y = pos
    step = font.get_linesize() + line_spacing
    for line in lines:
        surface.blit(font.render(line, False, color), (x, y))
        y += step
    return y - pos[1]

def draw_text_centered(surface, text, font, color, center_x, y):
    label = font.render(text, False, color)
    surface.blit(label, (center_x - label.get_width() // 2, y))

class MessageBox:
    def __init__(self, rect, font, title=None, padding=8):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.padding = padding
        self.title = title
        self.text = ""
        self.visible = False
        self._time = 0.0

    def show(self, text, title=None):
        self.text = text
        if title is not None:
            self.title = title
        self.visible = True
        self._time = 0.0

    def hide(self):
        self.visible = False

    def update(self, dt):
        self._time += dt

    def draw(self, surface):
        if not self.visible:
            return

        pygame.draw.rect(surface, settings.COLOR_BG, self.rect)
        pygame.draw.rect(surface, settings.COLOR_TEXT, self.rect, 2)

        x = self.rect.x + self.padding
        y = self.rect.y + self.padding
        max_w = self.rect.width - 2 * self.padding

        if self.title:
            used = draw_text(surface, self.title, self.font, settings.COLOR_HIGHLIGHT, (x, y), max_w)
            y += used + 4

        draw_text(surface, self.text, self.font, settings.COLOR_TEXT, (x, y), max_w)

        # setinha piscando no canto inferior direito
        if int(self._time * 2) % 2 == 0:
            ax = self.rect.right - self.padding - 6
            ay = self.rect.bottom - self.padding - 4
            pygame.draw.polygon(
                surface,
                settings.COLOR_HIGHLIGHT,
                [(ax, ay), (ax + 6, ay), (ax + 3, ay + 4)],
            )


class Menu:
    def __init__(self, items, font, pos, spacing=4):
        self.items = items
        self.font = font
        self.pos = pos
        self.spacing = spacing
        self.index = 0

    def update(self, inputs):
        if inputs.pressed("up"):
            self.index = (self.index - 1) % len(self.items)
        if inputs.pressed("down"):
            self.index = (self.index + 1) % len(self.items)
        if inputs.pressed("confirm"):
            return self.index
        return None

    def draw(self, surface):
        x, y = self.pos
        step = self.font.get_linesize() + self.spacing
        for i, item in enumerate(self.items):
            selected = i == self.index
            color = settings.COLOR_HIGHLIGHT if selected else settings.COLOR_TEXT
            prefix = "> " if selected else "  "
            surface.blit(self.font.render(prefix + item, False, color), (x, y + i * step))
            
def draw_lives(surface, lives, total):
    size = 8
    gap = 4
    x = settings.INTERNAL_WIDTH - 8 - total * (size + gap)
    for i in range(total):
        rect = pygame.Rect(x + i * (size + gap), 4, size, size)
        if i < lives:
            pygame.draw.rect(surface, settings.COLOR_ERROR, rect)
        else:
            pygame.draw.rect(surface, settings.COLOR_DIM, rect, 1)
            
def draw_score(surface, font, state):
    label = font.render(f"{state.score} pts", False, settings.COLOR_TEXT)
    surface.blit(label, (settings.INTERNAL_WIDTH - 8 - label.get_width(), 16))