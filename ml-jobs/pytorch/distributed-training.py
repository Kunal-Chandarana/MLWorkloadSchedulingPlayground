#!/usr/bin/env python3
"""
Distributed PyTorch training job using torch.distributed

This simulates a multi-GPU distributed training workload.
"""

import os
import time
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.optim as optim
import argparse
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description='Distributed PyTorch Training')
    parser.add_argument('--duration', type=int, default=120,
                       help='Training duration in seconds')
    parser.add_argument('--model-size', type=str, default='medium',
                       choices=['small', 'medium', 'large'],
                       help='Model size')
    parser.add_argument('--batch-size', type=int, default=64,
                       help='Batch size per GPU')
    parser.add_argument('--backend', type=str, default='gloo',
                       choices=['gloo', 'nccl'],
                       help='Distributed backend')
    return parser.parse_args()


def setup_distributed():
    """Initialize distributed training environment"""
    # Get rank and world size from environment variables
    # (set by Kubernetes or torch.distributed.launch)
    rank = int(os.environ.get('RANK', 0))
    world_size = int(os.environ.get('WORLD_SIZE', 1))
    master_addr = os.environ.get('MASTER_ADDR', 'localhost')
    master_port = os.environ.get('MASTER_PORT', '29500')
    
    print(f"Initializing process group: rank={rank}, world_size={world_size}")
    print(f"Master: {master_addr}:{master_port}")
    
    # Initialize process group
    if world_size > 1:
        dist.init_process_group(
            backend=args.backend,
            init_method=f'tcp://{master_addr}:{master_port}',
            rank=rank,
            world_size=world_size
        )
    
    return rank, world_size


def get_model(size):
    """Create a simple model"""
    if size == 'small':
        return nn.Sequential(
            nn.Linear(784, 256),
            nn.ReLU(),
            nn.Linear(256, 10)
        )
    elif size == 'medium':
        return nn.Sequential(
            nn.Linear(784, 512),
            nn.ReLU(),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, 10)
        )
    else:  # large
        return nn.Sequential(
            nn.Linear(784, 2048),
            nn.ReLU(),
            nn.Linear(2048, 1024),
            nn.ReLU(),
            nn.Linear(1024, 512),
            nn.ReLU(),
            nn.Linear(512, 10)
        )


def train(args):
    """Distributed training"""
    rank, world_size = setup_distributed()
    
    print(f"[Rank {rank}] Starting distributed training")
    
    # Set device
    if torch.cuda.is_available():
        device = torch.device(f'cuda:{rank % torch.cuda.device_count()}')
        torch.cuda.set_device(device)
    else:
        device = torch.device('cpu')
    
    print(f"[Rank {rank}] Using device: {device}")
    
    # Create model
    model = get_model(args.model_size).to(device)
    
    # Wrap model with DistributedDataParallel
    if world_size > 1:
        model = nn.parallel.DistributedDataParallel(model)
    
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()
    
    if rank == 0:
        params = sum(p.numel() for p in model.parameters())
        print(f"Model created with {params} parameters")
        print(f"Training on {world_size} GPUs")
    
    # Training loop
    start_time = time.time()
    epoch = 0
    
    while time.time() - start_time < args.duration:
        epoch += 1
        
        # Simulate batch
        fake_input = torch.randn(args.batch_size, 784).to(device)
        fake_labels = torch.randint(0, 10, (args.batch_size,)).to(device)
        
        # Forward pass
        outputs = model(fake_input)
        loss = criterion(outputs, fake_labels)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        
        # Log progress (only rank 0)
        if rank == 0 and epoch % 10 == 0:
            elapsed = time.time() - start_time
            print(f"[{datetime.now()}] Epoch {epoch}, Loss: {loss.item():.4f}, "
                  f"Elapsed: {elapsed:.1f}s")
        
        time.sleep(0.1)
    
    # Cleanup
    if world_size > 1:
        dist.destroy_process_group()
    
    if rank == 0:
        total_time = time.time() - start_time
        print(f"[{datetime.now()}] Training completed!")
        print(f"Total epochs: {epoch}")
        print(f"Total time: {total_time:.1f}s")
        print(f"Throughput: {epoch / total_time:.2f} epochs/sec")


if __name__ == '__main__':
    args = parse_args()
    train(args)

