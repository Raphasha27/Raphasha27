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

// --- AI LOGIC (BFS) ---

function getAIMove() {
    // Simple recalculate path if empty or invalid
    if (path.length === 0) {
        path = bfs(snake[0], food);
    }

    if (path.length > 0) {
        const nextMove = path.shift();
        return { x: nextMove.x - snake[0].x, y: nextMove.y - snake[0].y };
    }

    // Fallback: If no path to food, try any safe move (Survival Mode)
    statusText.innerText = "SURVIVAL MODE (NO PATH)";
    const safeMoves = getSafeMoves(snake[0]);
    if (safeMoves.length > 0) {
        // Pick one that is furthest from body or simply random for now
        // A better heuristic would be "follow tail"
        return safeMoves[0]; 
    }

    return null; // Death inevitable
}

function bfs(start, target) {
    let queue = [{ pos: start, path: [] }];
    let visited = new Set();
    visited.add(`${start.x},${start.y}`);

    // Create a virtual grid of the snake body to block paths
    // BUT we must consider the tail moving!
    // For simplicity in this version, we treat current body as static obstacles
    
    while (queue.length > 0) {
        const { pos, path } = queue.shift();

        if (pos.x === target.x && pos.y === target.y) {
            statusText.innerText = "PATH LOCKED";
            return path;
        }

        const neighbors = getSafeMoves(pos);
        for (let next of neighbors) {
            const key = `${next.x},${next.y}`;
            if (!visited.has(key)) {
                visited.add(key);
                queue.push({
                    pos: { x: next.x, y: next.y },
                    path: [...path, { x: next.x, y: next.y }]
                });
            }
        }
    }
    return []; // No path found
}

function getSafeMoves(head) {
    const moves = [
        { x: 0, y: -1 }, // Up
        { x: 0, y: 1 },  // Down
        { x: -1, y: 0 }, // Left
        { x: 1, y: 0 }   // Right
    ];

    return moves.map(m => ({ x: head.x + m.x, y: head.y + m.y }))
        .filter(pt => {
            // Check bounds
            if (pt.x < 0 || pt.x >= TILE_COUNT || pt.y < 0 || pt.y >= TILE_COUNT) return false;
            // Check collision with *current* snake body
            if (isCollision(pt)) return false;
            return true;
        });
}

// Start
init();
