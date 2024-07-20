import os
import qrcode
import time
import random
import flask_bcrypt
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from flask import json, jsonify, request, url_for, redirect, session, make_response, send_from_directory
from flask import abort, render_template, render_template_string, Flask, flash
from flask_restful import Resource, Api
import configparser
import socket
import jwt, uuid, datetime
import copy
import traceback
import hashlib
from casino import Azar, Roulette
from db_controller import ManageDatabase

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png']
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 50
app.config['UPLOAD_PATH'] = 'uploads'
app.config['TEMPLATES_AUTO_RELOAD'] = True

# -- Read INI file
configFile = configparser.ConfigParser()
configFile.read('config.ini')

secret = os.urandom(32)
app.config['SECRET_KEY'] = secret
app.secret_key = secret

bcrypt = flask_bcrypt.Bcrypt(app)
CORS(app)
api = Api(app)
PORT_FLASK = 5002


class Controls(object):
    HOST = 'localhost'
    DATABASE = 'casinos_tao'
    USER = 'tao'
    PASSWORD = 'root'
    PORT = 5432

    @staticmethod
    def insert_customer_play(amount, roulette_id, affiliate_code) -> tuple:
        def check_if_pending(dbconn, cursor):
            if not status:
                return []
            sql_query = """
            SELECT 
                *
            FROM 
                public.plays p
            WHERE
                p.validated=%s
            """
            cursor.execute(sql_query, (False,))
            record = cursor.fetchone()
            return record

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        dt = datetime.datetime.now()
        group_name = str(uuid.uuid1())

        if type(affiliate_code) == list:
            for user in affiliate_code:
                sql_query = """
                INSERT INTO 
                    public.plays (play_date, roulette_id, affiliate_code, amount, validated, group_name)
                VALUES 
                    (%s, %s, %s, %s, %s, %s);
                """
                cursor.execute(sql_query, (dt, roulette_id, user['affiliate_code'], amount, False, group_name))
                dbconn.commit()
        else:
            pending = check_if_pending(dbconn, cursor)
            if not pending:
                sql_query = """
                INSERT INTO 
                    public.plays (play_date, roulette_id, affiliate_code, amount, validated, group_name)
                VALUES 
                    (%s, %s, %s, %s, %s, %s);
                """
                cursor.execute(sql_query, (dt, roulette_id, affiliate_code, amount, False, group_name))
                dbconn.commit()
                count = cursor.rowcount
                if count > 0:
                    return True, f'Apuesta de {amount} recibida, espere un momento y giraremos la ruleta!'
                else:
                    return False, 'No fue posible agregar su jugada'
            else:
                return False, 'Tienes una apuesta en proceso.Por el momento no puedes hacer más apuestas.'
        ManageDatabase.close_connection(dbconn, cursor)

    @staticmethod
    def update_token(roulette_id):
        """
        Actualiza el token cuando el usuario entra a una nueva mesa. De esta forma en el token llevamos la informacion de la mesa donde está.
        """
        #-- Decodificar el token y guardar este valor momentaneamente
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')
            payload['roulette_id'] = roulette_id
            #--actualizar token
            token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')

            session['token'] = token
            session['roulette_id'] = False
        except jwt.exceptions.InvalidSignatureError as e:
            return {'status':False, 'payload':{}}
        except:
            return {'status':False, 'payload':{}}
        else:
            return {'status':True, 'payload':data}

    @staticmethod
    def admin_set_free_numbers():
        pass 

    @staticmethod
    def validate_token(token : str) -> dict:
        """Decodificar token
        :param token: Request token
        """
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms='HS256')
        except jwt.exceptions.InvalidSignatureError as e:
            return {'status':False, 'payload':{}}
        except:
            return {'status':False, 'payload':{}}
        else:
            return {'status':True, 'payload':data}

    @staticmethod
    def set_roulette_opens(roulette_id, numbers):
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        UPDATE public.casinos_roulettes cr
        SET
            free_numbers=%s
        WHERE
            cr.roulette_id=%s;
        """
        cursor.execute(sql_query, (numbers, roulette_id))
        dbconn.commit()
        ManageDatabase.close_connection(dbconn, cursor)

    @staticmethod
    def set_open_numbers(roulette_id) -> list:
        """
        Obtiene los numeros abiertos indicados por el crupier, es decir, se toman desde la base de datos.
        Esta funcion es para el usuario
        """
        #-- Obtener configuracion de la mesa
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        SELECT 
            zero_fix, form, user_covers
        FROM 
            roulette_settings rs
        WHERE
            roulette_id=%s
        """
        cursor.execute(sql_query, (roulette_id,))
        records = cursor.fetchall()
        records = [(dict(row)['zero_fix'],dict(row)['form'],dict(row)['user_covers']) for row in records]
        ManageDatabase.close_connection(dbconn, cursor)

        if records:
            zero_fix = records[0][0]
            form = records[0][1]
            user_covers = records[0][2]
            #-- Buscar informacion en la base de datos sobre cuales son los numeros abiertos de la me roulette_id
            numbers = Controls.generate_numbers(roulette_id, user_covers, zero_fix=zero_fix, _form=form)
            return numbers, True
        else:
            return [], False
        
    @staticmethod
    def get_roulette_probabilities(token) -> list:
        """
        Retorna la lista de probabilidades disponibles.
        Estamos separando las mesas por porcentaje de probabilidad para dar mas libertad al usuario
        """
        data = Controls.validate_token(token)['payload']
        casino_account = data['casino_account']

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        SELECT 
            probability
        FROM 
            games_probabilities gmp 
        WHERE
            %s
        """
        cursor.execute(sql_query, (True,))
        records = cursor.fetchall()
        records = [dict(row)['probability'] for row in records]
        ManageDatabase.close_connection(dbconn, cursor)

        if records:
            return records
        else:
            return []

    @staticmethod
    def get_roulette_online_users(roulette_id, token):
        """
        Obtiene el total de usuarios conectados en la mesa, obviando al usuario crupier
        """
        if str(roulette_id).startswith('R'):
            data = Controls.validate_token(token)['payload']
            casino_account = data['casino_account']

            dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
            if not status:
                return {}

            sql_query = """
            SELECT 
                affiliate_code
            FROM 
                global_access
            WHERE
                roulette_id=%s AND log_status=%s AND (affiliate_code LIKE '%%AF%%');
            """
            cursor.execute(sql_query, (roulette_id, True))
            records = cursor.fetchall()
            records = [dict(row) for row in records]
            ManageDatabase.close_connection(dbconn, cursor)
            
            if records:
                return records
            else:
                return {}
        else:
            return {}

    @staticmethod
    def get_roulette_data(roulette_id, token) -> dict:
        """
        """
        if str(roulette_id).startswith('R'):
            data = Controls.validate_token(token)['payload']
            casino_account = data['casino_account']

            dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
            if not status:
                return {}
            sql_query = """
            SELECT 
                cr.id, cr.roulette_id , cr.roulette_result,cr.next_amount, rs.roulette_protected_type, rs.user_covers, rs.user_plays,rs.roulette_min_invest,rs.roulette_max_invest, rs.max_earning,rs.min_earning, rs.roulette_comment, rs.divisa, rs.require_users, cr.round_number, cr.crupier_step, r.roulette_name, rs.roulette_max_users, rs.divisa, rs.tao_commision, cr.free_numbers, cr.tao_number,r.roulette_image ,rs.probability as roulette_probability,cr.roulette_active , r.roulette_type  
            FROM 
                casinos_roulettes cr 
            JOIN roulettes r ON r.roulette_id = cr.roulette_id
            JOIN roulette_settings rs ON rs.roulette_id = cr.roulette_id
            WHERE
                cr.casino_account = %s AND cr.roulette_id= %s;
            """
            cursor.execute(sql_query, (casino_account, roulette_id))
            records = cursor.fetchall()
            records = [dict(row) for row in records]
            ManageDatabase.close_connection(dbconn, cursor)

            return records[0]
        else:
            return {}

    @staticmethod
    def get_roulettes(token) -> list:
        """
        Retorna las mesas disponibles en el casino
        """

        data = Controls.validate_token(token)['payload']
        casino_account = data['casino_account']

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        SELECT 
            cr.id, cr.roulette_id ,cr.roulette_result,cr.next_amount, rs.roulette_protected_type, rs.user_covers, rs.user_plays,rs.roulette_min_invest,rs.roulette_max_invest, rs.max_earning,rs.min_earning,rs.roulette_comment, rs.divisa, rs.require_users, cr.round_number, cr.crupier_step, r.roulette_name, rs.roulette_max_users, rs.divisa, rs.tao_commision, cr.free_numbers, cr.tao_number,r.roulette_image ,rs.probability as roulette_probability,cr.roulette_active , r.roulette_type  
        FROM 
            casinos_roulettes cr 
        JOIN roulettes r ON r.roulette_id = cr.roulette_id and cr.roulette_active=TRUE
        JOIN roulette_settings rs ON rs.roulette_id = cr.roulette_id
        WHERE
            cr.casino_account = %s
        ORDER BY roulette_id ASC;
        """
        cursor.execute(sql_query, (casino_account,))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        ManageDatabase.close_connection(dbconn, cursor)

        return records

    @staticmethod
    def get_session_round(roulette_id) -> int:
        """
        Obtiene el valor de la ronda actual
        """
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        SELECT 
            round_number
        FROM 
            casinos_roulettes cr
        WHERE
            cr.roulette_id = %s;
        """
        cursor.execute(sql_query, (roulette_id,))
        records = cursor.fetchall()
        round_number = [dict(row)['round_number'] for row in records]
        if round_number:
            round_number = int(round_number[0])
        ManageDatabase.close_connection(dbconn, cursor)

        return round_number

    @staticmethod
    def set_session_round(roulette_id) -> None:
        """
        Establece el valor de la ronda actual en la base de datos
        """

        old_round = Controls.get_session_round(roulette_id)
        if old_round < 10:
            new_round = old_round + 1
        else:
            new_round = 1
        session['round'] = new_round

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        UPDATE casinos_roulettes
        SET
            round_number=%s, free_numbers='-'
        WHERE
            roulette_id=%s;
        """
        cursor.execute(sql_query, (new_round, roulette_id))
        dbconn.commit()
        ManageDatabase.close_connection(dbconn, cursor)

    @staticmethod
    def calculate_unitary_amount(roulette_id) -> tuple:
        """
        Calcula el monto unitario que se debe colocar en cada posicion de la mesa
        """

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)

        if not status:
            return []

        #-- Actualizar STEP
        sql_query = """
        UPDATE public.casinos_roulettes cr
        SET
            crupier_step=4
        WHERE
            cr.roulette_id=%s;
        """
        cursor.execute(sql_query, (roulette_id,))
        dbconn.commit()

        #-- Calcula el monto por ficha que necesitamos jugar
        sql_query = """
        SELECT 
            SUM(pl.amount) as unitary 
        FROM 
            plays pl
        WHERE
            pl.roulette_id = %s AND pl.validated=%s
        """
        cursor.execute(sql_query, (roulette_id, False))
        records = cursor.fetchall()
        total_units = [dict(row)['unitary'] for row in records]
        if total_units:
            try:
                total_units = int(float(total_units[0]))
            except TypeError:
                total_units = 0

        #-- Obtiene el total de fichas que debe cubrirse en la mesa
        sql_query = """
        SELECT 
            user_plays
        FROM 
            roulette_settings rs
        WHERE
            rs.roulette_id = %s
        """
        cursor.execute(sql_query, (roulette_id,))
        records = cursor.fetchall()
        user_plays = [dict(row)['user_plays'] for row in records]
        if user_plays:
            user_plays = int(float(user_plays[0]))
        ManageDatabase.close_connection(dbconn, cursor)

        #-- Calcular
        if user_plays and total_units:
            try:
                unitary = total_units//user_plays
            except ZeroDivisionError:
                unitary = 0
            status = True
        else:
            unitary = 0
            status = True

        return status, unitary

    @staticmethod
    def bet_now(roulette_id) -> bool:
        """
        Llama al publico a apostar
        """
        Controls.update_step(roulette_id, 2)


    @staticmethod
    def get_active_users(roulette_id):
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        #-- Saber quienes estan conectados a la mesa
        sql_query = """
        SELECT 
            affiliate_code, auto_bet_active, log_status
        FROM 
            global_access
        WHERE
            roulette_id = %s AND log_status=%s AND (affiliate_code LIKE '%%F%%');
        """
        cursor.execute(sql_query, (roulette_id, True))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        ManageDatabase.close_connection(dbconn, cursor)

        return records

    @staticmethod
    def update_step(roulette_id, step:int, roulette_result=-1) -> bool:

        if step >= 3:
            no_more_bets = True
        else:
            no_more_bets = False

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []

        #--- AQUI PUEDO CREAR LAS JUGADAS AUTOMATICAMENTE PARA CADA USUARIO EN MESAS X2
        #-- conseguir el tipo de ruleta (x1,x2,..)
        #-- conseguir quienes estan activos en la mesa
        #-- crear una orden con el monto adecuado para cada usuario conectado
        #-- 

        #-- Primero consigue los free_numbers, tipo de ruleta(proteccion)
        sql_query = """
        SELECT 
            cr.free_numbers, r.roulette_protected_type
        FROM 
            casinos_roulettes cr
        JOIN roulette_settings r ON r.roulette_id = cr.roulette_id
        WHERE
            cr.roulette_id = %s
        LIMIT 1;
        """
        cursor.execute(sql_query, (roulette_id,))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        free_numbers = records[0]['free_numbers']
        roulette_protected_type = records[0]['roulette_protected_type']

        #-- Saber quienes estan activos
        sql_query = """
        SELECT 
            ga.affiliate_code, ga.roulette_id
        FROM 
            global_access ga
        WHERE
            ga.roulette_id = %s AND ga.auto_bet_active=%s AND ga.log_status=%s
        """
        cursor.execute(sql_query, (roulette_id, True, True))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        active_users = records

        #-- Crear las ordenes para cada usuario cuando estemos justo en el paso #3
        if step == 3:
            if roulette_protected_type == 'X2':
                amount = 35
                Controls.insert_customer_play(amount, roulette_id, active_users)

        #-- Actualizar tabla de jugadas con los numeros a dejar libres
        sql_query = """
        UPDATE public.plays pl
        SET
            free_numbers=%s
        WHERE
            roulette_id=%s AND validated=%s;
        """
        cursor.execute(sql_query, (free_numbers, roulette_id, False))
        dbconn.commit()

        #-- Ahora si, actualiza el STEP
        sql_query = """
        UPDATE public.casinos_roulettes cr
        SET
            crupier_step=%s, no_more_bets=%s, roulette_result=%s
        WHERE
            cr.roulette_id=%s;
        """
        cursor.execute(sql_query, (step, no_more_bets, roulette_result, roulette_id))
        dbconn.commit()
        ManageDatabase.close_connection(dbconn, cursor)

        return True

    @staticmethod
    def publish_result(roulette_id,  roulette_result)->bool:
        Controls.update_step(roulette_id, 6,  roulette_result)

        #-- Verificar si GANO o PERDIO
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        
        sql_query = """
        SELECT 
            cr.free_numbers, cr.roulette_result, cr.roulette_step, rs.user_plays, rs.roulette_protected_type, rs.tao_commision
        FROM 
            casinos_roulettes cr
        JOIN roulette_settings rs ON rs.roulette_id = cr.roulette_id
        WHERE
            cr.roulette_id = %s
        LIMIT 1;
        """
        cursor.execute(sql_query, (roulette_id,))
        records = cursor.fetchall()
        records = [dict(row) for row in records]

        free_numbers = records[0]['free_numbers']
        roulette_result = records[0]['roulette_result']
        user_plays = records[0]['user_plays']
        protected_type = records[0]['roulette_protected_type']
        tao_commision = records[0]['tao_commision']

        if records:
            amount = 35
        else:
            amount = 0

        if '{' in free_numbers:
            free_numbers = free_numbers.replace('{', '').replace('}', '').split(',')
            free_numbers = [int(float(x)) for x in free_numbers]

        #-- Obtener todas las jugadas abiertas en la mesa
        sql_query = """
        SELECT 
            *
        FROM 
            plays pl
        WHERE
            pl.roulette_id = %s AND pl.validated=%s
        """
        cursor.execute(sql_query, (roulette_id, False))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        active_plays = records

        for plx in active_plays:
            coin_amount = plx['amount']/float(user_plays)
            total_amount = plx['amount']
            if int(roulette_result) in free_numbers:
                play_result = f'loss [{roulette_result}]'
                profit = -1*total_amount
                commision = 0
                profit = profit - commision
            else:
                play_result = f'win [{roulette_result}]'
                profit = coin_amount*36 - coin_amount*user_plays
                commision = profit*tao_commision
                profit = profit - commision

            sql_query = """
            UPDATE public.plays pl
            SET
                play_result=%s, validated=%s, profit=%s, commision=%s
            WHERE
                pl.roulette_id=%s AND pl.validated=%s;
            """
            cursor.execute(sql_query, (play_result, True, profit, commision, roulette_id, False))
            dbconn.commit()
        ManageDatabase.close_connection(dbconn, cursor)

    @staticmethod
    def spin_roulette(roulette_id) -> bool:
        """
        Llamado de boton NO MAS. Modifica STEP_CRUPIER en la base de datos haciendo que los usuarios no puedan apostar mas
        """
        Controls.update_step(roulette_id, 5)
        return True

    @staticmethod
    def no_more_bets(roulette_id) -> bool:
        """
        Llamado de boton NO MAS. Modifica STEP_CRUPIER en la base de datos haciendo que los usuarios no puedan apostar mas
        """
        Controls.update_step(roulette_id, 3)
        return True

    @staticmethod
    def get_table_amounts(roulette_id, token) -> list:
        """
        Obtiene los montos a ganar disponibles en la mesa
        """
        data = Controls.validate_token(token)['payload']
        casino_account = data['casino_account']

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        SELECT 
            ra.amount as amount 
        FROM 
            roulette_amounts ra
        WHERE
            ra.roulette_id = %s AND ra.amount_active=%s
        order by amount ASC;
        """
        cursor.execute(sql_query, (roulette_id,True))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        ManageDatabase.close_connection(dbconn, cursor)
        return records

    @staticmethod
    def generate_numbers(roulette_id, total_numbers:int, zero_fix=False, _form='straight'):
        """
        Genera 2 numeros aleatorios. Esta funcion es para el administrador.
        """
        azar = Azar()
        roulette = Roulette('EU')
        numbers = azar.generate_numbers(roulette.table, total_numbers, zero_fix, _form='straight')
        del azar

        #-- Almacenar en la base de datos los numeros abiertos que se utilizaran en la roulette_id
        Controls.set_roulette_opens(roulette_id, numbers)

        #-- Indicar en que STEP voy
        Controls.update_step(roulette_id, 1)

        return numbers

    @staticmethod
    def clear_user_table_status(affiliate_code, casino_account, roulette_id):
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []

        #-- Primero consigue tipo de ruleta(proteccion)
        sql_query = """
        SELECT 
            cr.free_numbers, r.roulette_protected_type
        FROM 
            casinos_roulettes cr
        JOIN roulette_settings r ON r.roulette_id = cr.roulette_id
        WHERE
            cr.roulette_id = %s
        LIMIT 1;
        """
        cursor.execute(sql_query, (roulette_id,))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        roulette_protected_type = records[0]['roulette_protected_type']

        #-- Deja el auto_bet_tal cual este si es mesa de tipo X2,X3,...
        if roulette_protected_type == 'X1':
            sql_query = """
            UPDATE public.global_access ga
            SET
                roulette_id=%s, auto_bet_active=%s
            WHERE
                ga.roulette_id=%s AND ga.casino_account=%s AND ga.affiliate_code=%s;
            """
            cursor.execute(sql_query, ('-', False, roulette_id, casino_account, affiliate_code))
            dbconn.commit()
        ManageDatabase.close_connection(dbconn, cursor)

    @staticmethod
    def get_user_amount(token):
        pass

    @staticmethod
    def remove_session_keys():
        """
        Borra todas las posibles variables de session que han sido creadas
        """
        ks = copy.copy(list(session.keys()))
        for k in ks:
            del session[str(k)]

    @staticmethod
    def get_auto_bet_status(affiliate_code, roulette_id):
        """
        Obtiene el ultimo estado de auto apuesta del usuario
        """

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return ''

        sql_query = """
        SELECT 
            ga.auto_bet_active
        FROM 
            global_access ga
        WHERE
            ga.roulette_id = %s AND ga.affiliate_code=%s AND log_status=%s
        """
        cursor.execute(sql_query, (roulette_id, affiliate_code, True))
        records = cursor.fetchall()
        records = [dict(row) for row in records]
        ManageDatabase.close_connection(dbconn, cursor)

        auto_bet_active = records[0]['auto_bet_active']
        if auto_bet_active == True:
            auto_bet_active = 'checked'
        else:
            auto_bet_active = ''

        return auto_bet_active

    @staticmethod
    def stand_up_all_users():
        """
        Para a todos los usuarios de las mesas
        """
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        sql_query = """
        UPDATE 
            public.global_access 
        SET 
            access_date=%s, log_status=%s, auto_bet_active=%s
        WHERE 
            TRUE;
        """
        dt = datetime.datetime.now()
        cursor.execute(sql_query, (dt, False, False))
        dbconn.commit()
        count = cursor.rowcount
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def user_stand_up_table(affiliate_code):
        """
        Libera cupo en el roulette_id
        """
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        sql_query = """
        UPDATE 
            public.global_access 
        SET 
            roulette_id='-', auto_bet_active=False
        WHERE 
            affiliate_code=%s;
        """
        cursor.execute(sql_query, (affiliate_code,))
        dbconn.commit()
        count = cursor.rowcount
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def confirm_user_funds(token, amount:float):
        """
        Verifica si el usuario tiene saldo suficiente para apostar
        """
        return True

    @staticmethod
    def put_auto_bet_active(affiliate_code, _status) -> bool:
        """
        Coloca estado auto_bet_active para saber que el usuario nos abre sus fondos para jugar continuamente hasta que el decida
        """
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        sql_query = """
        UPDATE 
            public.global_access 
        SET 
            auto_bet_active=%s 
        WHERE 
            affiliate_code=%s;
        """
        cursor.execute(sql_query, (_status, affiliate_code))
        dbconn.commit()
        count = cursor.rowcount
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def set_user_roulette_id(affiliate_code, casino_account, roulette_id):

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        sql_query = """
        UPDATE 
            public.global_access 
        SET 
            roulette_id=%s, log_status=%s 
        WHERE 
            affiliate_code=%s AND casino_account=%s;
        """
        cursor.execute(sql_query, (roulette_id, True, affiliate_code, casino_account))
        dbconn.commit()
        count = cursor.rowcount
        if count > 0:
            return True
        else:
            return False

    @staticmethod
    def set_user_login(affiliate_code, casino_account):
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        sql_query = """
        SELECT 
            *
        FROM 
            public.global_access ga
        WHERE
            ga.affiliate_code = %s;
        """
        cursor.execute(sql_query, (affiliate_code,))
        record = cursor.fetchone()

        dt = datetime.datetime.now()
        if record:
            sql_query = """
            UPDATE 
                public.global_access
            SET 
                roulette_id='-', access_date=%s, auto_bet_active=%s, log_status=%s
            WHERE 
                affiliate_code=%s AND casino_account=%s;
            """
            cursor.execute(sql_query, (dt, False, True, affiliate_code, casino_account))
            dbconn.commit()
            count = cursor.rowcount
        else:
            sql_query = """
            INSERT INTO public.global_access (affiliate_code, access_date, log_status, casino_account, roulette_id, auto_bet_active)
            VALUES (%s, %s, %s, %s, %s, %s);
            """
            cursor.execute(sql_query, (affiliate_code, dt, True, casino_account, '-', False))
            dbconn.commit()
            count = cursor.rowcount
        ManageDatabase.close_connection(dbconn, cursor)

    @staticmethod
    def logout_user(affiliate_code):
        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return []
        sql_query = """
        UPDATE 
            public.global_access
        SET
            log_status=%s, auto_bet_active=%s, roulette_id='-', access_date=%s
        WHERE
            affiliate_code=%s;
        """
        dt = datetime.datetime.now()
        cursor.execute(sql_query, (False, False, dt, affiliate_code))
        dbconn.commit()
        ManageDatabase.close_connection(dbconn, cursor)

    @staticmethod
    def autenticate_user(affiliate_code, pwd):
        """
        Obtiene el casino asociado al correo indicado
        """

        #-- Convertir password en HASH
        h = hashlib.new('sha256')
        h.update(pwd.encode('utf-8'))
        pwd = h.hexdigest()

        dbconn, cursor, status = ManageDatabase.open_connection(Controls.HOST, Controls.DATABASE, Controls.USER, Controls.PASSWORD, Controls.PORT)
        if not status:
            return [], False

        if affiliate_code.startswith('CRP'):
            sql_query = """
            SELECT 
                casino_account, affiliate_code, username, userlastname,roulette_id 
            FROM 
                public.crupiers
            WHERE
                crupiers.affiliate_code = %s and crupiers.user_pin= %s;
            """
        else:
            sql_query = """
            SELECT 
                casino_account,affiliate_code,username,userlastname,roulette_id 
            FROM 
                public.customers
            WHERE
                customers.affiliate_code = %s and customers.user_pin= %s;
            """
        cursor.execute(sql_query, (affiliate_code, pwd))
        record = cursor.fetchone()
        ManageDatabase.close_connection(dbconn, cursor)
        
        if record:
            return record, True
        else:
            return '', False

#-------------------------------------------------

@app.route('/send_report', methods=['POST'])
def send_report():
    """
    Crea reporte del usuario
    """
    pass

@app.route('/reports', methods=['GET'])
def reports():
    """
    Muestra al usuario pagina para hacer reportes
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
        return render_template('reports.html')
    else:
        return render_template('unlogged.html'), 404

@app.route('/withdraw', methods=['GET'])
def withdraw():
    """
    Permite al usuario solicitar retiro de fondos
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
        return render_template('withdraw_page.html')
    else:
        return render_template('unlogged.html'), 404

@app.route('/history', methods=['GET'])
def history():
    """
    Permite al usuario ver el historico de jugadas
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
        return render_template('history_page.html')
    else:
        return render_template('unlogged.html'), 404

@app.route('/pay', methods=['POST'])
def pay():
    """
    Permite al usuario hacer un deposito a su cuenta
    """
    return render_template('deposit_send.html')

@app.route('/deposit', methods=['GET'])
def deposit_page():
    """
    Muestra la pagina de depositos
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
        return render_template('deposit_page.html', betcris_account=session['casino_account'], reload_type='Recarga Betcris')
    else:
        return render_template('unlogged.html'), 404

@app.route('/exit_table', methods=['POST'])
def exit_table():
    """
    Permite que el usuario desocupe la mesa
    """
    data = request.get_json()
    if 'token' in session.keys():
        session['roulette_id'] = False
        roulette_id = data['roulette_id']
        token = session['token']
        #-- Actualizar cupo en mesa
        Controls.user_stand_up_table(session['affiliate_code'])
        return jsonify({'info':'Gracias por su participacion', 'url':'/roulettes'})
    else:
        Controls.remove_session_keys()
        return render_template('unlogged.html'), 404

@app.route('/cancel_bet', methods=['POST'])
def cancel_bet():
    """
    Cancela la apuesta ,si existe, para el usuario en la tabla roulette_id
    """
    #-- Busca en la base de datos si existe alguna apuesta del usuario en la roulette_id
    #-- Retira la entrada del usuario en la mesa
    return jsonify({'info':'Su apuesta a sido cancelada.Siempre recuerde cancelar a tiempo, si excede el tiempo de corte no hay vuelta atras', 'status':True})

@app.route('/put_bet', methods=['POST'])
def put_bet():
    """
    El usuario confirma su inversion. Verificamos la apuesta y le indicamos si es aprobada o no.
    """
    data = request.get_json()
    if 'token' in session.keys():
        try:
            roulette_id = data['roulette_id']
            if_bet = data['if_bet']
            user_plays = int(float(data['user_plays']))
            user_covers = int(float(data['user_covers']))
            table_type = data['roulette_type']

            if table_type in ('X2', 'X3', 'X6'):
                #-- En este caso las jugadas las colocara el crupier, una para cada jugador
                if if_bet:
                    #-- Buscar el monto proximo en la base de datos
                    amount = 1
                    #-- Confirma que el usuario tenga saldo para esto y descuentaselo
                    _confimation = Controls.confirm_user_funds(session['token'], amount)
                    if _confimation:
                        #-- Colocar auto_bet_active en True
                        _status = Controls.put_auto_bet_active(session['affiliate_code'], True)
                        if _status:
                            return jsonify({'info':f'Disponibilidad *ACTIVADA*.\nMantenga su balance en observación y deténgase cuando alcance el beneficio que se haya propuesto.\n SUERTE!', 'status':True})
                        else:
                            return jsonify({'info':f'No fue posible aceptar su propuesta, intente más tarde', 'status':False})
                    else:
                        return jsonify({'info':f'No dispones de saldo para cubrir este tipo de jugadas, recarga tu cuenta', 'status':False})
                else:
                    _status = Controls.put_auto_bet_active(session['affiliate_code'], False)
                    if _status:
                        return jsonify({'info':f'Disponibilidad *DESACTIVADA*', 'status':True})
                    else:
                        return jsonify({'info':f'No fue posible efectuar el cambio indicado', 'status':False})
            else:
                try:
                    amount = float(data['bet_amount'])
                except Exception as e:
                    return jsonify({'info':f'Debe indicar un monto valido', 'status':False})

                if amount in [round(x['amount']*user_plays+user_covers, 2) for x in Controls.get_table_amounts(roulette_id, session['token'])]:
                    if if_bet:
                        #-- Confirma que el usuario tenga saldo para esto y descuentaselo
                        _confimation = Controls.confirm_user_funds(session['token'], amount)
                        if _confimation:
                            #-- En este caso la jugada la crea el propio jugador
                            #-- Coloca la apuesta del usuario en la base de datos
                            insert_status, message = Controls.insert_customer_play(amount, session['roulette_id'], session['affiliate_code'])
                            return jsonify({'info':message, 'status':insert_status})
                        else:
                            return jsonify({'info':f'No dispones de saldo para cubrir un monto de ${amount}, debe recargar su cuenta', 'status':False})
                    else:
                       return jsonify({'info':f'No voy', 'status':True})
                else:
                    return jsonify({'info':f'El monto {amount} no es valido, intente de nuevo con una denominacion valida', 'status':False})
        except Exception as e:
            return jsonify({'info':'Ocurrio un error en la transaccion', 'status':False})
    else:
        Controls.remove_session_keys()
        return render_template('main_page.html')

@app.route('/upload_deposit', methods=['POST'])
def upload_deposit():
    """
    Permite subir una imagen y datos de pago
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))

        file = request.files['file']
        if not file:
            return render_template('not_found.html', message='File not found')
        else:
            file.save(app.config['UPLOAD_PATH'] + '/' + file.filename)
            return render_template('deposit_send.html', message='File uploaded successfully')
    else:
        Controls.remove_session_keys()
        return render_template('unlogged.html'), 404

@app.route('/roulettes', methods=['GET'])
def roulettes():
    """
    Usuario indica que va en la apuesta
    """
    if 'token' in session.keys():
        #-- Esta parte magicamente hace que los crupiers sean redirijidos inmediatamente a su mesa porque su roulette_id siempr viene lleno.
        #-- Para los usuarios customers NO a menos que hayan estado conectados antes a la roulette_id
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
        else:
            roulettes=Controls.get_roulettes(session['token'])
            probabilities=Controls.get_roulette_probabilities(session['token'])
            for r in roulettes:
                r.update({'online_users':len(Controls.get_roulette_online_users(r['roulette_id'], session['token'])) })
            return render_template('roulettes.html', probabilities=probabilities, roulettes=roulettes)
    else:
        Controls.remove_session_keys()
        return render_template('unlogged.html'), 404

@app.route('/set_new_round', methods=['GET'])
def set_new_round():
    """
    Devuelve el paso del crupier a 0
    """
    if 'token' in session.keys():
        if session['affiliate_code'].startswith('CRP'):
            status = Controls.update_step(session['roulette_id'], 0)
            Controls.set_session_round(session['roulette_id'])
            if status:
                message = 'Nueva ronda iniciada'
            else:
                message = 'No fue posible reiniciar conteo'
            return jsonify({'status':status, 'message':message })
        else:
            Controls.remove_session_keys()
            return jsonify({'status':False, 'message':'Acceso denegado' })
    else:
        Controls.remove_session_keys()
        return jsonify({'status':False, 'message':'Acceso denegado' })

@app.route('/calculate_unitary_amount', methods=['POST'])
def calculate_unitary_amount():
    data = request.get_json()
    mode = data['mode']

    if 'token' in session.keys():
        if session['affiliate_code'].startswith('CRP'):
            status, total_units = Controls.calculate_unitary_amount(session['roulette_id'])
            if status:
                message = 'Montos calculados'
            else:
                message = 'No fue posible calcular el monto'
            return jsonify({'total_units':total_units, 'status':status, 'message':message })
        else:
            Controls.remove_session_keys()
            return jsonify({'total_units':0, 'status':False, 'message':'Acceso denegado' })
    else:
        Controls.remove_session_keys()
        return jsonify({'total_units':0, 'status':False, 'message':'Acceso denegado' })

@app.route('/no_more_bets', methods=['GET'])
def no_more_bets():
    if 'token' in session.keys():
        if session['affiliate_code'].startswith('CRP'):
            status = Controls.no_more_bets(session['roulette_id'])
            if status:
                message = 'Apuestas cerradas'
            else:
                message = 'Ocurrio algun error cerrando apuestas, verifique pronto'
            return jsonify({'numbers':[], 'status':status, 'message':message })
        else:
            Controls.remove_session_keys()
            return jsonify({'numbers':[], 'status':False, 'message':'Acceso denegado' })
    else:
        Controls.remove_session_keys()
        return jsonify({'numbers':[], 'status':False, 'message':'Acceso denegado' })

@app.route('/bet_now', methods=['GET'])
def bet_now():
    if 'token' in session.keys():
        if session['affiliate_code'].startswith('CRP'):
            status = Controls.bet_now(session['roulette_id'])
            message = '💲 Hagan sus apuestas 💲'
            return jsonify({'numbers':[], 'status':status, 'message':message })
        else:
            Controls.remove_session_keys()
            return jsonify({'numbers':[], 'status':False, 'message':'Acceso denegado' })
    else:
        Controls.remove_session_keys()
        return jsonify({'numbers':[], 'status':False, 'message':'Acceso denegado' })

@app.route('/set_open_numbers', methods=['GET'])
def set_roulette_opens():
    """
    Permite que el administrador genere los numeros
    """
    if 'token' in session.keys():
        if session['affiliate_code'].startswith('CRP'):
            numbers, status = Controls.set_open_numbers(session['roulette_id'])
            if status:
                message =  f'Numeros generados satisfactoriamente {numbers}'
            else:
                message = 'Ocurrio un error generando los numeros intente de nuevo!'
            return jsonify({'numbers':numbers, 'status':status, 'message':message })
        else:
            Controls.remove_session_keys()
            return jsonify({'numbers':[], 'status':False, 'message':'Acceso denegado' })
    else:
        Controls.remove_session_keys()
        return jsonify({'numbers':[], 'status':False, 'message':'Acceso denegado' })

@app.route('/publish_result', methods=['POST'])
def publish_result():
    """
    Captura todas las apuestas colocadas. Funcion de administrador
    """
    if 'token' in session.keys():
        if session['affiliate_code'].startswith('CRP'):
            data = request.get_json()
            roulette_result = data['roulette_result']
            Controls.publish_result(session['roulette_id'],  roulette_result)
            return jsonify({'message':'Ronda completada'})
        else:
            Controls.remove_session_keys()
            return render_template('denegado.html'), 404
    else:
        Controls.remove_session_keys()
        return render_template('denegado.html'), 404

@app.route('/spin_roulette', methods=['GET'])
def spin_roulette():
    """
    Captura todas las apuestas colocadas. Funcion de administrador
    """
    if 'token' in session.keys():
        if session['affiliate_code'].startswith('CRP'):
            Controls.spin_roulette(session['roulette_id'])
            return jsonify({'message':'Prepare la ruleta con la ficha indicada luego reporte el resultado'})
        else:
            Controls.remove_session_keys()
            return render_template('denegado.html'), 404
    else:
        Controls.remove_session_keys()
        return render_template('denegado.html'), 404

@app.route('/get_roulette_changes', methods=['GET'])
def get_roulette_changes():
    if 'token' in session.keys():
        online_users = len(Controls.get_roulette_online_users(session['roulette_id'], session['token']))
        roulette_data = Controls.get_roulette_data(session['roulette_id'], session['token'])
        roulette_data.update({'online_users':online_users})
        return jsonify(roulette_data)
    else:
        Controls.remove_session_keys()
        return jsonify({'error':True})

@app.route('/table/<roulette_id>', methods = ['GET'])
def usr_view_table(roulette_id):
    """
    Muestra la mesa actualizada al usuario
    """
    if 'token' in session.keys():

        online_users = Controls.get_roulette_online_users(roulette_id, session['token'])
        roulette_data = Controls.get_roulette_data(roulette_id, session['token'])
        user_in_table = False

        #-- Verifica si el usuario ya esta conectado en la ruleta
        for af in online_users:
            if 'affiliate_code' in af.keys():
                if session['affiliate_code'] == af['affiliate_code']:
                    user_in_table = True
                    break

        if session['affiliate_code'].startswith('CRP'):
            #-- En este caso roulette_id es la mesa que puede atender el crupier.
            #-- si el intenta entrar en una mesa que no le corresponde, el sistema no se lo permitira
            if session['roulette_id'] == roulette_id:
                Controls.set_user_roulette_id(session['affiliate_code'], session['casino_account'], roulette_id)
                Controls.update_token(roulette_id)
                session['roulette_id'] = roulette_id
                round_number = Controls.get_session_round(roulette_id)
                table_amounts = enumerate(Controls.get_table_amounts(roulette_id, session['token']))
                active_users = Controls.get_active_users(roulette_id)
                return render_template('adm_table_view.html',
                                            table_amounts = table_amounts,
                                            roulette_id = roulette_id,
                                            online_users = online_users,
                                            roulette_data = roulette_data,
                                            round_number = round_number,
                                            active_users = active_users
                                            )
            else:
                return render_template('denegado.html')
        else:
            #Obtiene el saldo en la cuenta del usuario
            amount = Controls.get_user_amount(session['token'])
            roulette_max_users = roulette_data['roulette_max_users']

            if (len(online_users) < roulette_max_users) or user_in_table :
                Controls.clear_user_table_status(session['affiliate_code'], session['casino_account'], roulette_id)
                Controls.set_user_roulette_id(session['affiliate_code'], session['casino_account'], roulette_id)
                Controls.update_token(roulette_id)
                session['roulette_id'] = roulette_id
                round_number = Controls.get_session_round(roulette_id)
                table_amounts = enumerate(Controls.get_table_amounts(roulette_id, session['token']))
                on_if = Controls.get_auto_bet_status(session['affiliate_code'], roulette_id)
                return render_template('usr_table_view.html',
                                        amount = amount,
                                        on_if = on_if,
                                        table_amounts = table_amounts,
                                        roulette_id = roulette_id,
                                        online_users = online_users,
                                        roulette_data = roulette_data
                                        )
            else:
                return render_template('table_full.html'), 200
    else:
        Controls.remove_session_keys()
        return render_template('unlogged.html'), 404

@app.route('/help', methods = ['GET'])
def help():
    """
    Muestra la mesa actualizada al usuario
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
    return render_template('help.html')

@app.route('/register', methods = ['POST'])
def register():
    """
    Registrar usuario en base de datos
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
    return jsonify({'note':'USUARIO REGISTRADO'})

@app.route('/signup_page', methods = ['POST', 'GET'])
def signup_page():
    """
    Mostrar pagina de registro
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
    return render_template('signup_page.html')
   
@app.route('/login_page', methods = ['GET'])
def login_page():
    """
    Mostrar pagina de login
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
    return render_template('login_page.html')

@app.route('/logout', methods = ['GET'])
def logout():
    """
    Desloguear usuario y todo lo que ello implica
    """
    if 'token' in session.keys():
        #-- Actualizar cupo en mesas
        Controls.logout_user(session['affiliate_code'])
        Controls.remove_session_keys()
    return render_template('main_page.html')

@app.route('/bad_credentials', methods = ['GET'])
def bad_credentials():
    return render_template('bad_credentials.html')

@app.route('/auth', methods = ['POST'])
def auth():
    """
    Autentica usuario en base datos
    """

    affiliate_code = request.form['affiliate_code'].upper()
    pwd = request.form['pwd']
    #-- Proceso de autenticacion
    user_data, valid_user = Controls.autenticate_user(affiliate_code, pwd)

    if valid_user:
        session['casino_account'] = user_data['casino_account']
        session['username'] = user_data['username']
        session['userlastname'] = user_data['userlastname']
        session['affiliate_code'] = user_data['affiliate_code']

        if affiliate_code.startswith('CRP'):
            session['roulette_id'] = user_data['roulette_id']
        else:
            session['roulette_id'] = False

        #--crear token
        payload = {'uuid':str(uuid.uuid1()), 'affiliate_code':affiliate_code, 'casino_account':user_data['casino_account'], 'username':user_data['username'], 'userlastname':user_data['userlastname'], 'roulette_id':user_data['roulette_id'], 'date_connection':datetime.datetime.now().strftime('%Y-%m-%d')}
        token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
        session['token'] = token
        
        Controls.set_user_login(affiliate_code, user_data['casino_account'])

        return redirect(url_for('roulettes', roulettes=Controls.get_roulettes(session['token'])))
    else:
        return redirect(url_for('bad_credentials'))

@app.route('/', methods = ['GET'])
@app.route('/casino', methods = ['GET'])
def main_page():
    """
    Mostrar pagina principal
    """
    if 'token' in session.keys():
        if session['roulette_id'] != False:
            return redirect(url_for('usr_view_table', roulette_id=session['roulette_id']))
    return render_template('main_page.html')

@app.route('/<folder>/<filename>')
def download(folder, filename):
    """
    Sirve el archivo desde la ruta indicada
    """
    downloads_dir = os.path.join(os.path.expanduser('~'), folder)
    return send_from_directory(directory=downloads_dir, path=filename, as_attachment=True)

@app.route('/files/<folder>/<filename>')
def serve_static(folder, filename):
    root_dir = os.path.join(os.path.expanduser('~'), folder)
    response = send_from_directory(directory=root_dir, path=filename, as_attachment=True)
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Cache-Control'] = 'public, max-age=31536000'
    response.headers['Connection'] = 'keep-alive'
    return response

#@app.errorhandler(404)
#def page_not_found(error):
#    return render_template('404.html'), 404

#@app.errorhandler(Exception)
#def handle_exception(e):
#    return render_template('500.html'), 500

if __name__ == '__main__':
    Controls.stand_up_all_users()
    app.run(debug=True, port=PORT_FLASK, host='0.0.0.0')
