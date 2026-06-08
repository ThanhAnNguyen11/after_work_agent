# Use official light python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for compiling some packages if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy all project code
COPY . .

# Expose ports
# 8000: FastAPI Backend
# 8501: Streamlit Frontend
EXPOSE 8000
EXPOSE 8501

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Run entrypoint
ENTRYPOINT ["./entrypoint.sh"]
