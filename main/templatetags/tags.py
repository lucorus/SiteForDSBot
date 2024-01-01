from django import template
from .. import views

register = template.Library()


# каждый уровень - 100 опыта.
# данная функция возвращает сколько процентов от следующего уровня уже есть у пользователя
@register.simple_tag(name='percent')
def percent(exp):
    return str(exp % 100) + '%'


# возвращает кол-во уровней у пользователя
@register.simple_tag(name='level')
def level(exp):
    return int(exp) // 100


# возвращает id пользователя в дискорд если он есть на переданном сервере
@register.simple_tag(name='on_server')
def on_server(user_id: str, server_id: int):
    try:
        connection = views.connect_db()
        cursor = connection.cursor()

        cursor.execute('''
        SELECT user_id FROM users WHERE server_id=%s
        ''', (server_id, ))
        users = cursor.fetchall()

        if (user_id,) in users:
            return user_id
    except:
        pass
    finally:
        views.close_db(cursor, connection)
    return False


@register.simple_tag(name='deposit_info')
def deposit_info(user_uuid):
    try:
        deposit = views.get_deposit_info(user_uuid)
        if len(deposit) > 0:
            return deposit
        else:
            return False
    except:
        return False

