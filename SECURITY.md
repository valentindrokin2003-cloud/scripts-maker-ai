# Security Guidelines

## Sensitive Information

### Never commit:
- ❌ ANTHROPIC_API_KEY (use `.env` instead)
- ❌ Private repository tokens
- ❌ Credentials, passwords, or secrets
- ❌ Internal URLs or internal infrastructure details

### Protected:
- ✅ `.env` — automatically ignored by `.gitignore`
- ✅ `.env.example` — template only, no actual secrets

## Cleanup Actions Taken

**Date:** 2026-03-18

1. **Removed from current files:**
   - Sberbank internal repository token from notebook files
   - `!python3.6 -m pip install -U sh --index-url https://...@sberosc.ca.sbrf.ru...`

2. **Added security controls:**
   - `.env` added to `.gitignore` (actual secrets not tracked)
   - `.env.example` provided as template
   - `python-dotenv` integrated for environment variables
   - `.gitattributes` configured for additional safety

3. **Git history:**
   - Note: Old commits may contain the token in git history
   - Current working tree is clean and safe
   - If this is a public repository, consider: `git clone --depth=1` or resetting history

## Best Practices

1. **Always use `.env` for secrets:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   # Never commit .env
   ```

2. **Check before committing:**
   ```bash
   git diff --cached | grep -i "token\|key\|password\|secret"
   ```

3. **Use git hooks (optional):**
   ```bash
   # Install pre-commit hook to prevent secret commits
   pip install pre-commit
   pre-commit install
   ```

## Contact

If you discover any security issues, please report them privately.
