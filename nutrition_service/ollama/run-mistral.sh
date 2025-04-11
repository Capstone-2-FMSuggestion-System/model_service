#!/bin/bash

# Khởi động Ollama server
./bin/ollama serve &
pid=$!

# Đợi server khởi động
sleep 5

# Tải mô hình Mistral
echo "Pulling Mistral model..."
ollama pull mistral

# Đợi quá trình hoàn tất
wait $pid