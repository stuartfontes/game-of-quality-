from src.core import settings
from src.core.screen import Screen
from src.core.ui import Menu, MessageBox, draw_text


class UITestScreen(Screen):
    def __init__(self, manager):
        super().__init__(manager)
        self.font = manager.assets.font("pixel.ttf", 16)
        self.menu = Menu(
            ["Perder uma vida", "Vencer", "Reiniciar partida"],
            self.font,
            (30, 60),
        )
        self.box = MessageBox((20, 120, 344, 80), self.font)

    def on_enter(self):
        self.manager.state.start_run("teste")

    def update(self, dt):
        self.box.update(dt)
        inputs = self.manager.input
        state = self.manager.state

        if self.box.visible:
            if inputs.pressed("confirm") or inputs.pressed("back"):
                self.box.hide()
            return

        chosen = self.menu.update(inputs)
        if chosen == 0 and not state.game_over:
            self.box.show(state.lose_life(), title="Atenção")
        elif chosen == 1 and not state.game_over:
            state.win()
            text = state.messages["victory"] + "\n" + state.messages["voucher"]
            self.box.show(text, title="Parabéns")
        elif chosen == 2:
            state.start_run("teste")

    def draw(self, surface):
        surface.fill(settings.COLOR_BG)
        state = self.manager.state

        info = f"Vidas: {state.lives}   Tentativa: {state.attempt}/{settings.MAX_ATTEMPTS}"
        draw_text(surface, info, self.font, settings.COLOR_TEXT, (30, 15))
        draw_text(surface, f"Resultado: {state.result}", self.font, settings.COLOR_TEXT, (30, 35))

        self.menu.draw(surface)
        self.box.draw(surface)