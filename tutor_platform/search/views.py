import json
import time
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, FormView, DetailView, UpdateView, DeleteView
from django.views.generic.base import View
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import SearchQuery, SearchFilter, SearchResult, SearchIndex, SearchSuggestion, SearchAnalytics
from .forms import TutorSearchForm, RequirementSearchForm, AdvancedSearchForm, SearchFilterForm
from .utils import SearchBackend, get_search_backend, build_search_query, rank_results
from .filters import TutorFilterSet, RequirementFilterSet

User = get_user_model()


class GlobalSearchView(LoginRequiredMixin, FormView):
    """Global search across all content types"""
    template_name = 'search/global_search.html'
    form_class = AdvancedSearchForm
    
    def form_valid(self, form):
        query = form.cleaned_data.get('query', '').strip()
        if not query:
            return self.form_invalid(form)
        
        # Record search query
        search_query = SearchQuery.objects.create(
            user=self.request.user,
            query=query,
            search_type='GLOBAL',
            filters=form.cleaned_data,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        
        # Perform search
        backend = get_search_backend()
        start_time = time.time()
        
        results = backend.search(
            query=query,
            content_types=['tutor', 'requirement', 'message', 'payment'],
            filters=form.cleaned_data,
            user=self.request.user
        )
        
        search_time = (time.time() - start_time) * 1000
        search_query.response_time_ms = int(search_time)
        search_query.results_count = len(results)
        search_query.save()
        
        # Update search suggestions
        SearchSuggestion.add_suggestion(query, 'GLOBAL')
        
        # Paginate results
        paginator = Paginator(results, 20)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = self.get_context_data(
            form=form,
            results=page_obj,
            query=query,
            search_query=search_query,
            total_results=len(results)
        )
        
        return render(self.request, self.template_name, context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_searches'] = SearchQuery.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:5]
        
        context['trending_searches'] = SearchSuggestion.objects.filter(
            is_trending=True,
            search_type='GLOBAL'
        ).order_by('-frequency')[:10]
        
        return context
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class TutorSearchView(LoginRequiredMixin, FormView):
    """Specialized search for tutors"""
    template_name = 'search/tutor_search.html'
    form_class = TutorSearchForm
    
    def form_valid(self, form):
        query = form.cleaned_data.get('query', '').strip()
        
        # Record search query
        search_query = SearchQuery.objects.create(
            user=self.request.user,
            query=query,
            search_type='TUTOR',
            filters=form.cleaned_data,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        
        # Perform search
        backend = get_search_backend()
        start_time = time.time()
        
        results = backend.search(
            query=query,
            content_types=['tutor'],
            filters=form.cleaned_data,
            user=self.request.user
        )
        
        search_time = (time.time() - start_time) * 1000
        search_query.response_time_ms = int(search_time)
        search_query.results_count = len(results)
        search_query.save()
        
        # Update search suggestions
        SearchSuggestion.add_suggestion(query, 'TUTOR')
        
        # Apply filters
        tutor_queryset = User.objects.filter(
            user_type='TUTOR',
            is_active=True
        ).select_related('tutorprofile')
        
        # Apply form filters
        if query:
            tutor_queryset = tutor_queryset.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(tutorprofile__bio__icontains=query) |
                Q(tutorprofile__professional_title__icontains=query)
            )
        
        # Apply additional filters
        subjects = form.cleaned_data.get('subjects')
        if subjects:
            tutor_queryset = tutor_queryset.filter(
                tutorprofile__tutor_subjects__subject__in=subjects
            ).distinct()
        
        min_rate = form.cleaned_data.get('hourly_rate_min')
        if min_rate:
            tutor_queryset = tutor_queryset.filter(
                Q(tutorprofile__hourly_rate_min__gte=min_rate) |
                Q(tutorprofile__hourly_rate_max__gte=min_rate)
            )
        
        max_rate = form.cleaned_data.get('hourly_rate_max')
        if max_rate:
            tutor_queryset = tutor_queryset.filter(
                Q(tutorprofile__hourly_rate_min__lte=max_rate) |
                Q(tutorprofile__hourly_rate_max__lte=max_rate)
            )
        
        availability = form.cleaned_data.get('availability_status')
        if availability:
            tutor_queryset = tutor_queryset.filter(
                tutorprofile__availability_status=availability
            )
        
        is_verified = form.cleaned_data.get('is_verified')
        if is_verified:
            tutor_queryset = tutor_queryset.filter(is_verified=True)
        
        # Apply filter set
        filter_set = TutorFilterSet(self.request.GET, queryset=tutor_queryset)
        
        # Paginate results
        paginator = Paginator(filter_set.qs, 20)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = self.get_context_data(
            form=form,
            filter_set=filter_set,
            results=page_obj,
            query=query,
            search_query=search_query,
            total_results=filter_set.qs.count()
        )
        
        return render(self.request, self.template_name, context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_searches'] = SearchQuery.objects.filter(
            user=self.request.user,
            search_type='TUTOR'
        ).order_by('-created_at')[:5]
        
        context['saved_filters'] = SearchFilter.objects.filter(
            user=self.request.user,
            search_type='TUTOR'
        ).order_by('-created_at')
        
        return context
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class RequirementSearchView(LoginRequiredMixin, FormView):
    """Specialized search for requirements"""
    template_name = 'search/requirement_search.html'
    form_class = RequirementSearchForm
    
    def form_valid(self, form):
        query = form.cleaned_data.get('query', '').strip()
        
        # Record search query
        search_query = SearchQuery.objects.create(
            user=self.request.user,
            query=query,
            search_type='REQUIREMENT',
            filters=form.cleaned_data,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        
        # Perform search
        backend = get_search_backend()
        start_time = time.time()
        
        results = backend.search(
            query=query,
            content_types=['requirement'],
            filters=form.cleaned_data,
            user=self.request.user
        )
        
        search_time = (time.time() - start_time) * 1000
        search_query.response_time_ms = int(search_time)
        search_query.results_count = len(results)
        search_query.save()
        
        # Update search suggestions
        SearchSuggestion.add_suggestion(query, 'REQUIREMENT')
        
        # Apply filters
        from requirements.models import Requirement
        
        requirement_queryset = Requirement.objects.filter(
            status='OPEN',
            visibility='PUBLIC'
        ).select_related('student', 'subject')
        
        # Apply form filters
        if query:
            requirement_queryset = requirement_queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query) |
                Q(specific_topics__icontains=query)
            )
        
        subject = form.cleaned_data.get('subject')
        if subject:
            requirement_queryset = requirement_queryset.filter(subject=subject)
        
        learning_level = form.cleaned_data.get('learning_level')
        if learning_level:
            requirement_queryset = requirement_queryset.filter(learning_level=learning_level)
        
        budget_min = form.cleaned_data.get('budget_min')
        if budget_min:
            requirement_queryset = requirement_queryset.filter(
                Q(budget_min__gte=budget_min) |
                Q(budget_max__gte=budget_min)
            )
        
        budget_max = form.cleaned_data.get('budget_max')
        if budget_max:
            requirement_queryset = requirement_queryset.filter(
                Q(budget_min__lte=budget_max) |
                Q(budget_max__lte=budget_max)
            )
        
        urgency = form.cleaned_data.get('urgency_level')
        if urgency:
            requirement_queryset = requirement_queryset.filter(urgency_level=urgency)
        
        location_type = form.cleaned_data.get('location_type')
        if location_type:
            requirement_queryset = requirement_queryset.filter(location_type=location_type)
        
        # Apply filter set
        filter_set = RequirementFilterSet(self.request.GET, queryset=requirement_queryset)
        
        # Paginate results
        paginator = Paginator(filter_set.qs, 20)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context = self.get_context_data(
            form=form,
            filter_set=filter_set,
            results=page_obj,
            query=query,
            search_query=search_query,
            total_results=filter_set.qs.count()
        )
        
        return render(self.request, self.template_name, context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_searches'] = SearchQuery.objects.filter(
            user=self.request.user,
            search_type='REQUIREMENT'
        ).order_by('-created_at')[:5]
        
        context['saved_filters'] = SearchFilter.objects.filter(
            user=self.request.user,
            search_type='REQUIREMENT'
        ).order_by('-created_at')
        
        return context
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class AdvancedSearchView(LoginRequiredMixin, FormView):
    """Advanced search with complex filtering options"""
    template_name = 'search/advanced_search.html'
    form_class = AdvancedSearchForm
    
    def form_valid(self, form):
        query = form.cleaned_data.get('query', '').strip()
        content_types = form.cleaned_data.get('content_types', ['tutor', 'requirement'])
        
        # Record search query
        search_query = SearchQuery.objects.create(
            user=self.request.user,
            query=query,
            search_type='GLOBAL',
            filters=form.cleaned_data,
            ip_address=self.get_client_ip(),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
        )
        
        # Perform search
        backend = get_search_backend()
        start_time = time.time()
        
        results = backend.search(
            query=query,
            content_types=content_types,
            filters=form.cleaned_data,
            user=self.request.user
        )
        
        search_time = (time.time() - start_time) * 1000
        search_query.response_time_ms = int(search_time)
        search_query.results_count = len(results)
        search_query.save()
        
        # Update search suggestions
        SearchSuggestion.add_suggestion(query, 'GLOBAL')
        
        # Group results by content type
        grouped_results = {}
        for result in results:
            content_type = result.get('content_type')
            if content_type not in grouped_results:
                grouped_results[content_type] = []
            grouped_results[content_type].append(result)
        
        # Paginate each group
        paginated_results = {}
        for content_type, items in grouped_results.items():
            paginator = Paginator(items, 10)
            page_number = self.request.GET.get(f'page_{content_type}', 1)
            paginated_results[content_type] = paginator.get_page(page_number)
        
        context = self.get_context_data(
            form=form,
            results=paginated_results,
            grouped_results=grouped_results,
            query=query,
            search_query=search_query,
            total_results=len(results)
        )
        
        return render(self.request, self.template_name, context)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_searches'] = SearchQuery.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:5]
        
        context['saved_filters'] = SearchFilter.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
        
        return context
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class SearchResultsView(LoginRequiredMixin, DetailView):
    """Display detailed search results with highlighting"""
    model = SearchQuery
    template_name = 'search/search_results.html'
    context_object_name = 'search_query'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.get_object()
        
        # Get cached results or perform new search
        cached_results = SearchResult.objects.filter(
            search_query=search_query
        ).select_related('search_query')
        
        if not cached_results.exists() or cached_results.first().is_expired():
            # Perform new search
            backend = get_search_backend()
            results = backend.search(
                query=search_query.query,
                content_types=['tutor', 'requirement'],
                filters=search_query.filters,
                user=self.request.user
            )
            
            # Cache results
            for result in results:
                SearchResult.objects.create(
                    search_query=search_query,
                    content_type=result.get('content_type'),
                    object_id=result.get('object_id'),
                    title=result.get('title'),
                    description=result.get('description'),
                    url=result.get('url'),
                    relevance_score=result.get('relevance_score', 0),
                    highlight_data=result.get('highlight_data', {}),
                    metadata=result.get('metadata', {}),
                    expires_at=timezone.now() + timezone.timedelta(hours=1)
                )
            
            cached_results = SearchResult.objects.filter(
                search_query=search_query
            ).select_related('search_query')
        
        # Paginate results
        paginator = Paginator(cached_results, 20)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        context['results'] = page_obj
        context['total_results'] = cached_results.count()
        
        return context


class SavedSearchesView(LoginRequiredMixin, ListView):
    """Manage saved search filters"""
    model = SearchFilter
    template_name = 'search/saved_searches.html'
    context_object_name = 'saved_filters'
    paginate_by = 20
    
    def get_queryset(self):
        return SearchFilter.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_types'] = [
            ('GLOBAL', 'Global Search'),
            ('TUTOR', 'Tutor Search'),
            ('REQUIREMENT', 'Requirement Search'),
            ('MESSAGE', 'Message Search'),
            ('PAYMENT', 'Payment Search'),
        ]
        return context


class SaveSearchFilterView(LoginRequiredMixin, FormView):
    """Save a new search filter"""
    form_class = SearchFilterForm
    template_name = 'search/save_filter.html'
    success_url = reverse_lazy('search:saved_searches')
    
    def form_valid(self, form):
        # Get current search parameters from session or request
        search_params = self.request.session.get('current_search_params', {})
        
        search_filter = SearchFilter.objects.create(
            user=self.request.user,
            name=form.cleaned_data['name'],
            search_type=search_params.get('search_type', 'GLOBAL'),
            filters=search_params.get('filters', {}),
            is_default=form.cleaned_data.get('is_default', False),
            is_public=form.cleaned_data.get('is_public', False)
        )
        
        messages.success(self.request, f'Search filter "{search_filter.name}" has been saved.')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_params'] = self.request.session.get('current_search_params', {})
        return context


class DeleteSearchFilterView(LoginRequiredMixin, DeleteView):
    """Delete a saved search filter"""
    model = SearchFilter
    template_name = 'search/delete_filter.html'
    success_url = reverse_lazy('search:saved_searches')
    
    def get_queryset(self):
        return SearchFilter.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Search filter has been deleted.')
        return super().delete(request, *args, **kwargs)


@method_decorator(csrf_exempt, name='dispatch')
class SearchAutocompleteView(LoginRequiredMixin, View):
    """AJAX endpoint for search autocomplete"""
    
    def get(self, request):
        query = request.GET.get('q', '').strip()
        search_type = request.GET.get('type', 'GLOBAL')
        
        if not query or len(query) < 2:
            return JsonResponse({'suggestions': []})
        
        # Get search suggestions
        suggestions = SearchSuggestion.objects.filter(
            query__icontains=query,
            search_type=search_type,
            is_active=True
        ).order_by('-frequency')[:10]
        
        # Get recent searches for this user
        recent_searches = SearchQuery.objects.filter(
            user=request.user,
            search_type=search_type,
            query__icontains=query
        ).order_by('-created_at')[:5]
        
        suggestion_list = []
        
        # Add suggestions
        for suggestion in suggestions:
            suggestion_list.append({
                'text': suggestion.query,
                'type': 'suggestion',
                'frequency': suggestion.frequency
            })
        
        # Add recent searches
        for search in recent_searches:
            suggestion_list.append({
                'text': search.query,
                'type': 'recent',
                'date': search.created_at.isoformat()
            })
        
        return JsonResponse({'suggestions': suggestion_list})


@method_decorator(csrf_exempt, name='dispatch')
class SearchAnalyticsView(LoginRequiredMixin, View):
    """AJAX endpoint for search analytics"""
    
    def get(self, request):
        search_type = request.GET.get('type', 'GLOBAL')
        days = int(request.GET.get('days', 30))
        
        # Get analytics data
        end_date = timezone.now().date()
        start_date = end_date - timezone.timedelta(days=days)
        
        analytics = SearchAnalytics.objects.filter(
            search_type=search_type,
            date__gte=start_date,
            date__lte=end_date
        ).order_by('-date')
        
        # Get top queries
        top_queries = SearchQuery.objects.filter(
            search_type=search_type,
            created_at__gte=start_date
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Calculate stats
        total_searches = analytics.aggregate(
            total=Count('total_searches')
        )['total'] or 0
        
        avg_response_time = analytics.aggregate(
            avg=Avg('avg_response_time_ms')
        )['avg'] or 0
        
        data = {
            'analytics': [
                {
                    'date': item.date.isoformat(),
                    'total_searches': item.total_searches,
                    'unique_searchers': item.unique_searchers,
                    'avg_results': item.avg_results_per_search,
                    'avg_response_time': item.avg_response_time_ms
                }
                for item in analytics
            ],
            'top_queries': [
                {
                    'query': item['query'],
                    'count': item['count']
                }
                for item in top_queries
            ],
            'summary': {
                'total_searches': total_searches,
                'avg_response_time': round(avg_response_time, 2)
            }
        }
        
        return JsonResponse(data)
