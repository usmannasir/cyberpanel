from django.urls import path
from . import views, api, scheduled_views

urlpatterns = [
    # Main AI Scanner pages
    path('', views.aiScannerHome, name='aiScannerHome'),
    path('setup-payment/', views.setupPayment, name='aiScannerSetupPayment'),
    path('setup-complete/', views.setupComplete, name='aiScannerSetupComplete'),
    path('start-scan/', views.startScan, name='aiScannerStartScan'),
    path('refresh-balance/', views.refreshBalance, name='aiScannerRefreshBalance'),
    path('add-payment-method/', views.addPaymentMethod, name='aiScannerAddPaymentMethod'),
    path('payment-method-complete/', views.paymentMethodComplete, name='aiScannerPaymentMethodComplete'),
    
    # Scan management
    path('scan-history/', views.getScanHistory, name='aiScannerHistory'),
    path('scan-details/<str:scan_id>/', views.getScanDetails, name='aiScannerDetails'),
    path('platform-monitor-url/<str:scan_id>/', views.getPlatformMonitorUrl, name='aiScannerPlatformMonitorUrl'),
    path('platform-status/<str:scan_id>/', views.getPlatformScanStatus, name='aiScannerPlatformStatus'),
    
    # Scheduled scans management
    path('scheduled-scans/', scheduled_views.scheduledScans, name='aiScannerScheduledScans'),
    path('scheduled-scans/<int:scan_id>/', scheduled_views.scheduledScanDetail, name='aiScannerScheduledScanDetail'),
    path('scheduled-scans/<int:scan_id>/toggle/', scheduled_views.toggleScheduledScan, name='aiScannerToggleScheduledScan'),
    path('scheduled-scans/<int:scan_id>/executions/', scheduled_views.scheduledScanExecutions, name='aiScannerScheduledScanExecutions'),

    # Note: the endpoints the scanner platform calls are in /api/urls.py
]