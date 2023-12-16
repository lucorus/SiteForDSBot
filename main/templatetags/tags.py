from django import template
register = template.Library()


'''
каждый уровень - 100 опыта.
данная функция возвращает сколько процентов от следующего уровня уже есть у пользователя
'''
@register.simple_tag(name='percent')
def percent(exp):
    return str(exp % 100) + '%'


'''
возвращает кол-во уровней у пользователя
'''
@register.simple_tag(name='level')
def level(exp):
    return exp // 100

