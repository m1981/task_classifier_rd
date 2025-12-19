#!/bin/bash
# scripts/setup-hooks.sh

# Create the hooks directory if it doesn't exist
mkdir -p .git/hooks

# Create the pre-push hook
cat > .git/hooks/pre-push << 'EOF'
#!/bin/bash

echo "Running pre-push checks..."

# 1. Run Linter (Example: ESLint, Flake8, etc.)
# Replace this with your actual lint command
echo "Running Linter..."
npm run lint
if [ $? -ne 0 ]; then
 echo "❌ Linting failed! Push aborted."
 exit 1
fi

# 2. Run Unit Tests
# Replace this with your actual test command
echo "Running Tests..."
npm run test
if [ $? -ne 0 ]; then
 echo "❌ Tests failed! Push aborted."
 exit 1
fi

echo "✅ All checks passed. Pushing to master..."
exit 0
EOF

# Make the hook executable
chmod +x .git/hooks/pre-push

echo "Git hooks installed successfully!"