import re
import json
import time
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.postgres.search import SearchVector, SearchQuery as PGSearchQuery, SearchRank
from django.db import models
from django.db.models import Q, Count, Avg
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth import get_user_model

from .models import SearchIndex, SearchResult, SearchQuery

User = get_user_model()


class SearchBackend:
    """Base class for search backends"""
    
    def __init__(self):
        self.name = "base"
    
    def search(self, query, content_types=None, filters=None, user=None):
        """Perform search with given parameters"""
        raise NotImplementedError("Subclasses must implement search method")
    
    def index_content(self, content_type, object_id, title, content, metadata=None):
        """Index content for searching"""
        raise NotImplementedError("Subclasses must implement index_content method")
    
    def remove_from_index(self, content_type, object_id):
        """Remove content from search index"""
        raise NotImplementedError("Subclasses must implement remove_from_index method")
    
    def get_suggestions(self, query, content_type=None, limit=10):
        """Get search suggestions for autocomplete"""
        raise NotImplementedError("Subclasses must implement get_suggestions method")


class DatabaseSearchBackend(SearchBackend):
    """Database-based search backend using PostgreSQL full-text search"""
    
    def __init__(self):
        super().__init__()
        self.name = "database"
    
    def search(self, query, content_types=None, filters=None, user=None):
        """Perform search using PostgreSQL full-text search"""
        if not query:
            return []
        
        results = []
        
        # Search tutors
        if not content_types or 'tutor' in content_types:
            tutor_results = self._search_tutors(query, filters, user)
            results.extend(tutor_results)
        
        # Search requirements
        if not content_types or 'requirement' in content_types:
            requirement_results = self._search_requirements(query, filters, user)
            results.extend(requirement_results)
        
        # Search messages
        if not content_types or 'message' in content_types:
            message_results = self._search_messages(query, filters, user)
            results.extend(message_results)
        
        # Search payments
        if not content_types or 'payment' in content_types:
            payment_results = self._search_payments(query, filters, user)
            results.extend(payment_results)
        
        # Sort by relevance score
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return results
    
    def _search_tutors(self, query, filters=None, user=None):
        """Search for tutors"""
        from accounts.models import TutorProfile, Subject
        
        queryset = User.objects.filter(
            user_type='TUTOR',
            is_active=True
        ).select_related('tutorprofile')
        
        # Apply text search
        search_query = PGSearchQuery(query)
        queryset = queryset.annotate(
            search_vector=SearchVector(
                'username', 'first_name', 'last_name',
                'tutorprofile__bio', 'tutorprofile__professional_title',
                'tutorprofile__teaching_experience'
            ),
            rank=SearchRank(
                SearchVector(
                    'username', 'first_name', 'last_name',
                    'tutorprofile__bio', 'tutorprofile__professional_title',
                    'tutorprofile__teaching_experience'
                ),
                search_query
            )
        ).filter(search_vector=search_query)
        
        # Apply filters
        if filters:
            # Subject filter
            subjects = filters.get('subjects')
            if subjects:
                queryset = queryset.filter(
                    tutorprofile__tutor_subjects__subject__in=subjects
                ).distinct()
            
            # Rate filter
            min_rate = filters.get('hourly_rate_min')
            if min_rate:
                queryset = queryset.filter(
                    Q(tutorprofile__hourly_rate_min__gte=min_rate) |
                    Q(tutorprofile__hourly_rate_max__gte=min_rate)
                )
            
            max_rate = filters.get('hourly_rate_max')
            if max_rate:
                queryset = queryset.filter(
                    Q(tutorprofile__hourly_rate_min__lte=max_rate) |
                    Q(tutorprofile__hourly_rate_max__lte=max_rate)
                )
            
            # Availability filter
            availability = filters.get('availability_status')
            if availability:
                queryset = queryset.filter(
                    tutorprofile__availability_status=availability
                )
            
            # Verification filter
            if filters.get('is_verified'):
                queryset = queryset.filter(is_verified=True)
            
            # Online filter
            if filters.get('is_online'):
                queryset = queryset.filter(is_online=True)
            
            # Featured filter
            if filters.get('is_featured'):
                queryset = queryset.filter(tutorprofile__is_featured=True)
            
            # Experience filter
            min_exp = filters.get('experience_years_min')
            if min_exp:
                queryset = queryset.filter(
                    tutorprofile__experience_years__gte=min_exp
                )
            
            max_exp = filters.get('experience_years_max')
            if max_exp:
                queryset = queryset.filter(
                    tutorprofile__experience_years__lte=max_exp
                )
            
            # Language filter
            languages = filters.get('languages')
            if languages:
                language_list = [lang.strip() for lang in languages.split(',')]
                for lang in language_list:
                    queryset = queryset.filter(
                        tutorprofile__languages__icontains=lang
                    )
        
        # Convert to result format
        results = []
        for tutor in queryset[:50]:  # Limit results
            result = {
                'content_type': 'tutor',
                'object_id': str(tutor.id),
                'title': tutor.get_full_name(),
                'description': tutor.tutorprofile.bio or tutor.tutorprofile.professional_title or '',
                'url': f'/accounts/tutor/{tutor.id}/',
                'relevance_score': tutor.rank or 0,
                'metadata': {
                    'username': tutor.username,
                    'avatar': tutor.profile_picture.url if tutor.profile_picture else None,
                    'hourly_rate_min': float(tutor.tutorprofile.hourly_rate_min) if tutor.tutorprofile.hourly_rate_min else None,
                    'hourly_rate_max': float(tutor.tutorprofile.hourly_rate_max) if tutor.tutorprofile.hourly_rate_max else None,
                    'is_verified': tutor.is_verified,
                    'is_online': tutor.is_online,
                    'rating': tutor.tutorprofile.get_average_rating(),
                    'experience_years': tutor.tutorprofile.experience_years,
                    'subjects': [
                        ts.subject.name for ts in tutor.tutorprofile.tutor_subjects.all()
                    ]
                }
            }
            results.append(result)
        
        return results
    
    def _search_requirements(self, query, filters=None, user=None):
        """Search for requirements"""
        from requirements.models import Requirement
        
        queryset = Requirement.objects.filter(
            status='OPEN',
            visibility='PUBLIC'
        ).select_related('student', 'subject')
        
        # Apply text search
        search_query = PGSearchQuery(query)
        queryset = queryset.annotate(
            search_vector=SearchVector('title', 'description', 'specific_topics'),
            rank=SearchRank(
                SearchVector('title', 'description', 'specific_topics'),
                search_query
            )
        ).filter(search_vector=search_query)
        
        # Apply filters
        if filters:
            # Subject filter
            subject = filters.get('subject')
            if subject:
                queryset = queryset.filter(subject=subject)
            
            # Learning level filter
            learning_level = filters.get('learning_level')
            if learning_level:
                queryset = queryset.filter(learning_level=learning_level)
            
            # Budget filter
            min_budget = filters.get('budget_min')
            if min_budget:
                queryset = queryset.filter(
                    Q(budget_min__gte=min_budget) |
                    Q(budget_max__gte=min_budget)
                )
            
            max_budget = filters.get('budget_max')
            if max_budget:
                queryset = queryset.filter(
                    Q(budget_min__lte=max_budget) |
                    Q(budget_max__lte=max_budget)
                )
            
            # Budget type filter
            budget_type = filters.get('budget_type')
            if budget_type:
                queryset = queryset.filter(budget_type=budget_type)
            
            # Urgency filter
            urgency = filters.get('urgency_level')
            if urgency:
                queryset = queryset.filter(urgency_level=urgency)
            
            # Location type filter
            location_type = filters.get('location_type')
            if location_type:
                queryset = queryset.filter(location_type=location_type)
            
            # Featured filter
            if filters.get('is_featured'):
                queryset = queryset.filter(is_featured=True)
            
            # Deadline filter
            deadline_days = filters.get('deadline_days')
            if deadline_days:
                deadline_date = timezone.now().date() + timedelta(days=deadline_days)
                queryset = queryset.filter(deadline__lte=deadline_date)
        
        # Convert to result format
        results = []
        for requirement in queryset[:50]:  # Limit results
            result = {
                'content_type': 'requirement',
                'object_id': str(requirement.id),
                'title': requirement.title,
                'description': requirement.description[:200] + '...' if len(requirement.description) > 200 else requirement.description,
                'url': f'/requirements/{requirement.slug}/',
                'relevance_score': requirement.rank or 0,
                'metadata': {
                    'student': requirement.student.get_full_name(),
                    'subject': requirement.subject.name,
                    'learning_level': requirement.get_learning_level_display(),
                    'budget_range': requirement.get_budget_range(),
                    'urgency_level': requirement.urgency_level,
                    'location_type': requirement.location_type,
                    'deadline': requirement.deadline.isoformat() if requirement.deadline else None,
                    'created_at': requirement.created_at.isoformat(),
                    'view_count': requirement.view_count,
                    'proposal_count': requirement.proposal_count
                }
            }
            results.append(result)
        
        return results
    
    def _search_messages(self, query, filters=None, user=None):
        """Search for messages"""
        from messaging.models import Message
        
        if not user:
            return []
        
        queryset = Message.objects.filter(
            Q(conversation__participant1=user) | Q(conversation__participant2=user)
        ).select_related('sender', 'conversation')
        
        # Apply text search
        search_query = PGSearchQuery(query)
        queryset = queryset.annotate(
            search_vector=SearchVector('content'),
            rank=SearchRank(SearchVector('content'), search_query)
        ).filter(search_vector=search_query)
        
        # Apply filters
        if filters:
            # Conversation type filter
            conversation_type = filters.get('conversation_type')
            if conversation_type == 'sent':
                queryset = queryset.filter(sender=user)
            elif conversation_type == 'received':
                queryset = queryset.exclude(sender=user)
            
            # Date filters
            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
            
            # Attachments filter
            if filters.get('has_attachments'):
                queryset = queryset.filter(attachments__isnull=False).distinct()
            
            # Unread filter
            if filters.get('is_unread'):
                # This would need more complex logic to determine unread status
                pass
        
        # Convert to result format
        results = []
        for message in queryset[:50]:  # Limit results
            result = {
                'content_type': 'message',
                'object_id': str(message.id),
                'title': f"Message from {message.sender.get_full_name()}",
                'description': message.content[:200] + '...' if len(message.content) > 200 else message.content,
                'url': f'/messaging/conversation/{message.conversation.id}/#message-{message.id}',
                'relevance_score': message.rank or 0,
                'metadata': {
                    'sender': message.sender.get_full_name(),
                    'conversation_id': str(message.conversation.id),
                    'created_at': message.created_at.isoformat(),
                    'is_read': message.is_read,
                    'has_attachments': message.attachments.exists()
                }
            }
            results.append(result)
        
        return results
    
    def _search_payments(self, query, filters=None, user=None):
        """Search for payments"""
        from paymentsdetails.models import Payment
        
        if not user:
            return []
        
        queryset = Payment.objects.filter(
            Q(payer=user) | Q(payee=user)
        ).select_related('payer', 'payee')
        
        # Apply text search
        search_query = PGSearchQuery(query)
        queryset = queryset.annotate(
            search_vector=SearchVector('description', 'transaction_id'),
            rank=SearchRank(SearchVector('description', 'transaction_id'), search_query)
        ).filter(search_vector=search_query)
        
        # Apply filters
        if filters:
            # Payment type filter
            payment_type = filters.get('payment_type')
            if payment_type:
                queryset = queryset.filter(payment_type=payment_type)
            
            # Status filter
            status = filters.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Amount filters
            min_amount = filters.get('amount_min')
            if min_amount:
                queryset = queryset.filter(amount__gte=min_amount)
            
            max_amount = filters.get('amount_max')
            if max_amount:
                queryset = queryset.filter(amount__lte=max_amount)
            
            # Date filters
            date_from = filters.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
            
            date_to = filters.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
            
            # Currency filter
            currency = filters.get('currency')
            if currency:
                queryset = queryset.filter(currency=currency)
        
        # Convert to result format
        results = []
        for payment in queryset[:50]:  # Limit results
            result = {
                'content_type': 'payment',
                'object_id': str(payment.id),
                'title': f"Payment {payment.id}",
                'description': payment.description or f"Payment from {payment.payer.get_full_name()} to {payment.payee.get_full_name()}",
                'url': f'/paymentsdetails/payment/{payment.id}/',
                'relevance_score': payment.rank or 0,
                'metadata': {
                    'amount': float(payment.amount),
                    'currency': payment.currency,
                    'status': payment.status,
                    'payment_type': payment.payment_type,
                    'payer': payment.payer.get_full_name(),
                    'payee': payment.payee.get_full_name(),
                    'created_at': payment.created_at.isoformat(),
                    'completed_at': payment.completed_at.isoformat() if payment.completed_at else None
                }
            }
            results.append(result)
        
        return results
    
    def index_content(self, content_type, object_id, title, content, metadata=None):
        """Index content in the database"""
        return SearchIndex.update_index(
            content_type=content_type,
            object_id=object_id,
            title=title,
            content=content,
            metadata=metadata
        )
    
    def remove_from_index(self, content_type, object_id):
        """Remove content from search index"""
        try:
            SearchIndex.objects.filter(
                content_type=content_type,
                object_id=object_id
            ).delete()
        except Exception:
            pass
    
    def get_suggestions(self, query, content_type=None, limit=10):
        """Get search suggestions from database"""
        from .models import SearchSuggestion
        
        queryset = SearchSuggestion.objects.filter(
            query__icontains=query,
            is_active=True
        )
        
        if content_type:
            queryset = queryset.filter(search_type=content_type.upper())
        
        return list(
            queryset.order_by('-frequency')[:limit]
            .values_list('query', flat=True)
        )


class ElasticsearchBackend(SearchBackend):
    """Elasticsearch search backend for advanced search capabilities"""
    
    def __init__(self):
        super().__init__()
        self.name = "elasticsearch"
        self.index_name = getattr(settings, 'ELASTICSEARCH_INDEX', 'tutor_platform')
        
        try:
            from elasticsearch import Elasticsearch
            self.es = Elasticsearch(
                hosts=getattr(settings, 'ELASTICSEARCH_HOSTS', ['localhost:9200'])
            )
            self.es.ping()  # Check connection
        except ImportError:
            self.es = None
        except Exception:
            self.es = None
    
    def search(self, query, content_types=None, filters=None, user=None):
        """Perform search using Elasticsearch"""
        if not self.es or not query:
            return []
        
        # Build Elasticsearch query
        es_query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "description^2", "content", "metadata.*"],
                                "fuzziness": "AUTO"
                            }
                        }
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "title": {},
                    "description": {},
                    "content": {}
                }
            },
            "size": 100
        }
        
        # Add content type filter
        if content_types:
            es_query["query"]["bool"]["filter"] = {
                "terms": {"content_type": content_types}
            }
        
        # Add additional filters
        if filters:
            # This would need to be expanded based on specific filter types
            pass
        
        try:
            response = self.es.search(index=self.index_name, body=es_query)
            results = []
            
            for hit in response['hits']['hits']:
                result = {
                    'content_type': hit['_source']['content_type'],
                    'object_id': hit['_source']['object_id'],
                    'title': hit['_source']['title'],
                    'description': hit['_source'].get('description', ''),
                    'url': hit['_source'].get('url', ''),
                    'relevance_score': hit['_score'],
                    'highlight_data': hit.get('highlight', {}),
                    'metadata': hit['_source'].get('metadata', {})
                }
                results.append(result)
            
            return results
        except Exception as e:
            # Fallback to database search
            return DatabaseSearchBackend().search(query, content_types, filters, user)
    
    def index_content(self, content_type, object_id, title, content, metadata=None):
        """Index content in Elasticsearch"""
        if not self.es:
            return False
        
        doc = {
            'content_type': content_type,
            'object_id': str(object_id),
            'title': title,
            'description': content[:500] if content else '',
            'content': content,
            'metadata': metadata or {},
            'indexed_at': timezone.now().isoformat()
        }
        
        try:
            self.es.index(
                index=self.index_name,
                id=f"{content_type}_{object_id}",
                body=doc
            )
            return True
        except Exception:
            return False
    
    def remove_from_index(self, content_type, object_id):
        """Remove content from Elasticsearch index"""
        if not self.es:
            return False
        
        try:
            self.es.delete(
                index=self.index_name,
                id=f"{content_type}_{object_id}"
            )
            return True
        except Exception:
            return False
    
    def get_suggestions(self, query, content_type=None, limit=10):
        """Get search suggestions from Elasticsearch"""
        if not self.es:
            return []
        
        es_query = {
            "suggest": {
                "text": query,
                "simple_phrase": {
                    "phrase": {
                        "field": "title",
                        "size": limit
                    }
                }
            }
        }
        
        try:
            response = self.es.search(index=self.index_name, body=es_query)
            suggestions = []
            
            for option in response['suggest']['simple_phrase'][0]['options']:
                suggestions.append(option['text'])
            
            return suggestions
        except Exception:
            return []


class HybridSearchBackend(SearchBackend):
    """Hybrid search backend combining database and Elasticsearch"""
    
    def __init__(self):
        super().__init__()
        self.name = "hybrid"
        self.db_backend = DatabaseSearchBackend()
        self.es_backend = ElasticsearchBackend()
    
    def search(self, query, content_types=None, filters=None, user=None):
        """Perform hybrid search combining multiple backends"""
        results = []
        
        # Try Elasticsearch first
        if self.es_backend.es:
            es_results = self.es_backend.search(query, content_types, filters, user)
            results.extend(es_results)
        
        # Fall back to database if needed
        if not results or len(results) < 10:
            db_results = self.db_backend.search(query, content_types, filters, user)
            
            # Remove duplicates and merge results
            existing_ids = set(r['object_id'] for r in results)
            for result in db_results:
                if result['object_id'] not in existing_ids:
                    results.append(result)
        
        # Re-rank results
        results = self._rerank_results(results, query, user)
        
        return results[:100]  # Limit total results
    
    def _rerank_results(self, results, query, user=None):
        """Re-rank results based on various factors"""
        for result in results:
            # Boost recent content
            if 'created_at' in result.get('metadata', {}):
                created_at = datetime.fromisoformat(result['metadata']['created_at'])
                days_old = (timezone.now() - created_at).days
                if days_old < 7:
                    result['relevance_score'] *= 1.2
                elif days_old < 30:
                    result['relevance_score'] *= 1.1
            
            # Boost verified content
            if result.get('content_type') == 'tutor' and result.get('metadata', {}).get('is_verified'):
                result['relevance_score'] *= 1.3
            
            # Boost featured content
            if result.get('metadata', {}).get('is_featured'):
                result['relevance_score'] *= 1.2
            
            # Boost content matching user preferences
            if user and result.get('content_type') == 'requirement':
                # Boost requirements in subjects user is interested in
                pass
        
        # Sort by updated relevance score
        results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        
        return results
    
    def index_content(self, content_type, object_id, title, content, metadata=None):
        """Index content in all backends"""
        self.db_backend.index_content(content_type, object_id, title, content, metadata)
        self.es_backend.index_content(content_type, object_id, title, content, metadata)
    
    def remove_from_index(self, content_type, object_id):
        """Remove content from all backends"""
        self.db_backend.remove_from_index(content_type, object_id)
        self.es_backend.remove_from_index(content_type, object_id)
    
    def get_suggestions(self, query, content_type=None, limit=10):
        """Get suggestions from all backends"""
        suggestions = []
        
        # Try Elasticsearch first
        if self.es_backend.es:
            es_suggestions = self.es_backend.get_suggestions(query, content_type, limit)
            suggestions.extend(es_suggestions)
        
        # Add database suggestions if needed
        if len(suggestions) < limit:
            db_suggestions = self.db_backend.get_suggestions(query, content_type, limit - len(suggestions))
            for suggestion in db_suggestions:
                if suggestion not in suggestions:
                    suggestions.append(suggestion)
        
        return suggestions[:limit]


def get_search_backend():
    """Get the configured search backend"""
    backend_name = getattr(settings, 'SEARCH_BACKEND', 'database')
    
    if backend_name == 'elasticsearch':
        return ElasticsearchBackend()
    elif backend_name == 'hybrid':
        return HybridSearchBackend()
    else:
        return DatabaseSearchBackend()


def build_search_query(query, filters=None):
    """Build a search query from user input and filters"""
    if not query:
        return None
    
    # Process query
    processed_query = query.strip()
    
    # Handle quoted phrases
    phrases = re.findall(r'"([^"]+)"', processed_query)
    for phrase in phrases:
        processed_query = processed_query.replace(f'"{phrase}"', '')
    
    # Extract remaining terms
    terms = [term.strip() for term in processed_query.split() if term.strip()]
    
    # Build query structure
    search_query = {
        'phrases': phrases,
        'terms': terms,
        'filters': filters or {}
    }
    
    return search_query


def rank_results(results, query, user=None):
    """Rank search results based on relevance and other factors"""
    if not results:
        return results
    
    # Calculate relevance scores
    for result in results:
        score = result.get('relevance_score', 0)
        
        # Boost exact matches
        title = result.get('title', '').lower()
        description = result.get('description', '').lower()
        query_lower = query.lower()
        
        if query_lower in title:
            score += 2.0
        if query_lower in description:
            score += 1.0
        
        # Boost based on content type
        content_type = result.get('content_type')
        if content_type == 'tutor':
            score *= 1.1
        elif content_type == 'requirement':
            score *= 1.0
        
        result['relevance_score'] = score
    
    # Sort by relevance score
    results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return results


def highlight_terms(text, terms, max_length=200):
    """Highlight search terms in text"""
    if not text or not terms:
        return text[:max_length] + ('...' if len(text) > max_length else '')
    
    highlighted_text = text
    for term in terms:
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        highlighted_text = pattern.sub(f'<mark>{term}</mark>', highlighted_text)
    
    # Truncate if too long
    if len(highlighted_text) > max_length:
        highlighted_text = highlighted_text[:max_length] + '...'
    
    return highlighted_text


def get_faceted_counts(results):
    """Get faceted counts for search results"""
    facets = {
        'content_types': {},
        'subjects': {},
        'urgency_levels': {},
        'budget_ranges': {}
    }
    
    for result in results:
        # Content type facets
        content_type = result.get('content_type')
        if content_type:
            facets['content_types'][content_type] = facets['content_types'].get(content_type, 0) + 1
        
        # Subject facets
        metadata = result.get('metadata', {})
        subject = metadata.get('subject')
        if subject:
            facets['subjects'][subject] = facets['subjects'].get(subject, 0) + 1
        
        # Urgency level facets
        urgency = metadata.get('urgency_level')
        if urgency:
            facets['urgency_levels'][urgency] = facets['urgency_levels'].get(urgency, 0) + 1
        
        # Budget range facets
        budget = metadata.get('budget_range')
        if budget:
            facets['budget_ranges'][budget] = facets['budget_ranges'].get(budget, 0) + 1
    
    return facets


def cache_search_results(query_hash, results, timeout=3600):
    """Cache search results for performance"""
    cache.set(f'search_results_{query_hash}', results, timeout)


def get_cached_search_results(query_hash):
    """Get cached search results"""
    return cache.get(f'search_results_{query_hash}')