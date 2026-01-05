from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('customer-profiles/', views.customer_profiles, name='customer_profiles'),
    path('agents/', views.agents, name='agents'),
    path('live-monitoring/', views.live_monitoring, name='live_monitoring'),
    path('agent-meet/<int:employee_id>/<int:session_id>/', views.agent_meet, name='agent_meet'),
    path('api/create-customer/', views.create_customer, name='create_customer'),
    path('api/send-link/<int:customer_id>/', views.send_vkyc_link, name='send_vkyc_link'),
    path('api/agent/create', views.create_agent, name='create_agent'),
    path('api/agents/', views.get_agents, name='get_agents'),
    path('vkyc/<str:unique_id>/', views.vkyc_page, name='vkyc_page'),
]

