from src.core import settings

print("Resolução interna:", settings.INTERNAL_WIDTH, "x", settings.INTERNAL_HEIGHT)
print("Raiz do projeto:", settings.BASE_DIR)
print("Assets:", settings.ASSETS_DIR)
print("Assets existe?", settings.ASSETS_DIR.exists())