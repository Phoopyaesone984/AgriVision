# marketPrice/templatetags/market_filters.py
from django import template

register = template.Library()

@register.filter
def unique_categories(crops):
    """Get unique categories from crop data"""
    categories = set()
    for item in crops:
        if item['crop'].category:
            categories.add(item['crop'].category)
    return sorted(list(categories))