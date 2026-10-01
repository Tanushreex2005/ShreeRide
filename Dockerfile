FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make sure .env is not copied (if it exists, but we rely on environment variables set at runtime)
# We don't copy .env because it's in .dockerignore (see below) and we set env vars via platform

# Expose the port the app runs on
EXPOSE 5000

# Define environment variable (optional, can be overridden)
ENV FLASK_ENV=production

# Run the app when the container launches
CMD ["python", "app.py"]