#!/usr/bin/env python3
"""
Generate 400 files of approximately 120MB each with dummy data.
Total output: ~48GB of dummy data files.
"""

import os
import random
import string
import time
from pathlib import Path

def generate_random_text(size_mb):
    """
    Generate random text data of approximately the specified size in MB.
    
    Args:
        size_mb (int): Target size in megabytes
    
    Returns:
        str: Random text data
    """
    # 1 MB = 1,048,576 bytes
    target_bytes = size_mb * 1024 * 1024
    
    # Generate random strings in chunks to avoid memory issues
    chunk_size = 8192  # 8KB chunks
    chunks = []
    current_size = 0
    
    while current_size < target_bytes:
        # Generate random string chunk
        remaining = min(chunk_size, target_bytes - current_size)
        chunk = ''.join(random.choices(
            string.ascii_letters + string.digits + string.punctuation + ' \n\t',
            k=remaining
        ))
        chunks.append(chunk)
        current_size += len(chunk)
    
    return ''.join(chunks)

def create_dummy_files(num_files=400, file_size_mb=120, output_dir='dummy_data'):
    """
    Create dummy data files.
    
    Args:
        num_files (int): Number of files to create
        file_size_mb (int): Target size for each file in MB
        output_dir (str): Directory to store the files
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    print(f"Generating {num_files} files of ~{file_size_mb}MB each...")
    print(f"Total estimated size: ~{(num_files * file_size_mb) / 1024:.1f}GB")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    print("-" * 50)
    
    start_time = time.time()
    
    for i in range(num_files):
        filename = f"dummy_file_{i+1:03d}.txt"
        filepath = os.path.join(output_dir, filename)
        
        file_start_time = time.time()
        
        # Generate dummy data
        print(f"Generating file {i+1}/{num_files}: {filename}... ", end="", flush=True)
        
        # Write data in smaller chunks to manage memory
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write file in 10MB chunks to manage memory usage
            chunks_per_file = file_size_mb // 10 if file_size_mb >= 10 else 1
            chunk_size = file_size_mb / chunks_per_file
            
            for chunk_num in range(chunks_per_file):
                chunk_data = generate_random_text(int(chunk_size))
                f.write(chunk_data)
        
        # Get actual file size
        actual_size_mb = os.path.getsize(filepath) / (1024 * 1024)
        file_time = time.time() - file_start_time
        
        print(f"Done ({actual_size_mb:.1f}MB, {file_time:.1f}s)")
    
    total_time = time.time() - start_time
    total_size_gb = sum(os.path.getsize(os.path.join(output_dir, f)) 
                       for f in os.listdir(output_dir)) / (1024**3)
    
    print("-" * 50)
    print(f"Generation complete!")
    print(f"Files created: {num_files}")
    print(f"Total size: {total_size_gb:.2f}GB")
    print(f"Total time: {total_time:.1f} seconds")
    print(f"Average time per file: {total_time/num_files:.1f} seconds")

def main():
    """Main function with configuration options."""
    
    # Configuration
    NUM_FILES = 400
    FILE_SIZE_MB = 1
    OUTPUT_DIR = 'batch_dummy_data_small'
    
    # Optional: Ask user for confirmation due to large file size
    total_gb = (NUM_FILES * FILE_SIZE_MB) / 1024
    response = input(f"This will create {NUM_FILES} files (~{total_gb:.1f}GB total). Continue? (y/N): ")
    
    if response.lower() in ['y', 'yes']:
        try:
            create_dummy_files(NUM_FILES, FILE_SIZE_MB, OUTPUT_DIR)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()