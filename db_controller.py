#!/usr/bin/env python 
# -*- coding: UTF-8 -*-

# Third party imports
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except:
    import mysql.connector
import configparser

# -- Read INI file
CONFIGFILE = configparser.ConfigParser()
CONFIGFILE.read('config.ini')

#-- DATABASE
USE_SECTION = CONFIGFILE['database']['use_section']
DRIVER =  CONFIGFILE[USE_SECTION]['driver']

class ManageDatabase(object):
    #-- https://www.psycopg.org/docs/usage.html
    #-- https://pynative.com/python-postgresql-select-data-from-table/
    #-- https://zetcode.com/python/psycopg2/
    def __init__(self):
        pass

    @staticmethod
    def open_connection(host:str, database:str, user:str, password:str, port:int):
        """
        Establece una conexion con la base de datos
        """
        try:
            if DRIVER == 'postgres':
                CONN = psycopg2.connect(host=host,
                                        database=database,
                                        user=user,
                                        password=password,
                                        port=port,
                                        connect_timeout=15)
                #-- Retornar resultado como diccionarios, accesibles por el nombre de la columna
                cursor = CONN.cursor(cursor_factory=RealDictCursor)
            elif DRIVER == 'mysql':
                CONN = mysql.connector.connect(
                    host=host,
                    database=database,
                    user=user,
                    password=password,
                    port=port)
                #-- Retornar resultado como diccionarios, accesibles por el nombre de la columna
                cursor = CONN.cursor(dictionary=True)
        except psycopg2.OperationalError:
            return (None, None, False)
        except:
            return (None, None, False)
        return (CONN, cursor, True)

    @staticmethod
    def close_connection(*args):
        """
        Cierra todas las conexiones agrupadas en el parametro
        Todo objeto en la conexion debe contener el metodo -close-
        """

        for obj in args:
            try:
                obj.close()
            except Exception as e:
                continue
