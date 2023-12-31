from django import template
from .. import views
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
    return int(exp) // 100


# возвращает id пользователя в дискорд если он есть на переданном сервере
@register.simple_tag(name='on_server')
def on_server(user_id: str, server_id: int):
    try:
        return views.on_server(user_id, server_id)
    except Exception as ex:
        logger.error(ex)
        return False


# берём данные о вкладе пользователя и если надо, то обновляем информацию о нём
@register.simple_tag(name='deposit_info')
def deposit_info(user_uuid):
    try:
        deposit = views.get_deposit_info(user_uuid)
        if deposit:
            change = views.calculate_deposit(deposit[0], deposit[5], deposit[4])
            if change:
                deposit = views.get_deposit_info(user_uuid)
            return deposit
        else:
            return False
    except Exception as ex:
        logger.error(ex)
        return False

