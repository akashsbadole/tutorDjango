import json
import uuid
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, FormView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import DeleteView
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Max
from django.core.paginator import Paginator
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from search.utils import get_search_backend
from search.models import SearchQuery

from .models import (
    Conversation, Message, MessageAttachment, OnlineClass, ClassParticipant,
    CommunicationPreference, BlockedUser, MaskedEmail, EmailLog, SharedFile,
    ClassRecording, ClassSchedule, ClassResource, ClassAttendance, ClassWaitingList
)
from .forms import (
    MessageForm, OnlineClassForm, CommunicationPreferencesForm,
    SharedFileForm, BlockUserForm, ClassRecordingForm, ClassScheduleForm,
    ClassResourceForm, ClassAttendanceForm, ClassWaitingListForm
)
from .utils import (
    generate_masked_email, can_users_communicate, detect_personal_info,
    create_conversation_if_allowed
)
from requirements.models import Award


class MessageListView(LoginRequiredMixin, ListView):
    """View for displaying all conversations for the current user"""
    model = Conversation
    template_name = 'messaging/message_list.html'
    context_object_name = 'conversations'
    paginate_by = 20
    
    def get_queryset(self):
        """Get conversations where the user is a participant"""
        user = self.request.user
        
        # Check if this is a search request
        search_query = self.request.GET.get('q')
        if search_query:
            # Record the search query
            SearchQuery.objects.create(
                user=user,
                query=search_query,
                content_type='messaging.conversation',
                ip_address=self.get_client_ip(self.request),
            )
            
            # Use search backend to find conversations
            backend = get_search_backend()
            search_results = backend.search(
                query=search_query,
                user=user,
                content_types=['messaging.conversation'],
                filters={'participant': user.id}
            )
            
            # Get conversation IDs from search results
            conversation_ids = [result['object_id'] for result in search_results.get('results', [])]
            
            # Return conversations matching search results
            return Conversation.objects.filter(
                id__in=conversation_ids,
                is_active=True
            ).select_related(
                'participant1', 'participant2', 'award'
            ).annotate(
                last_message_time=Max('messages__created_at'),
                unread_count=Count('messages', filter=Q(
                    Q(messages__created_at__gt=user.communication_preferences.participant1_last_read if user == user else user.communication_preferences.participant2_last_read)
                ))
            ).order_by('-last_message_time')
        
        # Regular queryset without search
        return Conversation.objects.filter(
            Q(participant1=user) | Q(participant2=user),
            is_active=True
        ).select_related(
            'participant1', 'participant2', 'award'
        ).annotate(
            last_message_time=Max('messages__created_at'),
            unread_count=Count('messages', filter=Q(
                Q(messages__created_at__gt=user.communication_preferences.participant1_last_read if user == user else user.communication_preferences.participant2_last_read)
            ))
        ).order_by('-last_message_time')
    
    def get_client_ip(self, request):
        """Helper method to get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        context['active_tab'] = 'messages'
        
        # Add search query to context if it exists
        search_query = self.request.GET.get('q')
        if search_query:
            context['search_query'] = search_query
            context['is_search'] = True
        
        # Get unread count for each conversation
        user = self.request.user
        for conversation in context['conversations']:
            conversation.unread_count = conversation.get_unread_count(user)
            conversation.other_participant = conversation.get_other_participant(user)
        
        return context


class MessageDetailView(LoginRequiredMixin, DetailView):
    """View for displaying a specific conversation"""
    model = Conversation
    template_name = 'messaging/message_detail.html'
    context_object_name = 'conversation'
    
    def get_object(self):
        """Get the conversation and check access permissions"""
        conversation = super().get_object()
        user = self.request.user
        
        # Check if user can access this conversation
        if not conversation.can_participant_access(user):
            raise PermissionDenied("You don't have permission to access this conversation")
        
        return conversation
    
    def get_context_data(self, **kwargs):
        """Add messages and form to context"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        conversation = self.object
        
        # Mark conversation as read
        conversation.mark_as_read(user)
        
        # Get messages for this conversation
        messages = conversation.messages.filter(
            is_deleted=False
        ).select_related('sender').order_by('created_at')
        
        # Add message form
        context['messages'] = messages
        context['message_form'] = MessageForm()
        context['other_participant'] = conversation.get_other_participant(user)
        context['shared_files'] = conversation.shared_files.all()[:5]  # Recent 5 files
        
        # Check if user has blocked the other participant
        context['is_blocked'] = BlockedUser.objects.filter(
            blocker=user,
            blocked=context['other_participant']
        ).exists()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle message sending"""
        self.object = self.get_object()
        user = request.user
        conversation = self.object
        other_participant = conversation.get_other_participant(user)
        
        # Check if user is blocked
        if BlockedUser.objects.filter(blocker=other_participant, blocked=user).exists():
            messages.error(request, "You cannot send messages to this user.")
            return redirect('messaging:detail', pk=conversation.pk)
        
        form = MessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.conversation = conversation
            message.sender = user
            
            # Check for personal contact information
            if message.message_type == Message.MessageType.TEXT:
                contains_contact, patterns = detect_personal_info(message.content)
                if contains_contact:
                    messages.warning(
                        request,
                        "Your message contains personal contact information, which is not allowed. "
                        "Please remove phone numbers, email addresses, or references to messaging apps."
                    )
                    context = self.get_context_data()
                    context['message_form'] = form
                    return self.render_to_response(context)
            
            message.save()
            
            # Handle file attachments
            if 'attachments' in request.FILES:
                for file in request.FILES.getlist('attachments'):
                    MessageAttachment.objects.create(
                        message=message,
                        file=file,
                        filename=file.name,
                        file_size=file.size,
                        content_type=file.content_type
                    )
            
            messages.success(request, "Message sent successfully.")
            return redirect('messaging:detail', pk=conversation.pk)
        else:
            context = self.get_context_data()
            context['message_form'] = form
            return self.render_to_response(context)


class MessageCreateView(LoginRequiredMixin, CreateView):
    """View for starting a new conversation"""
    model = Message
    form_class = MessageForm
    template_name = 'messaging/message_create.html'
    
    def get_context_data(self, **kwargs):
        """Add recipient information to context"""
        context = super().get_context_data(**kwargs)
        
        # Get recipient from query parameter
        recipient_id = self.request.GET.get('recipient')
        award_id = self.request.GET.get('award')
        
        if recipient_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            context['recipient'] = get_object_or_404(User, pk=recipient_id)
        
        if award_id:
            context['award'] = get_object_or_404(Award, pk=award_id)
        
        return context
    
    def form_valid(self, form):
        """Process the form and create a new conversation"""
        user = self.request.user
        recipient_id = self.request.POST.get('recipient')
        award_id = self.request.POST.get('award')
        
        if not recipient_id:
            form.add_error(None, "Please select a recipient.")
            return self.form_invalid(form)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient = get_object_or_404(User, pk=recipient_id)
        
        # Get award if provided
        award = None
        if award_id:
            award = get_object_or_404(Award, pk=award_id)
        
        # Check if users can communicate
        if not can_users_communicate(user, recipient, award):
            messages.error(
                self.request,
                "You can only communicate with users in an awarded requirement."
            )
            return self.form_invalid(form)
        
        # Check if user is blocked
        if BlockedUser.objects.filter(
            Q(blocker=recipient, blocked=user) | 
            Q(blocker=user, blocked=recipient)
        ).exists():
            messages.error(
                self.request,
                "Cannot start a conversation with this user."
            )
            return self.form_invalid(form)
        
        # Create or get existing conversation
        conversation = create_conversation_if_allowed(user, recipient, award)
        
        if not conversation:
            messages.error(
                self.request,
                "Unable to create conversation. Please check your permissions."
            )
            return self.form_invalid(form)
        
        # Create the message
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = user
        
        # Check for personal contact information
        if message.message_type == Message.MessageType.TEXT:
            contains_contact, patterns = detect_personal_info(message.content)
            if contains_contact:
                messages.warning(
                    self.request,
                    "Your message contains personal contact information, which is not allowed. "
                    "Please remove phone numbers, email addresses, or references to messaging apps."
                )
                return self.form_invalid(form)
        
        message.save()
        
        # Handle file attachments
        if 'attachments' in self.request.FILES:
            for file in self.request.FILES.getlist('attachments'):
                MessageAttachment.objects.create(
                    message=message,
                    file=file,
                    filename=file.name,
                    file_size=file.size,
                    content_type=file.content_type
                )
        
        messages.success(self.request, "Message sent successfully.")
        return redirect('messaging:detail', pk=conversation.pk)


class OnlineClassCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new online class"""
    model = OnlineClass
    form_class = OnlineClassForm
    template_name = 'messaging/online_class_create.html'
    
    def get_context_data(self, **kwargs):
        """Add session information to context"""
        context = super().get_context_data(**kwargs)
        
        # Get session from query parameter
        session_id = self.request.GET.get('session')
        if session_id:
            from requirements.models import Session
            context['session'] = get_object_or_404(Session, pk=session_id)
        
        # Add timezones for selection
        import pytz
        context['timezones'] = pytz.common_timezones
        
        return context
    
    def form_valid(self, form):
        """Process the form and create a new online class"""
        user = self.request.user
        session_id = self.request.POST.get('session')
        
        if not session_id:
            form.add_error(None, "Please select a session.")
            return self.form_invalid(form)
        
        from requirements.models import Session
        session = get_object_or_404(Session, pk=session_id)
        
        # Check if user is the host or participant in the session
        if session.award.student != user and session.award.tutor != user:
            messages.error(
                self.request,
                "You can only create online classes for sessions you're involved in."
            )
            return self.form_invalid(form)
        
        # Create the online class
        online_class = form.save(commit=False)
        online_class.session = session
        online_class.host = user
        online_class.save()
        
        # Generate join URLs
        online_class.generate_join_urls()
        
        # Add host as participant
        ClassParticipant.objects.create(
            online_class=online_class,
            user=user,
            role=ClassParticipant.Role.HOST
        )
        
        # Add the other participant (student or tutor)
        other_user = session.award.tutor if user == session.award.student else session.award.student
        ClassParticipant.objects.create(
            online_class=online_class,
            user=other_user,
            role=ClassParticipant.Role.PARTICIPANT
        )
        
        messages.success(self.request, "Online class created successfully.")
        return redirect('messaging:online_class_detail', pk=online_class.pk)


class OnlineClassDetailView(LoginRequiredMixin, DetailView):
    """View for displaying details of an online class"""
    model = OnlineClass
    template_name = 'messaging/online_class_detail.html'
    context_object_name = 'online_class'
    
    def get_object(self):
        """Get the online class and check access permissions"""
        online_class = super().get_object()
        user = self.request.user
        
        # Check if user is a participant
        if not ClassParticipant.objects.filter(
            online_class=online_class,
            user=user
        ).exists():
            raise PermissionDenied("You don't have permission to access this online class")
        
        return online_class
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        online_class = self.object
        
        # Get user's participation record
        try:
            context['participation'] = ClassParticipant.objects.get(
                online_class=online_class,
                user=user
            )
        except ClassParticipant.DoesNotExist:
            context['participation'] = None
        
        # Get all participants
        context['participants'] = online_class.participants.select_related('user').all()
        
        # Get class recordings
        context['recordings'] = online_class.recordings.all().order_by('-created_at')
        
        # Get class resources
        context['resources'] = online_class.resources.all().order_by('order', 'created_at')
        
        # Get class schedule if recurring
        if online_class.is_recurring:
            try:
                context['schedule'] = online_class.schedules.get()
            except ClassSchedule.DoesNotExist:
                context['schedule'] = None
        
        # Get attendance records
        context['attendance_records'] = online_class.attendance_records.select_related('user').all()
        
        # Get waiting list
        context['waiting_list'] = online_class.waiting_list.filter(is_active=True).order_by('joined_at')
        
        # Check if user can manage the class (host or has permission)
        context['can_manage'] = (
            online_class.host == user or
            (hasattr(user, 'user_type') and user.user_type == 'ADMIN')
        )
        
        # Get user's attendance record
        try:
            context['user_attendance'] = ClassAttendance.objects.get(
                online_class=online_class,
                user=user
            )
        except ClassAttendance.DoesNotExist:
            context['user_attendance'] = None
        
        return context


class CommunicationPreferencesView(LoginRequiredMixin, UpdateView):
    """View for managing communication preferences"""
    model = CommunicationPreference
    form_class = CommunicationPreferencesForm
    template_name = 'messaging/communication_preferences.html'
    success_url = reverse_lazy('messaging:preferences')
    
    def get_object(self):
        """Get or create communication preferences for the user"""
        preferences, created = CommunicationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    def form_valid(self, form):
        """Update preferences and show success message"""
        messages.success(self.request, "Communication preferences updated successfully.")
        return super().form_valid(form)


class SharedFileCreateView(LoginRequiredMixin, CreateView):
    """View for sharing a file"""
    model = SharedFile
    form_class = SharedFileForm
    template_name = 'messaging/shared_file_create.html'
    
    def get_context_data(self, **kwargs):
        """Add recipient and conversation information to context"""
        context = super().get_context_data(**kwargs)
        
        # Get parameters from query string
        recipient_id = self.request.GET.get('recipient')
        conversation_id = self.request.GET.get('conversation')
        award_id = self.request.GET.get('award')
        
        if recipient_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            context['recipient'] = get_object_or_404(User, pk=recipient_id)
        
        if conversation_id:
            context['conversation'] = get_object_or_404(Conversation, pk=conversation_id)
        
        if award_id:
            context['award'] = get_object_or_404(Award, pk=award_id)
        
        return context
    
    def form_valid(self, form):
        """Process the form and share the file"""
        user = self.request.user
        recipient_id = self.request.POST.get('recipient')
        conversation_id = self.request.POST.get('conversation')
        award_id = self.request.POST.get('award')
        
        if not recipient_id:
            form.add_error(None, "Please select a recipient.")
            return self.form_invalid(form)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient = get_object_or_404(User, pk=recipient_id)
        
        # Get related objects
        conversation = None
        if conversation_id:
            conversation = get_object_or_404(Conversation, pk=conversation_id)
        
        award = None
        if award_id:
            award = get_object_or_404(Award, pk=award_id)
        
        # Check if users can communicate
        if not can_users_communicate(user, recipient, award):
            messages.error(
                self.request,
                "You can only share files with users in an awarded requirement."
            )
            return self.form_invalid(form)
        
        # Create the shared file
        shared_file = form.save(commit=False)
        shared_file.uploaded_by = user
        shared_file.shared_with = recipient
        shared_file.conversation = conversation
        shared_file.award = award
        shared_file.save()
        
        messages.success(self.request, "File shared successfully.")
        return redirect('messaging:shared_file_detail', pk=shared_file.pk)


class SharedFileDetailView(LoginRequiredMixin, DetailView):
    """View for displaying a shared file"""
    model = SharedFile
    template_name = 'messaging/shared_file_detail.html'
    context_object_name = 'shared_file'
    
    def get_object(self):
        """Get the shared file and check access permissions"""
        shared_file = super().get_object()
        user = self.request.user
        
        # Check if user can access this file
        if not shared_file.can_access(user):
            raise PermissionDenied("You don't have permission to access this file")
        
        return shared_file
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        shared_file = self.object
        
        # Check if user is the owner
        context['is_owner'] = user == shared_file.uploaded_by
        
        return context


@require_POST
@login_required
def download_shared_file(request, pk):
    """View for downloading a shared file"""
    shared_file = get_object_or_404(SharedFile, pk=pk)
    user = request.user
    
    # Check if user can access this file
    if not shared_file.can_access(user):
        raise PermissionDenied("You don't have permission to access this file")
    
    # Increment download count
    shared_file.increment_download()
    
    # Return the file
    from django.http import FileResponse
    import os
    
    if os.path.exists(shared_file.file.path):
        return FileResponse(
            open(shared_file.file.path, 'rb'),
            content_type=shared_file.content_type
        )
    else:
        messages.error(request, "File not found.")
        return redirect('messaging:shared_file_detail', pk=shared_file.pk)


class BlockUserView(LoginRequiredMixin, FormView):
    """View for blocking a user"""
    form_class = BlockUserForm
    template_name = 'messaging/block_user.html'
    success_url = reverse_lazy('messaging:blocked_users')
    
    def get_context_data(self, **kwargs):
        """Add user to be blocked to context"""
        context = super().get_context_data(**kwargs)
        
        # Get user to be blocked from query parameter
        user_id = self.request.GET.get('user')
        if user_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            context['user_to_block'] = get_object_or_404(User, pk=user_id)
        
        return context
    
    def form_valid(self, form):
        """Block the user"""
        user = self.request.user
        user_to_block_id = self.request.POST.get('user_to_block')
        
        if not user_to_block_id:
            form.add_error(None, "Please select a user to block.")
            return self.form_invalid(form)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user_to_block = get_object_or_404(User, pk=user_to_block_id)
        
        # Check if user is already blocked
        if BlockedUser.objects.filter(blocker=user, blocked=user_to_block).exists():
            messages.warning(self.request, "This user is already blocked.")
            return redirect('messaging:blocked_users')
        
        # Create block
        BlockedUser.objects.create(
            blocker=user,
            blocked=user_to_block,
            reason=form.cleaned_data.get('reason', ''),
            is_permanent=form.cleaned_data.get('is_permanent', True),
            expires_at=form.cleaned_data.get('expires_at')
        )
        
        messages.success(self.request, f"You have blocked {user_to_block.get_full_name()}.")
        return super().form_valid(form)


class BlockedUsersListView(LoginRequiredMixin, ListView):
    """View for displaying blocked users"""
    model = BlockedUser
    template_name = 'messaging/blocked_users.html'
    context_object_name = 'blocked_users'
    paginate_by = 20
    
    def get_queryset(self):
        """Get users blocked by the current user"""
        return BlockedUser.objects.filter(
            blocker=self.request.user
        ).select_related('blocked').order_by('-created_at')


@require_POST
@login_required
def unblock_user(request, pk):
    """View for unblocking a user"""
    blocked_user = get_object_or_404(BlockedUser, pk=pk, blocker=request.user)
    blocked_user.delete()
    
    messages.success(request, f"You have unblocked {blocked_user.blocked.get_full_name()}.")
    return redirect('messaging:blocked_users')


@require_POST
@login_required
def delete_message(request, pk):
    """View for deleting a message"""
    message = get_object_or_404(Message, pk=pk)
    user = request.user
    
    # Check if user can delete this message
    if message.sender != user or not message.can_delete():
        raise PermissionDenied("You don't have permission to delete this message")
    
    # Mark as deleted
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.save()
    
    return JsonResponse({'success': True})


@require_POST
@login_required
def edit_message(request, pk):
    """View for editing a message"""
    message = get_object_or_404(Message, pk=pk)
    user = request.user
    
    # Check if user can edit this message
    if message.sender != user or not message.can_edit():
        raise PermissionDenied("You don't have permission to edit this message")
    
    # Get new content
    new_content = request.POST.get('content', '')
    if not new_content.strip():
        return JsonResponse({'success': False, 'error': 'Message content cannot be empty'})
    
    # Check for personal contact information
    contains_contact, patterns = detect_personal_info(new_content)
    if contains_contact:
        return JsonResponse({
            'success': False,
            'error': "Message contains personal contact information, which is not allowed."
        })
    
    # Update message
    message.content = new_content
    message.is_edited = True
    message.edited_at = timezone.now()
    message.save()
    
    return JsonResponse({
        'success': True,
        'content': message.content,
        'edited_at': message.edited_at.strftime('%Y-%m-%d %H:%M:%S')
    })


@require_POST
@login_required
def join_online_class(request, pk):
    """View for joining an online class"""
    online_class = get_object_or_404(OnlineClass, pk=pk)
    user = request.user
    
    # Check if user can join this class
    if not online_class.is_joinable():
        return JsonResponse({
            'success': False,
            'error': 'This class is not currently joinable'
        })
    
    # Get or create participation record
    participation, created = ClassParticipant.objects.get_or_create(
        online_class=online_class,
        user=user,
        defaults={'role': ClassParticipant.Role.PARTICIPANT}
    )
    
    if not created and participation.is_active:
        return JsonResponse({
            'success': False,
            'error': 'You have already joined this class'
        })
    
    # Mark as joined
    participation.is_active = True
    participation.joined_at = timezone.now()
    participation.ip_address = request.META.get('REMOTE_ADDR')
    participation.user_agent = request.META.get('HTTP_USER_AGENT', '')
    participation.save()
    
    # Update class status if needed
    if online_class.status == OnlineClass.Status.SCHEDULED:
        online_class.status = OnlineClass.Status.IN_PROGRESS
        online_class.actual_start = timezone.now()
        online_class.save()
    
    # Return join URL
    join_url = (
        online_class.join_url_host 
        if participation.role == ClassParticipant.Role.HOST 
        else online_class.join_url_participant
    )
    
    return JsonResponse({
        'success': True,
        'join_url': join_url
    })


@require_POST
@login_required
def leave_online_class(request, pk):
    """View for leaving an online class"""
    online_class = get_object_or_404(OnlineClass, pk=pk)
    user = request.user
    
    # Get participation record
    try:
        participation = ClassParticipant.objects.get(
            online_class=online_class,
            user=user
        )
    except ClassParticipant.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'You are not a participant in this class'
        })
    
    # Mark as left
    participation.is_active = False
    participation.left_at = timezone.now()
    participation.save()
    
    # Calculate duration
    participation.duration_minutes = participation.calculate_duration()
    participation.save()
    
    # Check if all participants have left
    active_participants = online_class.participants.filter(is_active=True).count()
    if active_participants == 0:
        online_class.status = OnlineClass.Status.COMPLETED
        online_class.actual_end = timezone.now()
        online_class.save()
    
    return JsonResponse({'success': True})


@login_required
def masked_email_info(request, pk):
    """View for displaying masked email information"""
    masked_email = get_object_or_404(MaskedEmail, pk=pk)
    user = request.user
    
    # Check if user is a participant
    if user not in [masked_email.student, masked_email.tutor]:
        raise PermissionDenied("You don't have permission to view this masked email")
    
    # Get email logs
    email_logs = EmailLog.objects.filter(
        masked_email=masked_email
    ).order_by('-created_at')
    
    return render(request, 'messaging/masked_email_info.html', {
        'masked_email': masked_email,
        'email_logs': email_logs,
        'is_student': user == masked_email.student,
    })


@login_required
def create_masked_email(request, award_id):
    """View for creating a new masked email"""
    award = get_object_or_404(Award, pk=award_id)
    user = request.user
    
    # Check if user is a participant in the award
    if user not in [award.student, award.tutor]:
        raise PermissionDenied("You don't have permission to create a masked email for this award")
    
    # Check if masked email already exists
    existing = MaskedEmail.objects.filter(
        award=award,
        student=award.student,
        tutor=award.tutor
    ).first()
    
    if existing and not existing.is_expired():
        messages.info(request, "A masked email already exists for this award.")
        return redirect('messaging:masked_email_info', pk=existing.pk)
    
    # Create new masked email
    masked_email = generate_masked_email(award)
    
    messages.success(request, "Masked email created successfully.")
    return redirect('messaging:masked_email_info', pk=masked_email.pk)


class ClassScheduleView(LoginRequiredMixin, DetailView):
    """View for managing class schedules"""
    model = ClassSchedule
    template_name = 'messaging/class_schedule.html'
    context_object_name = 'schedule'
    
    def get_object(self, queryset=None):
        """Get the schedule object"""
        schedule_id = self.kwargs.get('schedule_id')
        return get_object_or_404(ClassSchedule, id=schedule_id)
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        schedule = self.object
        user = self.request.user
        
        # Get the online class
        context['online_class'] = schedule.online_class
        
        # Get all scheduled instances
        context['scheduled_instances'] = schedule.instances.all().order_by('start_time')
        
        # Get schedule exceptions
        context['exceptions'] = schedule.exceptions.all().order_by('exception_date')
        
        # Check if user can manage the schedule
        context['can_manage'] = (
            schedule.online_class.host == user or
            (hasattr(user, 'user_type') and user.user_type == 'ADMIN')
        )
        
        return context


class ClassRecordingView(LoginRequiredMixin, DetailView):
    """View for managing class recordings"""
    model = ClassRecording
    template_name = 'messaging/class_recording.html'
    context_object_name = 'recording'
    
    def get_object(self, queryset=None):
        """Get the recording object"""
        recording_id = self.kwargs.get('recording_id')
        return get_object_or_404(ClassRecording, id=recording_id)
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        recording = self.object
        user = self.request.user
        
        # Get the online class
        context['online_class'] = recording.online_class
        
        # Get all recordings for this class
        context['all_recordings'] = recording.online_class.recordings.all().order_by('-created_at')
        
        # Check if user has access to this recording
        context['has_access'] = (
            recording.online_class.host == user or
            recording.online_class.participants.filter(user=user).exists() or
            (hasattr(user, 'user_type') and user.user_type == 'ADMIN')
        )
        
        return context


class ClassResourceView(LoginRequiredMixin, DetailView):
    """View for managing class resources"""
    model = ClassResource
    template_name = 'messaging/class_resource.html'
    context_object_name = 'resource'
    
    def get_object(self, queryset=None):
        """Get the resource object"""
        resource_id = self.kwargs.get('resource_id')
        return get_object_or_404(ClassResource, id=resource_id)
    
    def get_context_data(self, **kwargs):
        """Add additional context data"""
        context = super().get_context_data(**kwargs)
        resource = self.object
        user = self.request.user
        
        # Get the online class
        context['online_class'] = resource.online_class
        
        # Get all resources for this class
        context['all_resources'] = resource.online_class.resources.all().order_by('order', 'created_at')
        
        # Check if user has access to this resource
        context['has_access'] = (
            resource.online_class.host == user or
            resource.online_class.participants.filter(user=user).exists() or
            (hasattr(user, 'user_type') and user.user_type == 'ADMIN')
        )
        
        return context


class ClassAnalyticsView(LoginRequiredMixin, DetailView):
    """View for class analytics and statistics"""
    model = OnlineClass
    template_name = 'messaging/class_analytics.html'
    context_object_name = 'online_class'
    
    def get_context_data(self, **kwargs):
        """Add analytics data to context"""
        context = super().get_context_data(**kwargs)
        online_class = self.object
        user = self.request.user
        
        # Check if user can view analytics
        context['can_view_analytics'] = (
            online_class.host == user or
            (hasattr(user, 'user_type') and user.user_type == 'ADMIN')
        )
        
        if context['can_view_analytics']:
            from django.db.models import Avg, Sum
            
            # Attendance statistics
            total_participants = online_class.participants.count()
            attended_count = online_class.attendance_records.filter(attended=True).count()
            context['attendance_rate'] = (attended_count / total_participants * 100) if total_participants > 0 else 0
            
            # Engagement metrics
            context['avg_engagement_score'] = online_class.attendance_records.aggregate(
                avg_score=Avg('engagement_score')
            )['avg_score'] or 0
            
            # Recording statistics
            context['total_recordings'] = online_class.recordings.count()
            context['total_recording_views'] = online_class.recordings.aggregate(
                total_views=Sum('view_count')
            )['total_views'] or 0
            
            # Resource statistics
            context['total_resources'] = online_class.resources.count()
            context['total_resource_downloads'] = online_class.resources.aggregate(
                total_downloads=Sum('download_count')
            )['total_downloads'] or 0
            
            # Revenue tracking (if applicable)
            if hasattr(online_class, 'price') and online_class.price:
                context['total_revenue'] = total_participants * online_class.price
            else:
                context['total_revenue'] = 0
            
            # Recent activity
            context['recent_attendance'] = online_class.attendance_records.select_related('user').order_by('-join_time')[:10]
            
            # Attendance by date (for recurring classes)
            if online_class.is_recurring:
                context['attendance_by_date'] = online_class.attendance_records.values(
                    'join_time__date'
                ).annotate(
                    count=Count('id'),
                    attended=Count('id', filter=Q(attended=True))
                ).order_by('join_time__date')
        
        return context


class ClassRecordingCreateView(LoginRequiredMixin, CreateView):
    """View for creating class recordings"""
    model = ClassRecording
    form_class = ClassRecordingForm
    template_name = 'messaging/class_recording_form.html'
    
    def get_context_data(self, **kwargs):
        """Add online class to context"""
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        context['online_class'] = get_object_or_404(OnlineClass, id=class_id)
        return context
    
    def form_valid(self, form):
        """Process the valid form"""
        class_id = self.kwargs.get('class_id')
        online_class = get_object_or_404(OnlineClass, id=class_id)
        
        # Check if user can add recordings
        if online_class.host != self.request.user and not (
            hasattr(self.request.user, 'user_type') and self.request.user.user_type == 'ADMIN'
        ):
            messages.error(self.request, "You don't have permission to add recordings to this class.")
            return self.form_invalid(form)
        
        form.instance.online_class = online_class
        form.instance.created_by = self.request.user
        
        messages.success(self.request, "Recording added successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to class detail page"""
        return reverse_lazy('messaging:online_class_detail', kwargs={'pk': self.kwargs.get('class_id')})


class ClassResourceCreateView(LoginRequiredMixin, CreateView):
    """View for creating class resources"""
    model = ClassResource
    form_class = ClassResourceForm
    template_name = 'messaging/class_resource_form.html'
    
    def get_context_data(self, **kwargs):
        """Add online class to context"""
        context = super().get_context_data(**kwargs)
        class_id = self.kwargs.get('class_id')
        context['online_class'] = get_object_or_404(OnlineClass, id=class_id)
        return context
    
    def form_valid(self, form):
        """Process the valid form"""
        class_id = self.kwargs.get('class_id')
        online_class = get_object_or_404(OnlineClass, id=class_id)
        
        # Check if user can add resources
        if online_class.host != self.request.user and not (
            hasattr(self.request.user, 'user_type') and self.request.user.user_type == 'ADMIN'
        ):
            messages.error(self.request, "You don't have permission to add resources to this class.")
            return self.form_invalid(form)
        
        form.instance.online_class = online_class
        form.instance.uploaded_by = self.request.user
        
        messages.success(self.request, "Resource added successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        """Redirect to class detail page"""
        return reverse_lazy('messaging:online_class_detail', kwargs={'pk': self.kwargs.get('class_id')})
