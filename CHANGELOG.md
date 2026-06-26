# Changelog

## [Unreleased]
### Security
- Removed hardcoded secrets from .env.example
- Added Content-Security-Policy meta tags to all HTML pages
- Fixed XSS vulnerability in terminal command handler (input sanitization)
- Pinned Trivy action to version 0.28.0 with SARIF output
- Added Open Graph and SEO meta tags
- Updated security reporting policy

### Added
- New arcade game card linking to ai-snake-game full simulation
- Extended terminal commands: skills, education
- GitHub Security SARIF upload in CI pipeline
- Accessibility and SEO improvements across all pages
- Navigation bar to snake_ai.html for portfolio consistency

### Fixed
- Missing getSafeMoves function in ai-snake-game/game.js (caused runtime crash)
- Consolidated duplicate snake animation workflows
- Updated actions/checkout from v3 to v4 in CI workflows
- Removed committed log files from repository
- Added logs/ directory to .gitignore
- Refactored calculateSafeArea to reuse getNeighbors utility

### Changed
- Enhanced CONTRIBUTING.md with detailed security guidelines
- Expanded CODE_OF_CONDUCT.md with full contributor covenant
- Improved SECURITY.md with reporting process and SLA
