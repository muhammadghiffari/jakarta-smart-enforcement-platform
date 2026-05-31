#!/bin/bash
# Start JSEP Vite frontend
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

cd /home/mghiffaa/Jsep/frontend
npm run dev -- --host 0.0.0.0
