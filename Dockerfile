FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create downloads directory
RUN mkdir -p /downloads

# Make CLI executable
RUN chmod +x rd_cli.py

# Expose port for web interface
EXPOSE 8080

# Default command: run the web server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
