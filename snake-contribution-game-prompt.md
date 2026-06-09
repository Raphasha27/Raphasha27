# GitHub Contribution Snake Game — AI Prompt

Copy the following prompt into any AI coding tool (Cursor, Claude Code, Lovable, Bolt, Replit AI, etc.) to recreate the GitHub Snake contribution game using the exact layout shown in the reference images:

---

Create a modern interactive GitHub Contribution Snake Game inspired by the GitHub contribution graph.

**Layout Requirements**
- Use the GitHub contribution grid as the game board
- Small rounded square cells, ~7 rows × 52+ columns
- Light gray background with multiple shades of blue contribution squares
- Grid spacing and proportions matching GitHub's contribution calendar
- Each cell represents a contribution block

**Snake Design**
- Smooth animated snake with head slightly larger than body
- Rounded corners, bright green color with subtle glow
- Smooth movement between cells; body segments overlap slightly for natural appearance

**Food Design**
- Food appears on contribution squares using GitHub-style contribution colors (light blue, medium blue, dark blue)
- Subtle pulse animation on food items

**Game Mechanics**
- Snake automatically navigates the contribution graph using pathfinding (A* or BFS) to find the nearest contribution square
- Eats contribution blocks one by one, grows after each collected block
- Avoids self-collisions
- When all squares are collected, regenerate the board and continue

**Visual Style**
- Dark mode (background: #0D1117, subtle grid lines, GitHub blue palette dots, vibrant green snake)
- Modern glassmorphism UI panel showing: Score, Contributions Collected, Snake Length, Speed
- Smooth CSS animations throughout

**Extra Features**
- Responsive design (desktop + mobile)
- Start / Pause / Reset controls
- Adjustable speed slider
- Smooth 60fps animation using requestAnimationFrame
- Particle effect when food is collected
- Optional autoplay mode where snake solves board autonomously

**Technical Requirements**
- React + TypeScript
- TailwindCSS for styling
- Framer Motion for animations
- Modular component structure
- Clean, production-ready code
- Use CSS Grid to render the contribution graph
- Generate the contribution board from a 7×53 matrix representing GitHub contributions

**Goal**
The final result should look like a polished GitHub contribution heatmap where a bright green autonomous snake intelligently traverses the contribution graph, collecting all contribution squares while growing in length, closely matching the reference layout provided.

For even closer matching, attach reference images and add:
> "Match the spacing, cell size, proportions, contribution color distribution, and overall visual composition of the uploaded reference images as closely as possible."
