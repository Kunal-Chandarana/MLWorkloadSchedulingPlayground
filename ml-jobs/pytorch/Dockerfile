FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

WORKDIR /workspace

# Copy training scripts
COPY simple-training.py .
COPY distributed-training.py .

# Set Python to unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "simple-training.py"]

