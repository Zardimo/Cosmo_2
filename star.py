import os
import time
import curses
import asyncio
import random
from curses_tools import draw_frame, read_controls, get_frame_size
from physics import update_speed
from obstacles import Obstacle, show_obstacles, has_collision
from explosion import explode
from game_scenario import PHRASES, get_garbage_delay_tics


coroutines = []
spaceship_frame = ' '
obstacles = []
obstacles_in_last_collisions = []
year = 1957


class GameOver(Exception):
    def __init__(self):
        super().__init__()
        pass


async def count_years():
    global year
    while True:
        year += 1
        await sleep(15)


async def output_event(sub_canvas, row_length, column_length):
    global year
    coroutines.append(count_years())
    while True:
        if year in PHRASES:
            cosmo_year = f'Year {year}: {PHRASES[year]}'
        column_center = int(column_length/2 - len(cosmo_year)/2)
        sub_canvas.refresh()
        draw_frame(sub_canvas, 1, column_center, cosmo_year)
        await sleep(1)
        draw_frame(sub_canvas, 1, column_center, cosmo_year, negative=True)


async def show_gameover(canvas, row_center, column_center):
    game_over_frame = get_frame('./rocket_animation/game_over.txt')
    frame_row, frame_column = get_frame_size(game_over_frame)
    row_center = row_center - frame_row/2
    column_center = column_center - frame_column/2
    for _ in range(50):
        draw_frame(canvas, row_center, column_center, game_over_frame)
        await asyncio.sleep(0)
        draw_frame(canvas, row_center, column_center,
             game_over_frame, negative=True)
    raise GameOver()


async def fire(canvas, start_row, start_column, rows_speed=-0.3, columns_speed=0):
    """Display animation of gun shot. Direction and speed can be specified."""
    global obstacles
    global obstacles_in_last_collisions
    
    row, column = start_row, start_column

    canvas.addstr(round(row), round(column), '*')
    await asyncio.sleep(0)

    canvas.addstr(round(row), round(column), 'O')
    await asyncio.sleep(0)
    canvas.addstr(round(row), round(column), ' ')

    row += rows_speed
    column += columns_speed

    symbol = '-' if columns_speed else '|'

    rows, columns = canvas.getmaxyx()
    max_row, max_column = rows - 1, columns - 1

    curses.beep()
    while 0 < row < max_row and 0 < column < max_column:
        for obstacle in obstacles:
            if obstacle.has_collision(row, column):
                obstacles_in_last_collisions.append(obstacle)
                return None
        canvas.addstr(round(row), round(column), symbol)
        await asyncio.sleep(0)
        canvas.addstr(round(row), round(column), ' ')
        row += rows_speed
        column += columns_speed


async def fly_garbage(canvas, column, garbage_frame, speed=0.5):
    """Animate garbage, flying from top to bottom. Сolumn position will stay same, as specified on start."""
    global obstacles

    rows_number, columns_number = canvas.getmaxyx()

    column = max(column, 0)
    column = min(column, columns_number - 1)

    row = 0

    frame_row, frame_column = get_frame_size(garbage_frame)
    center_column = column + frame_column/2
    obstacle = Obstacle(row, column, frame_row, frame_column, 
        uid=f'garbage_{row}')
    obstacles.append(obstacle)
    while row < rows_number:
        if obstacle in obstacles_in_last_collisions:
            center_row = row + frame_row/2
            obstacles.remove(obstacle)
            coroutines.append(explode(canvas, center_row, center_column))
            obstacles_in_last_collisions.remove(obstacle)
            return None
        draw_frame(canvas, row, column, garbage_frame)
        obstacle.row = row
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, garbage_frame, negative=True)
        row += speed


def get_frame(frame_path):
    with open (frame_path, 'r') as frame:
        return frame.read()


async def blink(canvas, row, column, symbol):
    curses.curs_set(False)
    canvas.border()

    while True:
        canvas.addstr(row, column, symbol, curses.A_DIM)
        await sleep(7)

        canvas.addstr(row, column, symbol)
        await sleep(1)

        canvas.addstr(row, column, symbol, curses.A_BOLD)
        await sleep(5)

        canvas.addstr(row, column, symbol)
        await sleep(3)


async def fill_orbit_with_garbage(canvas, column_length, garbages):
    global obstacles
    global year
    edge = 1
    while True:
        timer = get_garbage_delay_tics(year)
        random_garbage = random.choice(garbages)
        right_border = get_frame_size(random_garbage)[1]
        garbage_column = random.randint(edge, column_length-right_border-edge)
        coroutines.append(fly_garbage(canvas, garbage_column, random_garbage))
        await sleep(timer)   


async def sleep(tics=1):
    for tic in range(tics):
        await asyncio.sleep(0)


def limit_frame_position(spaceship_coordinate, frame, side_length):
    if spaceship_coordinate+frame+1 > side_length:
        spaceship_coordinate = side_length-frame-1
    elif spaceship_coordinate < 1:
        spaceship_coordinate = 1
    return spaceship_coordinate


async def run_spaceship(canvas, row_length, column_length, both_edge):
    global spaceship_frame
    global obstacles

    row_speed = column_speed = 0
    row = row_center = row_length/2      #center_row_for_rocket
    column = column_center = column_length/2    #center_column_for_rocket
    frame_row, frame_column = get_frame_size(spaceship_frame)
    while True:
        for obstacle in obstacles:
            if obstacle.has_collision(row, column, frame_row, frame_column):
                coroutines.append(show_gameover(canvas, row_center,
                     column_center))
                return None
        row_drection, column_direction, space_direction = read_controls(canvas)
        row_speed, column_speed = update_speed(row_speed, column_speed,
             row_drection, column_direction)

        if space_direction and year > 2020:
            coroutines.append(fire(canvas, row, column+2))

        row += row_speed
        row = limit_frame_position(row, frame_row, row_length)

        column += column_speed
        column = limit_frame_position(column, frame_column, column_length)
        draw_frame(canvas, row, column, spaceship_frame)
        last_spaceship_frame_frame = spaceship_frame
        await asyncio.sleep(0)
        draw_frame(canvas, row, column, last_spaceship_frame_frame, negative=True)


async def animate_spaceship():
    global spaceship_frame
    rocket_frame_1 = get_frame('./rocket_animation/rocket_frame_1.txt')
    rocket_frame_2 = get_frame('./rocket_animation/rocket_frame_2.txt')
    frames = [rocket_frame_1, rocket_frame_2]
    while True:
        for frame in frames:
            spaceship_frame = frame
            await asyncio.sleep(0)


def main(canvas):
    all_garbage = os.listdir('./frames_garbages')
    garbages = []
    for garbage in all_garbage:
        garbage_path = os.path.join(f'./frames_garbages/{garbage}')
        garbages.append(get_frame(garbage_path))
    coroutines_garbages = []
    row_length, column_length = canvas.getmaxyx()
    symbols = '+*.:'
    edge = 1
    both_edge = 2
    sub_canvas_columns = column_length - both_edge*2
    sub_canvas_rows = 3
    sub_canvas_start_row = row_length - 5
    sub_canvas_start_column = both_edge + 1
    sub_canvas = canvas.derwin(sub_canvas_rows,
                               sub_canvas_columns,
                               sub_canvas_start_row,
                               sub_canvas_start_column)
    coroutines.append(animate_spaceship())
    coroutines.append(run_spaceship(canvas, row_length,
                                         column_length, both_edge))
    coroutines.append(output_event(sub_canvas, row_length, column_length))
    garbage_column = random.randint(edge, column_length-both_edge)
    garbage_column = random.randint(edge, column_length-both_edge)
    coroutines.append(fill_orbit_with_garbage(canvas, column_length, garbages))
    canvas.nodelay(1)
    for _ in range(100):
        random_row = random.randint(edge, row_length-both_edge)
        random_column = random.randint(edge, column_length-both_edge)
        random_symbol = random.choice(symbols)
        coroutines.append(blink(canvas, random_row,
                                 random_column, random_symbol))
    while coroutines:
        for coroutine in coroutines.copy():
            try:
                coroutine.send(None)
                canvas.border()
            except StopIteration:
                coroutines.remove(coroutine)
            except GameOver:
                return
        sub_canvas.refresh()
        canvas.refresh()
        time.sleep(0.1)


if __name__=='__main__':
    curses.update_lines_cols()
    curses.wrapper(main)