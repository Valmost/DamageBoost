from email.iterators import typed_subpart_iterator

import arcade
from math import *
import numpy as np
import random

from numpy.random.mtrand import Sequence

FREQUENCY = 0.05
n = 42
grid1 = np.random.rand(n) * 2 - 1
grid2 = np.random.rand(n // 3) * 2 - 1

def gp(x, gr):
    """--Get point--
    Takes the Nth position (x) on a certain grid of nodes (gr).
    Returns the Y value of the perlin noice (0.0 - 1.0).
    """
    x0 = int(x) # left node
    dx = x - x0
    s = 6 * dx ** 5 - 15 * dx ** 4 + 10 * dx ** 3
    g0 = gr[x0]
    g1 = gr[x0 + 1]
    d0 = g0 * dx
    d1 = g1 * (dx - 1)
    nv = (1 - s) * d0 + s * d1
    return nv


def normalize(value, old_min, old_max, new_min, new_max):
    return (value - old_min) * (new_max - new_min) / (old_max - old_min) + new_min


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Damage Boost"
GRAVITY = 12


def calc_slope_collision(angle, xs, ys, delta_time=0.016):
    """
    Calculate slope collision with surf/slide physics.
    Returns the updated xs and ys.
    """
    try:
        angle_rad = radians(angle)

        # Вектор направления склона (вдоль поверхности)
        slope_dir = np.array([cos(angle_rad), sin(angle_rad)])

        # Нормаль к склону (перпендикулярно поверхности)
        normal = np.array([-sin(angle_rad), cos(angle_rad)])

        # Нормализуем
        slope_dir = slope_dir / np.linalg.norm(slope_dir)
        normal = normal / np.linalg.norm(normal)

        # Текущая скорость
        velocity = np.array([xs, ys])

        # Проекция скорости на нормаль (сколько "врезаемся" в склон)
        normal_speed = np.dot(velocity, normal)

        # Если движемся В склон - отражаем
        if normal_speed < 0:
            # Удаляем компоненту, направленную в склон
            velocity = velocity - normal_speed * normal

            # Добавляем гравитацию ВДОЛЬ склона (это дает ускорение как в surf)
            # Гравитация = (0, -GRAVITY)
            # Проекция гравитации на склон: гравитация - (гравитация·нормаль)*нормаль
            gravity = np.array([0, -GRAVITY])
            gravity_normal = np.dot(gravity, normal) * normal
            gravity_along_slope = gravity - gravity_normal

            # Ускорение вдоль склона (чем круче склон, тем больше)
            velocity += gravity_along_slope * delta_time * 60  # Ускорение

        rad_velocity = normalize(np.linalg.norm(velocity), 0, 2000, 0, radians(90))
        # Сохраняем энергию (очень малое трение для surf)
        velocity *= 0.85 if rad_velocity < angle_rad - 0.1 else 1

        return velocity

    except Exception as e:
        print("Slope collision error:", e)
        return np.array([xs, ys])


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
        self.collisions = []
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

        self.ang = None

    def update(self, delta_time):

        self.center_y += self.ys * delta_time
        self.center_x += self.xs * delta_time

    def update_animation(self, delta_time):
        self.is_walking = abs(self.xs) > 15
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
        print('Collisions:', self.collisions)
        print('Ang:', pev.ang)
        if pev.collisions:
            print('Sent:', -pev.collisions[0].angle, pev.xs, pev.ys)
            print('Received:', *calc_slope_collision(-pev.collisions[0].angle, pev.xs, pev.ys))

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
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        self.setup()

        self.world_camera = arcade.camera.Camera2D()  # Камера для игрового мира

    def setup(self):
        print("setup")
        for x in range(-SCREEN_WIDTH, SCREEN_WIDTH * 2, 512):
            tile = arcade.Sprite("sprites/wall.png", scale=16)
            tile.center_x = x
            tile.center_y = 45
            self.walls.append(tile)

        for y in range(0, 5000, 250):
            slope = arcade.Sprite("sprites/wall.png", scale=16)
            slope.center_x = y
            slope.center_y = y / 1.8
            slope.angle = -30 #atan2(y, slope.center_x)
            self.walls.append(slope)

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
        pev.center_y += pev.ys * delta_time
        pev.center_x += pev.xs * delta_time

        pev.collisions = arcade.check_for_collision_with_list(pev, self.walls)#.sort(key=lambda c: c.angle)

        pev.is_airborne = len(pev.collisions) == 0

        if pev.collisions:
            for i, collision in enumerate(pev.collisions):
                if abs(collision.angle) > 0.1:
                    new_vel = calc_slope_collision(-collision.angle, pev.xs, pev.ys, delta_time)
                    pev.xs, pev.ys = new_vel[0], new_vel[1]

                    angle_rad = radians(collision.angle)

                    dx = pev.center_x - collision.center_x
                    dy = pev.center_y - collision.center_y

                    rotated_x = dx * cos(-angle_rad) - dy * sin(-angle_rad)
                    rotated_y = dx * sin(-angle_rad) + dy * cos(-angle_rad)

                    half_height = collision.height / 2

                    while arcade.check_for_collision(pev, collision):
                        pev.center_y += 1  # Поднимаем на 1 пиксель
                        # Также можно двигать немного по X в зависимости от угла
                        if collision.angle > 0:  # Наклон вправо
                            pev.center_x -= 0
                        else:  # Наклон влево
                            pev.center_x += 0
                    pev.center_y -= 1

                    if rotated_y < -half_height:
                        pev.ys += 5
                        rotated_y = -half_height + pev.height / 2 + 5

                        new_dx = rotated_x * cos(angle_rad) - rotated_y * sin(angle_rad)
                        new_dy = rotated_x * sin(angle_rad) + rotated_y * cos(angle_rad)

                        pev.center_x = collision.center_x + new_dx
                        pev.center_y = collision.center_y + new_dy
                    try:
                        if pev.collisions[i + 1].angle > 0.1: break
                    except IndexError:
                        break
                else:
                    pev.ys = 0 if len(pev.collisions) == 0 else max(pev.ys, 0)
                    pev.xs *= 0.95
        else:
            pev.ys -= GRAVITY * delta_time * 60

            if pev.ys < -800:
                pev.ys = -800

        # ============ CONTROLS ============
        move_speed = 1000
        air_control = 0

        if arcade.key.LEFT in self.keys_pressed:
            pev.face_direction = -1
            if not pev.is_airborne:
                pev.xs -= move_speed * delta_time
            else:
                pev.xs -= move_speed * delta_time * air_control

        if arcade.key.RIGHT in self.keys_pressed:
            pev.face_direction = 1
            if not pev.is_airborne:
                pev.xs += move_speed * delta_time
            else:
                pev.xs += move_speed * delta_time * air_control

        if arcade.key.UP in self.keys_pressed and not pev.is_airborne:
            # Jump
            pev.ys = 400
            pev.is_airborne = True

        if arcade.key.DOWN in self.keys_pressed and not pev.is_airborne:
            # surf boost
            boost_power = 2200
            pev.xs += boost_power * pev.face_direction * delta_time

        max_speed = 2000
        current_speed = sqrt(pev.xs ** 2 + pev.ys ** 2)
        if current_speed > max_speed and not pev.is_airborne:
            scale = max_speed / current_speed
            pev.xs *= scale
            pev.ys *= scale

        pev.update_animation(delta_time)

        # CAMERA
        position = (
            pev.center_x + pev.xs * 0.3,
            pev.center_y + pev.ys * 0.1
        )
        self.world_camera.position = arcade.math.lerp_2d(
            self.world_camera.position,
            position,
            pev.lerp,
        )

    def on_key_press(self, key, modifiers):
        self.keys_pressed.add(key)

    def on_key_release(self, key, modifiers):
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)


if __name__ == "__main__":
    app = DamageBoost()
    app.run()