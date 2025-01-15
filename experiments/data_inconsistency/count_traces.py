from web3 import Web3
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
import config


def get_block(w3, block_number):
    return w3.manager.request_blocking("trace_block", [block_number])


def count_traces(w3, block_number):
    try:
        block_traces = get_block(w3, block_number)
        return len(block_traces)
    except Exception as e:
        print(f"Error processing block {block_number}: {e}")
        return 0


def generate_block_ranges(start_block, end_block, chunk_size):
    for i in range(start_block, end_block, chunk_size):
        yield range(i, min(i + chunk_size, end_block))


def process_chunk(w3, block_range, total_traces, lock):
    local_count = 0
    for block_number in block_range:
        local_count += count_traces(w3, block_number)

    with lock:  # Update the shared total safely
        total_traces[0] += local_count

    return local_count


def main():
    w3 = Web3(Web3.HTTPProvider(config.ETHEREUM_NODE_URL))
    start_block = config.START
    end_block = config.END 
    chunk_size = config.CHUNK_SIZE
    max_workers = config.MAX_THREADS

    total_traces = [0]  # Shared variable for the total trace count
    lock = threading.Lock()  # Lock for thread-safe updates
    total_blocks = end_block - start_block
    completed_blocks = 0  # To track the completed blocks

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for block_range in generate_block_ranges(start_block, end_block, chunk_size):
            futures.append(executor.submit(process_chunk, w3, block_range, total_traces, lock))

        for future in as_completed(futures):
            completed_blocks += chunk_size
            percentage = min(100, (completed_blocks / total_blocks) * 100)
            print(f"Progress: {percentage:.2f}%")

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Total blocks: {total_blocks}")
    print(f"Total traces: {total_traces[0]}")
    print(f"Execution time: {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
