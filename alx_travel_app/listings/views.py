import os
import requests
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Booking, Payment, Hotel
from .serializers import BookingSerializer 
# Make sure to create a tasks.py file in your app for Celery tasks
# from .tasks import send_payment_confirmation_email 

class InitiatePaymentView(APIView):
    """
    API View to initiate a payment with Chapa.
    Expects a 'booking_id' in the request data.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        booking_id = request.data.get('booking_id')
        if not booking_id:
            return Response({"error": "Booking ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({"error": "Booking not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

        # Create or get the payment object
        payment, created = Payment.objects.get_or_create(
            booking=booking,
            defaults={'amount': booking.total_price}
        )

        # Chapa API details
        chapa_secret_key = os.getenv("CHAPA_SECRET_KEY")
        if not chapa_secret_key:
            return Response(
                {"error": "Chapa API key is not configured."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        headers = {
            "Authorization": f"Bearer {chapa_secret_key}",
            "Content-Type": "application/json"
        }

        # Unique transaction reference
        tx_ref = f"booking-{booking.id}-{payment.reference}"

        # Update payment with the transaction_id
        payment.transaction_id = tx_ref
        payment.save()

        payload = {
            "amount": str(booking.total_price),
            "currency": "ETB",
            "email": request.user.email,
            "first_name": request.user.first_name or "User",
            "last_name": request.user.last_name or "Name",
            "tx_ref": tx_ref,
            "callback_url": f"http://your-domain.com/api/verify-payment/", # Replace with your verification URL
            "return_url": "http://your-frontend-domain.com/payment-success/", # Replace with your frontend success URL
            "customization[title]": "Payment for Hotel Booking",
            "customization[description]": f"Booking for {booking.hotel.name}"
        }

        try:
            chapa_response = requests.post(
                "https://api.chapa.co/v1/transaction/initialize",
                json=payload,
                headers=headers
            )
            chapa_response.raise_for_status()
            response_data = chapa_response.json()

            if response_data.get("status") == "success":
                checkout_url = response_data["data"]["checkout_url"]
                return Response({"checkout_url": checkout_url}, status=status.HTTP_200_OK)
            else:
                payment.status = 'Failed'
                payment.save()
                return Response(
                    {"error": "Failed to initiate payment with Chapa.", "details": response_data},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except requests.exceptions.RequestException as e:
            payment.status = 'Failed'
            payment.save()
            return Response(
                {"error": f"An error occurred while communicating with Chapa: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyPaymentView(APIView):
    """
    API View to verify a payment with Chapa.
    Chapa will redirect to this view's URL (or send a webhook) after a payment attempt.
    """
    def get(self, request, *args, **kwargs):
        transaction_ref = request.GET.get('tx_ref')

        if not transaction_ref:
            return Response({"error": "Transaction reference is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(transaction_id=transaction_ref)
        except Payment.DoesNotExist:
            return Response({"error": "Payment record not found."}, status=status.HTTP_404_NOT_FOUND)

        chapa_secret_key = os.getenv("CHAPA_SECRET_KEY")
        headers = {"Authorization": f"Bearer {chapa_secret_key}"}

        try:
            chapa_response = requests.get(
                f"https://api.chapa.co/v1/transaction/verify/{transaction_ref}",
                headers=headers
            )
            chapa_response.raise_for_status()
            response_data = chapa_response.json()

            if response_data.get("status") == "success":
                payment.status = 'Completed'
                payment.save()
                
                # Trigger confirmation email via Celery
                # send_payment_confirmation_email.delay(payment.id)
                
                # You can redirect the user to a success page here
                return Response({"status": "Payment successful and verified."}, status=status.HTTP_200_OK)
            else:
                payment.status = 'Failed'
                payment.save()
                return Response(
                    {"status": "Payment verification failed.", "details": response_data},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except requests.exceptions.RequestException as e:
            return Response(
                {"error": f"An error occurred while verifying the payment: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Example BookingView to tie everything together
class BookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # A simplified booking creation process
        hotel_id = request.data.get('hotel_id')
        check_in = request.data.get('check_in_date')
        check_out = request.data.get('check_out_date')

        if not all([hotel_id, check_in, check_out]):
            return Response({"error": "Hotel, check-in, and check-out dates are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        hotel = get_object_or_404(Hotel, id=hotel_id)
        
        # Simplified price calculation
        from datetime import datetime
        days = (datetime.strptime(check_out, "%Y-%m-%d") - datetime.strptime(check_in, "%Y-%m-%d")).days
        total_price = hotel.price_per_night * days

        booking_data = {
            "user": request.user.id,
            "hotel": hotel.id,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "total_price": total_price
        }

        serializer = BookingSerializer(data=booking_data)
        if serializer.is_valid():
            booking = serializer.save()
            # After creating the booking, you can immediately call the initiate payment logic
            # or return the booking ID to the frontend to do it in a separate step.
            return Response({
                "message": "Booking created successfully. Please proceed to payment.",
                "booking_id": booking.id
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
