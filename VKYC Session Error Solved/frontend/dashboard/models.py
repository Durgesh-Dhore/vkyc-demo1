from django.db import models

# Note: We're using the same database as FastAPI backend
# These models are for Django admin integration
# The actual models are defined in backend/models.py

class Customer(models.Model):
    id = models.AutoField(primary_key=True)
    unique_id = models.CharField(max_length=100, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    vkyc_link = models.TextField(blank=True, null=True)
    kyc_type = models.CharField(max_length=10, default='VKYC')
    created_on = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'customers'
        managed = False  # Don't manage this table, it's managed by FastAPI
    
    def __str__(self):
        return f"{self.name} ({self.unique_id})"

