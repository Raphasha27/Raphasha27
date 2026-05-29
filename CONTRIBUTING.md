# Contributing Guidelines

Thank you for contributing to this repository!

## Development Workflow

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow coding conventions**:
   - HTML: semantic markup, accessibility attributes
   - CSS: use CSS custom properties, responsive design
   - JavaScript: ES6+, avoid inline event handlers where possible
   - Python: PEP 8, type hints where applicable

3. **Commit messages** follow [Conventional Commits](https://www.conventionalcommits.org/):
   - `feat:` new feature
   - `fix:` bug fix
   - `chore:` maintenance, tooling
   - `docs:` documentation
   - `security:` vulnerability fix
   - `refactor:` code restructure

4. **Before submitting a PR**:
   - Verify all HTML files render without errors
   - Check for hardcoded secrets or credentials
   - Ensure no `.env` files or logs are committed
   - Validate JavaScript for console errors

5. **Security first**: Never commit secrets, API keys, or tokens. Always use environment variables.

We appreciate your contributions to keeping this project secure and robust!
