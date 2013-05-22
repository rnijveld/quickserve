#!/usr/bin/env python
from subprocess import Popen, PIPE
from threading import Thread
from os import path, mkdir, getcwd, remove, getenv, environ, pathsep
from getpass import getuser
from random import choice
from string import hexdigits
from argparse import ArgumentParser
from shutil import rmtree
import sys

# Parse arguments
parser = ArgumentParser(description="Start a quick server for PHP projects with an index file. This uses nginx and php-fpm.")
parser.add_argument('-v', '--verbose', action='store_true', help="Display output from php-fpm and nginx")
parser.add_argument('-p', '--port', metavar='port', type=int, default=8080, help='Port number (default: 8080)')
parser.add_argument('-i', '--interface', metavar='address', type=str, default='*', help='Interface to listen to (default: *)')
parser.add_argument('-l', '--log', action='store_true', help="If set, show error log output")

rootgroup = parser.add_mutually_exclusive_group()
rootgroup.add_argument('-r', '--root', metavar='dir', type=str, help="Web root directory (default: .)")
rootgroup.add_argument('-b', '--base-index', action='store_true', help="Assume the directory the index file is in is the webroot")

parser.add_argument('--handlers', metavar='n', type=int, default=6, help="Number of PHP handlers (default: 6)")
parser.add_argument('--workers', metavar='n', type=int, default=2, help="Number of nginx workers (default: 2)")
parser.add_argument('--restart-after', metavar='n', type=int, default=0, help="Restart php-fpm processes after this amount of requests, 0 means no restarts (default: 0)")
parser.add_argument('--php-fpm-bin', metavar='path', type=str, default='php-fpm', help="Location of php-fpm binary (will search path if required) (default: php-fpm)")
parser.add_argument('--nginx-bin', metavar='path', type=str, default='nginx', help="Location of nginx binary (will search path if required) (defaults: nginx)")
parser.add_argument('-n', '--no-php-fpm', action='store_true', help="Disable php-fpm")
parser.add_argument('index', metavar='index_file', type=str, nargs='?', help="The root index file (default: index.php)")
args = parser.parse_args()

# Initialize the options dict
options = {}

# Generic config
options['HANDLERS'] = args.handlers
options['WORKERS'] = args.workers
options['RESTART_AFTER'] = args.restart_after

# Set root to default if it isn't set, and make it an absolute path
args.root = getcwd() if args.root == None else path.abspath(args.root)

# If we don't have an index specified, try finding one
if args.index == None:
    defaults = environ.get('QS_INDEX_PATH')
    if defaults != None:
        for option in defaults.split(pathsep):
            if path.isfile(option):
                args.base_index = True
                args.index = option
                break

    # Still nothing found? Assume the default
    if args.index == None:
        args.index = 'index.php'

# Base directory extraction
if args.base_index:
    root, indexfile = path.split(args.index)
    if root == '' or root == None:
        root = getcwd()

    if not path.isabs(root):
        root = path.abspath(root)
    options['LOCATION'] = root
    options['INDEX'] = indexfile
else:
    options['LOCATION'] = args.root
    options['INDEX'] = args.index

# Other options
options['INTERFACE'] = args.interface
options['PORT'] = args.port
options['TMP_DIR'] = '/tmp'
options['DEBUG'] = args.verbose
options['SHOW_LOGS'] = args.log
options['PHP_FPM_ENABLED'] = not args.no_php_fpm

# Detailed config
options['MAX_CLIENT_BODY_SIZE'] = '100M'
options['ERROR_REPORTING'] = 'E_ALL'
options['DISPLAY_ERRORS'] = 'on'
options['DATE_TIMEZONE'] = 'Europe/Amsterdam'

# Paths
options['NGINX_CMD'] = args.nginx_bin
options['PHPFPM_CMD'] = args.php_fpm_bin

# Username
if getuser() == 'root':
    options['NGINX_USER'] = getuser()
    options['PHP_USER'] = getenv('SUDO_USER')
    options['USER'] = 'user = {0}'.format(options['PHP_USER'])
else:
    options['NGINX_USER'] = getuser()
    options['PHP_USER'] = getuser()
    options['USER'] = ''

# Random file names for this instance
options['RAND'] = ''.join(choice(hexdigits[:16]) for _ in xrange(6))

# PHP-FPM configuration
options['PHPFPM_SOCKET_FILE'] = path.join(options['TMP_DIR'], 'php-fpm-' + options['RAND'] + '.socket')
options['PHPFPM_CONFIG_FILE'] = path.join(options['TMP_DIR'], 'php-fpm-config-' + options['RAND'] + '.ini')
options['PHPFPM_PID_FILE'] = path.join(options['TMP_DIR'], 'php-fpm-pid-' + options['RAND'] + '.pid')
options['PHPFPM_ERROR_LOG'] = path.join(options['TMP_DIR'], 'php-fpm-error-' + options['RAND'] + '.log')
options['PHPFPM_CONFIG'] = """
[global]
error_log={PHPFPM_ERROR_LOG}
daemonize=no

[www]
{USER}
listen = {PHPFPM_SOCKET_FILE}
pm = static
pm.max_children = {HANDLERS}
pm.max_requests = {RESTART_AFTER}
php_value[upload_max_filesize] = {MAX_CLIENT_BODY_SIZE}
php_value[post_max_size] = {MAX_CLIENT_BODY_SIZE}
php_value[error_reporting] = {ERROR_REPORTING}
php_flag[display_errors] = {DISPLAY_ERRORS}
php_value[date.timezone] = {DATE_TIMEZONE}
php_flag[short_open_tag] = off
php_value[xdebug.max_nesting_level] = 250
php_flag[xdebug.remote_enable] = on
php_flag[xdebug.remote_connect_back] = on
php_admin_value[error_log] = {PHPFPM_ERROR_LOG}
php_admin_flag[log_errors] = on
"""
options['PHPFPM_CONFIG'] = options['PHPFPM_CONFIG'].format(**options)

# Nginx configuration
options['NGINX_CONFIG_FILE'] = path.join(options['TMP_DIR'], 'nginx-' + options['RAND'] + '.conf')
options['NGINX_PID_FILE'] = path.join(options['TMP_DIR'], 'nginx-pid-' + options['RAND'] + '.pid')
options['NGINX_TMP_DIR'] = path.join(options['TMP_DIR'], 'nginx-tmp-' + options['RAND'])
options['NGINX_ERROR_LOG'] = path.join(options['TMP_DIR'], 'nginx-error-' + options['RAND'] + '.log')
options['NGINX_CLIENT_TMP'] = path.join(options['NGINX_TMP_DIR'], 'client_temp')
options['NGINX_PROXY_TMP'] = path.join(options['NGINX_TMP_DIR'], 'proxy_temp')
options['NGINX_FASTCGI_TMP'] = path.join(options['NGINX_TMP_DIR'], 'fastcgi_temp')
options['NGINX_UWSGI_TMP'] = path.join(options['NGINX_TMP_DIR'], 'uwsgi_temp')
options['NGINX_SCGI_TMP'] = path.join(options['NGINX_TMP_DIR'], 'scgi_temp')
options['NGINX_CONFIG'] = """
error_log {NGINX_ERROR_LOG} warn;

pid {NGINX_PID_FILE};
worker_processes {WORKERS};
events {{ worker_connections  1024; }}
daemon off;
master_process off;
http {{
    client_body_temp_path {NGINX_CLIENT_TMP} 1 2 3;
    proxy_temp_path {NGINX_PROXY_TMP} 1 2 3;
    fastcgi_temp_path {NGINX_FASTCGI_TMP} 1 2 3;
    uwsgi_temp_path {NGINX_UWSGI_TMP} 1 2 3;
    scgi_temp_path  {NGINX_SCGI_TMP} 1 2 3;

    access_log off;

    types {{
        text/html                             html htm shtml;
        application/xhtml+xml                 xhtml;
        text/plain                            txt;
        text/xml                              xml;

        text/css                              css less sass scss;
        application/x-javascript              js;
        text/x-yaml                           yaml yml;

        image/gif                             gif;
        image/jpeg                            jpeg jpg;
        image/png                             png;

        application/atom+xml                  atom;
        application/rss+xml                   rss;
        text/xsl                              xsl xslt;
        text/mathml                           mml;

        image/tiff                            tif tiff;
        image/x-icon                          ico;
        image/x-ms-bmp                        bmp;
        image/svg+xml                         svg svgz;
        image/webp                            webp;
        application/x-shockwave-flash         swf;
        application/pdf                       pdf;

        audio/midi                            mid midi kar;
        audio/mpeg                            mp3;
        audio/ogg                             ogg;
        audio/x-m4a                           m4a;
        audio/wav                             wav;

        video/mp4                             mp4;
        video/mpeg                            mpeg mpg;
        video/webm                            webm;
        video/x-flv                           flv;
        video/x-m4v                           m4v;
        video/x-msvideo                       avi;

        application/x-font-opentype           otf;
        application/x-font-truetype           ttf;
        application/x-font-woff               woff;
        apllication/vnd.ms-fontobject         eot;
    }}
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout  65;
    client_max_body_size {MAX_CLIENT_BODY_SIZE};
    server {{
        listen       {INTERFACE}:{PORT};
        server_name  localhost;
        root {LOCATION};
        index {INDEX};

        location / {{
            try_files $uri $uri/ /{INDEX}?$query_string;
        }}

        location ~ \.php$ {{
            fastcgi_pass      unix:/{PHPFPM_SOCKET_FILE};
            fastcgi_keep_conn on;
            fastcgi_split_path_info ^(.+\.php)(/.*)$;

            fastcgi_param QUERY_STRING      $query_string;
            fastcgi_param REQUEST_METHOD    $request_method;
            fastcgi_param CONTENT_TYPE      $content_type;
            fastcgi_param CONTENT_LENGTH    $content_length;
            fastcgi_param SCRIPT_NAME       $fastcgi_script_name;
            fastcgi_param REQUEST_URI       $request_uri;
            fastcgi_param DOCUMENT_URI      $document_uri;
            fastcgi_param DOCUMENT_ROOT     $document_root;
            fastcgi_param SERVER_PROTOCOL   $server_protocol;
            fastcgi_param HTTPS             $https if_not_empty;
            fastcgi_param GATEWAY_INTERFACE CGI/1.1;
            fastcgi_param SERVER_SOFTWARE   nginx/$nginx_version;
            fastcgi_param REMOTE_ADDR       $remote_addr;
            fastcgi_param REMOTE_PORT       $remote_port;
            fastcgi_param SERVER_ADDR       $server_addr;
            fastcgi_param SERVER_PORT       $server_port;
            fastcgi_param SERVER_NAME       $server_name;
            fastcgi_param REDIRECT_STATUS   200;
            fastcgi_param SCRIPT_FILENAME   $document_root$fastcgi_script_name;
            fastcgi_param APPLICATION_ENV   development;
        }}
    }}
}}
"""
options['NGINX_CONFIG'] = options['NGINX_CONFIG'].format(**options)

# Create nginx temporary directory and config
mkdir(options['NGINX_TMP_DIR'])
with open(options['NGINX_CONFIG_FILE'], 'w') as f:
    f.write(options['NGINX_CONFIG'])

# Create php-fpm temporary config file
with open(options['PHPFPM_CONFIG_FILE'], 'w') as f:
    f.write(options['PHPFPM_CONFIG'])

# Create log files
open(options['PHPFPM_ERROR_LOG'], 'a').close()
open(options['NGINX_ERROR_LOG'], 'a').close()

# PHP-FPM command
options['PHPFPM_COMMAND'] = [
    options['PHPFPM_CMD'],
    '-y', options['PHPFPM_CONFIG_FILE'],
    '-g', options['PHPFPM_PID_FILE'],
]

# Nginx command
options['NGINX_COMMAND'] = [
    options['NGINX_CMD'],
    '-p', options['TMP_DIR'],
    '-c', options['NGINX_CONFIG_FILE'],
    '-q',
]

# Let's get going
try:
    with open('/dev/null', 'w') as devnull:
        if not options['PHP_FPM_ENABLED']:
            print("Note: php-fpm will not be started")
        print("Serving {0} ({1})".format(options['LOCATION'], options['INDEX']))
        if getenv('SUDO_USER') != None:
            print("Nginx user: {0}; PHP user: {1}".format(options['NGINX_USER'], options['PHP_USER']))
        if options['DEBUG']:
            stdoutstream = sys.stdout
            stderrstream = sys.stderr
        else:
            stdoutstream = devnull
            stderrstream = devnull
        if options['PHP_FPM_ENABLED']:
            phpfpm = Popen(options['PHPFPM_COMMAND'], stdout=stdoutstream, stderr=stderrstream)
        nginx = Popen(options['NGINX_COMMAND'], stdout=stdoutstream, stderr=stderrstream)
        print("Server running on {0}:{1}...".format(options['INTERFACE'], options['PORT']))

        if options['SHOW_LOGS']:
            def enqueue_output(t, out):
                for line in iter(out.readline, b''):
                    print '[{0}] {1}'.format(t, line.strip())
                out.close()

            nginx_tail = Popen(['tail', '-f', options['NGINX_ERROR_LOG']], stdout=PIPE, stderr=stderrstream)
            thread_nginx_tail = Thread(target=enqueue_output, args=('nginx', nginx_tail.stdout))
            thread_nginx_tail.daemon = True
            thread_phpfpm_tail.start()

            if options['PHP_FPM_ENABLED']:
                phpfpm_tail = Popen(['tail', '-f', options['PHPFPM_ERROR_LOG']], stdout=PIPE, stderr=stderrstream)
                thread_phpfpm_tail = Thread(target=enqueue_output, args=('php-fpm', phpfpm_tail.stdout))
                thread_phpfpm_tail.daemon = True
                thread_nginx_tail.start()

        # Wait for the main command to exit
        if options['PHP_FPM_ENABLED']:
            phpfpm.wait()
            nginx.terminate()
        else:
            nginx.wait()

        # Shut down logging
        if options['SHOW_LOGS']:
            nginx_tail.terminate()
            if options['PHP_FPM_ENABLED']:
                phpfpm_tail.terminate()
except (KeyboardInterrupt, SystemExit):
    if options['PHP_FPM_ENABLED']:
        phpfpm.terminate()
    nginx.terminate()
    rmtree(options['NGINX_TMP_DIR'])
    remove(options['PHPFPM_CONFIG_FILE'])
    remove(options['NGINX_CONFIG_FILE'])
    remove(options['NGINX_ERROR_LOG'])
    remove(options['PHPFPM_ERROR_LOG'])
