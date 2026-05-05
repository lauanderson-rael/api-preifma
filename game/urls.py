from django.urls import path
from .views import (
    SessionStartView,
    SessionDetailView,
    SessionAnswerView,
    SessionFinishView,
    SessionHistoryView,
    SubjectProgressView,
    DailyMissionsView,
    MissionClaimView,
    AchievementListView,
    UserAchievementListView,
    DashboardView,
)

urlpatterns = [
    path('sessions/start/', SessionStartView.as_view(), name='session-start'),
    path('sessions/history/', SessionHistoryView.as_view(), name='session-history'),
    path('sessions/<int:pk>/', SessionDetailView.as_view(), name='session-detail'),
    path('sessions/<int:pk>/answers/', SessionAnswerView.as_view(), name='session-answers'),
    path('sessions/<int:pk>/finish/', SessionFinishView.as_view(), name='session-finish'),

    path('progress/subjects/', SubjectProgressView.as_view(), name='subject-progress'),
 
    path('missions/daily/', DailyMissionsView.as_view(), name='missions-daily'),
    path('missions/<int:pk>/claim/', MissionClaimView.as_view(), name='mission-claim'),
   
    path('achievements/', AchievementListView.as_view(), name='achievements'),
    path('achievements/user/', UserAchievementListView.as_view(), name='user-achievements'),

    path('dashboard/', DashboardView.as_view(), name='dashboard'),
]
