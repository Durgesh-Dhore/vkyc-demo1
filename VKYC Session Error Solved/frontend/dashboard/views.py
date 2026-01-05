from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import requests
import json
from django.conf import settings

BACKEND_API = settings.BACKEND_API_URL

def index(request):
    """Dashboard home"""
    return render(request, 'dashboard/index.html')

def customer_profiles(request):
    """Customer Profiles page"""
    customers = []
    error_message = None
    try:
        response = requests.get(f"{BACKEND_API}/api/customers", timeout=5)
        if response.status_code == 200:
            customers = response.json()
        else:
            error_message = f"Backend returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        error_message = f"Could not connect to backend at {BACKEND_API}. Make sure the FastAPI backend is running on port 8001."
    except Exception as e:
        error_message = f"Error: {str(e)}"
    
    return render(request, 'dashboard/customer_profiles.html', {
        'customers': customers,
        'error_message': error_message
    })

def agents(request):
    """Agents page"""
    agents_list = []
    error_message = None
    try:
        response = requests.get(f"{BACKEND_API}/api/agents", timeout=5)
        if response.status_code == 200:
            agents_list = response.json()
        else:
            error_message = f"Backend returned status {response.status_code}"
    except requests.exceptions.ConnectionError:
        error_message = f"Could not connect to backend at {BACKEND_API}. Make sure the FastAPI backend is running on port 8001."
    except Exception as e:
        error_message = f"Error: {str(e)}"
    
    return render(request, 'dashboard/agents.html', {
        'agents': agents_list,
        'error_message': error_message
    })

def live_monitoring(request):
    """Live Monitoring page"""
    return render(request, 'dashboard/live_monitoring.html')


def agent_meet(request, session_id, employee_id):
    """Agent meet view (meet-style window)"""
    return render(request, 'dashboard/agent_meet.html', {
        'employee_id': employee_id,
        'session_id': session_id
    })

def vkyc_page(request, unique_id):
    """
    VKYC page that loads template and passes unique_id
    """
    return render(request, 'vkyc/vkyc_page.html', {"unique_id": unique_id})

@csrf_exempt
def create_customer(request):
    """Create a new customer"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            response = requests.post(
                f"{BACKEND_API}/api/customers/create",
                json=data,
                timeout=10
            )
            return JsonResponse(response.json(), status=response.status_code)
        except requests.exceptions.ConnectionError:
            return JsonResponse({
                'error': f'Cannot connect to backend at {BACKEND_API}. Please start the FastAPI backend server.'
            }, status=503)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def send_vkyc_link(request, customer_id):
    """Send VKYC link via SMS and Email"""
    if request.method == 'POST':
        try:
            response = requests.post(
                f"{BACKEND_API}/api/customers/{customer_id}/send-link",
                timeout=10
            )
            return JsonResponse(response.json(), status=response.status_code)
        except requests.exceptions.ConnectionError:
            return JsonResponse({
                'error': f'Cannot connect to backend at {BACKEND_API}. Please start the FastAPI backend server.'
            }, status=503)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def create_agent(request):
    """Create a new agent"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            response = requests.post(
                f"{BACKEND_API}/api/agents/create",
                json=data,
                timeout=10
            )
            return JsonResponse(response.json(), status=response.status_code)
        except requests.exceptions.ConnectionError:
            return JsonResponse({
                'error': f'Cannot connect to backend at {BACKEND_API}. Please start the FastAPI backend server.'
            }, status=503)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def get_agents(request):
    """Get all agents"""
    if request.method == 'GET':
        try:
            response = requests.get(f"{BACKEND_API}/api/agents", timeout=10)
            
            # Check if response is JSON
            try:
                data = response.json()
            except ValueError:
                # Response is not JSON (might be HTML error page)
                return JsonResponse({
                    'error': f'Backend returned invalid response (status {response.status_code}). Make sure the FastAPI backend is running on port 8000.'
                }, status=503)
            
            # Return the data
            if response.status_code == 200:
                return JsonResponse(data, safe=False)
            else:
                # Backend returned an error
                error_msg = data.get('detail', data.get('error', f'Backend returned status {response.status_code}'))
                return JsonResponse({'error': error_msg}, status=response.status_code)
                
        except requests.exceptions.ConnectionError:
            return JsonResponse({
                'error': f'Cannot connect to backend at {BACKEND_API}. Please start the FastAPI backend server.'
            }, status=503)
        except requests.exceptions.Timeout:
            return JsonResponse({
                'error': 'Request to backend timed out. Please try again.'
            }, status=504)
        except Exception as e:
            return JsonResponse({'error': f'Error: {str(e)}'}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

