import pygame

from src.core import settings
from src.core.screen import Screen

class TestScreen(Screen):
    def __init__(self, manager, bg_color, text, target):
        super().__init__(manager)
        self.bg_color = bg_color
        self.text = text
        self.target = target
        self.font = pygame.font.Font(None, 20)
        self.elapsed = 0.0
        
    def on_enter(self):
        self.elapsed = 0.0
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in settings.KEYMAP["confirm"]:
            self.manager.go_to(self.target)
            
    def update(self, dt):
        self.elapsed += dt
        
    def draw(self, surface):
        surface.fill(self.bg_color)
        label = self.font.render(self.text, False, settings.COLOR_TEXT)
        surface.blit(label, (20, 20))
        timer = self.font.render(f"{self.elapsed:.1f} s", False, settings.COLOR_HIGHLIGHT)
        surface.blit(timer, (20, 50))