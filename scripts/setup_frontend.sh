#!/bin/bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install 20

cd /home/mghiffaa/Jsep
mkdir -p frontend
cd frontend
rm -rf package.json node_modules package-lock.json src
npm create vite@latest . -- --template react-ts
npm install
npm install maplibre-gl@4 echarts react-echarts zustand @radix-ui/react-dialog @radix-ui/react-tabs tailwindcss postcss autoprefixer socket.io-client
npx tailwindcss init -p
