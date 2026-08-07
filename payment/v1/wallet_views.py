from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
import stripe
from django.conf import settings
from common.response import CustomJSONRenderer
from client.models import Wallet, Transaction, Project
from client.v1.serializers.dashboard import WalletSerializer, TransactionSerializer
from payment.models import PricingPlan, Subscription
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)
stripe.api_key = settings.STRIPE_SECRET_KEY

class WalletBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(owner=request.user)
        serializer = WalletSerializer(wallet)
        return Response(serializer.data)

class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(owner=request.user)
        transactions = wallet.transactions.all().order_by('-date')
        
        # Simple pagination or just return all for now as per current frontend expectation
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

class TopUpView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        amount = request.data.get('amount')
        payment_method_id = request.data.get('payment_method_id')
        success_url = request.data.get('success_url', settings.STRIPE_SUCCESS_URL)
        cancel_url = request.data.get('cancel_url', settings.STRIPE_CANCEL_URL)
        
        if not amount:
            return Response({"error": "Amount is required"}, status=400)
        
        try:
            amount_cents = int(float(amount) * 100)
            
            if payment_method_id:
                from ..utils import get_or_create_stripe_customer
                stripe_customer = get_or_create_stripe_customer(request.user)
                
                # Create a direct PaymentIntent using the saved card
                intent = stripe.PaymentIntent.create(
                    amount=amount_cents,
                    currency='usd',
                    customer=stripe_customer.stripe_customer_id,
                    payment_method=payment_method_id,
                    confirm=True,
                    off_session=False, # User is present to handle potential 3D Secure
                    return_url=success_url,
                    metadata={
                        'user_id': request.user.id,
                        'type': 'top_up',
                        'amount': amount
                    }
                )
                
                if intent.status == 'succeeded':
                    # Create transaction which also updates wallet balance
                    Transaction.objects.create(
                        wallet=stripe_customer.user.wallet,
                        amount=Decimal(amount),
                        transaction_type='top_up',
                        description="Wallet Top-up via Saved Card",
                        reference_id=intent.id
                    )
                    
                    # Send branded wallet top-up email (21-wallet-topup)
                    try:
                        from admin_portal.orr_email_service import ORREmailService
                        ORREmailService.send_wallet_topup(
                            recipient_email=request.user.email,
                            transaction_id=intent.id,
                            added_amount=str(amount),
                            currency_symbol='$',
                            new_balance=str(stripe_customer.user.wallet.balance),
                            wallet_url='https://orr.solutions/wallet',
                        )
                    except Exception as email_err:
                        logger.error(f"Failed to send wallet top-up email: {email_err}")
                        
                    return Response({
                        "status": "success",
                        "message": "Top-up completed successfully"
                    })
                elif intent.status == 'requires_action':
                    return Response({
                        "status": "requires_action",
                        "client_secret": intent.client_secret
                    })
                else:
                    return Response({
                        "status": "error",
                        "error": f"Payment failed with status: {intent.status}"
                    }, status=400)
                    
            # If no saved card, use Stripe Checkout
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Wallet Top-up',
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata={
                    'user_id': request.user.id,
                    'type': 'top_up',
                    'amount': amount
                }
            )
            return Response({"checkout_url": session.url})
        except Exception as e:
            logger.error(f"Top-up error: {str(e)}")
            return Response({"error": str(e)}, status=400)

class PayWithWalletView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        invoice_id = request.data.get('invoice_id') or request.data.get('plan_id')
        if not invoice_id:
            return Response({"error": "Invoice ID or Plan ID is required"}, status=400)

        wallet, _ = Wallet.objects.get_or_create(owner=request.user)

        # 1. Check if paying an existing Invoice
        inv = Invoice.objects.filter(Q(id=invoice_id) | Q(stripe_invoice_id=str(invoice_id)), user=request.user).first()
        if inv:
            if inv.status == 'paid':
                return Response({"status": "success", "message": "Invoice is already paid"})
            if wallet.balance < inv.amount:
                return Response({"error": f"Insufficient wallet balance. Balance: ${wallet.balance}, Invoice: ${inv.amount}"}, status=400)

            Transaction.objects.create(
                wallet=wallet,
                amount=inv.amount,
                transaction_type='deduction',
                description=f"Payment for Invoice #{inv.stripe_invoice_id}"
            )
            inv.status = 'paid'
            inv.save()

            try:
                from admin_portal.orr_email_service import ORREmailService
                ORREmailService.send_invoice_paid(
                    recipient_email=request.user.email,
                    invoice_id=inv.stripe_invoice_id,
                    total_amount=f"USD {inv.amount}",
                    receipt_url=f"https://orr.solutions/account/invoices/{inv.id}"
                )
            except Exception as e:
                logger.error(f"Failed to send invoice paid email: {e}")

            return Response({
                "status": "success",
                "message": "Invoice paid successfully via wallet"
            })

        # 2. Fallback: PricingPlan subscription payment
        try:
            plan = PricingPlan.objects.get(id=invoice_id)
            plan_amount = Decimal(plan.amount) / Decimal(100)
            
            if wallet.balance < plan_amount:
                return Response({"error": "Insufficient wallet balance"}, status=400)
            
            Transaction.objects.create(
                wallet=wallet,
                amount=plan_amount,
                transaction_type='deduction',
                description=f"Payment for {plan.name} plan"
            )
            
            import uuid
            existing_sub = Subscription.objects.filter(user=request.user, plan=plan).first()
            stripe_sub_id = existing_sub.stripe_subscription_id if existing_sub and existing_sub.stripe_subscription_id else f"wallet_sub_{uuid.uuid4().hex[:16]}"

            Subscription.objects.update_or_create(
                user=request.user,
                plan=plan,
                defaults={
                    'stripe_subscription_id': stripe_sub_id,
                    'plan_name': plan.name,
                    'is_active': True,
                    'current_period_end': timezone.now() + timezone.timedelta(days=30)
                }
            )

            # Create Invoice
            from payment.models import Invoice
            from django.utils import timezone
            
            Invoice.objects.create(
                user=request.user,
                stripe_invoice_id=f"wallet_inv_{uuid.uuid4().hex[:16]}",
                billing_title=f"Payment for {plan.name}",
                status="paid",
                billing_date=timezone.now().date(),
                amount=plan_amount,
                currency="USD",
                plan=plan.name,
                users=1
            )
            
            return Response({"message": "Payment successful, subscription activated"}, status=200)
            
        except PricingPlan.DoesNotExist:
            return Response({"error": "Invalid plan"}, status=400)
        except Exception as e:
            logger.error(f"Wallet payment error: {str(e)}")
            return Response({"error": str(e)}, status=400)
