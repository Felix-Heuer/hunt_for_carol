#!/usr/bin/env python3
import hashlib
import random
import string
import time
import argparse
import multiprocessing
import os
from concurrent.futures import ProcessPoolExecutor
import sys


def generate_random_string(length):
    """Generate a random string of specified length."""
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


def find_matching_hash(args):
    """Find a random string whose SHA256 hash starts with the specified prefix."""
    prefix, string_length, process_id = args

    # Convert prefix to bytes if it's not already
    if isinstance(prefix, str):
        prefix_bytes = prefix.encode('utf-8')
    else:
        prefix_bytes = prefix

    count = 0
    start_time = time.time()
    report_interval = 100000  # Report progress every 100k attempts

    while True:
        # Generate a random string with the process ID appended to ensure uniqueness across processes
        # random_string = f"{generate_random_string(string_length)}-{process_id}-{count}"
        random_string = f"{generate_random_string(string_length)}@sha2.org"
        # Calculate its SHA256 hash
        hash_bytes = hashlib.sha256(random_string.encode('utf-8')).digest()
        hash_hex = hashlib.sha256(random_string.encode('utf-8')).hexdigest()

        # Check if the hash starts with the specified prefix
        if hash_hex.startswith(prefix):
            elapsed_time = time.time() - start_time
            hashes_per_second = count / elapsed_time if elapsed_time > 0 else 0
            return {
                'string': random_string,
                'hash': hash_hex,
                'attempts': count,
                'time': elapsed_time,
                'hashes_per_second': hashes_per_second
            }

        count += 1

        # Periodically report progress
        if count % report_interval == 0:
            elapsed_time = time.time() - start_time
            hashes_per_second = count / elapsed_time if elapsed_time > 0 else 0
            print(f"Process {process_id}: {count} attempts, {hashes_per_second:.2f} hashes/s", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description='Find a string whose SHA256 hash has a specific prefix')
    parser.add_argument('--prefix', type=str, default='4361726F6C', help='Desired prefix of the SHA256 hash (hex format)')
    # parser.add_argument('--prefix', type=str, default='1234', help='Desired prefix of the SHA256 hash (hex format)')
    parser.add_argument('--length', type=int, default=8, help='Length of random strings to generate')
    parser.add_argument('--processes', type=int, default=multiprocessing.cpu_count(),
                        help='Number of processes to use (default: number of CPU cores)')
    10100000
    args = parser.parse_args()

    print(f"Searching for a string whose SHA256 hash starts with '{args.prefix}'")
    print(f"Using {args.processes} processes")

    start_time = time.time()

    # Create a process pool and distribute the work
    process_args = [(args.prefix, args.length, i) for i in range(args.processes)]

    with ProcessPoolExecutor(max_workers=args.processes) as executor:
        # Start all processes and get the first result
        futures = [executor.submit(find_matching_hash, arg) for arg in process_args]

        try:
            # Wait for the first process to find a match
            for future in futures:
                result = future.result()
                if result:
                    # Cancel all other futures since we found a match
                    for f in futures:
                        if not f.done():
                            f.cancel()
                    break
        except KeyboardInterrupt:
            print("\nSearch interrupted by user")
            for f in futures:
                if not f.done():
                    f.cancel()
            return

    total_time = time.time() - start_time

    # Print the results
    print("\nSUCCESS! Found matching hash:")
    print(f"String: {result['string']}")
    print(f"SHA256: {result['hash']}")
    print(f"Process ID: {process_args[futures.index(future)][2]}")
    print(f"Attempts: {result['attempts']}")
    print(f"Time: {result['time']:.2f} seconds")
    print(f"Hash rate: {result['hashes_per_second']:.2f} hashes/second")
    print(f"Total wall clock time: {total_time:.2f} seconds")


if __name__ == '__main__':
    main()
    # main()