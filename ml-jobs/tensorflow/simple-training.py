#!/usr/bin/env python3
"""
Simple TensorFlow training job for testing GPU scheduling
"""

import os
import time
import argparse
from datetime import datetime

# Suppress TensorFlow warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

import tensorflow as tf


def parse_args():
    parser = argparse.ArgumentParser(description='Simple TensorFlow Training Job')
    parser.add_argument('--duration', type=int, default=60,
                       help='Training duration in seconds')
    parser.add_argument('--model-size', type=str, default='small',
                       choices=['small', 'medium', 'large'],
                       help='Model size')
    parser.add_argument('--batch-size', type=int, default=32,
                       help='Batch size')
    parser.add_argument('--job-name', type=str, default='tf-training-job',
                       help='Job name for logging')
    return parser.parse_args()


def get_model(size):
    """Create a simple Keras model"""
    if size == 'small':
        return tf.keras.Sequential([
            tf.keras.layers.Dense(256, activation='relu', input_shape=(784,)),
            tf.keras.layers.Dense(10, activation='softmax')
        ])
    elif size == 'medium':
        return tf.keras.Sequential([
            tf.keras.layers.Dense(512, activation='relu', input_shape=(784,)),
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.Dense(10, activation='softmax')
        ])
    else:  # large
        return tf.keras.Sequential([
            tf.keras.layers.Dense(1024, activation='relu', input_shape=(784,)),
            tf.keras.layers.Dense(512, activation='relu'),
            tf.keras.layers.Dense(256, activation='relu'),
            tf.keras.layers.Dense(10, activation='softmax')
        ])


def train(args):
    """Train model"""
    print(f"[{datetime.now()}] Starting TensorFlow training job: {args.job_name}")
    print(f"Configuration: model={args.model_size}, batch_size={args.batch_size}")
    
    # Check GPU availability
    gpus = tf.config.list_physical_devices('GPU')
    print(f"GPUs available: {len(gpus)}")
    
    if gpus:
        for gpu in gpus:
            print(f"  - {gpu.name}")
        # Enable memory growth
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
    
    # Create model
    model = get_model(args.model_size)
    model.compile(
        optimizer='adam',
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    
    param_count = model.count_params()
    print(f"Model created with {param_count} parameters")
    
    # Training loop
    start_time = time.time()
    epoch = 0
    
    while time.time() - start_time < args.duration:
        epoch += 1
        
        # Generate fake data
        fake_input = tf.random.normal([args.batch_size, 784])
        fake_labels = tf.random.uniform([args.batch_size], 0, 10, dtype=tf.int32)
        
        # Train step
        with tf.GradientTape() as tape:
            predictions = model(fake_input, training=True)
            loss = tf.keras.losses.sparse_categorical_crossentropy(
                fake_labels, predictions
            )
            loss = tf.reduce_mean(loss)
        
        gradients = tape.gradient(loss, model.trainable_variables)
        model.optimizer.apply_gradients(zip(gradients, model.trainable_variables))
        
        # Log progress
        if epoch % 10 == 0:
            elapsed = time.time() - start_time
            print(f"[{datetime.now()}] Epoch {epoch}, Loss: {loss.numpy():.4f}, "
                  f"Elapsed: {elapsed:.1f}s")
        
        time.sleep(0.1)
    
    total_time = time.time() - start_time
    print(f"[{datetime.now()}] Training completed!")
    print(f"Total epochs: {epoch}")
    print(f"Total time: {total_time:.1f}s")
    print(f"Throughput: {epoch / total_time:.2f} epochs/sec")


if __name__ == '__main__':
    args = parse_args()
    train(args)

