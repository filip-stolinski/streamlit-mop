# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install obabel package using apt
RUN apt-get update && apt-get install -y openbabel

# Ensure mopac_files directory is executable
RUN chmod +x /app/mopac_files/*

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Run streamlit app
CMD ["streamlit", "run", "run_mop.py"]