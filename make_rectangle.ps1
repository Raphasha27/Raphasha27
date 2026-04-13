$file = "c:\Users\rapha\OneDrive\Desktop\Raphasha27\Raphasha27\assets\bot_animated.svg"
$content = Get-Content $file -Raw

# Extract base64 strings
$regex = "data:image/jpeg;base64,[^`"]+"
$matches = [regex]::Matches($content, $regex)
$b1 = $matches[0].Value
$b2 = $matches[1].Value

# Create a new SVG that is rectangular (removing the triangle clip path)
# We use a 600x400 viewbox for a more "banner-like" or "landscape" rectangle
$newSvg = @"
<svg width="600" height="400" viewBox="0 0 500 333" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid slice">
  <style>
    .f1 { animation: flash1 6s infinite; }
    .f2 { animation: flash2 6s infinite; }
    @keyframes flash1 {
      0%, 45% { opacity: 1; }
      50%, 95% { opacity: 0; }
      100% { opacity: 1; }
    }
    @keyframes flash2 {
      0%, 45% { opacity: 0; }
      50%, 95% { opacity: 1; }
      100% { opacity: 0; }
    }
  </style>
  <image class="f1" href="$b1" width="500" height="500" y="-83" />
  <image class="f2" href="$b2" width="500" height="500" y="-83" />
</svg>
"@

[IO.File]::WriteAllText($file, $newSvg)
