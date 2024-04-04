# Bitcoin-Regtest-Server

This repo contains all relevant code and documentation needed for running a Regtest bitcoind server. This server was needed for the Blockchain engineering project (see [issue 5986](https://github.com/Tribler/tribler/issues/5986) for more information on the project). We had to create our own server as at the time of writing, Taproot was still unreleased. This means that we had to run our own Bitcoin Regtest network to make it possible to use Taproot. 
## Implementation

At the ending of [documentation](https://github.com/Tribler/trustchain-superapp/blob/master/currencyii/README.md) we see the architecture overview. This overview describes how the two servers located at https://taproot.tribler.org work together with the android app. The application consists of two main parts, the android app and the regtest server. As we are expanding upon the previous group we will only discuss the added regtest server and how it is integrated into the app. The app makes several connections to our regtest server. First, to add bitcoin to the wallet of a user. When the user clicks on the UI button "getBTC" we call the https://taproot.tribler.org/addBTC?address="yourwalletaddres" where the python server validates the adres and transfers 10 BTC from a "bank" account to desired wallet by calling RPC commands via bash to the bitcoind regtest server. We make sure that the "bank" account has plenty resources via a cronjob which adds bitcoins every 15 minutes to the address. This setup was chosen as we can now directly transfer funds to a user rather than first mining the blocks everytime the HTTPS requests is received, which would result in much slower respond times. The balance is updated in the UI via BitcoinJ, which connects to our regtest server directly to retrieve the wallet balance. This is the onlything BitcoinJ does: keep track of balance and UTXOs. Since BitcoinJ did not have Taproot support at the time of writing, this was the only way to make it work. We wrote our own Taproot library, which can be found in the codebase, and create transactions using this library. Hopefully, BitcoinJ has Taproot support when you read this, and if so, we highly suggest refactoring the code to use that instead of our own library. Lastly, the request to https://taproot.tribler.org/generateBlock?tx_id="transaction_in_hex" can be made. This HTTPS request is made by the app once we have collected enough signature to process the transaction.

The server uses Letsencrypt to retrieve a certificate for HTTPS. This certificate is automatically renewed via cronjob (crontab of root user) which runs on the first day of the month. To receive the signature ACME identification is needed, while this could be done via DNS, HTTP was easier for us. So also you will find code in the python server that performs the response to an ACME challenge. The code for server (and bash history for help) is all on this github. This github contains all of our scripts, which are fully documented. In addition, our own library, as well as all other code, is fully documented. Please check out the code with the documentation to understand the flow in the app and how everything works together.

## Bitcoin commands
- Start: ./home/bitcoin/bitcoin-0.26.1/bin/bitcoind -conf=[Absolute path to the config, it is located in home/bitcoin/bitcoin-node/bitcoin.conf]
- Stop: ./home/bitcoin/bitcoin-0.26.1/bin/bitcoin-cli -conf=[Absolute path to the config, it is located in home/bitcoin/bitcoin-node/bitcoin.conf] stop
- For more commands see: https://chainquery.com/bitcoin-cli

## Reset bitcoin server
- delete everything in the .bitcoin folder
- restart bitcoind
- create a new wallet
- load the new wallet
- generate a new address for the wallet
- copy this address to the python server and the crontab job
- make sure all devices connected to the network are reset as well (otherwise they do not have matching blockchains)

## Reset python server
- ```ps aux | grep python```
- find process ID (26546):
```root     26546  0.0  0.2  22732 19136 ?        S    Apr28   3:43 python3 /home/bitcoin/server.py```
- kill process: ```kill 26546```
- restart server: ```nohup python3 /home/bitcoin/server.py &```
- verify it is running ```tail -f /home/bitcoin/nohup.out```

## Future work
- Wrap the server using Nginx for security & availability (also easier to refresh certificate).
- Automatic resetting of bitcoin server if no more balance (regtest can only generate 15000 bitcoin).
