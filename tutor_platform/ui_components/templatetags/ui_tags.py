from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import format_html, mark_safe
from django.utils.safestring import mark_safe
import json
import re

register = template.Library()


@register.filter
@stringfilter
def add_class(value, css_class):
    """
    Adds a CSS class to a form field widget.
    Usage: {{ field|add_class:"form-control" }}
    """
    if hasattr(value, 'as_widget'):
        widget = value.field.widget
        current_classes = widget.attrs.get('class', '')
        if current_classes:
            new_classes = f"{current_classes} {css_class}"
        else:
            new_classes = css_class
        widget.attrs['class'] = new_classes
        return value
    return value


@register.filter
def get_attr(obj, attr):
    """
    Gets an attribute of an object, supports nested attributes.
    Usage: {{ user|get_attr:"profile.bio" }}
    """
    try:
        for part in attr.split('.'):
            obj = getattr(obj, part)
        return obj
    except (AttributeError, TypeError):
        return None


@register.filter
def currency(value):
    """
    Formats a number as currency.
    Usage: {{ price|currency }}
    """
    try:
        value = float(value)
        return f"${value:,.2f}"
    except (ValueError, TypeError):
        return value


@register.filter
def date(value, format_string="M d, Y"):
    """
    Formats a date.
    Usage: {{ created_at|date }}
    """
    try:
        from django.utils import timezone
        if hasattr(value, 'strftime'):
            return value.strftime(format_string)
        return value
    except (AttributeError, ValueError):
        return value


@register.filter
def datetime(value, format_string="M d, Y h:i A"):
    """
    Formats a datetime.
    Usage: {{ created_at|datetime }}
    """
    try:
        from django.utils import timezone
        if hasattr(value, 'strftime'):
            return value.strftime(format_string)
        return value
    except (AttributeError, ValueError):
        return value


@register.filter
def time_ago(value):
    """
    Returns a human-readable time ago string.
    Usage: {{ created_at|time_ago }}
    """
    try:
        from django.utils import timezone
        import datetime
        
        if not isinstance(value, (datetime.datetime, datetime.date)):
            return value
            
        now = timezone.now()
        if isinstance(value, datetime.date):
            value = timezone.make_aware(datetime.datetime.combine(value, datetime.time.min))
            
        diff = now - value
        
        if diff.days == 0:
            if diff.seconds < 60:
                return "just now"
            elif diff.seconds < 3600:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            else:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} week{'s' if weeks != 1 else ''} ago"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months} month{'s' if months != 1 else ''} ago"
        else:
            years = diff.days // 365
            return f"{years} year{'s' if years != 1 else ''} ago"
    except (AttributeError, TypeError, ImportError):
        return value


@register.filter
def truncate_words(value, num_words=10, suffix="..."):
    """
    Truncates text after a certain number of words.
    Usage: {{ content|truncate_words:20 }}
    """
    try:
        words = value.split()
        if len(words) <= num_words:
            return value
        return ' '.join(words[:num_words]) + suffix
    except (AttributeError, TypeError):
        return value


@register.filter
def truncate_chars(value, num_chars=100, suffix="..."):
    """
    Truncates text after a certain number of characters.
    Usage: {{ content|truncate_chars:100 }}
    """
    try:
        if len(value) <= num_chars:
            return value
        return value[:num_chars] + suffix
    except (AttributeError, TypeError):
        return value


@register.filter
def yesno(value, yes="Yes", no="No", maybe="Maybe"):
    """
    Returns Yes/No/Maybe based on the value.
    Usage: {{ is_active|yesno }}
    """
    if value is True:
        return yes
    elif value is False:
        return no
    else:
        return maybe


@register.filter
def default_if_none(value, default=""):
    """
    Returns default value if the value is None.
    Usage: {{ user.bio|default_if_none:"No bio available" }}
    """
    return value if value is not None else default


@register.filter
def percentage(value, total):
    """
    Calculates percentage.
    Usage: {{ votes|percentage:total_votes }}
    """
    try:
        if total == 0:
            return 0
        return round((value / total) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def file_size(value):
    """
    Formats file size in human-readable format.
    Usage: {{ file.size|file_size }}
    """
    try:
        size = int(value)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    except (ValueError, TypeError):
        return value


@register.filter
def phone_number(value):
    """
    Formats a phone number.
    Usage: {{ user.phone|phone_number }}
    """
    try:
        # Remove all non-numeric characters
        phone = re.sub(r'\D', '', str(value))
        
        # Format based on length
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone[0] == '1':
            return f"+1 ({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        else:
            return value
    except (AttributeError, TypeError):
        return value


@register.simple_tag
def htmx_attrs(target=None, swap=None, trigger=None, indicator=None, push_url=None):
    """
    Generates HTMX attributes.
    Usage: {% htmx_attrs target="#content" swap="innerHTML" %}
    """
    attrs = []
    
    if target:
        attrs.append(f'hx-target="{target}"')
    
    if swap:
        attrs.append(f'hx-swap="{swap}"')
    
    if trigger:
        attrs.append(f'hx-trigger="{trigger}"')
    
    if indicator:
        attrs.append(f'hx-indicator="{indicator}"')
    
    if push_url:
        attrs.append(f'hx-push-url="{push_url}"')
    
    return mark_safe(' '.join(attrs))


@register.simple_tag
def alpine_data(**kwargs):
    """
    Generates Alpine.js data attributes.
    Usage: {% alpine_data open=false search="" %}
    """
    data = {}
    for key, value in kwargs.items():
        if isinstance(value, bool):
            data[key] = value
        elif isinstance(value, str):
            data[key] = f"'{value}'"
        else:
            data[key] = value
    
    json_data = json.dumps(data)
    return mark_safe(f'x-data="{json_data}"')


@register.simple_tag
def alpine_bind(attribute, expression):
    """
    Generates Alpine.js bind attribute.
    Usage: {% alpine_bind "class" "open ? 'active' : ''" %}
    """
    return mark_safe(f'x-bind:{attribute}="{expression}"')


@register.simple_tag
def alpine_on(event, expression):
    """
    Generates Alpine.js on attribute.
    Usage: {% alpine_on "click" "open = !open" %}
    """
    return mark_safe(f'x-on:{event}="{expression}"')


@register.simple_tag
def alpine_transition(show=True, enter="transition ease-out duration-300", 
                    enter_start="opacity-0", enter_end="opacity-100",
                    leave="transition ease-in duration-200",
                    leave_start="opacity-100", leave_end="opacity-0"):
    """
    Generates Alpine.js transition attributes.
    Usage: {% alpine_transition %}
    """
    attrs = []
    
    if show:
        attrs.append('x-show="show"')
        attrs.append('x-transition')
        attrs.append(f'x-enter="{enter}"')
        attrs.append(f'x-enter-start="{enter_start}"')
        attrs.append(f'x-enter-end="{enter_end}"')
        attrs.append(f'x-leave="{leave}"')
        attrs.append(f'x-leave-start="{leave_start}"')
        attrs.append(f'x-leave-end="{leave_end}"')
    
    return mark_safe(' '.join(attrs))


@register.inclusion_tag('ui_components/breadcrumb.html')
def breadcrumb(items):
    """
    Renders a breadcrumb navigation.
    Usage: {% breadcrumb items %}
    """
    return {'items': items}


@register.inclusion_tag('ui_components/alert.html')
def alert(message, level='info', dismissible=True, icon=None):
    """
    Renders an alert message.
    Usage: {% alert "Success message" "success" %}
    """
    return {
        'message': message,
        'level': level,
        'dismissible': dismissible,
        'icon': icon
    }


@register.inclusion_tag('ui_components/badge.html')
def badge(text, level='secondary', pill=False):
    """
    Renders a badge.
    Usage: {% badge "New" "success" pill=True %}
    """
    return {
        'text': text,
        'level': level,
        'pill': pill
    }


@register.inclusion_tag('ui_components/progress.html')
def progress(value, total=100, show_percentage=True, striped=False, animated=False):
    """
    Renders a progress bar.
    Usage: {% progress 75 100 %}
    """
    percentage = 0
    try:
        value = float(value)
        total = float(total)
        if total > 0:
            percentage = min(100, (value / total) * 100)
    except (ValueError, TypeError, ZeroDivisionError):
        pass
    
    return {
        'value': value,
        'total': total,
        'percentage': percentage,
        'show_percentage': show_percentage,
        'striped': striped,
        'animated': animated
    }


@register.inclusion_tag('ui_components/avatar.html')
def avatar(user, size='md', show_name=False, link=False):
    """
    Renders a user avatar.
    Usage: {% avatar user "lg" True True %}
    """
    return {
        'user': user,
        'size': size,
        'show_name': show_name,
        'link': link
    }


@register.inclusion_tag('ui_components/rating.html')
def rating(value, max_rating=5, readonly=True, show_value=False):
    """
    Renders a star rating.
    Usage: {% rating 4 5 False True %}
    """
    return {
        'value': value,
        'max_rating': max_rating,
        'readonly': readonly,
        'show_value': show_value
    }


@register.simple_tag
def csrf_token_script():
    """
    Returns a script tag with CSRF token for AJAX requests.
    Usage: {% csrf_token_script %}
    """
    try:
        from django.middleware.csrf import get_token
        from django.template import RequestContext
        request = None  # This would need to be passed in a real implementation
        token = get_token(request) if request else ''
        return mark_safe(f'<script>window.CSRF_TOKEN = "{token}";</script>')
    except ImportError:
        return mark_safe('<script>window.CSRF_TOKEN = "";</script>')


@register.filter
def markdown(value):
    """
    Converts markdown to HTML.
    Usage: {{ content|markdown }}
    """
    try:
        import markdown
        return mark_safe(markdown.markdown(value, safe_mode='escape'))
    except ImportError:
        return value


@register.filter
def urlize(value):
    """
    Converts URLs in text to clickable links.
    Usage: {{ content|urlize }}
    """
    try:
        import re
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        urls = re.findall(url_pattern, value)
        
        for url in urls:
            value = value.replace(url, f'<a href="{url}" target="_blank" rel="noopener">{url}</a>')
        
        return mark_safe(value)
    except (AttributeError, TypeError):
        return value