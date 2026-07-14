from datetime import datetime
from decimal import Decimal
import stripe
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from common.permissions import IsAdminUser
from ..tasks import handle_stripe_event
from django.utils.timezone import make_aware
from ..models import Invoice, PricingPlan, Subscription, CheckoutSessionLog, StripeCustomer
from client.models import Wallet, Transaction
from .serializers import (
    BillingPortalSerializer,
    SetupIntentResponseSerializer,
    ChangePlanSerializer,
    CreateCheckoutSerializer,
    InvoiceHistorySerializer,
    PauseSubscriptionSerializer,
    PricingPlanSerializer,
    AddPaymentMethodSerializer
)
from ..utils import get_or_create_stripe_customer
import logging
logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY  

User = settings.AUTH_USER_MODEL


@extend_schema(
    tags=["payment"],
)
class CreateCheckoutSession(APIView):
    serializer_class = CreateCheckoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        price_id = request.data.get("price_id")
        payment_method_id = request.data.get("payment_method_id")

        if not price_id:
            logger.error("price_id is missing in request data")
            return Response({"error": "price_id is required"}, status=400)
        
        try:
            plan = PricingPlan.objects.get(stripe_price_id=price_id)
        except PricingPlan.DoesNotExist:
            logger.error(f"PricingPlan not found for price_id: {price_id}")
            return Response({"error": "Invalid price_id"}, status=400)
        
        if Subscription.objects.filter(user=request.user, plan=plan, is_active=True).exists():
            return Response(
                {"error": "You already have an active subscription for this plan."},
                status=400
            )

        stripe_profile = get_or_create_stripe_customer(request.user)
        customer_id = stripe_profile.stripe_customer_id

        # Handle subscriptions (Monthly or Metered) and One-time payments
        if plan.billing_type in ["monthly", "metered", "one_time", "hourly"]:
            try:
                # Determine mode based on recurring vs one-time (safety check)
                is_recurring = plan.billing_type in ["monthly", "metered"]
                try:
                    stripe_price = stripe.Price.retrieve(price_id)
                    is_recurring = stripe_price.recurring is not None
                except stripe.error.InvalidRequestError as e:
                    # Catch mode mismatch (e.g. Test price in Live mode or vice versa)
                    logger.warning(f"Stripe Price ID mismatch or error for {price_id}: {str(e)}. Falling back to plan amount.")
                except Exception as e:
                    logger.warning(f"General error retrieving price {price_id}: {str(e)}")

                # If a payment method is provided, try to create the subscription (or payment) directly
                if payment_method_id:
                    logger.info(f"Creating direct {plan.billing_type} charge for user: {request.user.id} with payment_method: {payment_method_id}")
                    
                    # Ensure the payment method is attached to the customer
                    try:
                        stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)
                        stripe.Customer.modify(
                            customer_id,
                            invoice_settings={"default_payment_method": payment_method_id}
                        )
                    except Exception as e:
                        logger.warning(f"Note: Payment method attachment issue (might already be attached): {str(e)}")

                    if is_recurring:
                        # Create Subscription
                        subscription = stripe.Subscription.create(
                            customer=customer_id,
                            items=[{"price": price_id, "quantity": 1}],
                            default_payment_method=payment_method_id,
                            payment_behavior="default_incomplete",
                            expand=["latest_invoice.payment_intent"],
                            metadata={
                                "user_id": request.user.id,
                                "plan_id": plan.id,
                                "billing_type": plan.billing_type,
                            }
                        )
                        
                        payment_intent = subscription.latest_invoice.payment_intent
                        
                        if payment_intent.status == 'succeeded':
                            with transaction.atomic():
                                # Immediate fulfillment
                                invoice_id = subscription.latest_invoice.id if hasattr(subscription.latest_invoice, 'id') else f"pi_{payment_intent.id}"
                                Invoice.objects.get_or_create(
                                    stripe_invoice_id=invoice_id,
                                    defaults={
                                        "user": request.user,
                                        "billing_title": f"Subscription for {plan.name}",
                                        "status": "paid",
                                        "billing_date": timezone.now().date(),
                                        "amount": Decimal(payment_intent.amount) / Decimal(100),
                                        "currency": payment_intent.currency.upper(),
                                        "plan": plan.name,
                                        "users": 1
                                    }
                                )

                                Subscription.objects.update_or_create(
                                    user=request.user,
                                    plan=plan,
                                    defaults={
                                        "stripe_customer_id": customer_id,
                                        "stripe_subscription_id": subscription.id,
                                        "plan_name": plan.name,
                                        "is_active": True,
                                        "current_period_end": timezone.now() + timezone.timedelta(days=30),
                                        "used_hours": 0 if plan.billing_type == "metered" else None,
                                    }
                                )

                                wallet, _ = Wallet.objects.get_or_create(owner=request.user)
                                Transaction.objects.create(
                                    wallet=wallet,
                                    amount=Decimal(payment_intent.amount) / Decimal(100),
                                    transaction_type='deduction',
                                    description=f"Subscription for {plan.name} (via Card)",
                                    reference_id=payment_intent.id
                                )

                            return Response({
                                "status": "success",
                                "message": f"{plan.billing_type.capitalize()} subscription created successfully",
                                "subscription_id": subscription.id
                            })
                        elif payment_intent.status == 'requires_action':
                            return Response({
                                "status": "requires_action",
                                "client_secret": payment_intent.client_secret,
                                "subscription_id": subscription.id
                            })
                        else:
                             return Response({
                                "status": "error",
                                "error": f"Payment failed with status: {payment_intent.status}"
                            }, status=400)
                    else:
                        # One-time payment fallback
                        logger.info(f"Creating direct one-time payment for user: {request.user.id}")
                        payment_intent = stripe.PaymentIntent.create(
                            amount=plan.amount,
                            currency="usd",
                            customer=customer_id,
                            payment_method=payment_method_id,
                            off_session=True,
                            confirm=True,
                            metadata={
                                "user_id": request.user.id,
                                "plan_id": plan.id,
                                "billing_type": "one_time_fallback",
                            }
                        )

                        if payment_intent.status == 'succeeded':
                            # --- IMMEDIATE FULFILLMENT ---
                            # This ensures the user sees the update without waiting for webhooks
                            with transaction.atomic():
                                # 1. Create Invoice record
                                Invoice.objects.get_or_create(
                                    stripe_invoice_id=payment_intent.id,
                                    defaults={
                                        "user": request.user,
                                        "billing_title": f"Payment for {plan.name}",
                                        "status": "paid",
                                        "billing_date": timezone.now().date(),
                                        "amount": Decimal(payment_intent.amount) / Decimal(100),
                                        "currency": payment_intent.currency.upper(),
                                        "plan": plan.name,
                                        "users": 1
                                    }
                                )

                                existing_sub = Subscription.objects.filter(user=request.user, plan=plan).first()
                                stripe_sub_id = existing_sub.stripe_subscription_id if existing_sub and existing_sub.stripe_subscription_id else f"onetime_{payment_intent.id}"

                                # 2. Update Subscription status
                                Subscription.objects.update_or_create(
                                    user=request.user,
                                    plan=plan,
                                    defaults={
                                        "stripe_customer_id": customer_id,
                                        "stripe_subscription_id": stripe_sub_id,
                                        "plan_name": plan.name,
                                        "is_active": True,
                                        "current_period_end": timezone.now() + timezone.timedelta(days=30),
                                        "used_hours": 0 if plan.billing_type == "metered" else None,
                                    }
                                )
                            
                                # 3. Create Transaction record in Wallet History
                                # Note: This will automatically reduce the wallet balance via the Transaction.save() signal
                                wallet, _ = Wallet.objects.get_or_create(owner=request.user)
                                Transaction.objects.create(
                                    wallet=wallet,
                                    amount=Decimal(payment_intent.amount) / Decimal(100),
                                    transaction_type='deduction',
                                    description=f"Payment for {plan.name} (via Card)",
                                    reference_id=payment_intent.id
                                )
                            
                            return Response({
                                "status": "success",
                                "message": f"{plan.billing_type.capitalize()} payment successful",
                                "payment_intent_id": payment_intent.id
                            })
                        else:
                            return Response({
                                "status": "error",
                                "error": f"Payment requires secondary confirmation or failed: {payment_intent.status}"
                            }, status=400)

                # Fallback to Checkout Session
                logger.info(f"Creating Stripe checkout session for user: {request.user.id}")
                
                checkout_params = {
                    "mode": "subscription" if is_recurring else "payment",
                    "customer": customer_id,
                    "payment_method_types": ["card"],
                    "line_items": [{"price": price_id, "quantity": 1}],
                    "metadata": {
                        "user_id": request.user.id,
                        "plan_id": plan.id,
                        "billing_type": plan.billing_type,
                        "email": request.user.email,
                    },
                    "success_url": settings.STRIPE_SUCCESS_URL + "?session_id={CHECKOUT_SESSION_ID}",
                    "cancel_url": settings.STRIPE_CANCEL_URL,
                }
                
                session = stripe.checkout.Session.create(**checkout_params)
                
                CheckoutSessionLog.objects.create(
                    user=request.user,
                    plan=plan,
                    stripe_session_id=session.id,
                    status="initiated" 
                )
                return Response({"checkout_url": session.url})

            except Exception as e:
                logger.error(f"Error creating Stripe session/subscription: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Invalid billing type"}, status=400)


@csrf_exempt
def stripe_webhook(request):

    if request.method == "GET":
       return HttpResponse("pong", status=200)
    
    if request.method != "POST":
        return HttpResponse(status=405)
    
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

    if not sig_header:
        logger.error("Missing Stripe signature header")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.exception("Invalid Stripe webhook signature")
        return HttpResponse(status=400)

    
    try:
        handle_stripe_event.delay(event)  
    except Exception:
        logger.exception("Failed to enqueue Stripe event to Celery")
    return HttpResponse(status=200)








@extend_schema(
    tags=["payment"],
)
class ChangePlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        price_id = serializer.validated_data["price_id"]
        prorate = serializer.validated_data["prorate"]

        try:
            sub = request.user.subscription
        except Subscription.DoesNotExist:
            return Response({"detail": "No subscription"}, status=404)

        try:
            stripe_sub = stripe.Subscription.retrieve(sub.stripe_subscription_id)

            item_id = stripe_sub["items"]["data"][0]["id"]

            updated = stripe.Subscription.modify(
                sub.stripe_subscription_id,
                items=[
                    {
                        "id": item_id,
                        "price": price_id,
                    }
                ],
                proration_behavior="create_prorations" if prorate else "none",
            )

            sub.plan_name = (
                updated["items"]["data"][0]["plan"].get("nickname") or sub.plan_name
            )
            sub.current_period_end = timezone.datetime.fromtimestamp(
                updated["current_period_end"], tz=timezone.utc
            )
            sub.save()

            return Response({"stripe_subscription": updated})
        except Exception as e:
            return Response({"error": str(e)}, status=400)


@extend_schema(
    tags=["payment"],
)
class PauseSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PauseSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sub = request.user.subscription
        except Subscription.DoesNotExist:
            return Response({"detail": "No subscription"}, status=404)

        action = serializer.validated_data["action"]

        try:
            if action == "pause":
                body = {
                    "pause_collection": {
                        "behavior": serializer.validated_data.get(
                            "behavior", "keep_as_draft"
                        )
                    }
                }
                if "resumes_at" in serializer.validated_data:
                    resumes_at = serializer.validated_data["resumes_at"]
                    body["pause_collection"]["resumes_at"] = int(resumes_at.timestamp())
                updated = stripe.Subscription.modify(sub.stripe_subscription_id, **body)

                sub.is_active = False
                sub.save()
                return Response({"paused_subscription": updated})

            else:
                updated = stripe.Subscription.modify(
                    sub.stripe_subscription_id, pause_collection=""
                )
                sub.is_active = True
                sub.save()
                return Response({"resumed_subscription": updated})

        except Exception as e:
            return Response({"error": str(e)}, status=400)


@extend_schema(
    tags=["payment"],
)
class BillingPortalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BillingPortalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sub = request.user.subscription
        except Subscription.DoesNotExist:
            return Response({"detail": "No subscription"}, status=404)

        try:
            session = stripe.billing_portal.Session.create(
                customer=sub.stripe_customer_id,
                return_url=serializer.validated_data["return_url"],
            )
            return Response({"url": session.url})
        except Exception as e:
            return Response({"error": str(e)}, status=400)




@extend_schema(
    tags=["payment"],
)
class BillingHistoryView(ListAPIView):
    serializer_class = InvoiceHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user).order_by("-created_at")


@extend_schema(
    tags=["payment"],
)
class PricingPlanViewSet(viewsets.ModelViewSet):
    queryset = PricingPlan.objects.all()
    serializer_class = PricingPlanSerializer

    def get_permissions(self):

        if self.request.method in ("GET", "HEAD", "OPTIONS"):
            return [AllowAny()]
        return [IsAdminUser()]

    def perform_create(self, serializer):
        name = serializer.validated_data["name"]
        amount = serializer.validated_data["amount"]
        description = serializer.validated_data.get("description", "")
        product = stripe.Product.create(
            name=name,
            description=description,
        )
        price = stripe.Price.create(
            product=product.id,
            unit_amount=amount,
            currency="usd",
            recurring={"interval": "month"},
        )
        serializer.save(stripe_price_id=price.id)




@extend_schema(
    tags=["payment"],
)
class CreateStripeCustomerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        stripe_profile = get_or_create_stripe_customer(request.user)
        return Response(
            {"stripe_customer_id": stripe_profile.stripe_customer_id},
            status=status.HTTP_200_OK
        )
    
@extend_schema(tags=["payment"])
class GetStripeCustomerView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stripe_profile = get_or_create_stripe_customer(request.user)

        return Response(
            {"stripe_customer_id": stripe_profile.stripe_customer_id},
            status=status.HTTP_200_OK
        )

@extend_schema(
    tags=["payment"],
)
class AddPaymentMethodView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddPaymentMethodSerializer
    def post(self, request):
        serializer = AddPaymentMethodSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        stripe_profile  = get_or_create_stripe_customer(request.user)
        customer_id = stripe_profile.stripe_customer_id
        pm_id = serializer.validated_data["payment_method_id"]
        try:
    
            stripe.PaymentMethod.attach(pm_id, customer=customer_id)

            stripe.Customer.modify(
                customer_id,
                invoice_settings={"default_payment_method": pm_id}
            )
            stripe_profile.default_payment_method = pm_id
            stripe_profile.has_valid_payment_method = True
            stripe_profile.last_payment_failed = False
            stripe_profile.save(
                update_fields=[
                    "default_payment_method",
                    "has_valid_payment_method",
                    "last_payment_failed",
                ]
            )
        except stripe.error.InvalidRequestError as e:
            return Response(
                {
                    "error": "Invalid payment method",
                    "details": str(e),
                    "action": "Please re-add your card"
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except stripe.error.StripeError:
            return Response(
                {
                    "error": "Payment service temporarily unavailable"
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        return Response(
            {"message": "Payment method added"},
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    tags=["payment"],
)
class ListPaymentMethodsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            customer_id = request.user.stripe_profile.stripe_customer_id
        except StripeCustomer.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        pms = stripe.PaymentMethod.list(
            customer=customer_id,
            type="card"
        )

        return Response([
            {
                "id": pm.id,
                "brand": pm.card.brand,
                "last4": pm.card.last4,
                "exp_month": pm.card.exp_month,
                "exp_year": pm.card.exp_year,
            }
            for pm in pms.data
        ])


@extend_schema(
    tags=["payment"],
)
class DeletePaymentMethodView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, id):
        stripe.PaymentMethod.detach(id)
        return Response(status=status.HTTP_204_NO_CONTENT)





@extend_schema(
    tags=["payment"],
)
class CreateSetupIntent(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class=SetupIntentResponseSerializer
    def post(self, request):
        user = request.user
        
        subscription, _ = Subscription.objects.get_or_create(user=user)
        full_name = f"{user.first_name} {user.last_name}".strip()
        if not full_name:
            full_name = user.username
        if not subscription.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=full_name or user.username,
            )
            subscription.stripe_customer_id = customer.id
            subscription.save()
        else:
            customer = stripe.Customer.retrieve(subscription.stripe_customer_id)

        setup_intent = stripe.SetupIntent.create(
            customer=customer.id,
            payment_method_types=["card"],
        )

        return Response({
            "client_secret": setup_intent.client_secret,
            "customer_id": customer.id
        })
    
@extend_schema(
    tags=["payment"],
)
class SubscriptionStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Correctly check for subscriptions using the related_name 'subscriptions'
        subscription = request.user.subscriptions.filter(is_active=True).first()
        
        # If no active subscription, try to find the most recent one (even if inactive)
        if not subscription:
            subscription = request.user.subscriptions.order_by('-created_at').first()

        if not subscription or not subscription.plan_name:
            # Fallback check for one-time plan purchases in Invoice history if no subscription object exists
            # Use __iexact for case-insensitive matching
            last_invoice = Invoice.objects.filter(user=request.user, status__iexact='paid').order_by('-created_at').first()
            if last_invoice:
                return Response({
                    "is_subscribed": True,
                    "plan_name": last_invoice.plan or "Active Plan",
                    "current_period_end": None
                })
            return Response({
                "is_subscribed": False,
                "plan_name": None
            })

        # Check if subscription is truly active based on current_period_end
        is_active = subscription.is_active
        if subscription.current_period_end:
             is_active = is_active and (subscription.current_period_end > timezone.now())
        
        # For one-time plans (like 'meeting'), they might not have a current_period_end
        # but are considered 'subscribed' if the record exists and is_active is true
        is_subscribed = is_active or (subscription.plan_name is not None and subscription.is_active)

        return Response({
            "is_subscribed": is_subscribed,
            "plan_id": subscription.plan.id if subscription.plan else None,
            "plan_name": subscription.plan_name,
            "current_period_end": subscription.current_period_end
        })
