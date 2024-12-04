# Set base image
FROM python:3.9

# Expose the application port
EXPOSE 5000

# Create a parent directory
WORKDIR /project

# Create the working directory inside the parent directory
RUN mkdir app

# Set the working directory to the new directory
WORKDIR /project/app

# Copy Python dependencies
COPY requirements.txt /project/app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the new working directory
COPY . /project/app/

# Command to run the server
CMD ["python", "server.py"]
