class Screen:
    """classe base: toda tela de jogo herda"""
    
    def __init__(self, manager):
        self.manager = manager
        
    def on_enter(self):
        """chamado quando a tela se torna ativa"""
        
    def on_exit(self):
        """chamado quando a tela deixa de ser a ativa"""
        
    def handle_event(self, event):
        """recebe cada evento do pygame(teclad, etc...)"""
        
    def update(self, dt):
        """lógica da tela dt = segundos desde o ultimo quadro"""
        
    def draw(self, surface):
        """"desenha na superficie interna"""