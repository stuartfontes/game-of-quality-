from pathlib import Path

import pygame 

INTERNAL_WIDTH = 384
INTERNAL_HEIGHT = 216
TILE_SIZE = 24
FPS = 60
WINDOW_TITLE = "as aventuras do CLT - Episódio 1: Enfrente a CAM / Por: Mauricio Stuart e toda UPP-1 "

BASE_DIR = Path(__file__).resolve().parents[2]

ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"

FONTS_DIR = ASSETS_DIR / "fonts"
MAPS_DIR = ASSETS_DIR / "maps"
SOUNDS_DIR = ASSETS_DIR / "sounds"
SPRITES_DIR = ASSETS_DIR / "sprites"
TILES_DIR = ASSETS_DIR / "tiles"
RESULTS_FILE = DATA_DIR / "results.jsonl"

COLOR_BG = (20, 24, 36)
COLOR_TEXT = (240, 240, 240)
COLOR_HIGHLIGHT = (255, 200, 60)
COLOR_ERROR = (220, 60, 60)
COLOR_SUCCESS = (80, 200, 120)

MAX_ATTEMPTS = 3
IDLE_RESET_SECONDS = 5
FADE_DURATION = 0.4

KEYMAP = {
    "up": [pygame.K_UP, pygame.K_w],
    "down":[pygame.K_DOWN, pygame.K_s],
    "left":[pygame.K_LEFT, pygame.K_a],
    "right":[pygame.K_RIGHT, pygame.K_d],
    "confirm":[pygame.K_RETURN],
    "back":[pygame.K_BACKSPACE],
    "jump":[pygame.K_SPACE, pygame.K_UP],
    "interact":[pygame.K_e],
    "quit":[pygame.K_ESCAPE]
}