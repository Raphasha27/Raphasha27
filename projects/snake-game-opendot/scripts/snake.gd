extends Node2D

enum { UP, DOWN, LEFT, RIGHT }

const MOVE_INTERVAL := 0.15
const SEGMENT_SIZE := 31

var direction: int = RIGHT
var next_direction: int = RIGHT
var segments: Array
var moving: bool = false

@onready var move_timer: Timer = $MoveTimer

var game: Node2D


func init(g: Node2D) -> void:
	game = g
	reset()


func reset() -> void:
	direction = RIGHT
	next_direction = RIGHT
	moving = false
	segments = []

	segments.append(Vector2(9, 10))
	segments.append(Vector2(8, 10))

	for s in segments:
		game.occupy_cell(s.x, s.y)

	move_timer.start(MOVE_INTERVAL)
	moving = true
	queue_redraw()


func _unhandled_input(event: InputEvent) -> void:
	if not moving:
		return

	if event.is_action_pressed("ui_up") and direction != DOWN:
		next_direction = UP
	elif event.is_action_pressed("ui_down") and direction != UP:
		next_direction = DOWN
	elif event.is_action_pressed("ui_left") and direction != RIGHT:
		next_direction = LEFT
	elif event.is_action_pressed("ui_right") and direction != LEFT:
		next_direction = RIGHT


func _on_move_timer_timeout() -> void:
	if game.state != game.STATE_PLAYING:
		return

	direction = next_direction
	var head := segments[0] as Vector2
	var new_x := head.x
	var new_y := head.y

	match direction:
		UP:    new_y -= 1
		DOWN:  new_y += 1
		LEFT:  new_x -= 1
		RIGHT: new_x += 1

	if new_x < 0 or new_x >= game.GRID_SIZE or new_y < 0 or new_y >= game.GRID_SIZE:
		game.game_over()
		return

	if not game.is_cell_free(new_x, new_y):
		game.game_over()
		return

	var tail := segments.pop_back() as Vector2
	game.free_cell(tail.x, tail.y)

	segments.push_front(Vector2(new_x, new_y))
	game.occupy_cell(new_x, new_y)

	if new_x == game.food.grid_x and new_y == game.food.grid_y:
		grow()
		game.add_score(10)
		game.food.spawn()

	queue_redraw()


func grow() -> void:
	var tail := segments[-1] as Vector2
	segments.append(tail)
	game.occupy_cell(tail.x, tail.y)


func _draw() -> void:
	for i in segments.size():
		var pos := segments[i] as Vector2
		var color := Color(0.1, 0.7, 0.1) if i == 0 else Color(0.05, 0.5, 0.05)
		var rect := Rect2(pos * game.CELL_SIZE + Vector2.ONE, Vector2(SEGMENT_SIZE, SEGMENT_SIZE))
		draw_rect(rect, color)
