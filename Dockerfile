# Use the official Python slim image as a base
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt /app/requirements.txt

# Install the required dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code into the container
COPY . /app

# Command to run your bot
CMD ["python", "Line.py"]
