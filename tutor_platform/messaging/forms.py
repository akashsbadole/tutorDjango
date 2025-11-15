import re
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from .models import (
    Message, OnlineClass, CommunicationPreference, BlockedUser,
    SharedFile, MessageAttachment, Conversation, EmailAttachment, ClassParticipant,
    ClassRecording, ClassSchedule, ClassResource, ClassAttendance, ClassWaitingList
)
from requirements.models import Award, Session

User = get_user_model()


class MessageForm(forms.ModelForm):
    """Form for creating and editing messages"""
    
    class Meta:
        model = Message
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Type your message here...',
                'class': 'form-control'
            })
        }
    
    attachments = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control'
        }),
        help_text="You can attach files. Maximum file size is 10MB."
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['content'].label = "Message"
    
    def clean_content(self):
        """Validate message content for personal contact information"""
        content = self.cleaned_data.get('content', '')
        
        # Check for personal contact information
        phone_patterns = [
            r'\b\d{10}\b',  # 10-digit numbers
            r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # US format
            r'\+\d{1,3}[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # International
        ]
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        # Check for phone numbers
        for pattern in phone_patterns:
            if re.search(pattern, content):
                raise ValidationError(
                    "Phone numbers are not allowed in messages. "
                    "Please use the platform's communication features instead."
                )
        
        # Check for email addresses
        if re.search(email_pattern, content):
            raise ValidationError(
                "Email addresses are not allowed in messages. "
                "Please use the platform's communication features instead."
            )
        
        # Check for messaging apps
        messaging_apps = [
            r'\bwhatsapp\b',
            r'\btelegram\b',
            r'\bsignal\b',
            r'\bwechat\b',
            r'\bfacebook messenger\b',
            r'\bdiscord\b',
            r'\bskype\b',
        ]
        
        for app_pattern in messaging_apps:
            if re.search(app_pattern, content, re.IGNORECASE):
                raise ValidationError(
                    "References to external messaging apps are not allowed. "
                    "Please use the platform's communication features instead."
                )
        
        # Check for social media
        social_media = [
            r'\bfacebook\b',
            r'\binstagram\b',
            r'\btwitter\b',
            r'\blinkedin\b',
            r'\bsnapchat\b',
        ]
        
        for social_pattern in social_media:
            if re.search(social_pattern, content, re.IGNORECASE):
                raise ValidationError(
                    "References to social media platforms are not allowed. "
                    "Please use the platform's communication features instead."
                )
        
        return content
    
    def clean_attachments(self):
        """Validate file attachments"""
        attachments = self.cleaned_data.get('attachments')
        
        if attachments:
            # Check file size (10MB limit)
            if attachments.size > 10 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 10MB.")
            
            # Check file type (basic validation)
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'application/pdf', 'text/plain', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            ]
            
            if attachments.content_type not in allowed_types:
                raise ValidationError(
                    f"File type {attachments.content_type} is not allowed. "
                    "Please upload images, PDFs, or Office documents."
                )
        
        return attachments


class OnlineClassForm(forms.ModelForm):
    """Form for creating online classes"""
    
    class Meta:
        model = OnlineClass
        fields = [
            'title', 'description', 'meeting_url', 'meeting_id', 'password',
            'platform', 'scheduled_start', 'scheduled_end', 'max_participants',
            'is_recording', 'settings'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'meeting_url': forms.URLInput(attrs={'class': 'form-control'}),
            'meeting_id': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.TextInput(attrs={'class': 'form-control'}),
            'platform': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'scheduled_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_recording': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize session field with proper queryset
        if user:
            # Filter sessions to only include those where user is a participant
            session_queryset = Session.objects.filter(
                Q(award__student=user) | Q(award__tutor=user)
            )
        else:
            session_queryset = Session.objects.all()
            
        self.fields['session'] = forms.ModelChoiceField(
            queryset=session_queryset,
            widget=forms.HiddenInput(),
            required=False
        )
    
    def clean_scheduled_end(self):
        """Validate that end time is after start time"""
        scheduled_start = self.cleaned_data.get('scheduled_start')
        scheduled_end = self.cleaned_data.get('scheduled_end')
        
        if scheduled_start and scheduled_end:
            if scheduled_end <= scheduled_start:
                raise ValidationError("End time must be after start time.")
        
        return scheduled_end
    
    def clean_max_participants(self):
        """Validate maximum participants"""
        max_participants = self.cleaned_data.get('max_participants')
        
        if max_participants and max_participants < 2:
            raise ValidationError("Maximum participants must be at least 2.")
        
        return max_participants
    
    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        scheduled_start = cleaned_data.get('scheduled_start')
        scheduled_end = cleaned_data.get('scheduled_end')
        
        if scheduled_start and scheduled_end:
            # Check if the class is scheduled in the past
            if scheduled_start < timezone.now():
                raise ValidationError("Start time cannot be in the past.")
            
            # Check if the duration is reasonable (not more than 8 hours)
            duration = scheduled_end - scheduled_start
            if duration.total_seconds() > 8 * 60 * 60:  # 8 hours
                raise ValidationError("Class duration cannot exceed 8 hours.")
        
        return cleaned_data


class CommunicationPreferencesForm(forms.ModelForm):
    """Form for managing communication preferences"""
    
    class Meta:
        model = CommunicationPreference
        fields = [
            'allow_platform_messages', 'allow_email_communication', 
            'allow_file_sharing', 'allow_online_classes',
            'email_notification_frequency', 'auto_reply_message',
            'is_auto_reply_enabled', 'working_hours_start',
            'working_hours_end', 'timezone'
        ]
        widgets = {
            'allow_platform_messages': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_email_communication': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_file_sharing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_online_classes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'email_notification_frequency': forms.Select(attrs={'class': 'form-control'}),
            'auto_reply_message': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Enter your auto-reply message...'
            }),
            'is_auto_reply_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'working_hours_start': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'working_hours_end': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean_auto_reply_message(self):
        """Validate auto-reply message"""
        auto_reply_message = self.cleaned_data.get('auto_reply_message', '')
        is_auto_reply_enabled = self.cleaned_data.get('is_auto_reply_enabled', False)
        
        if is_auto_reply_enabled and not auto_reply_message.strip():
            raise ValidationError("Auto-reply message cannot be empty when auto-reply is enabled.")
        
        return auto_reply_message
    
    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        working_hours_start = cleaned_data.get('working_hours_start')
        working_hours_end = cleaned_data.get('working_hours_end')
        
        if working_hours_start and working_hours_end:
            if working_hours_start >= working_hours_end:
                raise ValidationError("Working hours start time must be before end time.")
        
        return cleaned_data


class SharedFileForm(forms.ModelForm):
    """Form for sharing files"""
    
    class Meta:
        model = SharedFile
        fields = ['file', 'description', 'is_public', 'expires_at']
        widgets = {
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional description of the file'
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'help_text': 'Leave blank for no expiration'
            })
        }
    
    file = forms.FileField(
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text="Maximum file size is 50MB."
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize recipient field with proper queryset
        if user:
            # Filter recipients to users with whom the current user can communicate
            # This would need to be implemented based on business logic
            recipient_queryset = User.objects.filter(
                Q(award__student=user) | Q(award__tutor=user)
            ).distinct()
        else:
            recipient_queryset = User.objects.all()
            
        self.fields['recipient'] = forms.ModelChoiceField(
            queryset=recipient_queryset,
            widget=forms.Select(attrs={'class': 'form-control'}),
            required=True
        )
        
        # Initialize other fields
        self.fields['conversation'] = forms.ModelChoiceField(
            queryset=Conversation.objects.all(),
            widget=forms.HiddenInput(),
            required=False
        )
        
        self.fields['award'] = forms.ModelChoiceField(
            queryset=Award.objects.all(),
            widget=forms.HiddenInput(),
            required=False
        )
    
    def clean_file(self):
        """Validate file"""
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (50MB limit)
            if file.size > 50 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 50MB.")
            
            # Basic file type validation
            # In a production environment, you would want more comprehensive validation
            # including scanning for malware
            allowed_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf',
                '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.txt', '.zip', '.rar'
            ]
            
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(
                    f"File extension .{file_extension} is not allowed."
                )
        
        return file
    
    def clean_expires_at(self):
        """Validate expiration date"""
        expires_at = self.cleaned_data.get('expires_at')
        
        if expires_at and expires_at <= timezone.now():
            raise ValidationError("Expiration date must be in the future.")
        
        return expires_at


class BlockUserForm(forms.Form):
    """Form for blocking a user"""
    
    # user_to_block field will be initialized in __init__
    
    reason = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Optional reason for blocking this user'
        })
    )
    
    is_permanent = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Block this user permanently"
    )
    
    expires_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        }),
        help_text="When to unblock the user (only for temporary blocks)"
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize user_to_block field with proper queryset
        if user:
            # Filter to users that the current user can block
            # Exclude users already blocked and self
            user_to_block_queryset = User.objects.filter(
                ~Q(pk=user.pk) &
                ~Q(blocked_by__blocker=user)
            ).distinct()
        else:
            user_to_block_queryset = User.objects.all()
            
        self.fields['user_to_block'] = forms.ModelChoiceField(
            queryset=user_to_block_queryset,
            widget=forms.HiddenInput(),
            required=True
        )
    
    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        is_permanent = cleaned_data.get('is_permanent')
        expires_at = cleaned_data.get('expires_at')
        
        if not is_permanent and not expires_at:
            raise ValidationError(
                "Please specify an expiration date for temporary blocks."
            )
        
        if expires_at and expires_at <= timezone.now():
            raise ValidationError("Expiration date must be in the future.")
        
        return cleaned_data


class ConversationForm(forms.Form):
    """Form for starting a new conversation"""
    
    # recipient and award fields will be initialized in __init__
    
    subject = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Optional subject for the conversation'
        })
    )
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Initialize recipient field with proper queryset
        if user:
            # Filter recipients to users with whom the current user can communicate
            # This would need to be implemented based on business logic
            recipient_queryset = User.objects.filter(
                Q(award__student=user) | Q(award__tutor=user)
            ).distinct()
            
            # Filter awards to those involving the current user
            award_queryset = Award.objects.filter(
                Q(student=user) | Q(tutor=user)
            )
        else:
            recipient_queryset = User.objects.all()
            award_queryset = Award.objects.all()
            
        self.fields['recipient'] = forms.ModelChoiceField(
            queryset=recipient_queryset,
            widget=forms.Select(attrs={'class': 'form-control'}),
            required=True
        )
        
        self.fields['award'] = forms.ModelChoiceField(
            queryset=award_queryset,
            widget=forms.Select(attrs={'class': 'form-control'}),
            required=False,
            help_text="Optional: Select an award related to this conversation"
        )


class MessageSearchForm(forms.Form):
    """Form for searching messages"""
    
    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search messages...'
        })
    )
    
    search_in = forms.ChoiceField(
        choices=[
            ('all', 'All Messages'),
            ('sent', 'Sent Messages'),
            ('received', 'Received Messages')
        ],
        initial='all',
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
    
    has_attachments = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class EmailAttachmentForm(forms.ModelForm):
    """Form for email attachments"""
    
    class Meta:
        model = EmailAttachment
        fields = ['filename', 'file_path', 'file_size', 'content_type']
        widgets = {
            'filename': forms.TextInput(attrs={'class': 'form-control'}),
            'file_path': forms.TextInput(attrs={'class': 'form-control'}),
            'file_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'content_type': forms.TextInput(attrs={'class': 'form-control'}),
        }


class MessageAttachmentForm(forms.ModelForm):
    """Form for message attachments"""
    
    class Meta:
        model = MessageAttachment
        fields = ['file', 'filename', 'file_size', 'content_type']
        widgets = {
            'filename': forms.TextInput(attrs={'class': 'form-control'}),
            'file_size': forms.NumberInput(attrs={'class': 'form-control'}),
            'content_type': forms.TextInput(attrs={'class': 'form-control'}),
        }


class OnlineClassUpdateForm(forms.ModelForm):
    """Form for updating online class details"""
    
    class Meta:
        model = OnlineClass
        fields = [
            'title', 'description', 'meeting_url', 'meeting_id', 'password',
            'platform', 'scheduled_start', 'scheduled_end', 'max_participants',
            'is_recording', 'recording_url', 'status', 'settings'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'meeting_url': forms.URLInput(attrs={'class': 'form-control'}),
            'meeting_id': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.TextInput(attrs={'class': 'form-control'}),
            'platform': forms.Select(attrs={'class': 'form-control'}),
            'scheduled_start': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'scheduled_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_recording': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'recording_url': forms.URLInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }


class ClassParticipantForm(forms.ModelForm):
    """Form for managing class participants"""
    
    class Meta:
        model = ClassParticipant
        fields = ['role', 'joined_at', 'left_at', 'duration_minutes', 'is_active']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
            'joined_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'left_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ClassRecordingForm(forms.ModelForm):
    """Form for creating and managing class recordings"""
    
    class Meta:
        model = ClassRecording
        fields = [
            'title', 'description', 'recording_url', 'recording_id',
            'platform_recording_id', 'duration_minutes', 'file_size_bytes',
            'thumbnail_url', 'status', 'is_public', 'password_protected',
            'password', 'download_enabled', 'expires_at'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'recording_url': forms.URLInput(attrs={'class': 'form-control'}),
            'recording_id': forms.TextInput(attrs={'class': 'form-control'}),
            'platform_recording_id': forms.TextInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'file_size_bytes': forms.NumberInput(attrs={'class': 'form-control'}),
            'thumbnail_url': forms.URLInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'password_protected': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'password': forms.TextInput(attrs={'class': 'form-control'}),
            'download_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }
    
    def clean_expires_at(self):
        """Validate expiration date"""
        expires_at = self.cleaned_data.get('expires_at')
        
        if expires_at and expires_at <= timezone.now():
            raise ValidationError("Expiration date must be in the future.")
        
        return expires_at


class ClassScheduleForm(forms.ModelForm):
    """Form for creating and managing class schedules"""
    
    class Meta:
        model = ClassSchedule
        fields = [
            'title', 'description', 'recurrence_pattern', 'recurrence_interval',
            'recurrence_days', 'start_date', 'end_date', 'start_time',
            'end_time', 'timezone', 'max_participants', 'is_active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'recurrence_pattern': forms.Select(attrs={'class': 'form-control'}),
            'recurrence_interval': forms.NumberInput(attrs={'class': 'form-control'}),
            'recurrence_days': forms.CheckboxSelectMultiple(attrs={'class': 'form-check'}),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'start_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'end_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'timezone': forms.Select(attrs={'class': 'form-control'}),
            'max_participants': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_end_date(self):
        """Validate end date"""
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise ValidationError("End date must be after start date.")
        
        return end_date
    
    def clean_end_time(self):
        """Validate end time"""
        start_time = self.cleaned_data.get('start_time')
        end_time = self.cleaned_data.get('end_time')
        
        if start_time and end_time and end_time <= start_time:
            raise ValidationError("End time must be after start time.")
        
        return end_time


class ClassResourceForm(forms.ModelForm):
    """Form for creating and managing class resources"""
    
    class Meta:
        model = ClassResource
        fields = [
            'title', 'description', 'resource_type', 'file', 'url',
            'order', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'resource_type': forms.Select(attrs={'class': 'form-control'}),
            'url': forms.URLInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_file(self):
        """Validate file"""
        file = self.cleaned_data.get('file')
        
        if file:
            # Check file size (100MB limit)
            if file.size > 100 * 1024 * 1024:
                raise ValidationError("File size cannot exceed 100MB.")
            
            # Basic file type validation
            allowed_extensions = [
                '.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf',
                '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.txt', '.zip', '.rar', '.mp4', '.avi', '.mov', '.mp3'
            ]
            
            file_extension = file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                raise ValidationError(
                    f"File extension .{file_extension} is not allowed."
                )
        
        return file
    
    def clean(self):
        """Additional form validation"""
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        url = cleaned_data.get('url')
        
        if not file and not url:
            raise ValidationError("Please provide either a file or a URL.")
        
        return cleaned_data


class ClassAttendanceForm(forms.ModelForm):
    """Form for managing class attendance"""
    
    class Meta:
        model = ClassAttendance
        fields = [
            'status', 'engagement_score',
            'notes', 'ip_address', 'user_agent'
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'engagement_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'user_agent': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ClassWaitingListForm(forms.ModelForm):
    """Form for managing class waiting lists"""
    
    class Meta:
        model = ClassWaitingList
        fields = [
            'notes', 'is_active'
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }