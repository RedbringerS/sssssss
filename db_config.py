from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

DB_CONFIG = {
    'user': config.get('DATABASE', 'user'),
    'password': config.get('DATABASE', 'password'),
    'host': config.get('DATABASE', 'host'),
    'port': config.getint('DATABASE', 'port'),
    'database': config.get('DATABASE', 'db'),
}