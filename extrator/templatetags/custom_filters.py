# extrator/templatetags/custom_filters.py

from django import template
from datetime import date, datetime

register = template.Library()

@register.filter
def age(value):
    if value:
        today = date.today()
        born = value
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return ''

@register.filter(name='convert_date_format')
def convert_date_format(value):
    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            return ''
    return value