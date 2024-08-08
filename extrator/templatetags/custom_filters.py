# extrator/templatetags/custom_filters.py

from django import template
from datetime import date

register = template.Library()

@register.filter
def age(value):
    if value:
        today = date.today()
        born = value
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return ''
