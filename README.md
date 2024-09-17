# SCSC

Analyzing the smart contract supply chain.

## Prerequisites

TODO

## Usage

### Single contract supply chain

Computes the supply chain of a smart-contract at a given block (or over a block period TODO)

    ./scsc --block 1234 --address 0xabcdef012345678
    ./scsc --json  --block 1234 --address 0xabcdef012345678 (TODO)

### Contract graph 

    ./scsc --graph --from-block 1234 --to-block 2234  --output graph.dot

TODO: explain the medadata available on the graph (supplier, mutable, vulnerable, ...)
