const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');
const scoreEl = document.getElementById('score');
const highScoreEl = document.getElementById('high-score');
const statusText = document.getElementById('status-text');

// Game Constants
const TILE_SIZE = 20;
const TILE_COUNT = canvas.width / TILE_SIZE; // 30x30 grid
const FPS = 15; // Speed of the simulation

// Game State
let snake = [];
let food = { x: 0, y: 0 };
let dx = 0;
let dy = 0;
let score = 0;
let highScore = 0;
let gameLoop;

// AI State
let path = []; // Current calculated path

// Initialize Game
function init() {
    snake = [
        { x: 10, y: 10 },
        { x: 9, y: 10 },
        { x: 8, y: 10 }
    ];
    score = 0;
    scoreEl.innerText = score;
    spawnFood();
    dx = 1; dy = 0;
    
    if (gameLoop) clearInterval(gameLoop);
    gameLoop = setInterval(update, 1000 / FPS);
}

// Main Game Loop
function update() {
    // 1. AI Decision
    const decision = getAIMove();
    if (decision) {
        dx = decision.x;
        dy = decision.y;
    }

    // 2. Move Snake
    const head = { x: snake[0].x + dx, y: snake[0].y + dy };

    // 3. Collision Detection (Walls or Body)
    if (head.x < 0 || head.x >= TILE_COUNT || head.y < 0 || head.y >= TILE_COUNT || isCollision(head)) {
        gameOver();
        return;
    }

    snake.unshift(head);

    // 4. Eat Food
    if (head.x === food.x && head.y === food.y) {
        score += 10;
        scoreEl.innerText = score;
        if (score > highScore) {
            highScore = score;
            highScoreEl.innerText = highScore;
        }
        spawnFood();
        // Path needs recalculation since food moved
        path = [];
    } else {
        snake.pop();
    }

    // 5. Render
    draw();
}

// Draw Everything
function draw() {
    // Clear Screen
    ctx.fillStyle = '#161b22';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Draw Snake
    snake.forEach((segment, index) => {
        // Head is brighter, body pulses
        ctx.fillStyle = index === 0 ? '#4ade80' : '#22c55e';
        
        // Cyber-glow effect
        ctx.shadowBlur = index === 0 ? 15 : 0;
        ctx.shadowColor = '#22c55e';
        
        ctx.fillRect(segment.x * TILE_SIZE, segment.y * TILE_SIZE, TILE_SIZE - 2, TILE_SIZE - 2);
        
        ctx.shadowBlur = 0; // Reset shadow
    });

    // Draw Food
    ctx.fillStyle = '#ef4444';
    ctx.shadowBlur = 15;
    ctx.shadowColor = '#ef4444';
    ctx.beginPath();
    ctx.arc(
        food.x * TILE_SIZE + TILE_SIZE / 2, 
        food.y * TILE_SIZE + TILE_SIZE / 2, 
        TILE_SIZE / 2 - 2, 
        0, Math.PI * 2
    );
    ctx.fill();
    ctx.shadowBlur = 0;
}

// Helper: Check Collision with Body
function isCollision(pt) {
    // Ignore tail tip if we are moving (it will move away)
    // But simplistic check for now
    for (let i = 0; i < snake.length - 1; i++) {
        if (pt.x === snake[i].x && pt.y === snake[i].y) return true;
    }
    return false;
}

// Spawn Food in valid location
function spawnFood() {
    let valid = false;
    while (!valid) {
        food.x = Math.floor(Math.random() * TILE_COUNT);
        food.y = Math.floor(Math.random() * TILE_COUNT);
        valid = !isCollision(food);
    }
}

function gameOver() {
    // Auto Restart for continuous showcase
    statusText.innerText = "CRITICAL FAILURE. REBOOTING SYSTEM...";
    statusText.style.color = "#ef4444";
    setTimeout(() => {
        statusText.innerText = "CALCULATING PATH...";
        statusText.style.color = "#6b7280";
        init();
    }, 1000);
}

// --- ELITE AI ENGINE (A* PATHFINDING + FLOOD-FILL) ---

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
    // 1. Primary Algorithm: A* to target food
    if (path.length === 0) {
        path = aStar(snake[0], food);
    }

    if (path.length > 0) {
        const nextMove = path.shift();
        return { x: nextMove.x - snake[0].x, y: nextMove.y - snake[0].y };
    }

    // 2. Safety Fallback: Flood-Fill Analysis
    // If no path to food, find the move that leads to the largest open area
    statusText.innerText = "SURVIVAL MODE: FLOOD-FILL ACTIVE";
    statusText.style.color = "#fbbf24";
    
    const safeMoves = getSafeMoves(snake[0]);
    let bestMove = null;
    let maxArea = -1;

    for (let move of safeMoves) {
        const area = calculateSafeArea(move);
        if (area > maxArea) {
            maxArea = area;
            bestMove = move;
        }
    }

    if (bestMove) {
        return { x: bestMove.x - snake[0].x, y: bestMove.y - snake[0].y };
    }

    return null; // Death inevitable
}

function aStar(start, target) {
    let openSet = [{ pos: start, g: 0, h: heuristic(start, target), f: heuristic(start, target), path: [] }];
    let closedSet = new Set();

    while (openSet.length > 0) {
        // Sort by F score (G + H)
        openSet.sort((a, b) => a.f - b.f);
        const current = openSet.shift();

        if (current.pos.x === target.x && current.pos.y === target.y) {
            statusText.innerText = "PATH LOCKED (A*)";
            statusText.style.color = "#4ade80";
            return current.path;
        }

        closedSet.add(`${current.pos.x},${current.pos.y}`);

        const neighbors = getSafeMoves(current.pos);
        for (let next of neighbors) {
            if (closedSet.has(`${next.x},${next.y}`)) continue;

            const g = current.g + 1;
            const h = heuristic(next, target);
            const f = g + h;

            const existing = openSet.find(o => o.pos.x === next.x && o.pos.y === next.y);
            if (!existing || g < existing.g) {
                if (!existing) {
                    openSet.push({ pos: next, g, h, f, path: [...current.path, next] });
                } else {
                    existing.g = g;
                    existing.f = f;
                    existing.path = [...current.path, next];
                }
            }
        }
    }
    return [];
}

function heuristic(a, b) {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

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
