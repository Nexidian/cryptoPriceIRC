import socket
import sys
import signal
import requests
from time import sleep

# List of users who can issue commands
admins = ["x31xc0"]

# The names say it all. Just remember the channel name needs the # in front of it
irc_channel = '#test'
irc_ident = 'crypto'
irc_nick = 'crypto2'
irc_realname = 'x31xc0_test'
host = '127.0.0.1'
# 6667 is the standard port for IRC servers
port = 6667
# This is the command string used to talk to the bot
command_str = '!crypto'
# Create a socket object. This will be used to read/send to the IRC server
s = socket.socket()

# This can be as high or low as you want. 1024 is perfectly fine as it is longer
# than the max message anyway
BUFFER_SIZE = 1024
RECV_BUFFER = ''


# Signal handler to listen to and trap and SIGs we recieve. This will stop the program from crashing unclean
def signal_handler(sig_signal, frame):
    print("[-] SIGINT captured. Closing bot: {0} {1}".format(sig_signal, frame))
    s.close()
    sys.exit(0)


# Register the sig handler
signal.signal(signal.SIGINT, signal_handler)


# This function gets called whenever we get any data from the socket. It will parse the response an respond to messages
# or call a function to respond
def parse_response(_list, _raw):
    for line in _list:
        line = line.rstrip()
        line = line.split()
        print(line)

        # Need to respond to any ping requests or the bot will get kicked
        if line[0] == "PING":
            content = "PONG {0}\r\n".format(line[1])
            s.send(bytearray(content, 'utf8'))

        # Some IRC servers like UnrealIRCd require a welcome message to be displayed before you can join a channel
        # Not all IRC servers do this but ok to do it anyway
        # '001' is the response code for the welcome message.
        if line[1] == '001':
            s.send(bytes("JOIN {0}\r\n".format(irc_channel), 'utf8'))

        # Any message sent by users in the same channel as the bot will be labelled PRIVMSG
        if line[1] == "PRIVMSG":
            # Get the count of the elements in the response list
            size = len(line)
            # Create an index to start from because we have split the response into a list
            # for e.g. [':x31xc0!luke@Clk-5A6CB62E', 'PRIVMSG', '#test', ':hey']
            # Anything after including the 3rd element will be the message, so we can simply iterate through the size
            # of the list and stitch together the message
            i = 3
            message = ""
            while i < size:
                message += line[i] + ' '
                i = i + 1
            message = message.strip(':')

            # Look for command
            if (message.split(' ', 1)[0]) == command_str:
                # Get the person who sent the message
                sender = ""
                for char in line[0]:
                    if char == "!":
                        break
                    if char != ":":
                        sender += char

                # Get the sender of the message
                send_destination = line[2]
                # Send to ParseCommands once we have everything
                parse_commands(sender, send_destination, message)


def parse_commands(_sender, _send_destination, _message):
    # Only users listed in admins can issue commands
    if _sender in admins:
        print("Sender: {0} Message: {1} From: {2}".format(_sender, _message, _send_destination))
        _message = _message.replace(command_str, "")
        _message = _message.strip()
        print("Stripped:{0}".format(_message))

    command = _message.split(' ', 1)[0]

    sendto = ''

    if _send_destination == irc_ident:
        sendto = _sender
    else:
        sendto = _send_destination

    if (_message.split(' ', 1)[0]) == "say":
        # This is if the bot gets a PM rather than just listening in a chan
        send_raw_text(_message, sendto)

    if command == "check":
        check_price(_message, sendto)

    if (_message.split(' ', 1)[0]) == "join":
        join(_message)

    if (_message.split(' ', 1)[0]) == "quit":
        quit()


def send_raw_text(_message, _send_destination):
    _message = _message.replace("say", "")
    _message = _message.strip()
    s.send(bytes("PRIVMSG {0} {1}\r\n".format(_send_destination, _message.encode("UTF-8"))))


# Check crypto price with a ticker name
def check_price(_raw_message, _send_destination):
    # Remove the command as we don't need it now
    ticker = _raw_message.replace("check", "")
    # Strip any white space left over
    ticker = ticker.strip()
    # Grab the first word only e.g. "bitcoin sometext" would become just "bitcoin"
    ticker = ticker.split(' ', 1)[0]
    # Early exit if we don't have something to check
    if ticker != '':
        # Use the requests library to simplify a cURL request
        coinmarket_response = requests.get('https://api.coinmarketcap.com/v1/ticker/{0}'.format(ticker))
        # Convert the response object to a JSON string for parsing
        response_json = coinmarket_response.json()

        # Generic check for error
        if 'error' in response_json:
            s.send(bytes("PRIVMSG {0} {1}\r\n".format(_send_destination,
                                                      'Could not find ticker with name '+ticker), "utf8"))
        else:
            # Format the message to return to the channel
            message = "{0} price is at: {1}".format(ticker, response_json[0]['price_usd'])
            # Send the message back to the channel
            s.send(bytes("PRIVMSG {0} {1}\r\n".format(_send_destination, message), "utf8"))


# Tells the bot to join a given channel
def join(_chan):
    _chan = _chan.replace("join", "")
    _chan = _chan.strip()
    s.send(bytes("JOIN {0}\r\n".format(_chan)))


# Removes the bot from the IRC and closes the connection
def quit():
    s.send(bytes("QUIT\r\n", "utf8"))
    close_connection()


# Attempts to connect to an IRC with the credentials given
def connect_to_irc():
    try:
        s.connect((host, port))
    except socket.error as msg:
        print('Connect failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
        sys.exit(msg[0])

    s.send(bytes("NICK {0}\r\n".format(irc_nick), 'utf8'))
    s.send(bytes("USER {0} {1} test :{2}\r\n".format(irc_ident, host, irc_realname), 'utf8'))
    # Sleep needed to receive mode from IRC
    sleep(2)


# Close the socket connection and exit the script
def close_connection():
    s.close()
    sys.exit(0)


connect_to_irc()

# Main loop
while 1:
    # Constantly read 1024 bytes at a time from the socket
    RECV_BUFFER = RECV_BUFFER + s.recv(BUFFER_SIZE).decode("UTF-8")
    # This is needed for parsing commands/messages from the IRC
    raw = RECV_BUFFER
    # Split the buffer into a list for easier parsing
    response = RECV_BUFFER.split("\n")
    # Clea RECV_BUFFER for the next read cycle
    RECV_BUFFER = response.pop()
    # Time to parse the response and do stuff
    parse_response(response, raw)
