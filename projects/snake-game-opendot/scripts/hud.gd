extends CanvasLayer

@onready var score_label: Label = $ScoreLabel


func update_score(s: int) -> void:
	score_label.text = "Score: " + str(s)
