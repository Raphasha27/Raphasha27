extends Node2D

const CELL_SIZE := 32
const GRID_SIZE := 20

enum { STATE_PLAYING, STATE_GAME_OVER }

var grid: Array
var state: int = STATE_PLAYING
var score: int = 0

@onready var snake: Snake = $Snake
@onready var food: Food = $Food
@onready var hud: HUD = $HUD
@onready var game_over_label: Label = $GameOverLabel


func _ready() -> void:
	randomize()
	init_grid()
	snake.init(self)
	food.init(self)
	food.spawn()
	hud.update_score(score)


func init_grid() -> void:
	grid.clear()
	for x in GRID_SIZE:
		grid.append([])
		for y in GRID_SIZE:
			grid[x].append(0)


func _process(_delta: float) -> void:
	if state == STATE_GAME_OVER and Input.is_action_just_pressed("ui_accept"):
		reset_game()


func reset_game() -> void:
	state = STATE_PLAYING
	score = 0
	game_over_label.hide()
	init_grid()
	snake.reset()
	food.spawn()
	hud.update_score(score)


func game_over() -> void:
	state = STATE_GAME_OVER
	game_over_label.show()


func add_score(points: int) -> void:
	score += points
	hud.update_score(score)


func is_cell_free(x: int, y: int) -> bool:
	return grid[x][y] == 0


func occupy_cell(x: int, y: int) -> void:
	grid[x][y] = 1


func free_cell(x: int, y: int) -> void:
	grid[x][y] = 0
