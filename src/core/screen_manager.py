class ScreenManager:
    def __init__(self):
        self._screens = {}
        self.current = None
        self.running = True
        
    def register(self, name, screen):
        self._screens[name] = screen
        
    def go_to(self, name):
        if self.current is not None:
            self.current.on_exit()
        self.current = self._screens[name]
        self.current.on_enter()
        
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