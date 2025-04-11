FROM ollama/ollama:latest

# Set working directory
WORKDIR /app

# Copy the script to run Mistral
COPY run-mistral.sh /app/run-mistral.sh

# Make the script executable
RUN chmod +x /app/run-mistral.sh

# Set environment variables
ENV OLLAMA_HOST="0.0.0.0"
ENV OLLAMA_MODELS_PATH="/root/.ollama/models"

# Expose the default Ollama port
EXPOSE 11434

# Use the script as entrypoint
ENTRYPOINT ["/app/run-mistral.sh"] 