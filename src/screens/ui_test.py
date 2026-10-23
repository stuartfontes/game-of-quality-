from src.core import settings
from src.core.screen import Screen
from src.core.ui import Menu, MessageBox, draw_text


class UITestScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = manager.assets.font("pixel.ttf", 16)

        self.menu = Menu(
            ["Jogo 1: Plataforma", "Jogo 2: Montar receita", "Instruções"],
            self.font,
            (30, 40),
        )
        self.box = MessageBox((20, 120, 344, 80), self.font, title="Atenção")
        self.messages = [
            "O controle em processo salvou no momento! Tome cuidado",
            "A garantia da qualidade salvou desta vez! Tome cuidado",
            "Infelizmente o produto foi para o mercado! :(",
        ]

    def update(self, dt):
        self.box.update(dt)
        inputs = self.manager.input

        if self.box.visible:
            if inputs.pressed("confirm") or inputs.pressed("back"):
                self.box.hide()
            return

        chosen = self.menu.update(inputs)
        if chosen is not None:
            self.box.show(self.messages[chosen])

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        draw_text(surface, "Teste de interface", self.font, settings.COLOR_TEXT, (30, 15))
        self.menu.draw(surface)
        self.box.draw(surface)