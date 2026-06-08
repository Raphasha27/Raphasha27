extends Node2D

var grid_x: int
var grid_y: int

var game: Node2D


func init(g: Node2D) -> void:
	game = g


func spawn() -> void:
	var free_cells: Array[Vector2] = []
	for x in game.GRID_SIZE:
		for y in game.GRID_SIZE:
			if game.is_cell_free(x, y):
				free_cells.append(Vector2(x, y))

	if free_cells.is_empty():
		return

	var pos := free_cells[randi() % free_cells.size()]
	grid_x = int(pos.x)
	grid_y = int(pos.y)
	position = pos * game.CELL_SIZE
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ONE, Vector2(31, 31)), Color(0.9, 0.15, 0.15))
