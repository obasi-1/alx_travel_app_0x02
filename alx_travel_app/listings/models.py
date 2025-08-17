from django.db import models
import uuid

class Hotel(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField()
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    image_url = models.URLField()

    def __str__(self):
        return self.name

class Booking(models.Model):
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    hotel = models.ForeignKey(Hotel, on_delete=models.CASCADE)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking for {self.hotel.name} by {self.user.username}"

class Payment(models.Model):
    """
    Model to store payment information for bookings.
    """
    PAYMENT_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    reference = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='Pending')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=255, blank=True, null=True, help_text="Chapa's transaction reference")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Payment for Booking {self.booking.id} - {self.status}"

