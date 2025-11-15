from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.utils import timezone

from .models import (
    Requirement, Proposal, Award, Session, Review, SavedRequirement, FavoriteTutor
)
from .forms import (
    RequirementPostForm, ProposalForm, AwardForm, SessionForm, ReviewForm, 
    SavedRequirementForm, FavoriteTutorForm, RequirementSearchForm
)
from accounts.models import Subject, User


class StudentRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a student"""
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'user_type') and self.request.user.user_type == 'STUDENT'


class TutorRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure user is a tutor"""
    def test_func(self):
        return self.request.user.is_authenticated and hasattr(self.request.user, 'user_type') and self.request.user.user_type == 'TUTOR'


class RequirementListView(ListView):
    """View for browsing requirements"""
    model = Requirement
    template_name = 'requirements/requirement_list.html'
    context_object_name = 'requirements'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Requirement.objects.filter(
            status='OPEN',
            visibility='PUBLIC'
        ).select_related('student', 'subject')
        
        # Apply search and filters - integrate with search app
        form = RequirementSearchForm(self.request.GET)
        if form.is_valid():
            q = form.cleaned_data.get('q')
            if q:
                # Use the search app for more advanced search
                try:
                    from search.utils import get_search_backend
                    
                    # Record search query for analytics
                    from search.models import SearchQuery
                    search_query = SearchQuery.objects.create(
                        user=self.request.user if self.request.user.is_authenticated else None,
                        query=q,
                        search_type='REQUIREMENT',
                        filters=self.request.GET.dict(),
                        ip_address=self.get_client_ip(self.request),
                        user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                    )
                    
                    # Perform search using search backend
                    backend = get_search_backend()
                    search_results = backend.search(
                        query=q,
                        content_types=['requirement'],
                        filters=self.request.GET.dict(),
                        user=self.request.user if self.request.user.is_authenticated else None
                    )
                    
                    # Extract requirement IDs from search results
                    requirement_ids = [result.get('object_id') for result in search_results if result.get('content_type') == 'requirement']
                    
                    # Filter queryset by searched requirement IDs
                    if requirement_ids:
                        queryset = queryset.filter(id__in=requirement_ids)
                    else:
                        # Fallback to basic search if no results from search app
                        queryset = queryset.filter(
                            Q(title__icontains=q) |
                            Q(description__icontains=q) |
                            Q(specific_topics__icontains=q)
                        )
                except ImportError:
                    # Fallback to basic search if search app is not available
                    queryset = queryset.filter(
                        Q(title__icontains=q) |
                        Q(description__icontains=q) |
                        Q(specific_topics__icontains=q)
                    )
            
            subject = form.cleaned_data.get('subject')
            if subject:
                queryset = queryset.filter(subject=subject)
            
            learning_level = form.cleaned_data.get('learning_level')
            if learning_level:
                queryset = queryset.filter(learning_level=learning_level)
            
            budget_type = form.cleaned_data.get('budget_type')
            if budget_type:
                queryset = queryset.filter(budget_type=budget_type)
            
            urgency_level = form.cleaned_data.get('urgency_level')
            if urgency_level:
                queryset = queryset.filter(urgency_level=urgency_level)
            
            location_type = form.cleaned_data.get('location_type')
            if location_type:
                queryset = queryset.filter(location_type=location_type)
            
            min_budget = form.cleaned_data.get('min_budget')
            if min_budget:
                queryset = queryset.filter(
                    Q(budget_min__gte=min_budget) | Q(budget_max__gte=min_budget)
                )
            
            max_budget = form.cleaned_data.get('max_budget')
            if max_budget:
                queryset = queryset.filter(
                    Q(budget_max__lte=max_budget) | Q(budget_min__lte=max_budget)
                )
            
            sort_by = form.cleaned_data.get('sort_by')
            if sort_by:
                queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = RequirementSearchForm(self.request.GET)
        context['subjects'] = Subject.objects.filter(is_active=True)
        return context


class RequirementDetailView(DetailView):
    """View for viewing requirement details"""
    model = Requirement
    template_name = 'requirements/requirement_detail.html'
    context_object_name = 'requirement'
    slug_url_kwarg = 'slug'
    
    def get_object(self):
        obj = super().get_object()
        # Increment view count
        obj.view_count += 1
        obj.save(update_fields=['view_count'])
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        requirement = self.get_object()
        
        # Check if user has already submitted a proposal
        if (self.request.user.is_authenticated and 
            hasattr(self.request.user, 'user_type') and 
            self.request.user.user_type == 'TUTOR'):
            try:
                context['user_proposal'] = requirement.proposals.filter(
                    tutor=self.request.user
                ).first()
            except:
                context['user_proposal'] = None
        
        # Check if requirement is saved by current user
        if self.request.user.is_authenticated:
            context['is_saved'] = SavedRequirement.objects.filter(
                user=self.request.user,
                requirement=requirement
            ).exists()
        
        # Get proposals for students who posted requirement
        if (self.request.user.is_authenticated and 
            self.request.user == requirement.student):
            try:
                context['proposals'] = requirement.proposals.all().select_related('tutor')
            except:
                context['proposals'] = []
        
        return context


class RequirementCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    """View for students to post new requirements"""
    model = Requirement
    form_class = RequirementPostForm
    template_name = 'requirements/requirement_form.html'
    success_url = reverse_lazy('requirements:list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.student = self.request.user
        messages.success(self.request, 'Your requirement has been posted successfully!')
        return super().form_valid(form)


class RequirementUpdateView(LoginRequiredMixin, StudentRequiredMixin, UpdateView):
    """View for students to edit their requirements"""
    model = Requirement
    form_class = RequirementPostForm
    template_name = 'requirements/requirement_form.html'
    slug_url_kwarg = 'slug'
    
    def get_object(self):
        obj = super().get_object()
        if obj.student != self.request.user:
            raise Http404("You don't have permission to edit this requirement")
        return obj
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Your requirement has been updated successfully!')
        return super().form_valid(form)


class ProposalCreateView(LoginRequiredMixin, TutorRequiredMixin, CreateView):
    """View for tutors to submit proposals"""
    model = Proposal
    form_class = ProposalForm
    template_name = 'requirements/proposal_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.requirement = get_object_or_404(Requirement, slug=kwargs['slug'])
        
        # Check if requirement is open for proposals
        if self.requirement.status != 'OPEN':
            messages.error(request, 'This requirement is not accepting new proposals.')
            return redirect('requirements:detail', slug=self.requirement.slug)
        
        # Check if tutor has already submitted a proposal
        if Proposal.objects.filter(
            requirement=self.requirement,
            tutor=request.user
        ).exists():
            messages.error(request, 'You have already submitted a proposal for this requirement.')
            return redirect('requirements:detail', slug=self.requirement.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['requirement'] = self.requirement
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        kwargs['requirement'] = self.requirement
        return kwargs
    
    def form_valid(self, form):
        form.instance.status = 'SUBMITTED'
        form.instance.submitted_at = timezone.now()
        messages.success(self.request, 'Your proposal has been submitted successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('requirements:detail', kwargs={'slug': self.requirement.slug})


class ProposalListView(LoginRequiredMixin, ListView):
    """View for managing proposals"""
    model = Proposal
    template_name = 'requirements/proposal_list.html'
    context_object_name = 'proposals'
    paginate_by = 10
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'user_type') and user.user_type == 'TUTOR':
            return Proposal.objects.filter(
                tutor=user
            ).select_related('requirement', 'requirement__student')
        elif hasattr(user, 'user_type') and user.user_type == 'STUDENT':
            return Proposal.objects.filter(
                requirement__student=user
            ).select_related('tutor', 'requirement')
        return Proposal.objects.none()


class ProposalDetailView(LoginRequiredMixin, DetailView):
    """View for viewing proposal details"""
    model = Proposal
    template_name = 'requirements/proposal_detail.html'
    context_object_name = 'proposal'
    pk_url_kwarg = 'proposal_id'
    
    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        
        # Check permissions
        if (hasattr(user, 'user_type') and user.user_type == 'TUTOR' and
            obj.tutor != user):
            raise Http404("You don't have permission to view this proposal")
        elif (hasattr(user, 'user_type') and user.user_type == 'STUDENT' and
            obj.requirement.student != user):
            raise Http404("You don't have permission to view this proposal")
        
        return obj


class AwardCreateView(LoginRequiredMixin, StudentRequiredMixin, CreateView):
    """View for students to select and award tutors"""
    model = Award
    form_class = AwardForm
    template_name = 'requirements/award_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.proposal = get_object_or_404(Proposal, id=kwargs['proposal_id'])
        
        # Check if user owns requirement
        if self.proposal.requirement.student != request.user:
            raise Http404("You don't have permission to award this proposal")
        
        # Check if requirement already has an award
        if Award.objects.filter(requirement=self.proposal.requirement).exists():
            messages.error(request, 'This requirement has already been awarded.')
            return redirect('requirements:detail', slug=self.proposal.requirement.slug)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['proposal'] = self.proposal
        context['requirement'] = self.proposal.requirement
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['proposal'] = self.proposal
        kwargs['student'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Update proposal status
        self.proposal.status = 'ACCEPTED'
        self.proposal.accepted_at = timezone.now()
        self.proposal.save()
        
        # Update requirement status
        requirement = self.proposal.requirement
        requirement.status = 'AWARDED'
        requirement.save()
        
        # Reject other proposals
        Proposal.objects.filter(
            requirement=requirement
        ).exclude(id=self.proposal.id).update(status='REJECTED')
        
        messages.success(self.request, 'Tutor has been awarded successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('requirements:detail', kwargs={'slug': self.proposal.requirement.slug})


class SessionListView(LoginRequiredMixin, ListView):
    """View for managing tutoring sessions"""
    model = Session
    template_name = 'requirements/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 10
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'user_type') and user.user_type == 'TUTOR':
            return Session.objects.filter(
                award__tutor=user
            ).select_related('award', 'award__requirement', 'award__student')
        elif hasattr(user, 'user_type') and user.user_type == 'STUDENT':
            return Session.objects.filter(
                award__student=user
            ).select_related('award', 'award__tutor', 'award__requirement')
        return Session.objects.none()


class SessionCreateView(LoginRequiredMixin, CreateView):
    """View for scheduling tutoring sessions"""
    model = Session
    form_class = SessionForm
    template_name = 'requirements/session_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.award = get_object_or_404(Award, id=kwargs['award_id'])
        
        # Check if user is part of award
        if (request.user != self.award.student and 
            request.user != self.award.tutor):
            raise Http404("You don't have permission to create sessions for this award")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['award'] = self.award
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['award'] = self.award
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Session has been scheduled successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('requirements:session-list')


class ReviewCreateView(LoginRequiredMixin, CreateView):
    """View for submitting reviews after completed sessions"""
    model = Review
    form_class = ReviewForm
    template_name = 'requirements/review_form.html'
    
    def dispatch(self, request, *args, **kwargs):
        self.award = get_object_or_404(Award, id=kwargs['award_id'])
        
        # Check if user is part of award
        if (request.user != self.award.student and 
            request.user != self.award.tutor):
            raise Http404("You don't have permission to review this award")
        
        # Check if award is completed
        if self.award.status != 'COMPLETED':
            messages.error(request, 'You can only review completed awards.')
            return redirect('requirements:session-list')
        
        # Check if user has already reviewed
        reviewer = request.user
        reviewee = self.award.tutor if reviewer == self.award.student else self.award.student
        
        if Review.objects.filter(
            award=self.award,
            reviewer=reviewer
        ).exists():
            messages.error(request, 'You have already reviewed this award.')
            return redirect('requirements:session-list')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['award'] = self.award
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['award'] = self.award
        kwargs['reviewer'] = self.request.user
        kwargs['reviewee'] = (
            self.award.tutor if self.request.user == self.award.student 
            else self.award.student
        )
        return kwargs
    
    def form_valid(self, form):
        messages.success(self.request, 'Your review has been submitted successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('requirements:session-list')


@login_required
def save_requirement(request, slug):
    """View for saving/unsaving requirements"""
    requirement = get_object_or_404(Requirement, slug=slug)
    
    if request.method == 'POST':
        saved_req = SavedRequirement.objects.filter(
            user=request.user,
            requirement=requirement
        ).first()
        
        if saved_req:
            saved_req.delete()
            return JsonResponse({'status': 'unsaved'})
        else:
            SavedRequirement.objects.create(
                user=request.user,
                requirement=requirement
            )
            return JsonResponse({'status': 'saved'})
    
    return JsonResponse({'status': 'error'}, status=400)


@login_required
def favorite_tutor(request, tutor_id):
    """View for favoriting/unfavoriting tutors"""
    tutor = get_object_or_404(User, id=tutor_id)
    
    if not hasattr(tutor, 'user_type') or tutor.user_type != 'TUTOR':
        raise Http404("Tutor not found")
    
    if request.method == 'POST':
        favorite = FavoriteTutor.objects.filter(
            student=request.user,
            tutor=tutor
        ).first()
        
        if favorite:
            favorite.delete()
            return JsonResponse({'status': 'unfavorited'})
        else:
            FavoriteTutor.objects.create(
                student=request.user,
                tutor=tutor
            )
            return JsonResponse({'status': 'favorited'})
    
    return JsonResponse({'status': 'error'}, status=400)
    


@login_required
def withdraw_proposal(request, proposal_id):
    """View for tutors to withdraw their proposals"""
    proposal = get_object_or_404(Proposal, id=proposal_id, tutor=request.user)
    
    if request.method == 'POST':
        if proposal.status in ['DRAFT', 'SUBMITTED']:
            proposal.status = 'WITHDRAWN'
            proposal.save()
            messages.success(request, 'Your proposal has been withdrawn.')
        else:
            messages.error(request, 'This proposal cannot be withdrawn.')
        
        return redirect('requirements:proposal-list')
    
    return render(request, 'requirements/confirm_withdraw.html', {'proposal': proposal})

    def get_client_ip(self, request):
        """Helper method to get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
