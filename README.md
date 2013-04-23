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
some temporary configuration for nginx and php-pfm and then run these services
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

## Getting started
Want to get some help? USe `--help` on the script to see what options are
available. Some examples:

```sh
# Run the script in the current directory using app.php as the index
quickserve.py app.php

# Change the root folder to public and use index.php (default) as the index
quickserve.py -r ./public

# Change the port and interface (only allow from localhost on port 1234)
quickserve.py -i 127.0.0.1 -p 1234

# Use a different php-fpm binary
quickserve.py --php-fpm-bin php-fpm54
```
