from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from client.models import Activity


class VerifyEmailSerializer(serializers.Serializer):
    uid = serializers.CharField(help_text="User UID from email")
    token = serializers.CharField(help_text="Email verification token")


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()
    portal = serializers.ChoiceField(choices=["client", "admin", "consultant", "pm"], default="client", required=False)

    def validate_email(self, value):
        if not User.objects.filter(email=value):
            raise serializers.ValidationError("User with this email does not exist. ")
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, data):
        try:
            uid = force_str(urlsafe_base64_decode(data["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid user identifier")

        token_generator = PasswordResetTokenGenerator()
        if not token_generator.check_token(user, data["token"]):
            raise serializers.ValidationError("Invalid or expired token")
        data["user"] = user
        return data

    def save(self, **kwargs):
        user = self.validated_data["user"]
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        validate_password(data["new_password"])
        return data


class AccountSettingsDetailsSerializer(serializers.Serializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)

    country = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    zip_code = serializers.CharField(required=False, allow_blank=True)
    bio_text = serializers.CharField(required=False, allow_blank=True)
    bio_attachment = serializers.FileField(required=False, allow_null=True)
    timezone = serializers.CharField(required=False)
    profile_pic = serializers.ImageField(required=False)
    phone_number = serializers.CharField(required=False, allow_blank=True)


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = [
            "id",
            "activity_type",
            "title",
            "message",
            "metadata",
            "is_read",
            "created_at",
        ]
