# Quickserve
Quickly serve a PHP project. Do you want a server:

- That is perfectly suited for your PHP project with a single index file that
  should receive all requests, except those for static resources.
- That quickly starts and stops when you request it.
- That runs in any directory right away.
- That handles multiple requests in parallel.
- That can have multiple instances running at the same time.

Then this is what you want. This is a quick python script that allows you to
run a server using nginx and php-fpm in any server. This script will create
some temporary configuration for nginx and php-fpm and then run these services
using these configuration files. When you're done developing you just press
`Ctrl + C` and the script stops the server and removes all temporary files,
leaving you with a nice and clean filesystem.

## Requirements
This script requires recent versions of `nginx` and `php-fpm`. By default the
script requires these commands to be available on the `PATH` for the user
you're executing the script under.

- **Windows**: I don't think this is going to work for you.
- **Mac OS**: You can use macports to get nginx and a more recent version
  of php-fpm. Note that macports installs php-fpm for php 5.4 as a binary
  with the name `php-fpm54`. The `php-fpm` you'll find installed is the one
  provided with Mac OS. Either edit the script, provide a command line
  parameter every time you're using the script or create a symlink that
  precedes the one Mac OS provides.
- **Linux**: nginx and php-fpm are available in most recent distributions their
  package managers. Just make sure nginx and php-fpm are available on the
  `PATH` and you should be good to go.

## HTTP2 and TLS
To enable HTTP2 install nginx version 1.9.5 or higher and configure a TLS
certificate. By default quickserve will look in /usr/local/etc/nginx/ for a
cert.pem and a cert.key file. Alternatively, you can provide certificate and
key files using the parameters --nginx-key and --nginx-cert

Use the following command to generate a self-signed certificate for `localhost`:

```sh
openssl req -x509 -sha256 -newkey rsa:2048 \
-keyout /usr/local/etc/nginx/cert.key -out /usr/local/etc/nginx/cert.pem \
-days 1024 -nodes -subj '/CN=localhost'

chmod 0600 /usr/local/etc/nginx/cert.key
```

If you want to use other (local) domains over HTTP2, generate a certificate
with multiple (wildcard) domains:

Create a file `openssl.cnf`:

```boilerplate
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = localhost

[v3_req]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
basicConstraints = CA:TRUE
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = *.localhost.dev
DNS.3 = *.example.dev
IP.1 = 127.0.0.1
```

Generate a certificate:

```sh
openssl req -x509 -sha256 -newkey rsa:2048 \
-keyout /usr/local/etc/nginx/cert.key \
-out /usr/local/etc/nginx/cert.pem \
-days 1024 -nodes -config openssl.cnf
```

## Getting started
Want to get some help? USe `--help` on the script to see what options are
available. Some examples:

```sh
# Run the script in the current directory using app.php as the index
quickserve.py app.php

# Change the root folder to public and use index.php (default) as the index
quickserve.py -r ./public

# Determine the root and index by giving a path
quickserve.py -b ~/development/website/public/app.php

# Change the port and interface (only allow from localhost on port 1234)
quickserve.py -i 127.0.0.1 -p 1234

# Use a different php-fpm binary
quickserve.py --php-fpm-bin php-fpm54
```
