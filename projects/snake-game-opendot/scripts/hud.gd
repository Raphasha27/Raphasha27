extends CanvasLayer

@onready var score_label: Label = $ScoreLabel
@onready var info_label: Label = $InfoLabel


func update_score(score: int, high_score: int, diff_name: String) -> void:
	score_label.text = "Score: " + str(score)
	info_label.text = "Best: " + str(high_score) + "  |  " + diff_name + "  |  1-2-3: Difficulty"
