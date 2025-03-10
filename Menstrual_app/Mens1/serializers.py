from datetime import timedelta
from rest_framework import serializers
from .models import MenstrualCycle, MenstrualCycleHistory, FlowIntensityLog, Prediction, UserProfile
from django.contrib.auth.models import User

class UserProfileSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(slug_field='username', queryset=User.objects.all())
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'birthdate', 'bio', 'next_menstruation_start',
            'menstruation_status', 'safe_sex_zone', 'cycle_state'
        ]
        
    def validate_user(self, value):
        if not User.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("User does not exist.")
        return value

    def update(self, instance, validated_data):
        # Updating the UserProfile instance if necessary.
        instance.user = validated_data.get('user', instance.user)
        instance.birthdate = validated_data.get('birthdate', instance.birthdate)
        instance.bio = validated_data.get('bio', instance.bio)
        instance.next_menstruation_start = validated_data.get('next_menstruation_start', instance.next_menstruation_start)
        instance.menstruation_status = validated_data.get('menstruation_status', instance.menstruation_status)
        instance.safe_sex_zone = validated_data.get('safe_sex_zone', instance.safe_sex_zone)
        instance.cycle_state = validated_data.get('cycle_state', instance.cycle_state)

        instance.save()
        return instance
    

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)  # Ensures password is not returned in the response

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        user.is_active = False
        user.save()
        return user
    

class MenstrualCycleSerializer(serializers.ModelSerializer):
    ovulation_date = serializers.DateField(read_only=True)
    next_period_prediction = serializers.DateField(read_only=True)
    cycle_length = serializers.IntegerField(read_only=True)

    class Meta:
        model = MenstrualCycle
        fields = ['id', 'user', 'menstruation_start', 'menstruation_end', 'cycle_length', 'ovulation_date', 'next_period_prediction']

    def create(self, validated_data):
        menstruation_start = validated_data.get('menstruation_start')
        menstruation_end = validated_data.get('menstruation_end')

        if menstruation_start and menstruation_end:
            cycle_length = (menstruation_end - menstruation_start).days
        else:
            cycle_length = 28  # Default cycle length

        # Predict ovulation date (typically 14 days before the next period)
        ovulation_date = menstruation_start + timedelta(days=(cycle_length - 14)) if menstruation_start else None
        next_period_prediction = menstruation_end + timedelta(days=cycle_length) if menstruation_end else None

        validated_data['cycle_length'] = cycle_length
        validated_data['ovulation_date'] = ovulation_date

        menstrual_cycle = super().create(validated_data)

        # Update `next_period_prediction` after creation
        menstrual_cycle.next_period_prediction = next_period_prediction
        menstrual_cycle.save()

        return menstrual_cycle
# MenstrualCycleHistory Serializer
class FlowIntensityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowIntensityLog
        fields = ['id', 'cycle', 'date', 'intensity']

class MenstrualCycleHistorySerializer(serializers.ModelSerializer):
    flow_logs = FlowIntensityLogSerializer(many=True, read_only=True)
    avg_flow_intensity = serializers.FloatField(read_only=True)

    class Meta:
        model = MenstrualCycleHistory
        fields = ['id', 'user', 'related_cycle', 'menstruation_start', 'menstruation_end', 'cycle_length', 'flow_logs', 'symptoms', 'avg_flow_intensity']

    def create(self, validated_data):
        flow_logs = validated_data.get('flow_logs', [])
        avg_flow_intensity = 0
        if flow_logs:
            avg_flow_intensity = sum([log.intensity for log in flow_logs]) / len(flow_logs)

        validated_data['avg_flow_intensity'] = avg_flow_intensity
        return super().create(validated_data)

# FlowIntensityLog Serializer
class FlowIntensityLogSerializer(serializers.ModelSerializer):
    cycle_duration = serializers.IntegerField(read_only=True)

    class Meta:
        model = FlowIntensityLog
        fields = ['id', 'cycle', 'date', 'intensity', 'cycle_duration']

    def create(self, validated_data):
        cycle = validated_data.get('cycle')
        if cycle:
            cycle_duration = (cycle.menstruation_end - cycle.menstruation_start).days
            validated_data['cycle_duration'] = cycle_duration

        return super().create(validated_data)

# Prediction Serializer
class PredictionSerializer(serializers.ModelSerializer):
    ovulation_prediction = serializers.DateField(read_only=True)
    next_period_prediction = serializers.DateField(read_only=True)
    ovulation_prediction_accuracy = serializers.FloatField(read_only=True)

    class Meta:
        model = Prediction
        fields = ['id', 'user', 'menstrual_cycle', 'ovulation_prediction_accuracy', 'next_period_prediction', 'ovulation_prediction']

    def create(self, validated_data):
        cycle = validated_data.get('menstrual_cycle')
        # Compute Ovulation Prediction
        ovulation_date = cycle.ovulation_date
        next_period_date = cycle.next_period_prediction

        # Adjusting prediction accuracy based on cycle regularity
        accuracy = 0.95  # Default for regular cycles
        if cycle.cycle_length > 32 or cycle.cycle_length < 22:  # Example for irregular cycles
            accuracy = 0.8  # Decreased accuracy for irregular cycles

        validated_data['ovulation_prediction'] = ovulation_date
        validated_data['next_period_prediction'] = next_period_date
        validated_data['ovulation_prediction_accuracy'] = accuracy

        return super().create(validated_data)