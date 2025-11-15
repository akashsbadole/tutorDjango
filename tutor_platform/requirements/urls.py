from django.urls import path
from . import views

app_name = 'requirements'

urlpatterns = [
    # Requirement URLs
    path('', views.RequirementListView.as_view(), name='list'),
    path('create/', views.RequirementCreateView.as_view(), name='create'),
    path('<slug:slug>/', views.RequirementDetailView.as_view(), name='detail'),
    path('<slug:slug>/edit/', views.RequirementUpdateView.as_view(), name='edit'),
    
    # Proposal URLs
    path('proposal/', views.ProposalListView.as_view(), name='proposal-list'),
    path('<slug:slug>/propose/', views.ProposalCreateView.as_view(), name='propose'),
    path('proposal/<int:proposal_id>/', views.ProposalDetailView.as_view(), name='proposal-detail'),
    path('proposal/<int:proposal_id>/withdraw/', views.withdraw_proposal, name='proposal-withdraw'),
    
    # Award URLs
    path('award/create/<int:proposal_id>/', views.AwardCreateView.as_view(), name='award-create'),
    
    # Session URLs
    path('session/', views.SessionListView.as_view(), name='session-list'),
    path('session/create/<int:award_id>/', views.SessionCreateView.as_view(), name='session-create'),
    
    # Review URLs
    path('review/create/<int:award_id>/', views.ReviewCreateView.as_view(), name='review-create'),
    
    # Utility URLs
    path('save/<slug:slug>/', views.save_requirement, name='save'),
    path('favorite/<int:tutor_id>/', views.favorite_tutor, name='favorite-tutor'),
]