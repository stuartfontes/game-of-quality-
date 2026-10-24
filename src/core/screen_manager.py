from src.core import settings


class ScreenManager:
    def __init__(self, input_manager, assets, state):
        self.input = input_manager
        self.assets = assets
        self.state = state
        self._screens = {}
        self.current = None
        self.current_name = None
        self.home_screen = None
        self.running = True

    def register(self, name, screen):
        self._screens[name] = screen

    def go_to(self, name):
        if self.current is not None:
            self.current.on_exit()
        self.current = self._screens[name]
        self.current_name = name
        self.current.on_enter()

    def reset_to_home(self):
        self.state.start_run(None)
        self.input.reset_idle()
        self.go_to(self.home_screen)

    def check_idle(self):
        if self.home_screen is None or self.current_name == self.home_screen:
            return
        if self.input.idle_time >= settings.IDLE_RESET_SECONDS:
            self.reset_to_home()

    def quit(self):
        self.running = False

    def handle_event(self, event):
        if self.current:
            self.current.handle_event(event)

    def update(self, dt):
        if self.current:
            self.current.update(dt)

    def draw(self, surface):
        if self.current:
            self.current.draw(surface)