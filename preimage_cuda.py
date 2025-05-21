#!/usr/bin/env python3
import numpy as np
import time
import argparse
import string
import random
import sys
from datetime import timedelta

# GPU imports
import pycuda.driver as cuda
import pycuda.autoinit
from pycuda.compiler import SourceModule

# CUDA kernel for SHA256 computation
cuda_sha256_kernel = """
// SHA256 implementation for CUDA
#include <stdio.h>
#include <stdint.h>

// SHA256 constants
__constant__ uint32_t k[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

// Right rotate function
__device__ uint32_t rotr(uint32_t x, int n) {
    return (x >> n) | (x << (32 - n));
}

// SHA256 functions
__device__ uint32_t ch(uint32_t x, uint32_t y, uint32_t z) {
    return (x & y) ^ (~x & z);
}

__device__ uint32_t maj(uint32_t x, uint32_t y, uint32_t z) {
    return (x & y) ^ (x & z) ^ (y & z);
}

__device__ uint32_t ep0(uint32_t x) {
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22);
}

__device__ uint32_t ep1(uint32_t x) {
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25);
}

__device__ uint32_t sig0(uint32_t x) {
    return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3);
}

__device__ uint32_t sig1(uint32_t x) {
    return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10);
}

// SHA256 hash computation
__device__ void sha256_transform(uint32_t state[8], const uint32_t data[16]) {
    uint32_t a, b, c, d, e, f, g, h, i, j, t1, t2, m[64];

    // Prepare message schedule
    for (i = 0, j = 0; i < 16; ++i, j += 4)
        m[i] = data[i];

    for (; i < 64; ++i)
        m[i] = sig1(m[i-2]) + m[i-7] + sig0(m[i-15]) + m[i-16];

    // Initialize working variables
    a = state[0];
    b = state[1];
    c = state[2];
    d = state[3];
    e = state[4];
    f = state[5];
    g = state[6];
    h = state[7];

    // Main loop
    for (i = 0; i < 64; ++i) {
        t1 = h + ep1(e) + ch(e, f, g) + k[i] + m[i];
        t2 = ep0(a) + maj(a, b, c);
        h = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
    }

    // Update state
    state[0] += a;
    state[1] += b;
    state[2] += c;
    state[3] += d;
    state[4] += e;
    state[5] += f;
    state[6] += g;
    state[7] += h;
}

// Main kernel function
extern "C" __global__ void find_hash_with_prefix(
    const char* charset,
    int charset_length,
    int string_length,
    uint32_t prefix_value,
    int prefix_length,
    char* result_string,
    uint32_t* result_hash,
    int* found_flag,
    uint64_t nonce_offset
) {
    uint64_t idx = blockIdx.x * blockDim.x + threadIdx.x;
    uint64_t nonce = idx + nonce_offset;

    // If solution already found, exit early
    if (*found_flag)
        return;

    // Buffer to build our test string
    char buffer[64] = {0};
    int pos = 0;

    // First add nonce as string
    uint64_t temp_nonce = nonce;
    char nonce_str[21];  // Max 20 digits for 64-bit int + null terminator
    int nonce_len = 0;

    do {
        nonce_str[nonce_len++] = '0' + (temp_nonce % 10);
        temp_nonce /= 10;
    } while (temp_nonce > 0);

    // Reverse the nonce string
    for (int i = nonce_len - 1; i >= 0; i--) {
        buffer[pos++] = nonce_str[i];
    }

    // Add separator
    buffer[pos++] = '-';

    // Generate the random string part using thread id and nonce
    for (int i = 0; i < string_length; i++) {
        // Use combination of nonce and position to select characters
        uint64_t val = nonce + i * 17 + blockIdx.x * 31 + threadIdx.x * 13;
        buffer[pos++] = charset[val % charset_length];
    }

    buffer[pos] = '\\0';  // Null terminate

    // Prepare for SHA256
    uint32_t state[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };

    // Prepare data blocks (simplified for demonstration)
    uint32_t data[16] = {0};
    for (int i = 0; i < pos; i++) {
        data[i / 4] |= ((uint32_t)buffer[i]) << (24 - 8 * (i % 4));
    }

    // Add padding
    int bit_len = pos * 8;
    int pad_pos = pos;

    // Add 1 bit followed by zeros
    data[pad_pos / 4] |= 0x80 << (24 - 8 * (pad_pos % 4));
    pad_pos++;

    // Ensure we have space for length
    if (pad_pos > 56) {
        sha256_transform(state, data);
        memset(data, 0, 64);
    }

    // Add length in bits at the end
    data[15] = bit_len;

    // Transform
    sha256_transform(state, data);

    // Check if the hash has the desired prefix
    // For simplicity, we'll check first 4 bytes - adjust based on prefix length
    uint32_t first_word = state[0];

    // Create mask for prefix bits
    uint32_t mask = 0;
    if (prefix_length >= 8) {
        mask = 0xFFFFFFFF;
    } else {
        mask = (1 << (prefix_length * 4)) - 1;
        mask = mask << (32 - prefix_length * 4);
    }

    // Isolate the relevant bits and compare
    uint32_t hash_prefix = first_word & mask;

    if ((hash_prefix >> (32 - prefix_length * 4)) == prefix_value) {
        // We found a match! Atomically check and set the found flag
        if (atomicCAS(found_flag, 0, 1) == 0) {
            // Copy result string
            for (int i = 0; i < pos; i++) {
                result_string[i] = buffer[i];
            }
            result_string[pos] = '\\0';

            // Copy hash values
            for (int i = 0; i < 8; i++) {
                result_hash[i] = state[i];
            }
        }
    }
}
"""


def hex_prefix_to_uint32(prefix):
    """Convert a hex prefix string to uint32 value for GPU comparison"""
    # Pad with zeros if needed
    if len(prefix) % 2 != 0:
        prefix = prefix + '0'

    # Convert to bytes and then to uint32
    value = int(prefix, 16)
    return value


def format_hash(hash_array):
    """Format a hash array to hex string"""
    return ''.join(f'{x:08x}' for x in hash_array)


def main():
    parser = argparse.ArgumentParser(description='GPU-accelerated SHA256 hash prefix finder')
    parser.add_argument('--prefix', type=str, default='000', help='Prefix to search for (in hex)')
    parser.add_argument('--length', type=int, default=10, help='Length of random string part')
    parser.add_argument('--threads', type=int, default=256, help='Number of threads per block')
    parser.add_argument('--blocks', type=int, default=64, help='Number of blocks to launch')

    args = parser.parse_args()

    # Validate prefix (must be hex)
    try:
        int(args.prefix, 16)
    except ValueError:
        print(f"Error: Prefix '{args.prefix}' must be a valid hexadecimal string")
        return

    prefix_length = len(args.prefix)
    prefix_value = hex_prefix_to_uint32(args.prefix)

    print(f"Searching for SHA256 hash with prefix: {args.prefix}")
    print(f"Using {args.blocks} blocks with {args.threads} threads each")

    # Compile the CUDA kernel
    mod = SourceModule(cuda_sha256_kernel)
    find_hash_kernel = mod.get_function("find_hash_with_prefix")

    # Setup GPU buffers
    charset = np.array(list(string.ascii_letters + string.digits), dtype=np.dtype('c'))
    charset_length = len(charset)

    # Allocate memory for results
    result_string = np.zeros(64, dtype=np.dtype('c'))
    result_hash = np.zeros(8, dtype=np.uint32)
    found_flag = np.zeros(1, dtype=np.int32)

    # Copy to GPU
    charset_gpu = cuda.mem_alloc(charset.nbytes)
    cuda.memcpy_htod(charset_gpu, charset)

    result_string_gpu = cuda.mem_alloc(result_string.nbytes)
    result_hash_gpu = cuda.mem_alloc(result_hash.nbytes)
    found_flag_gpu = cuda.mem_alloc(found_flag.nbytes)

    # Initialize found flag
    cuda.memcpy_htod(found_flag_gpu, found_flag)

    # Track performance
    total_hashes = 0
    batch_size = args.blocks * args.threads
    start_time = time.time()
    last_report_time = start_time
    nonce_offset = 0

    try:
        # Main mining loop
        while True:
            # Launch kernel
            find_hash_kernel(
                charset_gpu, np.int32(charset_length),
                np.int32(args.length),
                np.uint32(prefix_value),
                np.int32(prefix_length),
                result_string_gpu,
                result_hash_gpu,
                found_flag_gpu,
                np.uint64(nonce_offset),
                block=(args.threads, 1, 1),
                grid=(args.blocks, 1)
            )

            # Check if we found a result
            cuda.memcpy_dtoh(found_flag, found_flag_gpu)

            if found_flag[0] == 1:
                # Get the results
                cuda.memcpy_dtoh(result_string, result_string_gpu)
                cuda.memcpy_dtoh(result_hash, result_hash_gpu)

                # Convert result string from bytes to string
                result_str = ''.join(chr(x) for x in result_string if x != 0)
                hash_hex = format_hash(result_hash)

                # Calculate stats
                end_time = time.time()
                total_time = end_time - start_time
                hashes_per_second = total_hashes / total_time if total_time > 0 else 0

                # Print results
                print("\nSUCCESS! Found matching hash:")
                print(f"String: {result_str}")
                print(f"SHA256: {hash_hex}")
                print(f"Time: {timedelta(seconds=total_time)}")
                print(f"Average hash rate: {hashes_per_second / 1000000:.2f} MH/s")
                break

            # Update stats
            total_hashes += batch_size
            nonce_offset += batch_size
            current_time = time.time()

            # Report progress every second
            if current_time - last_report_time >= 1.0:
                elapsed = current_time - start_time
                rate = total_hashes / elapsed if elapsed > 0 else 0
                print(
                    f"\rHashes: {total_hashes:,} | Rate: {rate / 1000000:.2f} MH/s | Time: {timedelta(seconds=int(elapsed))}",
                    end="")
                sys.stdout.flush()
                last_report_time = current_time

    except KeyboardInterrupt:
        print("\nSearch interrupted by user")

    finally:
        # Free GPU memory
        charset_gpu.free()
        result_string_gpu.free()
        result_hash_gpu.free()
        found_flag_gpu.free()


if __name__ == "__main__":
    main()