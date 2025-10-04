FROM tensorflow/tensorflow:2.15.0-gpu

WORKDIR /workspace

# Copy training scripts
COPY simple-training.py .

# Set Python to unbuffered mode
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "simple-training.py"]

