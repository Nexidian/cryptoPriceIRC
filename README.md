# cryptoPriceIRC
For the challenge i decided to go with an IRC bot as they are simple to implement without needing rely on any 3rd 
party libraries or modules. I have built quite a few IRC bots in my time with varying levels of complexity but almost all
of them have been written in Perl. I took this opportunity to use Python instead. 

The IRC protocol is pretty simplistic in its nature and has been heavily documented over the many years its been around.
The best source of information for this protocol however is the IRC RFC would you can find here https://tools.ietf.org/html/rfc1459

### How does it work?
When the script has run it will attempt to connect to an IRC server with the given credentials. You can have a look at 
the RFC to get more information about individual parts but the basic information needed is as follows
```python
irc_ident = 'crypto'
irc_nick = 'crypto2'
irc_realname = 'x31xc0_test'
```
This information is needed to authenticate yourself with the IRC server and it needs to be provided in a certain order,
again you can check the RFC for more information, but the basic order is as follows

```python
s.send(bytes("NICK {0}\r\n".format(irc_nick), 'utf8'))
s.send(bytes("USER {0} {1} test :{2}\r\n".format(irc_ident, host, irc_realname), 'utf8'))
```
First we have to supply our nick, which is the handle we will be using, this along with the ident is used to register
a user with the name service on the IRC. This process will prevent multiple users having the same name. The IRC will
recieve a message like this 

```text
NICK crypto2
USER CRYPTO 127.0.0.1 x31xc0_test
```
When we send this data to the server it will begin the registration process. We can only join a channel and begin sending
messages once the IRC has recognised and registered us as a user. This needs to happen with every connection. Once the 
IRC is happy and we are good to go we can join a channel with the following command 

```python
s.send(bytes("JOIN {0}\r\n".format(irc_channel), 'utf8'))
```

### Parsing commands
When we recieve data from the socket it looks a little something like this
```text
:x31xc0!luke@Clk-5A6CB62E PRIVMSG #test :hello
```
To make this a little easier to read and parse we split the string into a list so it then looks like this

```text
[':x31xc0!luke@Clk-5A6CB62E', 'PRIVMSG', '#test', ':hello']
```
This makes parsing the response a little easier, we can easily check if this is a message and which channel it came from
by querying the list e.g. 

```python
# This would be #test given the example response above
channel = response[1]
``` 

The parse_response method takes the response list as a parameter and attempts to decide which type of message it is
```python
def parse_response(_list, _raw):
    for line in _list:
        line = line.rstrip()
        line = line.split()
        print(line)

        if line[0] == "PING":
            content = "PONG {0}\r\n".format(line[1])
            s.send(bytearray(content, 'utf8'))

        if line[1] == '001':
            s.send(bytes("JOIN {0}\r\n".format(irc_channel), 'utf8'))

        if line[1] == "PRIVMSG":
            size = len(line)
            i = 3
            message = ""
            while i < size:
                message += line[i] + ' '
                i = i + 1
            message = message.strip(':')

            if (message.split(' ', 1)[0]) == command_str:
                sender = ""
                for char in line[0]:
                    if char == "!":
                        break
                    if char != ":":
                        sender += char

                send_destination = line[2]
                parse_commands(sender, send_destination, message)
```
If recieve a message in the channel we check for the presence of our command string. This is used for issuing commands
to the bot. 

That is essentially it, once we detect the command string we have a look through the parse_commands function to see if 
any match and execute them. The main command here is the check_price command which is why i built this bot. 

```python
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
```
We simply perform a cURL request to the coinmarketcap API for the price information given a coin name. This is returned
to us in JSON format so its just a case of parsing this to get the price we need and send that back to the channel

This is what a simple interaction with the bot looks like

```text
17:18 -!- crypto2 [crypto@Clk-5A6CB62E] has joined #test
17:18 <@x31xc0> !crypto check iota
17:18 < crypto2> iota price is at: 3.64415
17:19 <@x31xc0> !crypto check bitcoin
17:19 < crypto2> bitcoin price is at: 15133.0
```


