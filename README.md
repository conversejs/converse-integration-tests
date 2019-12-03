# Intro

This is a proof of concept for creating integration tests for Converse.js, using Selenium. It works by spinning up a Converse.js session in a headless Firefox instance, logging in and joining a MUC. Simultaneously a regular XMPP client will periodically send messages to the Converse.js user and the MUC it has joined. Using Selenium, we check whether the messages sent are actually received by Converse.js and added to the DOM.

It is currently focused on testing issues related to reconnection. To simulate the case of a Converse.js user reconnecting, all (websocket) connections are proxied via an nginx instance which is restarted on demand.

The goal is to quickly reproduce issues that arise during reconnection, for example duplicate messages or missing messages. I aim to test for the most common scenario, e.g. having a modern Server that passes the XMPP Compliance Suite, enabling MAM, no OMEMO, etc.

The ultimate goal is to make this setup self-containing and run it as part of the Converse.js testsuite.

# Installing

Create a dedicated VM for this purpose, give it a FQDN with matching DNS entry and Letsencrypt certificate.

Development takes place on Ubuntu 18.04, other distros YMMV.

`sudo apt install firefox firefox-geckodriver xvfb python-pip`
`sudo pip install selenium setuptools sleekxmpp`

## Ejabberd

Install Ejabberd 19.09.1 using their Linux installer: https://www.process-one.net/en/ejabberd/downloads/

Change the configuration to enable MAM by default:

```
  mod_mam:
    default: always # xmppdev

  mod_muc:
    default_room_options:
      mam: true # xmppdev
```

## Nginx

Install nginx and create a configuration to serve Converse.js and proxy websockets to Ejabberd:

```
upstream ejabberd {
    keepalive 16;
    
    server localhost:5443;
}
    
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name xmppdev.example.com;

    root /var/www;
    
    location /ws {
        proxy_pass https://ejabberd/ws;
        proxy_http_version 1.1;
        proxy_read_timeout 90;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Converse.js

Install Converse.js in `/var/www/converse` and give it the configuration you want to test, e.g. create this 'index.html':

```
<html>
<head>
<link rel="stylesheet" type="text/css" media="screen" href="https://cdn.conversejs.org/5.0.5/dist/converse.css">
<script src="https://cdn.conversejs.org/5.0.5/dist/converse.js" charset="utf-8"></script>
</head>
<body>
<script>
    var props = {
        websocket_url: "wss://xmppdev.example.com/ws",
        default_domain: "xmppdev.example.com",
        view_mode: "fullscreen",
        enable_smacks: true
    };

    converse.initialize(props);
</script>
</body>
</html>
```

# Configuration

* Create an XMPP user 'test1' and 'bot1'
* Create roster entries between 'test1' and 'bot1'
* Create a MUC named 'testmuc' and set it to persistent
* Create a MUC bookmark with autojoin for 'test1' to this MUC

Create a 'config.ini' file based on 'config.ini.example'

# Run

`./test.py`
