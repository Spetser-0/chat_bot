#!/bin/bash
# Render Environment Setup Helper
# ─────────────────────────────────
# Run this locally to verify your environment variables before deploying.

set -e

echo "🔍 Checking required environment variables for Spetser AI..."
echo ""

# Required variables
REQUIRED_VARS=(
  "APP_ENV"
  "APP_SECRET_KEY"
  "SESSION_SECRET_KEY"
  "DATABASE_URL"
  "SMTP_HOST"
  "SMTP_PORT"
  "SMTP_USER"
  "SMTP_PASSWORD"
  "SMTP_FROM"
)

# Optional variables (with defaults)
OPTIONAL_VARS=(
  "REDIS_URL"
  "RATE_LIMIT_BACKEND"
  "LOG_LEVEL"
)

missing=()

for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    missing+=("$var")
    echo "❌ Missing: $var"
  else
    # Mask sensitive values
    if [[ "$var" == *"SECRET"* ]] || [[ "$var" == *"PASSWORD"* ]]; then
      echo "✅ $var = [REDACTED]"
    else
      echo "✅ $var = ${!var}"
    fi
  fi
done

echo ""

if [ ${#missing[@]} -eq 0 ]; then
  echo "✨ All required variables are set!"
  echo ""
  echo "You can now deploy to Render with these environment variables."
  exit 0
else
  echo "⚠️  Missing ${#missing[@]} required variables:"
  printf '  - %s\n' "${missing[@]}"
  echo ""
  echo "Add these to your Render dashboard or export them locally."
  exit 1
fi
