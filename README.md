# ALX Travel App 0x02 - Chapa Payment Integration

This project is an extension of the ALX Travel App, focusing on integrating the Chapa payment gateway for handling hotel booking payments securely.

# Features

Payment Model: A dedicated model to store and track payment status.

Chapa API Integration: Securely communicate with the Chapa API for payment processing.

Payment Initiation: Endpoint to start the payment process for a booking.

Payment Verification: Endpoint to verify the status of a payment after the user interacts with the Chapa checkout page.

Environment-Based API Keys: Securely manage API credentials using environment variables.

(Optional) Asynchronous Task: Send payment confirmation emails using Celery for a non-blocking user experience.

Project Setup

1. Duplicate Project

Clone or duplicate the alx_travel_app_0x01 project into a new directory named alx_travel_app_0x02.

2. Install Dependencies

Ensure you have the necessary Python packages installed.

pip install django djangorestframework requests python-dotenv
# For Celery (optional)
pip install celery redis

3. Chapa API Credentials

Sign Up: Create an account on the Chapa Developers Portal.

Get API Keys: Navigate to the API Keys section in your dashboard to get your Secret Key for the sandbox environment.

Store API Key: Create a .env file in the root of your Django project and add your secret key:

# .env
CHAPA_SECRET_KEY=CHAPA_SECRET_KEY_HERE

Make sure to add .env to your .gitignore file to prevent committing secrets.

4. Apply Migrations

After adding the Payment model to listings/models.py, run the migrations to update your database schema.

python manage.py makemigrations listings
python manage.py migrate

Payment Workflow
Create a Booking: A user first creates a booking for a hotel. The system calculates the total price and saves the booking.

Initiate Payment: The frontend receives the booking_id and makes a POST request to the /api/initiate-payment/ endpoint.

Redirect to Chapa: The Django backend communicates with the Chapa API and receives a checkout_url. This URL is sent back to the frontend. The user is then redirected to this URL to complete the payment.

Complete Payment: The user enters their payment details on the Chapa-hosted page.

Verification: After the payment attempt, Chapa calls the callback_url you provided, which is your /api/verify-payment/ endpoint.

Update Status: The verification endpoint checks the final status with Chapa. It then updates the Payment model's status to "Completed" or "Failed".

Confirmation: If the payment is "Completed", a confirmation email is sent to the user.

API Endpoints

POST /api/bookings/: Creates a new booking.

Request Body: { "hotel_id": 1, "check_in_date": "2024-10-01", "check_out_date": "2024-10-05" }

Response: { "message": "Booking created...", "booking_id": 123 }

POST /api/initiate-payment/: Initiates the payment for a booking.

Request Body: { "booking_id": 123 }

Response: { "checkout_url": "https://checkout.chapa.co/..." }

GET /api/verify-payment/?tx_ref=<transaction_ref>: Verifies the payment status. This is typically called by Chapa.

Response: { "status": "Payment successful and verified." }

Testing the Integration

Use Chapa's sandbox environment to test the entire flow without using real money.

1. Initiate Payment
Use a tool like curl or Postman to simulate a booking and payment initiation.

# First, create a booking (ensure you are authenticated)
curl -X POST http://127.0.0.1:8000/api/bookings/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
        "hotel_id": 1,
        "check_in_date": "2024-11-15",
        "check_out_date": "2024-11-17"
      }'

# You will get a booking_id in the response. Use it here:
curl -X POST http://127.0.0.1:8000/api/initiate-payment/ \
  -H "Authorization: Token YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"booking_id": 1}'

Log/Screenshot Point 1: Successful Initiation
The response from the second command will contain the checkout_url. This confirms successful initiation.

{
  "checkout_url": "https://checkout.chapa.co/checkout/payment/..."
}

(Insert screenshot of your terminal or Postman showing this successful response here.)

2. Simulate Payment

Open the checkout_url in your browser.

Use Chapa's test card details to simulate a successful or failed payment.

3. Verify Payment

After completing the payment on the Chapa page, Chapa will attempt to contact your callback_url. Ensure your local server is accessible to the internet (using a tool like ngrok) for this to work in a live test.

Alternatively, you can manually trigger the verification by taking the tx_ref from the initiation step and making a GET request.

Log/Screenshot Point 2: Successful Verification
Check your Django server logs. You should see a GET request to /api/verify-payment/... and a successful verification message.

[25/Jul/2024 10:30:00] "GET /api/verify-payment/?tx_ref=booking-1-some-uuid HTTP/1.1" 200

(Insert screenshot of your server logs showing the 200 OK response for the verification endpoint.)

4. Check Database

Access the Django admin panel or the database shell.

Find the Payment object related to your booking. Its status should now be "Completed".

Log/Screenshot Point 3: Payment Model Updated
Query the Payment model to confirm the status update.

from listings.models import Payment
p = Payment.objects.get(booking__id=1)
print(p.status)
# Expected output: Completed
