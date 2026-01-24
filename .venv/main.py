import arcade
from math import *
import numpy as np
import random

FREQUENCY = 0.05
n = 42
grid1 = np.random.rand(n) * 2 - 1
grid2 = np.random.rand(n // 3) * 2 - 1

def gn(x, gr):
    x0 = int(x)
    dx = x - x0
    s = 6 * dx ** 5 - 15 * dx ** 4 + 10 * dx ** 3
    g0 = gr[x0]
    g1 = gr[x0 + 1]
    d0 = g0 * dx
    d1 = g1 * (dx - 1)
    nv = (1 - s) * d0 + s * d1
    return nv


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Damage Boost"
GRAVITY = 12


class Arme(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.scale = 4.0
        self.speed = 30
        self.health = 100

        self.idle_r = arcade.load_texture("sprites/idle_r.png")
        self.idle_l = arcade.load_texture("sprites/idle_l.png")
        self.move_r = arcade.load_texture("sprites/move_r.png")
        self.move_l = arcade.load_texture("sprites/move_l.png")

        self.texture = self.idle_r

        self.center_x = SCREEN_WIDTH // 2
        self.center_y = SCREEN_HEIGHT + 400

        # Physics
        self.face_direction = 1
        self.is_walking = False
        self.is_airborne = False
        self.lerp = 0.1
        ## Constants
        self.mass = 10
        self.ys = 0.0
        self.xs = 0.0
        self.friction = 0.9
        self.air_friction = 0.00005
        self.jump_force = 0
        self.old_x = self.center_x
        self.old_y = self.center_y
        self.speed_limit = 250.0
        self.boost = 50.0
        arcade.schedule(self.debug, 0.1)

    def update(self, delta_time):

        self.center_y += self.ys * delta_time
        self.center_x += self.xs * delta_time

        self.is_walking = abs(self.xs) > 15

    def update_animation(self, delta_time):
        if self.is_walking and not self.is_airborne:
            if self.face_direction == -1:
                self.texture = self.move_l
            elif self.face_direction == 1:
                self.texture = self.move_r
        elif self.face_direction == -1:
            self.texture = self.idle_l
        elif self.face_direction == 1:
            self.texture = self.idle_r

    def debug(self, ar):
        print('Movement:', self.xs, self.ys)

    def on_close(self):
        arcade.unschedule(self.debug)
        super().on_close()


pev = Arme()


class DamageBoost(arcade.Window):
    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)
        self.pev_list = arcade.SpriteList()
        self.pev_list.append(pev)
        self.keys_pressed = set()
        self.walls = arcade.SpriteList()
        self.setup()

        self.world_camera = arcade.camera.Camera2D()  # Камера для игрового мира

    def setup(self):
        print("setup")
        for x in range(-SCREEN_WIDTH, SCREEN_WIDTH * 2, 1):
            tile = arcade.Sprite("sprites/wall.png", scale=1/32)
            tile.center_x = x
            tile.center_y = 32 + x / 4
            self.walls.append(tile)


        self.engine = arcade.PhysicsEnginePlatformer(
            player_sprite=pev,
            gravity_constant=0,
            walls=self.walls
        )

    def on_draw(self):
        self.world_camera.use()
        self.clear()
        self.pev_list.draw(pixelated=True)
        self.walls.draw(pixelated=True)

    def on_update(self, delta_time):
        pev.old_x, pev.old_y = pev.center_x, pev.center_y

        pev.is_airborne = not self.engine.can_jump()
        if pev.is_airborne:  # ========= Airborne:
            pev.ys += -GRAVITY
            pev.ys += -pev.ys * abs(pev.ys) * pev.air_friction

        else:  # ==================== On ground:
            pev.ys = 0
            if abs(pev.xs) < 0.01:  # If too slow, stop entirely
                pev.xs = 0.0
            else:
                pev.xs *= pev.friction

        # ======================== KEYS:
        if arcade.key.LEFT in self.keys_pressed and not pev.is_airborne:
            pev.face_direction = -1
            pev.xs -= pev.speed

        if arcade.key.RIGHT in self.keys_pressed and not pev.is_airborne:
            pev.face_direction = 1
            pev.xs += pev.speed

        if arcade.key.UP in self.keys_pressed and not pev.is_airborne: # UP while grounded
            pev.ys += pev.jump_force
            pev.center_y += 5

        if arcade.key.DOWN in self.keys_pressed and not pev.is_airborne:
            pev.xs += pev.boost * pev.face_direction

        self.pev_list.update(delta_time)
        self.pev_list.update_animation()

        # ============ CAMERA
        position = (
            pev.center_x + pev.xs * 0.3,
            pev.center_y + pev.ys * 0.1
        )
        self.world_camera.position = arcade.math.lerp_2d(  # Изменяем позицию камеры
            self.world_camera.position,
            position,
            pev.lerp,  # Плавность следования камеры
        )
        self.engine.update()

        pev.xs = (pev.center_x - pev.old_x) / delta_time
        pev.ys = (pev.center_y - pev.old_y) / delta_time

    def on_key_press(self, key, modifiers):
        self.keys_pressed.add(key)

    def on_key_release(self, key, modifiers):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)


if __name__ == "__main__":
    app = DamageBoost()
    app.run()