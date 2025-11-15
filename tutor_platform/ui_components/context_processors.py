from django.conf import settings
from django.http import HttpRequest


def ui_context(request: HttpRequest):
    """
    Context processor for UI components.
    Adds UI configuration and settings to template context.
    """
    ui_config = getattr(settings, 'UI_COMPONENTS', {})
    
    # Get theme from cookie or default
    theme = request.COOKIES.get(
        ui_config.get('THEME_STORAGE_KEY', 'ui_theme'),
        ui_config.get('DEFAULT_THEME', 'light')
    )
    
    # Build context
    context = {
        # Theme settings
        'ui_theme': theme,
        'theme_cookie_name': ui_config.get('THEME_STORAGE_KEY', 'ui_theme'),
        
        # HTMX settings
        'htmx_enabled': ui_config.get('HTMX_ENABLED', True),
        'htmx_default_target': ui_config.get('HTMX_DEFAULT_TARGET', '#content'),
        'htmx_default_swap': ui_config.get('HTMX_DEFAULT_SWAP', 'innerHTML'),
        'htmx_loading_class': ui_config.get('HTMX_LOADING_CLASS', 'htmx-loading'),
        'htmx_request_class': ui_config.get('HTMX_REQUEST_CLASS', 'htmx-request'),
        'htmx_indicator_class': ui_config.get('HTMX_INDICATOR_CLASS', 'htmx-indicator'),
        
        # Alpine.js settings
        'alpine_enabled': ui_config.get('ALPINE_ENABLED', True),
        'alpine_debug': ui_config.get('ALPINE_DEBUG', settings.DEBUG),
        
        # Component settings
        'auto_initialize': ui_config.get('AUTO_INITIALIZE', True),
        'lazy_load_images': ui_config.get('LAZY_LOAD_IMAGES', True),
        'animations_enabled': ui_config.get('ANIMATIONS_ENABLED', True),
        'toast_notifications': ui_config.get('TOAST_NOTIFICATIONS', True),
        'toast_duration': ui_config.get('TOAST_DURATION', 5000),
        'toast_position': ui_config.get('TOAST_POSITION', 'top-right'),
        
        # Form settings
        'form_auto_resize': ui_config.get('FORM_AUTO_RESIZE', True),
        'form_char_counter': ui_config.get('FORM_CHAR_COUNTER', True),
        'form_auto_focus': ui_config.get('FORM_AUTO_FOCUS', True),
        'form_validation_feedback': ui_config.get('FORM_VALIDATION_FEEDBACK', True),
        
        # Table settings
        'table_sorting': ui_config.get('TABLE_SORTING', True),
        'table_filtering': ui_config.get('TABLE_FILTERING', True),
        'table_pagination': ui_config.get('TABLE_PAGINATION', True),
        'table_items_per_page': ui_config.get('TABLE_ITEMS_PER_PAGE', 25),
        'table_search_debounce': ui_config.get('TABLE_SEARCH_DEBOUNCE', 300),
        
        # Modal settings
        'modal_backdrop': ui_config.get('MODAL_BACKDROP', True),
        'modal_keyboard': ui_config.get('MODAL_KEYBOARD', True),
        'modal_focus': ui_config.get('MODAL_FOCUS', True),
        'modal_animation': ui_config.get('MODAL_ANIMATION', True),
        
        # Search settings
        'search_auto_complete': ui_config.get('SEARCH_AUTO_COMPLETE', True),
        'search_recent_searches': ui_config.get('SEARCH_RECENT_SEARCHES', True),
        'search_max_recent': ui_config.get('SEARCH_MAX_RECENT', 5),
        'search_debounce': ui_config.get('SEARCH_DEBOUNCE', 300),
        
        # Notification settings
        'notification_polling': ui_config.get('NOTIFICATION_POLLING', True),
        'notification_poll_interval': ui_config.get('NOTIFICATION_POLL_INTERVAL', 30000),
        'notification_sound': ui_config.get('NOTIFICATION_SOUND', False),
        'notification_desktop': ui_config.get('NOTIFICATION_DESKTOP', False),
        
        # Performance settings
        'lazy_loading': ui_config.get('LAZY_LOADING', True),
        'image_optimization': ui_config.get('IMAGE_OPTIMIZATION', True),
        'minify_html': ui_config.get('MINIFY_HTML', not settings.DEBUG),
        'cache_templates': ui_config.get('CACHE_TEMPLATES', not settings.DEBUG),
        'compress_assets': ui_config.get('COMPRESS_ASSETS', not settings.DEBUG),
        
        # User information
        'is_authenticated': request.user.is_authenticated,
        'user_type': getattr(request.user, 'user_type', None) if request.user.is_authenticated else None,
        'user_display_name': request.user.get_full_name() or request.user.username if request.user.is_authenticated else None,
        
        # Request information
        'is_ajax': request.headers.get('X-Requested-With') == 'XMLHttpRequest',
        'is_htmx': request.headers.get('HX-Request') == 'true',
        'is_mobile': is_mobile(request),
        'is_tablet': is_tablet(request),
        'is_desktop': is_desktop(request),
    }
    
    return context


def is_mobile(request: HttpRequest) -> bool:
    """
    Check if the request is from a mobile device.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    mobile_keywords = [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 
        'windows phone', 'opera mini', 'iemobile'
    ]
    return any(keyword in user_agent for keyword in mobile_keywords)


def is_tablet(request: HttpRequest) -> bool:
    """
    Check if the request is from a tablet device.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    tablet_keywords = ['ipad', 'tablet', 'kindle', 'silk']
    return any(keyword in user_agent for keyword in tablet_keywords)


def is_desktop(request: HttpRequest) -> bool:
    """
    Check if the request is from a desktop device.
    """
    return not (is_mobile(request) or is_tablet(request))