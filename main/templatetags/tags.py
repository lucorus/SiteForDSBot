from django import template
from .. import functions
import logging

logger = logging.getLogger('main')

register = template.Library()


# каждый уровень - 100 опыта.
# данная функция возвращает сколько процентов от следующего уровня уже есть у пользователя
@register.simple_tag(name='percent')
def percent(exp):
    return str(exp % 100) + '%'


# возвращает кол-во уровней у пользователя
@register.simple_tag(name='level')
def level(exp):
    try:
        return int(exp) // 100
    except:
        return 0


# возвращает id пользователя в дискорд если он есть на переданном сервере
@register.simple_tag(name='on_server')
def on_server(user_id: int, server_id: int):
    try:
        return functions.on_server(int(user_id), server_id)
    except Exception as ex:
        logger.error(ex)
        return False


# берём данные о вкладе пользователя и если надо, то обновляем информацию о нём
@register.simple_tag(name='deposit_info')
def deposit_info(user_uuid):
    try:
        deposit = functions.get_deposit_info(user_uuid)
        if deposit:
            change = functions.calculate_deposit(deposit[0], deposit[5], deposit[4])
            if change:
                deposit = functions.get_deposit_info(user_uuid)
            return deposit
        else:
            return False
    except Exception as ex:
        logger.error(ex)
        return False

