import pygame
import os
import cyal.listener



def main():
    from libs import options

    options.initialize()
    from libs import consts, menus
    from libs.version import version, note

    pygame.init()
    pygame.display.set_caption(
        f"{consts.TITLE}, version {version.major}.{version.minor}.{version.patch} {note}"
    )
    screen = pygame.display.set_mode((900, 500))
    from libs import game

    g = game.Game(screen)
    g.start()
    g.loop()


if __name__ == "__main__":
    main()
