import uuid
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    NotificationPreference, NotificationTemplate, Notification,
    PushDevice, NotificationType, SystemNotification
)


class NotificationPreferenceForm(forms.ModelForm):
    """Form for updating notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'push_enabled', 'in_app_enabled',
            'email_message', 'email_proposal', 'email_award',
            'email_session', 'email_review', 'email_payment', 'email_system',
            'push_message', 'push_proposal', 'push_award',
            'push_session', 'push_review', 'push_payment', 'push_system',
            'in_app_message', 'in_app_proposal', 'in_app_award',
            'in_app_session', 'in_app_review', 'in_app_payment', 'in_app_system',
            'email_frequency', 'quiet_hours_enabled', 'quiet_hours_start',
            'quiet_hours_end', 'quiet_hours_timezone', 'auto_delete_read',
            'auto_delete_days'
        ]
        widgets = {
            'quiet_hours_start': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'quiet_hours_end': forms.TimeInput(
                attrs={'type': 'time', 'class': 'form-control'}
            ),
            'quiet_hours_timezone': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'email_frequency': forms.Select(
                attrs={'class': 'form-control'}
            ),
            'auto_delete_days': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '1', 'max': '365'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        """Customize form initialization"""
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to all fields
        for field_name, field in self.fields.items():
            if field.widget.__class__.__name__ not in ['CheckboxInput', 'Select']:
                field.widget.attrs['class'] = 'form-control'
        
        # Add help text for quiet hours
        self.fields['quiet_hours_start'].help_text = _(
            "Start time for quiet hours when notifications won't be sent"
        )
        self.fields['quiet_hours_end'].help_text = _(
            "End time for quiet hours when notifications won't be sent"
        )
        self.fields['quiet_hours_timezone'].help_text = _(
            "Timezone for quiet hours calculation"
        )
        
        # Add help text for auto-delete
        self.fields['auto_delete_days'].help_text = _(
            "Number of days after which read notifications are automatically deleted"
        )
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        
        quiet_hours_enabled = cleaned_data.get('quiet_hours_enabled')
        quiet_hours_start = cleaned_data.get('quiet_hours_start')
        quiet_hours_end = cleaned_data.get('quiet_hours_end')
        
        # Validate quiet hours
        if quiet_hours_enabled:
            if not quiet_hours_start or not quiet_hours_end:
                raise forms.ValidationError(_(
                    "Both quiet hours start and end must be set when quiet hours are enabled"
                ))
        
        # Validate auto-delete days
        auto_delete_read = cleaned_data.get('auto_delete_read')
        auto_delete_days = cleaned_data.get('auto_delete_days')
        
        if auto_delete_read and (not auto_delete_days or auto_delete_days <= 0):
            raise forms.ValidationError(_(
                "Auto-delete days must be a positive number when auto-delete is enabled"
            ))
        
        return cleaned_data


class NotificationTemplateForm(forms.ModelForm):
    """Form for creating and editing notification templates"""
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'notification_type', 'subject_template',
            'body_template', 'html_template', 'is_default', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'notification_type': forms.Select(attrs={'class': 'form-control'}),
            'subject_template': forms.TextInput(attrs={'class': 'form-control'}),
            'body_template': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'html_template': forms.Textarea(attrs={'class': 'form-control', 'rows': 12}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Customize form initialization"""
        super().__init__(*args, **kwargs)
        
        # Add help text for template fields
        self.fields['subject_template'].help_text = _(
            "Use {{ variable }} for placeholders. Available variables: "
            "title, content, recipient_name, sender_name, notification_type, "
            "priority, created_at, action_url, action_text"
        )
        self.fields['body_template'].help_text = _(
            "Use {{ variable }} for placeholders. Available variables: "
            "title, content, recipient_name, sender_name, notification_type, "
            "priority, created_at, action_url, action_text"
        )
        self.fields['html_template'].help_text = _(
            "HTML version of the email body. Use same variables as body template."
        )
        self.fields['is_default'].help_text = _(
            "Only one template can be default per notification type"
        )
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        is_default = cleaned_data.get('is_default')
        notification_type = cleaned_data.get('notification_type')
        
        # Check if there's already a default template for this type
        if is_default and notification_type:
            existing_default = NotificationTemplate.objects.filter(
                notification_type=notification_type,
                is_default=True
            ).exclude(pk=self.instance.pk if self.instance.pk else None)
            
            if existing_default.exists():
                raise forms.ValidationError(_(
                    "There is already a default template for this notification type"
                ))
        
        return cleaned_data


class NotificationSearchForm(forms.Form):
    """Form for searching and filtering notifications"""
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search notifications...')
        })
    )
    
    read_status = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('read', _('Read')),
            ('unread', _('Unread')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notification_type = forms.ChoiceField(
        choices=[('', _('All Types'))] + list(Notification.Type.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priority = forms.ChoiceField(
        choices=[('', _('All Priorities'))] + list(Notification.Priority.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(_(
                "Start date cannot be after end date"
            ))
        
        return cleaned_data


class BulkNotificationForm(forms.Form):
    """Form for bulk notification actions"""
    
    action = forms.ChoiceField(
        choices=[
            ('mark_read', _('Mark as Read')),
            ('mark_unread', _('Mark as Unread')),
            ('delete', _('Delete')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    notification_ids = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def clean_notification_ids(self):
        """Validate and convert notification IDs"""
        ids_string = self.cleaned_data.get('notification_ids')
        if not ids_string:
            return []
        
        try:
            # Split comma-separated IDs and convert to UUID list
            ids = [uuid.UUID(id.strip()) for id in ids_string.split(',') if id.strip()]
            return ids
        except ValueError:
            raise forms.ValidationError(_("Invalid notification IDs"))


class PushNotificationForm(forms.ModelForm):
    """Form for registering push notification devices"""
    
    class Meta:
        model = PushDevice
        fields = [
            'device_token', 'device_type', 'device_id',
            'app_version', 'os_version'
        ]
        widgets = {
            'device_token': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Device token'),
                'readonly': True
            }),
            'device_type': forms.Select(attrs={'class': 'form-control'}),
            'device_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Device identifier')
            }),
            'app_version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('App version')
            }),
            'os_version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Operating system version')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        """Customize form initialization"""
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['device_token'].help_text = _(
            "Unique token for push notifications (usually auto-detected)"
        )
        self.fields['device_type'].help_text = _(
            "Type of device (mobile, web, desktop)"
        )
        self.fields['device_id'].help_text = _(
            "Unique device identifier (optional)"
        )
        self.fields['app_version'].help_text = _(
            "Version of the app (optional)"
        )
        self.fields['os_version'].help_text = _(
            "Operating system version (optional)"
        )


class NotificationTypePreferenceForm(forms.ModelForm):
    """Form for managing notification type preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'email_enabled', 'push_enabled', 'in_app_enabled',
            'email_message', 'email_proposal', 'email_award',
            'email_session', 'email_review', 'email_payment', 'email_system',
            'push_message', 'push_proposal', 'push_award',
            'push_session', 'push_review', 'push_payment', 'push_system',
            'in_app_message', 'in_app_proposal', 'in_app_award',
            'in_app_session', 'in_app_review', 'in_app_payment', 'in_app_system',
        ]
        widgets = {
            'email_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'push_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'in_app_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Customize form initialization"""
        super().__init__(*args, **kwargs)
        
        # Group fields by category for better organization
        self.email_fields = [
            'email_message', 'email_proposal', 'email_award',
            'email_session', 'email_review', 'email_payment', 'email_system'
        ]
        self.push_fields = [
            'push_message', 'push_proposal', 'push_award',
            'push_session', 'push_review', 'push_payment', 'push_system'
        ]
        self.in_app_fields = [
            'in_app_message', 'in_app_proposal', 'in_app_award',
            'in_app_session', 'in_app_review', 'in_app_payment', 'in_app_system'
        ]
        
        # Add checkbox widgets to all boolean fields
        for field_name in self.email_fields + self.push_fields + self.in_app_fields:
            self.fields[field_name].widget = forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            )


class SystemNotificationForm(forms.ModelForm):
    """Form for creating and editing system notifications"""
    
    class Meta:
        model = SystemNotification
        fields = [
            'title', 'message', 'notification_type', 'target_audience',
            'priority', 'action_url', 'action_text', 'start_time',
            'end_time', 'is_active', 'is_dismissible'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'notification_type': forms.Select(attrs={'class': 'form-control'}),
            'target_audience': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'action_url': forms.URLInput(attrs={'class': 'form-control'}),
            'action_text': forms.TextInput(attrs={'class': 'form-control'}),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_dismissible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        """Customize form initialization"""
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['title'].help_text = _("Brief title for the notification")
        self.fields['message'].help_text = _("Detailed message content")
        self.fields['notification_type'].help_text = _("Type of notification")
        self.fields['target_audience'].help_text = _("Who will see this notification")
        self.fields['priority'].help_text = _("Importance level of the notification")
        self.fields['action_url'].help_text = _("URL to open when action is clicked (optional)")
        self.fields['action_text'].help_text = _("Text for action button (optional)")
        self.fields['start_time'].help_text = _("When to start showing the notification")
        self.fields['end_time'].help_text = _("When to stop showing the notification (optional)")
        self.fields['is_active'].help_text = _("Whether the notification is currently active")
        self.fields['is_dismissible'].help_text = _("Whether users can dismiss the notification")
    
    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Validate dates
        if start_time and end_time and start_time > end_time:
            raise forms.ValidationError(_(
                "Start time cannot be after end time"
            ))
        
        # Validate action URL and text
        action_url = cleaned_data.get('action_url')
        action_text = cleaned_data.get('action_text')
        
        if action_url and not action_text:
            raise forms.ValidationError(_(
                "Action text is required when action URL is provided"
            ))
        
        if action_text and not action_url:
            raise forms.ValidationError(_(
                "Action URL is required when action text is provided"
            ))
        
        return cleaned_data


class NotificationDigestForm(forms.Form):
    """Form for creating notification digests"""
    
    frequency = forms.ChoiceField(
        choices=[
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text=_("How often to send digest emails")
    )
    
    include_types = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text=_("Select notification types to include in digest")
    )
    
    max_notifications = forms.IntegerField(
        min_value=1,
        max_value=100,
        initial=20,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text=_("Maximum number of notifications to include in each digest")
    )
    
    def __init__(self, *args, **kwargs):
        """Customize form initialization"""
        super().__init__(*args, **kwargs)
        
        # Populate notification types choices
        self.fields['include_types'].choices = [
            (nt.name, nt.name)
            for nt in NotificationType.objects.filter(is_active=True)
        ]