bind = 'unix:fopdcw.sock'
# workers = 3
workers = 1 
worker_class = 'eventlet'
umask = 7
# Be aware that upstream processes (such as nginx) in the request chain may have their own timeout
# values. See /etc/nginx/sites-available/fopdw 
timeout = 5*60
