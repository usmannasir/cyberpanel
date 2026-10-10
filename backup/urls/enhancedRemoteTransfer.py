from django.urls import path
from backup.views import enhancedRemoteTransfer as ert

urlpatterns = [
    # Main enhanced remote transfer page
    path('enhancedRemoteTransfer/', ert.enhanced_remote_transfer_view, name='enhanced_remote_transfer'),

    # API endpoints
    path('diskAnalysis/', ert.disk_analysis_view, name='disk_analysis'),
    path('updateRecommendations/', ert.update_recommendations_view, name='update_recommendations'),
    path('fetchRemoteAccounts/', ert.fetch_remote_accounts_view, name='fetch_remote_accounts'),
    path('startEnhancedTransfer/', ert.start_enhanced_transfer_view, name='start_enhanced_transfer'),
    path('transferProgress/', ert.transfer_progress_view, name='transfer_progress'),
    path('cancelTransfer/', ert.cancel_transfer_view, name='cancel_transfer'),
]