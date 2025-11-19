# Development Workflow

## Testing Unreleased Features

### Install from Development Branch

```bash
# Install from dev branch
pip install --upgrade --break-system-packages git+https://github.com/vibery-studio/vibewp.git@dev

# Or with pipx
pipx install git+https://github.com/vibery-studio/vibewp.git@dev --force
```

### Workflow

1. **Development happens on `dev` branch**
   ```bash
   git checkout dev
   # Make changes, test locally
   git commit -m "feat: new feature"
   git push origin dev
   ```

2. **Test on server**
   ```bash
   pipx install git+https://github.com/vibery-studio/vibewp.git@dev --force
   vibewp --version  # Should show version with -dev suffix
   ```

3. **When stable, merge to main and release**
   ```bash
   git checkout main
   git merge dev
   # Bump version in cli/__init__.py
   git tag v1.x.x
   git push origin main --tags
   gh release create v1.x.x
   ```

### Version Naming

- **Dev branch**: `1.4.5-dev` (in `cli/__init__.py`)
- **Main branch**: `1.4.5` (production release)

### Quick Commands

```bash
# Install latest dev
vibewp-dev-install() {
  pipx install git+https://github.com/vibery-studio/vibewp.git@dev --force
}

# Switch back to stable
vibewp-stable-install() {
  pipx install git+https://github.com/vibery-studio/vibewp.git --force
}
```

## Local Development

```bash
# Clone and install in editable mode
git clone https://github.com/vibery-studio/vibewp.git
cd vibewp
pip install -e .

# Make changes and test immediately
vibewp --version
```
