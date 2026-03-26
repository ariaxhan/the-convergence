# Armature Installation Guide

## Package Names

- **Package name** (for pip): `armature-ai`
- **Import name** (in Python): `armature`

```bash
# Install
pip install -e .

# Import
from armature import run_optimization
```

## Installation Methods

### 1. Development Install (Editable)

For local development where you want changes to reflect immediately:

```bash
cd /path/to/armature-ai
pip install -e .
```

This creates a symbolic link, so code changes take effect immediately without reinstalling.

### 2. Backend Integration

For the backend to use Armature:

```bash
# Already in backend/requirements.txt as:
armature-ai

# Install dependencies
cd /path/to/backend
pip install -r requirements.txt
```

### 3. Production Install

```bash
pip install -e .
```

## Verify Installation

```bash
# Test 1: Import check
python -c "from armature import run_optimization; print('✅ SDK import works')"

# Test 2: Check version
python -c "from armature import __version__; print(f'Armature v{__version__}')"

# Test 3: CLI check
armature --help
```

## Installing from Source

If you need the latest development version:

```bash
# Clone repository
git clone https://github.com/ariaxhan/armature-ai.git
cd armature-ai

# Install in development mode
pip install -e .

# Or build and install
pip install build
python -m build
pip install dist/the_armature-*.whl
```

## Backend Integration Setup

### Step 1: Install Package

```bash
cd backend
pip install -e ../armature-ai
```

### Step 2: Verify Import

```python
# Test in Python
from armature import run_optimization
print("✅ Armature SDK ready")
```

### Step 3: Update Requirements (if needed)

The backend's `requirements.txt` already includes:
```
armature-ai
```

If you need a specific version:
```
armature-ai>=0.1.2
```

## Common Issues

### Issue: Import Error

```python
ImportError: No module named 'armature'
```

**Solution**: Package not installed. Run:
```bash
pip install -e .
```

### Issue: Wrong Python Environment

```bash
# Check which Python/pip you're using
which python
which pip

# Use correct environment
source venv/bin/activate  # if using venv
pip install -e .
```

### Issue: Editable Install Not Working

```bash
# Reinstall in editable mode
pip uninstall armature-ai
cd /path/to/armature-ai
pip install -e .
```

## Development Workflow

### For Armature Development

```bash
cd armature-ai
pip install -e .
# Make changes to code
# Test immediately (no reinstall needed)
python test_script.py
```

### For Backend Development

```bash
# Install Armature in editable mode
cd backend
pip install -e ../armature-ai

# Now backend can import latest Armature code
python -m app.background_jobs.executors.armature_optimization
```

## Dependencies

Armature requires:
- Python >= 3.11
- pydantic >= 2.0.0
- httpx >= 0.25.0
- pyyaml >= 6.0.0
- Other dependencies (see pyproject.toml)

These are automatically installed when you install `armature-ai`.

## Next Steps

After installation, see:
- `SDK_USAGE.md` - How to use the SDK
- `examples/` - Working examples
- `README.md` - Full documentation

