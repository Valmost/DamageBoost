from email.iterators import typed_subpart_iterator

import arcade
from arcade import gui
from math import *
import numpy as np
import random
import os
from pyglet.graphics import Batch
from numpy.random.mtrand import Sequence
from datetime import datetime


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

        slope_dir = np.array([cos(angle_rad), sin(angle_rad)])

        normal = np.array([-sin(angle_rad), cos(angle_rad)])

        slope_dir = slope_dir / np.linalg.norm(slope_dir)
        normal = normal / np.linalg.norm(normal)

        velocity = np.array([xs, ys])

        normal_speed = np.dot(velocity, normal)

        if normal_speed < 0:
            velocity = velocity - normal_speed * normal

            gravity = np.array([0, -GRAVITY])
            gravity_normal = np.dot(gravity, normal) * normal
            gravity_along_slope = gravity - gravity_normal

            velocity += gravity_along_slope * delta_time * 60  # Ускорение

        rad_velocity = normalize(np.linalg.norm(velocity), 0, 2000, 0, radians(90))
        if rad_velocity < angle_rad + 0.5:
            velocity *= 0.9
        else:
            velocity *= 1
            pev.is_airborne = True

        return velocity

    except Exception as e:
        print("Slope collision error:", e)
        return np.array([xs, ys])


SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "Damage Boost"
GRAVITY = 12

MIN_WIND_SPEED = 450.0 
MAX_WIND_SPEED = 2000.0  
WIND_VOLUME_RANGE = (0.1, 0.8)
WIND_PITCH_RANGE = (0.8, 1.5) 

ENGINE_MIN_SPEED = 50.0
ENGINE_VOLUME_RANGE = (0.1, 0.6)
ENGINE_PITCH_RANGE = (0.7, 1.3)

BRAKE_THRESHOLD = 100.0 
BRAKE_MIN_DURATION = 0.3 


class DustParticle(arcade.SpriteCircle):
    def __init__(self, x, y, color=(200, 200, 200, 150)):
        radius = random.randint(1, 3)
        super().__init__(radius=radius, color=color)
        self.center_x = x
        self.center_y = y
        self.lifetime = 0.4
        self.timer = 0.0
        self.change_x = random.uniform(-20, 20)
        self.change_y = random.uniform(5, 15)
        self.alpha = 150

    def update(self, delta_time):
        self.timer += delta_time
        self.center_x += self.change_x * delta_time
        self.center_y += self.change_y * delta_time
        self.change_x *= 0.95
        self.change_y *= 0.9
        self.alpha = int(150 * (1 - self.timer / self.lifetime))
        return self.timer < self.lifetime and self.alpha > 0


class Arme(arcade.Sprite):
    def __init__(self):
        super().__init__()
        self.scale = 4.0
        self.speed = 30
        self.health = 100

        self.dust_particles = arcade.SpriteList()
        self.dust_timer = 0.0
        self.last_ground_x = self.center_x 

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

        self.speed = 0.0  
        self.prev_speed = 0.0  
        self.wind_sound_player = None
        self.engine_sound_player = None
        self.brake_sound_player = None
        self.brake_sound_timer = 0.0
        self.load_sounds()

    def load_sounds(self):
        try:
            if os.path.exists("sound/169913__mydo1__skydive.wav"):
                self.wind_sound = arcade.load_sound("sound/169913__mydo1__skydive.wav")
            else:
                print("Wind sound file not found!")
                self.wind_sound = None

            if os.path.exists("sound/242740__marlonhj__engine.wav"):
                self.engine_sound = arcade.load_sound("sound/242740__marlonhj__engine.wav")
            else:
                print("Engine sound file not found!")
                self.engine_sound = None

            if os.path.exists("sound/536769__egomassive__tire.ogg"):
                self.brake_sound = arcade.load_sound("sound/536769__egomassive__tire.ogg")
            else:
                print("Brake sound file not found!")
                self.brake_sound = None

        except Exception as e:
            print(f"Error loading sounds: {e}")
            self.wind_sound = None
            self.engine_sound = None
            self.brake_sound = None

    def update(self, delta_time):
        self.center_y += self.ys * delta_time
        self.center_x += self.xs * delta_time

        self.prev_speed = self.speed
        self.speed = sqrt(self.xs ** 2 + self.ys ** 2)

        self.update_sounds(delta_time)

    def update_sounds(self, delta_time):
        if self.brake_sound_timer > 0:
            self.brake_sound_timer -= delta_time
            if self.brake_sound_timer <= 0 and self.brake_sound_player:
                self.brake_sound_player.pause()

        if not self.is_airborne or self.speed < MIN_WIND_SPEED:
            if self.wind_sound_player and self.wind_sound_player.playing:
                self.wind_sound_player.pause()
        else:
            wind_intensity = normalize(self.speed, MIN_WIND_SPEED, MAX_WIND_SPEED, 0.0, 1.0)
            wind_intensity = max(0.0, min(1.0, wind_intensity))  # Ограничиваем 0-1

            volume = normalize(wind_intensity, 0.0, 1.0, WIND_VOLUME_RANGE[0], WIND_VOLUME_RANGE[1])
            pitch = normalize(wind_intensity, 0.0, 1.0, WIND_PITCH_RANGE[0], WIND_PITCH_RANGE[1])

            if self.wind_sound and not self.is_airborne:
                if not self.wind_sound_player or not self.wind_sound_player.playing:
                    self.wind_sound_player = self.wind_sound.play(
                        volume=volume,
                        loop=True
                    )
                else:
                    self.wind_sound_player.volume = volume
                    self.wind_sound_player.pitch = pitch

        if self.is_airborne or not self.engine_sound:
            pass
        else:
            engine_intensity = normalize(abs(self.xs), ENGINE_MIN_SPEED, MAX_WIND_SPEED, 0.0, 1.0)
            engine_intensity = max(0.0, min(1.0, engine_intensity))

            volume = normalize(engine_intensity, 0.0, 1.0, ENGINE_VOLUME_RANGE[0], ENGINE_VOLUME_RANGE[1])
            pitch = normalize(engine_intensity, 0.0, 1.0, ENGINE_PITCH_RANGE[0], ENGINE_PITCH_RANGE[1])

            if not self.engine_sound_player or not self.engine_sound_player.playing:
                self.engine_sound_player = self.engine_sound.play(
                    volume=volume,
                    #pitch=pitch,
                    loop=True
                )
            else:
                self.engine_sound_player.volume = volume
                self.engine_sound_player.pitch = pitch

        if self.brake_sound:
            speed_drop = self.prev_speed - self.speed

            if speed_drop > BRAKE_THRESHOLD and self.speed > 100:
                if self.brake_sound_player and self.brake_sound_player.playing:
                    self.brake_sound_player.pause()

                brake_intensity = normalize(speed_drop, BRAKE_THRESHOLD, 1000.0, 0.3, 1.0)
                brake_intensity = max(0.3, min(1.0, brake_intensity))

                self.brake_sound_player = self.brake_sound.play(
                    volume=brake_intensity * 0.7,  # Немного тише
                )
                self.brake_sound_timer = BRAKE_MIN_DURATION

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
        print('Position:', self.center_x, self.center_y)
        print('Speed:', self.speed)
        print('Collisions:', self.collisions)
        print('Airborne:', self.is_airborne)
        if pev.collisions:
            print('Sent:', -pev.collisions[0].angle, pev.xs, pev.ys)
            print('Received:', *calc_slope_collision(-pev.collisions[0].angle, pev.xs, pev.ys))

    def on_close(self):
        if self.wind_sound_player and self.wind_sound_player.playing:
            self.wind_sound_player.pause()
        if self.engine_sound_player and self.engine_sound_player.playing:
            self.engine_sound_player.pause()
        if self.brake_sound_player and self.brake_sound_player.playing:
            self.brake_sound_player.pause()

        arcade.unschedule(self.debug)
        super().on_close()


pev = Arme()

import arcade
from math import *
import numpy as np
import random
import os



class MainMenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        self.background_color = arcade.color.BLACK

        self.v_box = arcade.gui.UIBoxLayout()

        title_label = arcade.gui.UILabel(
            text="DAMAGE BOOST",
            font_size=48,
            font_name="Kenney Future",
            text_color=arcade.color.WHITE
        )
        self.v_box.add(title_label)

        level1_button = arcade.gui.UIFlatButton(
            text="Уровень 1: Обучение",
            width=300,
            height=50
        )
        level1_button.on_click = self.on_level1_click
        self.v_box.add(level1_button)

        level2_button = arcade.gui.UIFlatButton(
            text="Уровень 2: Склоны",
            width=300,
            height=50
        )
        level2_button.on_click = self.on_level2_click
        self.v_box.add(level2_button)

        level3_button = arcade.gui.UIFlatButton(
            text="Уровень 3: Экстрим",
            width=300,
            height=50
        )
        level3_button.on_click = self.on_level3_click
        self.v_box.add(level3_button)

        exit_button = arcade.gui.UIFlatButton(
            text="Выход",
            width=200,
            height=40
        )
        exit_button.on_click = self.on_exit_click
        self.v_box.add(exit_button)

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(
            anchor_x="center_x",
            anchor_y="center_y",
            child=self.v_box
        )
        self.manager.add(anchor)

        self.selected_level = None

        self.menu_music = None
        if os.path.exists("sound/menu_music.wav"):
            self.menu_music = arcade.load_sound("sound/menu_music.wav")
            self.music_player = None

    def on_show_view(self):
        self.manager.enable()

        if self.menu_music and (not self.music_player or not self.music_player.playing):
            self.music_player = self.menu_music.play(loop=True, volume=0.3)

    def on_hide_view(self):
        """Вызывается при скрытии меню"""
        self.manager.disable()

    def on_draw(self):
        """Отрисовка меню"""
        self.clear()



        arcade.draw_text(
            "Выберите уровень",
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 100,
            arcade.color.LIGHT_GRAY,
            font_size=24,
            anchor_x="center",
            font_name="Kenney Future"
        )

        arcade.draw_text(
            "ESC - Вернуться в меню",
            SCREEN_WIDTH // 2,
            30,
            arcade.color.GRAY,
            font_size=14,
            anchor_x="center"
        )

        self.manager.draw()

    def on_level1_click(self, event):
        """Запуск уровня 1"""
        print("Запуск уровня 1")
        self.selected_level = 1
        self.start_game()

    def on_level2_click(self, event):
        """Запуск уровня 2"""
        print("Запуск уровня 2")
        self.selected_level = 2
        self.start_game()

    def on_level3_click(self, event):
        """Запуск уровня 3"""
        print("Запуск уровня 3")
        self.selected_level = 3
        self.start_game()

    def on_exit_click(self, event):
        """Выход из игры"""
        print("Выход из игры")
        arcade.close_window()

    def start_game(self):
        """Запуск игры с выбранным уровнем"""
        if self.selected_level:
            game_view = GameView(level=self.selected_level)
            self.window.show_view(game_view)

    def on_key_press(self, key, modifiers):
        """Обработка нажатий клавиш в меню"""
        if key == arcade.key.ESCAPE:
            # В меню ESC ничего не делает
            pass
        elif key == arcade.key.ENTER:
            self.selected_level = 1
            self.start_game()


class GameView(arcade.View):
    """Игровой экран с физикой"""

    def __init__(self, level=1):
        super().__init__()
        self.level = level

        # Создаем и настраиваем окно игры
        self.pev = Arme()
        self.pev_list = arcade.SpriteList()
        self.pev_list.append(self.pev)
        self.keys_pressed = set()
        self.time = 0
        self.hp = 100
        self.im = False
        self.world_len = 32000
        self.walls = arcade.SpriteList(use_spatial_hash=True)
        self.spikes = arcade.SpriteList()
        self.game_over = False  # Флаг завершения игры
        self.win = False  # Победа или поражение
        self.end_time = 0.0  # Время завершения

        self.end_manager = arcade.gui.UIManager()
        self.setup_end_screen()

        self.engine = arcade.PhysicsEnginePlatformer(
            player_sprite=self.pev,
            gravity_constant=0,
            walls=self.walls
        )


        self.world_camera = arcade.camera.Camera2D()
        self.gui_camera = arcade.camera.Camera2D()

        self.batch = Batch()

        self.setup_level()


        self.is_paused = False


        self.pause_manager = arcade.gui.UIManager()
        self.pause_manager.enable()
        self.setup_pause_menu()

    def setup_end_screen(self):
        self.end_manager.enable()

        end_v_box = arcade.gui.UIBoxLayout()

        self.end_title = arcade.gui.UILabel(
            text="",
            font_size=48,
            font_name="Kenney Future",
            text_color=arcade.color.WHITE
        )
        end_v_box.add(self.end_title)

        self.end_stats = arcade.gui.UILabel(
            text="",
            font_size=24,
            text_color=arcade.color.LIGHT_GRAY
        )
        end_v_box.add(self.end_stats)

        restart_button = arcade.gui.UIFlatButton(
            text="Играть снова",
            width=250,
            height=45
        )
        restart_button.on_click = self.on_restart_click
        end_v_box.add(restart_button)

        menu_button = arcade.gui.UIFlatButton(
            text="В главное меню",
            width=250,
            height=45
        )
        menu_button.on_click = self.on_end_menu_click
        end_v_box.add(menu_button)

        end_layout = arcade.gui.UIAnchorLayout()
        end_layout.add(
            anchor_x="center_x",
            anchor_y="center_y",
            child=end_v_box
        )

        self.end_manager.add(end_layout)
        self.end_manager.disable()

    def on_restart_click(self, event):
        """Перезапуск текущего уровня"""
        self.game_over = False
        self.win = False
        self.hp = 100
        self.time = 0.0
        self.end_manager.disable()

        self.setup_level()

    def on_end_menu_click(self, event):
        """Возврат в главное меню"""
        menu_view = MainMenuView()
        self.window.show_view(menu_view)

    def end_game(self, win):
        """Завершение игры (победа/поражение)"""
        self.game_over = True
        self.win = win
        self.end_time = self.time

        if win:
            self.end_title.text = "УРОВЕНЬ ПРОЙДЕН!"
            self.end_title.text_color = arcade.color.GOLD
        else:
            self.end_title.text = "ПОРАЖЕНИЕ"
            self.end_title.text_color = arcade.color.RED

        minutes = int(self.end_time // 60)
        seconds = int(self.end_time % 60)
        milliseconds = int((self.end_time % 1) * 1000)

        time_str = f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

        if win:
            self.end_stats.text = (
                f"Уровень: {self.level} \n"
                f"Время: {time_str} \n"
                f"Здоровье: {self.hp}/100"
            )
            with open('stats/stats.txt', 'a', encoding='UTF-8') as file:
                file.write(f"{datetime.now()}\nУровень: {self.level} "
                    f"\nВремя: {time_str}\nЗдоровье: {self.hp}/100\n\n\n")
        else:
            self.end_stats.text = (
                f"Уровень: {self.level} \n"
                f"Время: {time_str}\n "
                f"Причина: здоровье закончилось"
            )
            with open('stats/stats.txt', 'a', encoding='UTF-8') as file:
                file.write(f"{datetime.now()}\nУровень: {self.level} \nВремя: {time_str}"
                           f"\nПричина: здоровье закончилось\n\n\n")

        self.end_manager.enable()

        # Останавливаем игровые звуки
        if hasattr(self.pev, 'wind_sound_player') and self.pev.wind_sound_player:
            self.pev.wind_sound_player.pause()
        if hasattr(self.pev, 'engine_sound_player') and self.pev.engine_sound_player:
            self.pev.engine_sound_player.pause()

    def setup_level(self):
        self.pev.center_x = 400
        self.pev.center_y = 500
        self.pev.xs = 0
        self.pev.ys = -200
        self.time = 0
        self.hp = 100
        self.walls.clear()

        if self.level == 3:
            self.world_len = 16000
            n = 14
            grid1 = np.random.rand(n) * 2 - 1
            nodes_list = [gp(0, grid1) * 100]
            tile_len = 64
            for i in range(64, self.world_len // 2, tile_len):
                tile = arcade.Sprite('sprites/wall.png', scale=1)
                tile.center_x = i
                nodes_list.append(gp(i / self.world_len * n, grid1) * 500)
                y = nodes_list[-1] - nodes_list[-2]
                tile.scale = hypot(y, tile_len) / tile_len * 2
                tile.center_y = y / 2 + nodes_list[-2]
                tile.angle = -degrees(atan2(y, tile_len))
                print(tile.center_x, tile.center_y)
                self.walls.append(tile)

            for _ in range(10):
                tile = arcade.Sprite('sprites/spikes.png', scale=0.2)
                i = random.randrange(0, self.world_len // 2)
                tile.center_x = i
                y = gp(i / self.world_len * n, grid1) * 500
                tile.center_y = y + 25
                dy = gp((i + tile_len) / self.world_len * n, grid1) - y
                tile.angle = -degrees(atan2(dy, tile_len))
                self.spikes.append(tile)

        elif self.level == 2:
            self.world_len = 32000
            n = 14
            grid1 = np.random.rand(n) * 2 - 1
            nodes_list = [gp(0, grid1) * 100]
            tile_len = 64
            for i in range(64, self.world_len // 2, tile_len):
                tile = arcade.Sprite('sprites/wall.png', scale=1)
                tile.center_x = i
                nodes_list.append(gp(i / self.world_len * n, grid1) * 2000)
                y = nodes_list[-1] - nodes_list[-2]
                tile.scale = hypot(y, tile_len) / tile_len * 2
                tile.center_y = y / 2 + nodes_list[-2]
                tile.angle = -degrees(atan2(y, tile_len))
                print(tile.center_x, tile.center_y)
                self.walls.append(tile)

            for _ in range(5):
                tile = arcade.Sprite('sprites/spikes.png', scale=0.2)
                i = random.randrange(0, self.world_len // 4)
                tile.center_x = i
                y = gp(i / self.world_len * n, grid1) * 500
                tile.center_y = y
                dy = gp((i + tile_len) / self.world_len * n, grid1) - y
                tile.angle = -degrees(atan2(dy, tile_len))
                self.spikes.append(tile)

        elif self.level == 1:
            self.world_len = 16000
            n = 14
            grid1 = np.random.rand(n) * 2 - 1
            nodes_list = [gp(0, grid1) * 100]
            tile_len = 64
            for i in range(64, self.world_len // 2, tile_len):
                tile = arcade.Sprite('sprites/wall.png', scale=1)
                tile.center_x = i
                nodes_list.append(gp(i / self.world_len * n, grid1) * 500)
                y = nodes_list[-1] - nodes_list[-2]
                tile.scale = hypot(y, tile_len) / tile_len * 2
                tile.center_y = y / 2 + nodes_list[-2]
                tile.angle = -degrees(atan2(y, tile_len))
                print(tile.center_x, tile.center_y)
                self.walls.append(tile)

        self.engine.walls = self.walls

    def setup_pause_menu(self):
        """Настройка меню паузы"""
        self.pause_v_box = arcade.gui.UIBoxLayout()

        self.pause_widget = arcade.gui.UIAnchorLayout()
        self.pause_widget.add(
            anchor_x="center_x",
            anchor_y="center_y",
            child=self.pause_v_box
        )
        self.pause_manager.add(self.pause_widget)

        resume_button = arcade.gui.UIFlatButton(
            text="Продолжить",
            width=250,
            height=45
        )
        resume_button.on_click = self.on_resume_click
        self.pause_v_box.add(resume_button)

        menu_button = arcade.gui.UIFlatButton(
            text="В главное меню",
            width=250,
            height=45
        )
        menu_button.on_click = self.on_menu_click
        self.pause_v_box.add(menu_button)

        self.pause_widget = arcade.gui.UIAnchorLayout(
            anchor_x="center",
            anchor_y="center",
            child=self.pause_v_box
        )
        self.pause_manager.add(self.pause_widget)
        self.pause_manager.disable()

    def on_resume_click(self, event):
        """Продолжить игру"""
        self.is_paused = False
        self.pause_manager.disable()

    def on_menu_click(self, event):
        """Вернуться в главное меню"""
        self.is_paused = False
        menu_view = MainMenuView()
        self.window.show_view(menu_view)

    def on_show_view(self):
        """Вызывается при показе игрового экрана"""
        self.pause_manager.disable()

    def on_draw(self):
        """Отрисовка игрового экрана"""
        self.world_camera.use()
        self.clear()

        self.pev.dust_particles.draw()

        self.pev_list.draw(pixelated=True)
        self.spikes.draw(pixelated=True)
        self.walls.draw(pixelated=True)

        arcade.draw_text(
            f"Уровень {self.level}",
            pev.center_x - 350,
            pev.center_y + 200,
            arcade.color.LIGHT_GRAY,
            18
        )

        speed = sqrt(self.pev.xs ** 2 + self.pev.ys ** 2)
        arcade.draw_text(
            f"Скорость: {int(speed)} u/s",
            0,
            0,
            arcade.color.LIGHT_GRAY,
            16
        )

        self.gui_camera.use()
        self.batch.draw()

        if self.game_over: self.end_manager.draw()
        if self.is_paused: self.pause_manager.draw()

    def remove_im(self, arg):
        self.im = False

    def on_update(self, delta_time):
        """Обновление игровой логики"""
        if self.is_paused or self.game_over:
            return

        if self.hp <= 0:
            self.end_game(win=False)
            return

        if self.pev.center_x >= self.world_len // 2 or self.pev.center_y < -500:
            self.end_game(win=True)
            return

        self.pev.center_y += self.pev.ys * delta_time
        self.pev.center_x += self.pev.xs * delta_time

        self.pev.collisions = arcade.check_for_collision_with_list(self.pev, self.walls)

        if arcade.check_for_collision_with_list(self.pev, self.spikes) and not self.im:
            self.hp -= 20
            self.pev.center_y += 25
            self.pev.ys += 50
            self.im = True
            arcade.schedule(self.remove_im, 3.0)

        if not self.pev.is_airborne and abs(self.pev.xs) > 50:
            self.pev.dust_timer += delta_time
            if self.pev.dust_timer >= 0.05:
                self.pev.dust_timer = 0

                particle_count = min(int(abs(self.pev.xs) / 100), 5)

                for _ in range(particle_count):
                    offset_x = -10 if self.pev.face_direction == 1 else 10
                    dust = DustParticle(
                        x=self.pev.center_x + offset_x,
                        y=self.pev.bottom + 5,  # Чуть ниже ног
                        color=(
                            random.randint(150, 200),  # R
                            random.randint(150, 180),  # G
                            random.randint(100, 150),  # B
                            150  # Alpha
                        )
                    )
                    dust.change_x = random.uniform(-30, 30) + (self.pev.xs * 0.1)
                    dust.change_y = random.uniform(5, 25)
                    self.pev.dust_particles.append(dust)

        for particle in self.pev.dust_particles[:]:
            if not particle.update(delta_time):
                particle.remove_from_sprite_lists()

        self.pev.is_airborne = len(self.pev.collisions) == 0

        if self.pev.collisions:
            for i, collision in enumerate(self.pev.collisions):
                if abs(collision.angle) > 0.1:
                    new_vel = calc_slope_collision(-collision.angle, self.pev.xs, self.pev.ys, delta_time)
                    self.pev.xs, self.pev.ys = new_vel[0], new_vel[1]

                    angle_rad = radians(collision.angle)

                    dx = self.pev.center_x - collision.center_x
                    dy = self.pev.center_y - collision.center_y

                    rotated_x = dx * cos(-angle_rad) - dy * sin(-angle_rad)
                    rotated_y = dx * sin(-angle_rad) + dy * cos(-angle_rad)

                    half_height = collision.height / 2

                    while arcade.check_for_collision(self.pev, collision):
                        self.pev.center_y += 1
                        if collision.angle > 0:
                            self.pev.center_x -= 0
                        else:
                            self.pev.center_x += 0
                    self.pev.center_y -= 1

                    if rotated_y < -half_height:
                        self.pev.ys += 5
                        rotated_y = -half_height + self.pev.height / 2 + 5

                        new_dx = rotated_x * cos(angle_rad) - rotated_y * sin(angle_rad)
                        new_dy = rotated_x * sin(angle_rad) + rotated_y * cos(angle_rad)

                        self.pev.center_x = collision.center_x + new_dx
                        self.pev.center_y = collision.center_y + new_dy
                    try:
                        if self.pev.collisions[i + 1].angle > 0.1:
                            break
                    except IndexError:
                        break
                else:
                    self.pev.ys = 0 if len(self.pev.collisions) == 0 else max(self.pev.ys, 0)
                    self.pev.xs *= 0.95
        else:
            self.pev.ys -= GRAVITY * delta_time * 60

            if self.pev.ys < -800:
                self.pev.ys = -800

        # ============ CONTROLS ============
        move_speed = 1000
        air_control = 0

        if arcade.key.LEFT in self.keys_pressed:
            self.pev.face_direction = -1
            if not self.pev.is_airborne:
                self.pev.xs -= move_speed * delta_time
            else:
                self.pev.xs -= move_speed * delta_time * air_control

        if arcade.key.RIGHT in self.keys_pressed:
            self.pev.face_direction = 1
            if not self.pev.is_airborne:
                self.pev.xs += move_speed * delta_time
            else:
                self.pev.xs += move_speed * delta_time * air_control

        if arcade.key.UP in self.keys_pressed and not self.pev.is_airborne:
            self.pev.ys = 400
            self.pev.is_airborne = True

        if arcade.key.DOWN in self.keys_pressed and not self.pev.is_airborne:
            boost_power = 1000
            self.pev.xs += boost_power * self.pev.face_direction * delta_time

        max_speed = 2000
        current_speed = sqrt(self.pev.xs ** 2 + self.pev.ys ** 2)
        if current_speed > max_speed and not self.pev.is_airborne:
            scale = max_speed / current_speed
            self.pev.xs *= scale
            self.pev.ys *= scale

        self.pev.update_animation(delta_time)

        # CAMERA
        position = (
            self.pev.center_x + self.pev.xs * 0.3,
            self.pev.center_y + self.pev.ys * 0.1
        )
        self.world_camera.position = arcade.math.lerp_2d(
            self.world_camera.position,
            position,
            self.pev.lerp,
        )

        pev.update(delta_time)
        self.time += delta_time
        self.speed_text = arcade.Text(f"Speed {round(self.pev.xs)}", 0, 50,
                                      arcade.color.WHITE, font_size=25, anchor_x="left", batch=self.batch)
        self.time_text = arcade.Text(
            f"Time: {round(self.time)}", 0, 0,
            arcade.color.WHITE, font_size=14, anchor_x="left", batch=self.batch
        )
        self.time_text = arcade.Text(
            f"HP: {round(self.hp)}", 0, 100,
            arcade.color.WHITE, font_size=35, anchor_x="left", batch=self.batch
        )

    def on_key_press(self, key, modifiers):
        """Обработка нажатий клавиш"""
        self.keys_pressed.add(key)

        # ESC - пауза/меню
        if key == arcade.key.ESCAPE:
            self.is_paused = not self.is_paused
            if self.is_paused:
                self.pause_manager.enable()
            else:
                self.pause_manager.disable()

    def on_key_release(self, key, modifiers):
        """Обработка отпускания клавиш"""
        if key in self.keys_pressed:
            self.keys_pressed.remove(key)


class DamageBoost(arcade.Window):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color(arcade.color.BLACK)

        # Показываем главное меню при запуске
        menu_view = MainMenuView()
        self.show_view(menu_view)


if __name__ == "__main__":
    app = DamageBoost()
    app.run()
