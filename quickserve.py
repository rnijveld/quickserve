#!/usr/bin/env python
from subprocess import Popen
from os import path, mkdir, getcwd, remove
from random import choice
from string import hexdigits
from argparse import ArgumentParser
from shutil import rmtree
import sys

# Parse arguments
parser = ArgumentParser(description="Start a quick server for PHP projects with an index file. This uses nginx and php-fpm.")
parser.add_argument('-d', '--debug', action='store_true', help="Display more information")
parser.add_argument('-p', '--port', metavar='port', type=int, default=8080, help='Port number (default: 8080)')
parser.add_argument('-i', '--interface', metavar='address', type=str, default='*', help='Interface to listen to (default: *)')
parser.add_argument('-r', '--root', metavar='dir', type=str, default=getcwd(), help="Web root directory (default: .)")
parser.add_argument('--handlers', metavar='n', type=int, default=6, help="Number of handlers for requests (default: 6)")
parser.add_argument('--restart-after', metavar='n', type=int, default=0, help="Restart php-fpm processes after this amount of requests, 0 means no restarts (default: 0)")
parser.add_argument('--php-fpm-bin', metavar='path', type=str, default='php-fpm', help="Location of php-fpm binary (will search path if required) (default: php-fpm)")
parser.add_argument('--nginx-bin', metavar='path', type=str, default='nginx', help="Location of nginx binary (will search path if required) (defaults: nginx)")
parser.add_argument('index', metavar='index_file', type=str, default='index.php', nargs='?', help="The root index file (default: index.php)")
args = parser.parse_args()

if not path.isabs(args.root):
    args.root = path.abspath(args.root)

# Initialize the options dict
options = {}

# Generic config
options['HANDLERS'] = args.handlers
options['RESTART_AFTER'] = args.restart_after
options['LOCATION'] = args.root
options['INDEX'] = args.index
options['INTERFACE'] = args.interface
options['PORT'] = args.port
options['TMP_DIR'] = '/tmp'
options['DEBUG'] = args.debug

# Detailed config
options['MAX_CLIENT_BODY_SIZE'] = '100M'
options['ERROR_REPORTING'] = 'E_ALL'
options['DISPLAY_ERRORS'] = 'on'
options['DATE_TIMEZONE'] = 'Europe/Amsterdam'

# Paths
options['NGINX_CMD'] = args.nginx_bin
options['PHPFPM_CMD'] = args.php_fpm_bin

# Random file names for this instance
options['RAND'] = ''.join(choice(hexdigits[:16]) for _ in xrange(6))

# PHP-FPM configuration
options['PHPFPM_SOCKET_FILE'] = path.join(options['TMP_DIR'], 'php-fpm-' + options['RAND'] + '.socket')
options['PHPFPM_CONFIG_FILE'] = path.join(options['TMP_DIR'], 'php-fpm-config-' + options['RAND'] + '.ini')
options['PHPFPM_PID_FILE'] = path.join(options['TMP_DIR'], 'php-fpm-pid-' + options['RAND'] + '.pid')
options['PHPFPM_CONFIG'] = """
[global]
error_log=/dev/null
daemonize=no

[www]
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
"""
options['PHPFPM_CONFIG'] = options['PHPFPM_CONFIG'].format(**options)

# Nginx configuration
options['NGINX_CONFIG_FILE'] = path.join(options['TMP_DIR'], 'nginx-' + options['RAND'] + '.conf')
options['NGINX_PID_FILE'] = path.join(options['TMP_DIR'], 'nginx-pid-' + options['RAND'] + '.pid')
options['NGINX_TMP_DIR'] = path.join(options['TMP_DIR'], 'nginx-tmp-' + options['RAND'])
options['NGINX_CLIENT_TMP'] = path.join(options['NGINX_TMP_DIR'], 'client_temp')
options['NGINX_PROXY_TMP'] = path.join(options['NGINX_TMP_DIR'], 'proxy_temp')
options['NGINX_FASTCGI_TMP'] = path.join(options['NGINX_TMP_DIR'], 'fastcgi_temp')
options['NGINX_UWSGI_TMP'] = path.join(options['NGINX_TMP_DIR'], 'uwsgi_temp')
options['NGINX_SCGI_TMP'] = path.join(options['NGINX_TMP_DIR'], 'scgi_temp')
options['NGINX_CONFIG'] = """
error_log /dev/null crit;

pid {NGINX_PID_FILE};
worker_processes 2;
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
        location / {{
            index {INDEX};
            try_files $uri @rewriteapp;
        }}
        location @rewriteapp {{
            rewrite ^(.*)$ /{INDEX}/$1 last;
        }}
        location ~ ^/(.*?)\.php(/|$) {{
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
        print("Using webroot {0}".format(options['LOCATION']))
        if options['DEBUG']:
            stdoutstream = sys.stdout
            stderrstream = sys.stderr
        else:
            stdoutstream = devnull
            stderrstream = devnull
        phpfpm = Popen(options['PHPFPM_COMMAND'], stdout=stdoutstream, stderr=stderrstream)
        nginx = Popen(options['NGINX_COMMAND'], stdout=stdoutstream, stderr=stderrstream)
        print("Server running on {0}:{1}...".format(options['INTERFACE'], options['PORT']))

        phpfpm.wait()
        nginx.terminate()
except (KeyboardInterrupt, SystemExit):
    phpfpm.terminate()
    nginx.terminate()
    rmtree(options['NGINX_TMP_DIR'])
    remove(options['PHPFPM_CONFIG_FILE'])
    remove(options['NGINX_CONFIG_FILE'])
