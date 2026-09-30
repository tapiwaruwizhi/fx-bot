#!/usr/bin/env bash
# Builds the Flutter web app on Vercel.
# Required Vercel environment variables:
#   FLUTTER_VERSION  e.g. 3.35.4  (match `flutter --version` on your PC)
#   API_URL          e.g. https://fx-bot-api.onrender.com  (no trailing slash)
set -euo pipefail

if [ -z "${FLUTTER_VERSION:-}" ]; then
  echo "ERROR: set FLUTTER_VERSION in Vercel env vars (run 'flutter --version' locally)."
  exit 1
fi
if [ -z "${API_URL:-}" ]; then
  echo "ERROR: set API_URL in Vercel env vars (your Render URL)."
  exit 1
fi

SDK_PARENT="$PWD/.vercel-flutter"
FLUTTER_DIR="$SDK_PARENT/flutter"

if [ ! -x "$FLUTTER_DIR/bin/flutter" ]; then
  echo "Downloading Flutter $FLUTTER_VERSION ..."
  mkdir -p "$SDK_PARENT"
  curl -fsSL "https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_${FLUTTER_VERSION}-stable.tar.xz" \
    | tar -xJ -C "$SDK_PARENT"
fi

# The SDK is a git checkout; avoid "dubious ownership" errors when running as root
git config --global --add safe.directory "$FLUTTER_DIR" || true
export PATH="$FLUTTER_DIR/bin:$PATH"

flutter config --no-analytics >/dev/null
flutter config --enable-web >/dev/null
flutter --version
flutter pub get
flutter build web --release --dart-define=API_URL="$API_URL"
