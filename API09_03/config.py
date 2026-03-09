import os.path

SECRET_KEY = ('chave_secreta_do-Ti')

DEBUG = True

DB_HOST = 'localhost'
DB_NAME = r'E:\BANCO\BANCO.FDB'

DB_USER = 'sysdba'
DB_PASSWORD = 'sysdba'

UPLOAD_FOLDER = os.path.abspath(os.path.dirname(__file__))