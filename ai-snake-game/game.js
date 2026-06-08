const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const highScoreEl = document.getElementById('high-score');
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('status-dot');
const gameCount = document.getElementById('game-count');

const TILE_SIZE = 20;
const TILE_COUNT = canvas.width / TILE_SIZE;
const FPS = 15;

let snake = [];
let food = { x: 0, y: 0 };
let dx = 0, dy = 0;
let score = 0;
let highScore = 0;
let gameLoop;
let path = [];
let gamesPlayed = 0;

function init() {
  if (gameLoop) clearInterval(gameLoop);
  snake = [{ x: 10, y: 10 }, { x: 9, y: 10 }, { x: 8, y: 10 }];
  score = 0;
  gamesPlayed++;
  gameCount.textContent = 'Game #' + gamesPlayed;
  scoreEl.textContent = '0';
  spawnFood();
  dx = 1; dy = 0;
  setStatus('CALCULATING PATH...', '#6b7280', '');
  gameLoop = setInterval(update, 1000 / FPS);
}

function setStatus(text, color, dotClass) {
  statusText.textContent = text;
  statusText.style.color = color || '#6b7280';
  statusDot.className = 'status-dot' + (dotClass ? ' ' + dotClass : '');
}

function update() {
  const decision = getAIMove();
  if (decision) { dx = decision.x; dy = decision.y; }

  const head = { x: snake[0].x + dx, y: snake[0].y + dy };

  if (head.x < 0 || head.x >= TILE_COUNT || head.y < 0 || head.y >= TILE_COUNT || isCollision(head)) {
    gameOver();
    return;
  }

  snake.unshift(head);

  if (head.x === food.x && head.y === food.y) {
    score += 10;
    scoreEl.textContent = score;
    if (score > highScore) { highScore = score; highScoreEl.textContent = highScore; }
    spawnFood();
    path = [];
    setStatus('ATE FOOD - RECALCULATING', '#22c55e', '');
  } else {
    snake.pop();
  }

  draw();
}

function draw() {
  ctx.fillStyle = '#161b22';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Grid
  ctx.strokeStyle = '#1c2333';
  ctx.lineWidth = 0.5;
  for (let i = 0; i <= TILE_COUNT; i++) {
    ctx.beginPath();
    ctx.moveTo(i * TILE_SIZE, 0);
    ctx.lineTo(i * TILE_SIZE, canvas.height);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, i * TILE_SIZE);
    ctx.lineTo(canvas.width, i * TILE_SIZE);
    ctx.stroke();
  }

  // Snake
  snake.forEach((seg, i) => {
    const isHead = i === 0;
    const x = seg.x * TILE_SIZE + 1;
    const y = seg.y * TILE_SIZE + 1;
    const size = TILE_SIZE - 2;

    if (isHead) {
      ctx.shadowBlur = 12;
      ctx.shadowColor = '#22c55e';
      ctx.fillStyle = '#4ade80';
    } else {
      ctx.shadowBlur = 0;
      const t = 1 - (i / snake.length) * 0.5;
      ctx.fillStyle = `rgb(${Math.floor(34 * t)}, ${Math.floor(197 * t)}, ${Math.floor(94 * t)})`;
    }

    ctx.beginPath();
    ctx.roundRect(x, y, size, size, 4);
    ctx.fill();
    ctx.shadowBlur = 0;
  });

  // Food
  const fx = food.x * TILE_SIZE + TILE_SIZE / 2;
  const fy = food.y * TILE_SIZE + TILE_SIZE / 2;
  ctx.shadowBlur = 15;
  ctx.shadowColor = '#ef4444';
  ctx.fillStyle = '#ef4444';
  ctx.beginPath();
  ctx.arc(fx, fy, TILE_SIZE / 2 - 3, 0, Math.PI * 2);
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.fillStyle = '#ff6b6b';
  ctx.beginPath();
  ctx.arc(fx, fy, TILE_SIZE / 2 - 6, 0, Math.PI * 2);
  ctx.fill();
}

function isCollision(pt) {
  for (let i = 0; i < snake.length - 1; i++) {
    if (pt.x === snake[i].x && pt.y === snake[i].y) return true;
  }
  return false;
}

function spawnFood() {
  let valid = false;
  while (!valid) {
    food.x = Math.floor(Math.random() * TILE_COUNT);
    food.y = Math.floor(Math.random() * TILE_COUNT);
    valid = !isCollision(food);
  }
}

function gameOver() {
  setStatus('CRITICAL FAILURE - REBOOTING...', '#ef4444', 'error');
  setTimeout(() => {
    setStatus('CALCULATING PATH...', '#6b7280', '');
    init();
  }, 1000);
}

function getNeighbors(pos) {
  return [
    { x: pos.x + 1, y: pos.y }, { x: pos.x - 1, y: pos.y },
    { x: pos.x, y: pos.y + 1 }, { x: pos.x, y: pos.y - 1 }
  ];
}

function getSafeMoves(pos) {
  const snakeSet = new Set(snake.map(s => `${s.x},${s.y}`));
  return getNeighbors(pos).filter(n =>
    n.x >= 0 && n.x < TILE_COUNT && n.y >= 0 && n.y < TILE_COUNT &&
    !snakeSet.has(`${n.x},${n.y}`)
  );
}

function getAIMove() {
  if (path.length === 0) { path = aStar(snake[0], food); }

  if (path.length > 0) {
    const nextMove = path.shift();
    return { x: nextMove.x - snake[0].x, y: nextMove.y - snake[0].y };
  }

  setStatus('SURVIVAL MODE - FLOOD-FILL', '#fbbf24', 'warning');

  const safeMoves = getSafeMoves(snake[0]);
  let bestMove = null, maxArea = -1;

  for (let move of safeMoves) {
    const area = calculateSafeArea(move);
    if (area > maxArea) { maxArea = area; bestMove = move; }
  }

  if (bestMove) return { x: bestMove.x - snake[0].x, y: bestMove.y - snake[0].y };
  return null;
}

function aStar(start, target) {
  let openSet = [{ pos: start, g: 0, h: heuristic(start, target), f: heuristic(start, target), path: [] }];
  let closedSet = new Set();

  while (openSet.length > 0) {
    openSet.sort((a, b) => a.f - b.f);
    const current = openSet.shift();

    if (current.pos.x === target.x && current.pos.y === target.y) {
      setStatus('PATH LOCKED (A*)', '#4ade80', '');
      return current.path;
    }

    closedSet.add(`${current.pos.x},${current.pos.y}`);

    for (let next of getSafeMoves(current.pos)) {
      if (closedSet.has(`${next.x},${next.y}`)) continue;
      const g = current.g + 1;
      const h = heuristic(next, target);
      const f = g + h;
      const existing = openSet.find(o => o.pos.x === next.x && o.pos.y === next.y);
      if (!existing || g < existing.g) {
        if (!existing) openSet.push({ pos: next, g, h, f, path: [...current.path, next] });
        else { existing.g = g; existing.f = f; existing.path = [...current.path, next]; }
      }
    }
  }
  return [];
}

function heuristic(a, b) { return Math.abs(a.x - b.x) + Math.abs(a.y - b.y); }

function calculateSafeArea(start) {
  const queue = [start];
  const visited = new Set();
  const snakeSet = new Set(snake.map(s => `${s.x},${s.y}`));
  visited.add(`${start.x},${start.y}`);
  let area = 0;
  while (queue.length > 0 && area < 200) {
    const curr = queue.shift();
    area++;
    for (const next of getNeighbors(curr)) {
      const key = `${next.x},${next.y}`;
      if (next.x >= 0 && next.x < TILE_COUNT && next.y >= 0 && next.y < TILE_COUNT &&
          !snakeSet.has(key) && !visited.has(key)) {
        visited.add(key);
        queue.push(next);
      }
    }
  }
  return area;
}

// Start
init();
