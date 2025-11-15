from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    # Search views
    path('', views.GlobalSearchView.as_view(), name='global'),
    path('results/<int:pk>/', views.SearchResultsView.as_view(), name='results'),
    path('tutors/', views.TutorSearchView.as_view(), name='tutors'),
    path('requirements/', views.RequirementSearchView.as_view(), name='requirements'),
    path('advanced/', views.AdvancedSearchView.as_view(), name='advanced'),
    
    # Saved searches
    path('saved/', views.SavedSearchesView.as_view(), name='saved_searches'),
    path('saved/new/', views.SaveSearchFilterView.as_view(), name='save_filter'),
    path('saved/<int:pk>/delete/', views.DeleteSearchFilterView.as_view(), name='delete_saved'),
    
    # Search analytics
    path('analytics/', views.SearchAnalyticsView.as_view(), name='analytics'),
    
    # Auto-complete endpoints
    path('autocomplete/', views.SearchAutocompleteView.as_view(), name='autocomplete'),
]