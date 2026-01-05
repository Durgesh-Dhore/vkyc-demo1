from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('unique_id', 'name', 'mobile', 'email', 'kyc_type', 'created_on')
    list_filter = ('kyc_type', 'created_on')
    search_fields = ('unique_id', 'name', 'mobile', 'email')
    readonly_fields = ('unique_id', 'vkyc_link', 'created_on')

