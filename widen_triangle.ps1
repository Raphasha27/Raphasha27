$file = "c:\Users\rapha\OneDrive\Desktop\Raphasha27\Raphasha27\assets\bot_animated.svg"
$content = Get-Content $file -Raw

# Update triangle to be wider (longer on width)
# From: M 250 20 L 20 480 L 480 480 Z
# To a wider aspect:
$newSvg = $content -replace '<path d="M 250 20 L 20 480 L 480 480 Z" />', '<path d="M 250 50 L -150 450 L 650 450 Z" />'

# Revert speed to 6s (from 0.04s)
$newSvg = $newSvg -replace 'animation: flash1 0.04s infinite;', 'animation: flash1 6s infinite;'
$newSvg = $newSvg -replace 'animation: flash2 0.04s infinite;', 'animation: flash2 6s infinite;'

[IO.File]::WriteAllText($file, $newSvg)
