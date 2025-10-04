#!/usr/bin/env python3
"""
Simple PyTorch training job for testing GPU scheduling

This is a mock training job that simulates GPU workload.
"""

import os
import time
import torch
import argparse
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description='Simple PyTorch Training Job')
    parser.add_argument('--duration', type=int, default=60,
                       help='Training duration in seconds')
    parser.add_argument('--model-size', type=str, default='small',
                       choices=['small', 'medium', 'large'],
                       help='Model size')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--job-name', type=str, default='training-job',
                       help='Job name for logging')
    return parser.parse_args()


def get_model(size):
    """Create a simple model based on size"""
    if size == 'small':
        return torch.nn.Sequential(
            torch.nn.Linear(784, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, 10)
        )
    elif size == 'medium':
        return torch.nn.Sequential(
            torch.nn.Linear(784, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, 10)
        )
    else:  # large
        return torch.nn.Sequential(
            torch.nn.Linear(784, 1024),
            torch.nn.ReLU(),
            torch.nn.Linear(1024, 512),
            torch.nn.ReLU(),
            torch.nn.Linear(512, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, 10)
        )


def train(args):
    """Simulate training"""
    print(f"[{datetime.now()}] Starting training job: {args.job_name}")
    print(f"Configuration: model={args.model_size}, batch_size={args.batch_size}")
    
    # Check GPU availability
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    
    # Create model
    model = get_model(args.model_size).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = torch.nn.CrossEntropyLoss()
    
    print(f"Model created with {sum(p.numel() for p in model.parameters())} parameters")
    
    # Training loop
    start_time = time.time()
    epoch = 0
    
    while time.time() - start_time < args.duration:
        epoch += 1
        
        # Simulate batch processing
        fake_input = torch.randn(args.batch_size, 784).to(device)
        fake_labels = torch.randint(0, 10, (args.batch_size,)).to(device)
        
        # Forward pass
        outputs = model(fake_input)
        loss = criterion(outputs, fake_labels)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # Log progress
        if epoch % 10 == 0:
            elapsed = time.time() - start_time
            print(f"[{datetime.now()}] Epoch {epoch}, Loss: {loss.item():.4f}, "
                  f"Elapsed: {elapsed:.1f}s")
        
        # Small delay to simulate realistic training
        time.sleep(0.1)
    
    total_time = time.time() - start_time
    print(f"[{datetime.now()}] Training completed!")
    print(f"Total epochs: {epoch}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Throughput: {epoch / total_time:.2f} epochs/sec")


if __name__ == '__main__':
    args = parse_args()
    train(args)

