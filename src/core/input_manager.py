import pygame

from src.core import settings


class InputManager:
    def __init__(self, keymap=None):
        self.keymap = keymap or settings.KEYMAP

        self._key_to_actions = {}
        for action, keys in self.keymap.items():
            for key in keys:
                self._key_to_actions.setdefault(key, []).append(action)

        self._held_keys = set()
        self._pressed = set()
        self._released = set()
        self.idle_time = 0.0

    def begin_frame(self, dt):
        self._pressed.clear()
        self._released.clear()
        if self._held_keys:
            self.idle_time = 0.0
        else:
            self.idle_time += dt

    def reset_idle(self):
        self.idle_time = 0.0

    def process(self, event):
        if event.type == pygame.KEYDOWN:
            self.idle_time = 0.0
            self._held_keys.add(event.key)
            for action in self._key_to_actions.get(event.key, []):
                self._pressed.add(action)
        elif event.type == pygame.KEYUP:
            self._held_keys.discard(event.key)
            for action in self._key_to_actions.get(event.key, []):
                self._released.add(action)

    def pressed(self, action):
        return action in self._pressed

    def released(self, action):
        return action in self._released

    def held(self, action):
        return any(key in self._held_keys for key in self.keymap[action])