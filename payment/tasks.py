from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils.timezone import make_aware
from django.utils import timezone
import stripe

from .models import (
    User,
    PricingPlan,
    Subscription,
    CheckoutSessionLog,
    Invoice,
    StripeEvent,
    StripeCustomer,
)
from client.models import Wallet, Transaction
from admin_portal.payment_ticket_service import PaymentTicketService
from django.db import IntegrityError

logger = get_task_logger(__name__)


@shared_task(bind=True, max_retries=4, default_retry_delay=10)
def handle_stripe_event(self, event: dict):
    """
    Unified Stripe webhook handler with strict idempotency and retry safety.
    """

    event_id = event.get("id")
    event_type = event.get("type")

    if not event_id or not event_type:
        logger.error("Stripe event missing id or type")
        return

    data = event.get("data", {}).get("object", {}) or {}
    session_id = data.get("id") if event_type.startswith("checkout.session") else None

    logger.info("Processing Stripe event: %s", event_type)

    with transaction.atomic():
        try:
            with transaction.atomic():
                StripeEvent.objects.create(
                    event_id=event_id,
                    event_type=event_type,
                )
        except IntegrityError:
            logger.info("Duplicate Stripe event ignored: %s", event_id)
            return


        try:
            # -------------------------------
            # CHECKOUT COMPLETED
            # -------------------------------
            if event_type == "checkout.session.completed":
                if session_id:
                    CheckoutSessionLog.objects.filter(
                        stripe_session_id=session_id
                    ).update(status="completed")

                metadata = data.get("metadata") or {}
                user_id = metadata.get("user_id")
                plan_id = metadata.get("plan_id")
                billing_type = metadata.get("billing_type")

                subscription_id = data.get("subscription")
                customer_id = data.get("customer")

                if not (user_id and subscription_id):
                    logger.error("checkout.session.completed missing metadata")
                    raise ValueError("Missing metadata")

                user = User.objects.get(id=int(user_id))
                
                # Check if it's a Wallet Top-up
                if metadata.get('type') == 'top_up':
                    # Use session_id as reference_id for idempotency
                    if Transaction.objects.filter(reference_id=session_id).exists():
                        logger.info("Top-up transaction already processed for session: %s", session_id)
                        return
                        
                    amount = Decimal(metadata.get('amount', 0))
                    wallet, created = Wallet.objects.get_or_create(owner=user)
                    
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=amount,
                        transaction_type='payment',
                        description="Wallet Top-up via Stripe Checkout",
                        reference_id=session_id
                    )
                    logger.info("Wallet credited for user %s: %s", user.id, amount)

                    # Send branded wallet top-up email (21-wallet-topup)
                    try:
                        from admin_portal.orr_email_service import ORREmailService
                        ORREmailService.send_wallet_topup(
                            recipient_email=user.email,
                            transaction_id=session_id,
                            added_amount=str(amount),
                            currency_symbol='$',
                            new_balance=str(wallet.balance),
                            wallet_url='https://orr.solutions/wallet',
                        )
                    except Exception as email_err:
                        logger.error("Failed to send wallet top-up email: %s", email_err)
                    return

                plan = PricingPlan.objects.filter(id=int(plan_id)).first()

                sub = stripe.Subscription.retrieve(subscription_id)
                period_end = sub.get("current_period_end")
                current_period_end = (
                    make_aware(datetime.fromtimestamp(period_end))
                    if period_end else None
                )

                item = sub["items"]["data"][0]
                subscription_item_id = item["id"]

                Subscription.objects.update_or_create(
                    user=user,
                    defaults={
                        "stripe_subscription_id": subscription_id,
                        "stripe_customer_id": customer_id,
                        "stripe_subscription_item_id": subscription_item_id,
                        "plan": plan,
                        "plan_name": plan.name if plan else "Unknown Plan",
                        "is_active": True,
                        "current_period_end": current_period_end,
                        "used_hours": 0 if billing_type == "metered" else None,
                    },
                )
                logger.info("Subscription activated: %s", subscription_id)

                # Send branded payment success email (16-payment-success)
                try:
                    from admin_portal.orr_email_service import ORREmailService
                    ORREmailService.send_payment_success(
                        recipient_email=user.email,
                        invoice_id=session_id or 'N/A',
                        amount_paid=str(plan.price) if plan else '0.00',
                        currency_symbol='$',
                        payment_date=timezone.now().strftime('%B %d, %Y'),
                        payment_method='Stripe',
                        invoice_url=data.get('hosted_invoice_url', 'https://orr.solutions/billing'),
                    )
                except Exception as email_err:
                    logger.error("Failed to send payment success email: %s", email_err)
                return

            # -------------------------------
            # SUBSCRIPTION CREATED / UPDATED
            # -------------------------------
            if event_type in (
                "customer.subscription.created",
                "customer.subscription.updated",
            ):
                subscription_id = data.get("id")
                status = data.get("status")
                period_end = data.get("current_period_end")

                current_period_end = (
                    make_aware(datetime.fromtimestamp(period_end))
                    if period_end else None
                )

                is_active = status in ("active", "trialing")

                updated = Subscription.objects.filter(
                    stripe_subscription_id=subscription_id
                ).update(
                    is_active=is_active,
                    current_period_end=current_period_end,
                )

                if not updated:
                    logger.warning(
                        "Subscription %s not found yet, retrying", subscription_id
                    )
                    raise self.retry(countdown=10)
                return

            # -------------------------------
            # PAYMENT INTENT SUCCEEDED (Direct Top-ups or Plan Purchases)
            # -------------------------------
            if event_type == "payment_intent.succeeded":
                metadata = data.get("metadata") or {}
                payment_intent_id = data.get("id")
                user_id = metadata.get("user_id")
                
                if not payment_intent_id or not user_id:
                    logger.error("payment_intent.succeeded missing identifiers")
                    return

                # Idempotency check
                if Transaction.objects.filter(reference_id=payment_intent_id).exists() or \
                   Invoice.objects.filter(stripe_invoice_id=payment_intent_id).exists():
                    logger.info("Transaction already processed for intent: %s", payment_intent_id)
                    return

                user = User.objects.get(id=int(user_id))
                
                # Case 1: Wallet Top-up
                if metadata.get('type') == 'top_up':
                    amount = Decimal(metadata.get("amount", 0))
                    wallet, created = Wallet.objects.get_or_create(owner=user)
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=amount,
                        transaction_type='top_up',
                        description="Wallet Top-up via Saved Card",
                        reference_id=payment_intent_id
                    )
                    logger.info("Wallet credited via Direct Payment for user %s: %s", user.id, amount)
                
                # Case 2: Plan Purchase (Fallback/One-click)
                elif metadata.get('plan_id'):
                    plan_id = metadata.get('plan_id')
                    plan = PricingPlan.objects.get(id=int(plan_id))
                    amount = Decimal(data.get("amount", 0)) / Decimal(100)
                    
                    # Create Invoice record for billing history
                    Invoice.objects.create(
                        user=user,
                        stripe_invoice_id=payment_intent_id,
                        billing_title=f"Payment for {plan.name}",
                        status="paid",
                        billing_date=timezone.now().date(),
                        amount=amount,
                        currency=(data.get("currency") or "USD").upper(),
                        plan=plan.name,
                        users=1
                    )
                    
                    existing_sub = Subscription.objects.filter(user=user, plan=plan).first()
                    stripe_sub_id = existing_sub.stripe_subscription_id if existing_sub and existing_sub.stripe_subscription_id else f"onetime_{payment_intent_id}"

                    # Activate/Update Subscription
                    Subscription.objects.update_or_create(
                        user=user,
                        plan=plan,
                        defaults={
                            "stripe_customer_id": data.get("customer", ""),
                            "stripe_subscription_id": stripe_sub_id,
                            "plan_name": plan.name,
                            "is_active": True,
                            "current_period_end": timezone.now() + timezone.timedelta(days=30), # Default for one-time
                            "used_hours": 0 if plan.billing_type == "metered" else None,
                        },
                    )
                    logger.info("Subscription/Invoice recorded for plan %s via Direct Payment", plan_id)
                return

            # -------------------------------
            # INVOICE EVENTS
            # -------------------------------
            if event_type in (
                "invoice.paid",
                "invoice.payment_failed",
            ):
                normalized_event = "payment_succeeded" if event_type == "invoice.paid" else "payment_failed"

                invoice_id = data.get("id")
                customer_id = data.get("customer")
                subscription_id = (
                    data.get("subscription")
                    or data.get("lines", {})
                        .get("data", [{}])[0]
                        .get("subscription")
                )

                if not invoice_id or not subscription_id:
                    logger.error("Invoice event missing identifiers")
                    raise ValueError("Missing identifiers")

                if Invoice.objects.filter(stripe_invoice_id=invoice_id).exists():
                    logger.info("Duplicate invoice ignored: %s", invoice_id)
                    return

                subscription = Subscription.objects.filter(
                    stripe_subscription_id=subscription_id
                ).first()

                if not subscription:
                    raise self.retry(countdown=20, max_retries=4)
                stripe_profile = StripeCustomer.objects.filter(
                    stripe_customer_id=customer_id
                ).first()

                if not stripe_profile:
                    stripe_profile = StripeCustomer.objects.filter(user=subscription.user).first()
                    
                    if stripe_profile:
                        # 2. If found, UPDATE the existing profile with the new customer ID
                        stripe_profile.stripe_customer_id = customer_id
                        stripe_profile.save(update_fields=['stripe_customer_id'])
                    else:
                        stripe_profile = StripeCustomer.objects.create(
                            user=subscription.user,
                            stripe_customer_id=customer_id,
                            last_payment_failed=False,
                        )
                if normalized_event == "payment_succeeded":
                    subscription.is_active = True
                    stripe_profile.last_payment_failed = False

                elif normalized_event == "payment_failed":
                    subscription.is_active = False
                    stripe_profile.last_payment_failed = True

                subscription.save(update_fields=["is_active"])
                stripe_profile.save(update_fields=["last_payment_failed"])

                # Send branded payment email (16 or 17)
                try:
                    from admin_portal.orr_email_service import ORREmailService
                    amount_display = str(Decimal(int(data.get('amount_due') or data.get('total') or 0)) / Decimal(100))
                    currency = (data.get('currency') or 'USD').upper()
                    currency_symbol = '€' if currency == 'EUR' else '$'

                    if normalized_event == 'payment_succeeded':
                        ORREmailService.send_payment_success(
                            recipient_email=subscription.user.email,
                            invoice_id=invoice_id,
                            amount_paid=amount_display,
                            currency_symbol=currency_symbol,
                            payment_date=timezone.now().strftime('%B %d, %Y'),
                            payment_method='Stripe',
                            invoice_url=data.get('hosted_invoice_url', 'https://orr.solutions/billing'),
                        )
                    else:
                        ORREmailService.send_payment_failed(
                            recipient_email=subscription.user.email,
                            invoice_id=invoice_id,
                            failure_reason=data.get('last_payment_error', {}).get('message', 'Payment could not be processed.'),
                            update_payment_url='https://orr.solutions/billing',
                        )
                except Exception as email_err:
                    logger.error("Failed to send payment email: %s", email_err)

                amount_cents = int(data.get("amount_due") or data.get("total") or 0)
                amount = Decimal(amount_cents) / Decimal(100)

                created_ts = data.get("created")
                billing_date = (
                    make_aware(datetime.fromtimestamp(created_ts)).date()
                    if created_ts else None
                )

                line = data.get("lines", {}).get("data", [{}])[0]
                description = (
                    line.get("description")
                    or line.get("plan", {}).get("nickname")
                    or "Subscription"
                )

                Invoice.objects.update_or_create(
                    stripe_invoice_id=invoice_id,
                    defaults={
                        "user": subscription.user,
                        "billing_title": f"Invoice for {description}",
                        "status": data.get("status"),
                        "billing_date": billing_date,
                        "amount": amount,
                        "currency": (data.get("currency") or "").upper(),
                        "plan": description,
                        "invoice_pdf": data.get("invoice_pdf"),
                        "hosted_invoice_url": data.get("hosted_invoice_url"),
                        "users": 1,
                    },
                )

                logger.info("Invoice processed: %s", invoice_id)
                return

            # -------------------------------
            # SETUP INTENT
            # -------------------------------
            if event_type == "setup_intent.succeeded":
                customer_id = data.get("customer")
                payment_method_id = data.get("payment_method")

                subscription = Subscription.objects.filter(
                    stripe_customer_id=customer_id
                ).first()

                if subscription:
                    subscription.default_payment_method = payment_method_id
                    subscription.save(update_fields=["default_payment_method"])

                    stripe.Customer.modify(
                        customer_id,
                        invoice_settings={
                            "default_payment_method": payment_method_id
                        },
                    )
                return

            # -------------------------------
            # SUBSCRIPTION DELETED
            # -------------------------------
            if event_type == "customer.subscription.deleted":
                subscription_id = data.get("id")

                subscription = Subscription.objects.filter(
                    stripe_subscription_id=subscription_id
                ).first()

                if not subscription:
                    return

                if subscription.is_active:
                    PaymentTicketService.create_subscription_cancelled_ticket(
                        subscription
                    )
                    subscription.is_active = False
                    subscription.save(update_fields=["is_active"])
                return

            logger.debug("Unhandled Stripe event type: %s", event_type)

        except Exception as exc:
            raise self.retry(exc=exc, countdown=10, max_retries=4)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
)
def deactivate_expired_subscriptions(self):
    now = timezone.now()

    subs = Subscription.objects.filter(
        is_active=True,
        current_period_end__isnull=False,
        current_period_end__lte=now,
    )

    count = 0
    for sub in subs.select_related("user"):
        from ..services.subscriptions.deactivate_sub import deactivate_subscription

        if deactivate_subscription(sub, reason="period_end_reached"):
            count += 1

    logger.info("Celery deactivated %s subscriptions", count)
    return count