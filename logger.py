from logging import handlers, getLogger, Formatter
from logging.config import dictConfig
from logging.handlers import RotatingFileHandler
from os import getcwd

from config.config import log_level

# TBD:  Move the logging configuration to a dictionary stored in a configuration file.
# On linux use tail -F (translates as tail --follow=name --retry) to follow the 
# rotating log. tail -f stops following when the log gets rotated out from under it.
#
# This logger currenlty rotates based upon file size. Python also supports timed based 
# rotation.
#

handler = None

def get_the_fopdcw_log_handler():
    return handler

def get_top_level_logger():

   global handler

   logger = getLogger("fopdcw")
   logger.setLevel(log_level)

   handler = RotatingFileHandler(getcwd() + '/logs/fopdcw.log', maxBytes=10*1000*1000,\
                                 backupCount=5)

   formatter = Formatter(fmt='%(asctime)s %(levelname)s %(name)s:%(message)s', 
                             datefmt='%Y-%m-%d %I:%M:%S %p %Z')
   handler.setFormatter(formatter)
   handler.setLevel(log_level)

   logger.addHandler(handler)

   """ - 
   # Intercept werkzeug's outuput
   # 9/27/2018 - werkzeug appears to set a handler (StreamHandler) if there is no handler specified
   # and there is no log level set for the logger. So add an handler and set a level in order to 
   # keep werkzeug from creating it's own handler.
   #
   wl = getLogger('werkzeug')
   wl.addHandler(handler)
   wl.setLevel(DEBUG)
   """

   wl = getLogger('flask.app')
   wl.addHandler(handler)
   wl.setLevel(log_level)

   return logger

def get_sub_logger(name):
   return getLogger("fopdcw" + '.' + name)
