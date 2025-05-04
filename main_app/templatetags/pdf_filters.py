from django import template

register = template.Library()

@register.filter
def get_range(value):
    """
    Returns a range of numbers from 0 to value-1.
    Usage: {% for i in value|get_range %}
    """
    return range(value)

@register.filter
def index(sequence, position):
    """
    Returns the item at the given position in a sequence.
    Usage: {{ sequence|index:position }}
    """
    return sequence[position] 