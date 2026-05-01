# Start with official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (for faster rebuilds)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the code
COPY . .

# Tell Cloud Run which port to listen on
ENV PORT=8080

# Start the FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]