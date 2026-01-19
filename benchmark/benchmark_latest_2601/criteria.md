### The selection


| step | criteria| number | notes |
|--|--|--|--|
| 1 | source | 622 | |
| 2| On Ethereum | 249 | |
| 3 | Attack tx provided| 213 | |
| 4 | find normal tx in the same block | (207) 414 | ETH-068/113: no contract tx found in block ETH-051/127/136/154: could not load attack tx(due to they are not on Ethereum)|

How normal tx is find:
Select a tx which interacted with a contract randomly in the same block of attack tx.