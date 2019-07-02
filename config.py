import os


class Config(object):
    """This class is used to create a secret token for CSRF"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'DIPWDl1axz3K1KfXKfK5'
