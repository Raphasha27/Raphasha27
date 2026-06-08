extends Node2D

const CELL_SIZE := 32
const GRID_SIZE := 20

enum { STATE_PLAYING, STATE_GAME_OVER }
enum { DIFF_EASY, DIFF_MEDIUM, DIFF_HARD }

const DIFF_NAMES := ["Easy", "Medium", "Hard"]
const DIFF_SPEEDS := [0.2, 0.13, 0.08]

var grid: Array
var state: int = STATE_PLAYING
var score: int = 0
var difficulty: int = DIFF_MEDIUM
var high_scores: Dictionary = { 0: 0, 1: 0, 2: 0 }

@onready var snake: Snake = $Snake
@onready var food: Food = $Food
@onready var hud: HUD = $HUD
@onready var game_over_label: Label = $GameOverLabel


func _ready() -> void:
	randomize()
	load_high_scores()
	init_grid()
	snake.init(self)
	food.init(self)
	food.spawn()
	update_hud()


func init_grid() -> void:
	grid.clear()
	for x in GRID_SIZE:
		grid.append([])
		for y in GRID_SIZE:
			grid[x].append(0)


func _process(_delta: float) -> void:
	if state == STATE_GAME_OVER and Input.is_action_just_pressed("ui_accept"):
		reset_game()

	if Input.is_key_pressed(KEY_1):
		set_difficulty(DIFF_EASY)
	elif Input.is_key_pressed(KEY_2):
		set_difficulty(DIFF_MEDIUM)
	elif Input.is_key_pressed(KEY_3):
		set_difficulty(DIFF_HARD)


func set_difficulty(d: int) -> void:
	difficulty = d
	snake.set_speed(DIFF_SPEEDS[d])
	update_hud()


func load_high_scores() -> void:
	var config := ConfigFile.new()
	var err := config.load("user://high_scores.cfg")
	if err == OK:
		for d in [DIFF_EASY, DIFF_MEDIUM, DIFF_HARD]:
			high_scores[d] = config.get_value("scores", DIFF_NAMES[d], 0)


func save_high_scores() -> void:
	var config := ConfigFile.new()
	for d in [DIFF_EASY, DIFF_MEDIUM, DIFF_HARD]:
		config.set_value("scores", DIFF_NAMES[d], high_scores[d])
	config.save("user://high_scores.cfg")


func reset_game() -> void:
	state = STATE_PLAYING
	score = 0
	game_over_label.hide()
	init_grid()
	snake.reset()
	snake.set_speed(DIFF_SPEEDS[difficulty])
	food.spawn()
	update_hud()


func game_over() -> void:
	state = STATE_GAME_OVER
	if score > high_scores[difficulty]:
		high_scores[difficulty] = score
		save_high_scores()
	game_over_label.text = "GAME OVER\nScore: " + str(score) + "\nBest: " + str(high_scores[difficulty]) + "\n\nPress Enter to Restart"
	game_over_label.show()


func add_score(points: int) -> void:
	score += points
	update_hud()


func update_hud() -> void:
	hud.update_score(score, high_scores[difficulty], DIFF_NAMES[difficulty])


func is_cell_free(x: int, y: int) -> bool:
	return grid[x][y] == 0


func occupy_cell(x: int, y: int) -> void:
	grid[x][y] = 1


func free_cell(x: int, y: int) -> void:
	grid[x][y] = 0
