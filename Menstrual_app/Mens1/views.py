from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import UserProfile, MenstrualCycle, FlowIntensityLog, Prediction, MenstrualCycleHistory
from .serializers import UserProfileSerializer, MenstrualCycleSerializer, FlowIntensityLogSerializer, PredictionSerializer, MenstrualCycleHistorySerializer
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
import jwt
from rest_framework.permissions import AllowAny
import datetime
from .serializers import UserRegistrationSerializer

from rest_framework import viewsets
from .models import UserProfile, MenstrualCycle, FlowIntensityLog, MenstrualCycleHistory, Prediction
from .serializers import (
    UserProfileSerializer,
    MenstrualCycleSerializer,
    FlowIntensityLogSerializer,
    MenstrualCycleHistorySerializer,
    PredictionSerializer
)
from rest_framework.permissions import IsAuthenticated


# ViewSet for UserProfile model
class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)


# ViewSet for MenstrualCycle model
class MenstrualCycleViewSet(viewsets.ModelViewSet):
    queryset = MenstrualCycle.objects.all()
    serializer_class = MenstrualCycleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MenstrualCycle.objects.filter(user=self.request.user)


# ViewSet for FlowIntensityLog model
class FlowIntensityLogViewSet(viewsets.ModelViewSet):
    queryset = FlowIntensityLog.objects.all()
    serializer_class = FlowIntensityLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return FlowIntensityLog.objects.filter(user=self.request.user)


# ViewSet for MenstrualCycleHistory model
class MenstrualCycleHistoryViewSet(viewsets.ModelViewSet):
    queryset = MenstrualCycleHistory.objects.all()
    serializer_class = MenstrualCycleHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return MenstrualCycleHistory.objects.filter(user=self.request.user)


# ViewSet for Prediction model
class PredictionViewSet(viewsets.ModelViewSet):
    queryset = Prediction.objects.all()
    serializer_class = PredictionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Prediction.objects.filter(user=self.request.user)

class RegisterUserView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate email confirmation token
            token = jwt.encode(
                {"user_id": user.id, "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)},
                settings.SECRET_KEY,
                algorithm="HS256"
            )

            # Email confirmation link
            verification_link = f"http://127.0.0.1:8000/api/verify-email/{token}/"

            # Send email
            send_mail(
                "Email Verification",
                f"Click the link to verify your account: {verification_link}",
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )

            return Response({"message": "User created. Check email for verification link."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user = User.objects.get(id=payload["user_id"])

            if user.is_active:
                return Response({"message": "User already verified."}, status=status.HTTP_200_OK)

            user.is_active = True  # ✅ Activate user
            user.save()
            return Response({"message": "Email verified successfully!"}, status=status.HTTP_200_OK)

        except jwt.ExpiredSignatureError:
            return Response({"error": "Verification link expired."}, status=status.HTTP_400_BAD_REQUEST)
        except jwt.DecodeError:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)