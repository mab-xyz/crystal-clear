from web3 import Web3
from multiprocessing import Pool, Manager, Lock
import time
import config


def get_block(w3, block_number):
    """Fetch block trace using Web3."""
    return w3.manager.request_blocking("trace_block", [block_number])


def count_traces(w3, block_number):
    """Count traces in a given block."""
    try:
        block_traces = get_block(w3, block_number)
        return len(block_traces)
    except Exception as e:
        print(f"Error processing block {block_number}: {e}")
        return 0


def generate_block_ranges(start_block, end_block, chunk_size):
    """Generate ranges of blocks for chunk processing."""
    for i in range(start_block, end_block, chunk_size):
        yield range(i, min(i + chunk_size, end_block))


def process_chunk(block_range, node_url, total_traces, lock):
    """Process a range of blocks and update the total trace count."""
    w3 = Web3(Web3.HTTPProvider(node_url))  # Create a Web3 instance in each process
    local_count = 0

    for block_number in block_range:
        local_count += count_traces(w3, block_number)

    with lock:  # Safely update the shared total
        total_traces.value += local_count

    return local_count


def main():
    """Main function to process blocks using multiprocessing."""
    start_block = config.START
    end_block = config.END
    chunk_size = config.CHUNK_SIZE
    max_workers = config.MAX_PROCESSES

    # Shared variables for multiprocessing
    manager = Manager()
    total_traces = manager.Value("i", 0)  # Shared integer to count total traces
    completed_blocks = manager.Value("i", 0)  # Shared variable for progress tracking
    lock = manager.Lock()  # Lock for thread-safe updates

    total_blocks = end_block - start_block
    start_time = time.time()

    # Create block ranges
    block_ranges = list(generate_block_ranges(start_block, end_block, chunk_size))

    with Pool(processes=max_workers) as pool:
        # Pass tasks to the pool
        results = [
            pool.apply_async(
                process_chunk,
                args=(block_range, config.ETHEREUM_NODE_URL, total_traces, lock),
            )
            for block_range in block_ranges
        ]

        # Track progress
        for result in results:
            result.wait()  # Ensure the task is completed
            # Safely update completed_blocks
            with lock:
                completed_blocks.value += chunk_size
            percentage = min(100, (completed_blocks.value / total_blocks) * 100)
            print(f"Progress: {completed_blocks.value}/{total_blocks} ({percentage:.2f}%)")

    end_time = time.time()
    elapsed_time = end_time - start_time

    print(f"Total blocks ({start_block}-{end_block}): {total_blocks}")
    print(f"Total traces: {total_traces.value}")
    print(f"Execution time: {elapsed_time:.2f} seconds")

if __name__ == "__main__":
    main()
