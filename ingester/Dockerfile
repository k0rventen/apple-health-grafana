FROM python:3.12-alpine

# Set environment variables
ENV INFLUX_TOKEN=${INFLUX_TOKEN} \
    INFLUX_ORG=${INFLUX_ORG} \
    INFLUX_BUCKET=${INFLUX_BUCKET}

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy Python files
COPY *.py ./

# Set entrypoint
ENTRYPOINT ["python3", "-u", "app.py"]
