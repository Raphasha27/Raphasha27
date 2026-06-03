# Security Policy

## 🔒 Reporting a Vulnerability

I take the security of my projects seriously. If you discover a security vulnerability, please **do NOT** open a public issue.

Instead, **report privately** by emailing **402106633@my.richfield.ac.za**

You will receive a response within **48 hours** with the plan for addressing the issue.

### What to include:
- Description of the vulnerability
- Steps to reproduce
- Affected versions (if known)
- Potential impact

## 🛡️ Security Features

This repository uses:
- **Trivy** — Weekly automated vulnerability scanning (dependencies, secrets, IaC)
- **Dependabot** — Automated dependency updates
- **Branch Protection** — `main` branch requires PR review
- **Secret Scanning** — GitHub Advanced Security (if enabled)
- **CodeQL Analysis** — Automated code quality and security analysis

## ✅ Best Practices

- Never commit `.env` files, API keys, or credentials
- Use environment variables or GitHub Secrets for sensitive data
- Keep dependencies up to date
- Use 2FA on your GitHub account
- Review code before merging

## 📋 Supported Versions

| Version | Supported |
| ------- | --------- |
| Latest  | ✅ Yes    |
| Older   | ❌ No     |
