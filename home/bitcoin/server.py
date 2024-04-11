import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from urllib.parse import parse_qs
import logging
import subprocess
import ssl
import re
import copy
import os

# set the amount as you please (for testnest it is recommended to use a small amount)
amount = 0.00001
address_regex = r"[a-km-zA-HJ-NP-Z1-9]{25,50}$"
transaction_regex = r"[0-1]{5,11}[a-fA-F0-9]{100,800}"

command_start = ['/home/bitcoin/bitcoin-0.26.1/bin/bitcoin-cli', '-conf=/home/bitcoin/bitcoin-node/bitcoin.conf']
challenge_response = "Aegfote4P6GXJZrEtpl4LrV2bhCPYskHWmtNghJ7mrc"

# change the address to the address of the wallet you created (see readme for instructions)
address_stored_btc = 'tb1qfpd4u746w6m8305mzuwfy6494m402cjurkeprr'


def valid_hex(result):
    """Verify if string is valid hexadecimal"""
    try:
        int(result, 16)
        return True
    except ValueError:
        return False


def valid_json_response(data):
    """Verify if transaction response is valid json, should contain a hash value with hexadecimal string"""
    try:
        data = json.loads(data)
        s = json.dumps(data, indent=4, sort_keys=True)
        logging.info(f'JSON dumps: {s}')
        logging.info(f"Hash: {data['hash']}")
        return valid_hex(data['hash'])
    except ValueError:
        return False


class S(BaseHTTPRequestHandler):
    def _set_success_response(self):
        """Return 200 if request was successfully executed on regtest network"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _set_error_response(self):
        """Return 404 if request did not succeed"""
        self.send_error(404)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(f"Request failed, see server logs for more information".encode('utf-8'))

    def add_btc(self, query_params):
        """Validate input and if so execute sendtoaddress command, which transfers funds from predefined bitcoin
        wallet address to the requested address. We use sendtoadress as we can directly use the credits and
        call generatetoaddress afterwards to make sure the transaction is added to a block. We use a cron job to
        generate bitcoins to the predefined address"""
        if 'address' in query_params and len(query_params) == 1:
            address = query_params["address"][0]
            logging.info(f'Trying to add {amount} to address: {address}')

            if not re.match(address_regex, address):
                logging.info(f'Address is not valid')
                self._set_error_response()
                return

            command = copy.deepcopy(command_start)
            command.extend(['sendtoaddress', address, f'{amount}'])
            logging.info(f'COMMAND IS: {command}')

            result = subprocess.run(command, stdout=subprocess.PIPE)
            logging.info(f'Result is: {result}')

            if result.returncode != 0 or not valid_hex(result.stdout):
                logging.info(f'Result was not correct hexstring: {result.stdout}')
                self._set_error_response()
                return

            command = copy.deepcopy(command_start)
            command.extend(['generatetoaddress', '1', address_stored_btc])
            subprocess.run(command, stdout=subprocess.PIPE)

            logging.info(f'Added {amount} to bitcoin address: {address}')
            self._set_success_response()
            self.wfile.write(f"Added {amount} to bitcoin address: {address}".encode('utf-8'))
        else:
            self._set_error_response()

    def generate_block(self, query_params):
        """Execute transaction id if input is valid and only return success if transaction succeeded"""
        if 'tx_id' in query_params and len(query_params) == 1:
            transaction = query_params["tx_id"][0]
            logging.info(f'Received transaction: {transaction}')

            if not valid_hex(transaction):
                logging.info(f'Transaction is not valid')
                self._set_error_response()
                return

            command = copy.deepcopy(command_start)
            command.extend(['generateblock', address_stored_btc, f'["{transaction}"]'])

            result = subprocess.run(command, stdout=subprocess.PIPE)
            logging.info(f'Result is: {result}')

            if result.returncode != 0 or not valid_json_response(result.stdout):
                logging.info(f'Transaction failed, error code: {result.returncode} and output: {result.stdout}')
                self._set_error_response()
                return

            logging.info(f'Successfully received transaction: {transaction}')
            self._set_success_response()
            self.wfile.write(f"Successfully received transaction: {transaction}".encode('utf-8'))
        else:
            self._set_error_response()

    def serveACME(self, challenge):
        """Used for refresing the letsencrypt certificate"""
        self._set_success_response()
        logging.info(f'Acme challenge succesful')
        self.wfile.write(f"{challenge}.{challenge_response}".encode('utf-8'))
        
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")

    def do_GET(self):
        """Handle HTTP get requests"""
        logging.info("GET request,\nPath: %s\n", str(self.path))
        query_components = parse_qs(urlparse(self.path).query)
        path = urlparse(self.path).path
        if path == '/addBTC':
            self.add_btc(query_components)
        elif path == '/generateBlock':
            self.generate_block(query_components)
        elif path.startswith('/.well-known/acme-challenge/'):
            challenge = path.rsplit('/', 1)[-1]
            self.serveACME(challenge)
        else:
            self._set_error_response()

    def do_POST(self):
        self._set_error_response()


def run(server_class=HTTPServer, handler_class=S, port=443):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    httpd.socket = ssl.wrap_socket(httpd.socket, keyfile="/PATH_TO_YOUR/privkey.pem",
                                   certfile='/PATH_TO_YOUR/fullchain1.pem', server_side=True)
    logging.info('Starting server...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping server...\n')


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
