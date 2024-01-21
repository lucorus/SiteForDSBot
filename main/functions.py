from SiteForDSBot.settings import BASE_DIR
from datetime import datetime
from typing import Union
from . import models
import psycopg2
import logging
import environ
import pytz
import uuid
import os


'''
Функции, которые используются в представлениях
'''


logger = logging.getLogger('main')
try:
    env = environ.Env()
    environ.Env.read_env(env_file=os.path.join(BASE_DIR, '.env'))
    host = env('host')
    user = env('user')
    password = env('password')
    database = env('database')

    connection = psycopg2.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    cursor = connection.cursor()
except Exception as ex:
    logger.critical(ex)


# функции, работающие с соединением:


# возвращает объект connection
# (использовать для операций, которые могут вызвать ошибку, что не пропадало основное соединение)
def create_connect() -> psycopg2.extensions.connection:
    try:
        connection = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            database=database,
        )
        return connection
    except Exception as ex:
        print(ex)


def close_connect(curs: psycopg2.extensions.cursor, conn: psycopg2.extensions.connection) -> None:
    curs.close()
    conn.close()


# функции, работающие с депозитом:


def get_deposit_info(user_uuid: str) -> list:
    deposit = []
    try:
        cursor.execute(
            '''
            SELECT * FROM deposit WHERE investor=%s
            ''', (user_uuid, )
        )
        deposit = cursor.fetchone()
    except Exception as ex:
        logger.error(ex)
    return deposit


# Вычисляет сколько баллов получил пользователь по депозиту с процентом contribution_coefficient
def calculate_percent(points, time_delta) -> int:
    points = points * 0.05 + points
    time_delta -= 1
    if time_delta > 0:
        return calculate_percent(points, time_delta)
    else:
        return round(points)


# Изменяет кол-во баллов пользователя по его вкладу в базе данных (возвращает True если было изменение, а иначе False)
def calculate_deposit(deposit_uuid: str, points: int, deposit_last_update_time_time: str) -> bool:
    try:
        # находим кол-во дней со дня создания счёта
        time_delta = datetime.strptime(time_now(), "%Y/%m/%d/%H/%M") \
                 - datetime.strptime(deposit_last_update_time_time, "%Y/%m/%d/%H/%M")
        time_delta = time_delta.total_seconds() // 86400

        # если прошло больше дня, то изменяем кол-во баллов на счёте
        if time_delta >= 1:
            points = calculate_percent(points, time_delta)
            connect = create_connect()
            curs = connect.cursor()

            curs.execute(
                '''
                UPDATE deposit SET current_points=%s, last_update=%s WHERE uuid=%s
                ''', (points, time_now(), deposit_uuid))
            connect.commit()
            close_connect(curs, connect)
            return True
    except Exception as ex:
        logger.error(ex)
    return False


def create_deposit(user_uuid: str, user_points: int, points: int) -> None:
    try:
        conn = create_connect()
        curs = conn.cursor()

        curs.execute(
        '''
        INSERT INTO deposit VALUES(%s, %s, %s, %s, %s, %s);
        UPDATE users SET points=%s WHERE uuid=%s;
        ''', (str(uuid.uuid4()), user_uuid, points, time_now(),
              time_now(), points, user_points - points, user_uuid)
        )

        conn.commit()
        close_connect(curs, conn)
    except Exception as ex:
        logger.error(ex)


def delete_deposit(deposit_uuid: str, user_points: int, deposit_points: int, user_uuid: str) -> None:
    try:
        conn = create_connect()
        curs = conn.cursor()
        curs.execute(
            '''
            DELETE FROM deposit WHERE uuid=%s;
            UPDATE users SET points=%s WHERE uuid=%s
            ''', (deposit_uuid, user_points + deposit_points, user_uuid)
        )

        conn.commit()
        close_connect(curs, conn)
    except Exception as ex:
        logger.error(ex)


# функции, работающие с пользователями:


# возвращает id пользователя, если пользователь на сервере, иначе false
def on_server(user_id: int, guild_id: int) -> Union[str, bool]:
    try:
        guild_id = int(guild_id)
        cursor.execute(
            '''
            SELECT user_id FROM users WHERE guild=%s
            ''', (guild_id, )
        )
        users = cursor.fetchall()

        if (user_id,) in users:
            return user_id
        return False
    except Exception as ex:
        print('______')
        logger.error(ex)
        return False


# возвращает данные о 100 пользователях с самым большим количеством баллов / пользователях одного сервера
def get_users_info(guild_id: int=None) -> list:
    users = []
    try:
        if guild_id == None:
            cursor.execute(
                """
                SELECT * FROM users
                JOIN guilds ON users.guild = guild_id
                ORDER BY users.points DESC
                LIMIT 100
                """
            )
        else:
            cursor.execute(
                """
                SELECT * FROM users
                JOIN guilds ON users.guild = guild_id
                WHERE users.guild=%s ORDER BY users.points DESC
                """, (guild_id, )
            )
        users = cursor.fetchall()
    except Exception as ex:
        logger.error(ex)
    return users


# возвращает информацию о всех серверах, где есть пользователь / о сервере с переданным id
def get_user_info(user_id: str, guild_id: int=None) -> list:
    try:
        user_id = int(user_id)
        if not guild_id:
            # если id сервера нет, то возвращаем все сервера с данным юзером
            cursor.execute(
                """
                SELECT * FROM users
                JOIN guilds ON users.guild = guild_id
                WHERE user_id=%s ORDER BY users.points DESC
                """, (user_id, )
            )
        else:
            # иначе только сервер с указанным id
            cursor.execute(
                """
                SELECT * FROM users
                JOIN guilds ON users.guild = guild_id
                WHERE user_id=%s AND guild_id=%s ORDER BY users.points DESC
                """, (user_id, guild_id)
            )
        user_ds = cursor.fetchall()
        return user_ds
    except Exception as ex:
        logger.error(ex)
        return []


# функции, работающие с данными о сервере:


# возвращает данные о сервере
def get_guild(guild_id: int) -> list:
    try:
        cursor.execute(
            '''
            SELECT * FROM guilds WHERE guild_id=%s
            ''', (guild_id, )
        )
        return cursor.fetchall()[0]
    except:
        return []


# другое:

def time_now() -> str:
    timezone = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(timezone)
    formatted_time = moscow_time.strftime('%Y/%m/%d/%H/%M')
    return formatted_time


# Проверяет данные формы на валидность и возвращает словарь с ошибками
def checking_form_data(username, password, email) -> dict:
    errors = {}
    if models.CustomUser.objects.filter(username__iexact=username).exists():
        errors['username'] = 'Пользователь с таким именем уже существует!'
    if len(password) < 8:
        errors['password'] = 'Пароль должен состоять минимум из 8 символов'
    if models.CustomUser.objects.filter(email__iexact=email).exists():
        errors['email'] = 'Пользователь с такой почтой уже существует!'
    return errors
