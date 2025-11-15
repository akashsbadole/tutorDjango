from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def star_range(value):
    """Create a range of star icons based on rating value"""
    try:
        rating = float(value)
        full_stars = int(rating)
        half_star = 1 if rating - full_stars >= 0.5 else 0
        empty_stars = 5 - full_stars - half_star
        
        stars = []
        # Add full stars
        for _ in range(full_stars):
            stars.append('full')
        # Add half star if needed
        if half_star:
            stars.append('half')
        # Add empty stars
        for _ in range(empty_stars):
            stars.append('empty')
            
        return stars
    except (ValueError, TypeError):
        return []

@register.filter
def star_display(value):
    """Display star rating with HTML"""
    stars = star_range(value)
    html = '<span class="text-warning">'
    for star_type in stars:
        if star_type == 'full':
            html += '<i class="bi bi-star-fill"></i>'
        elif star_type == 'half':
            html += '<i class="bi bi-star-half"></i>'
        else:
            html += '<i class="bi bi-star"></i>'
    html += '</span>'
    return mark_safe(html)