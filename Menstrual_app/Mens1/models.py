
# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta, date
import datetime
from django.utils import timezone


# Flow Intensity options
FLOW_INTENSITY_CHOICES = [
    ('light', 'Light'),
    ('medium', 'Medium'),
    ('heavy', 'Heavy')
]

# Profile model for user details, cycle prediction, and menstruation status
class UserProfile(models.Model):
    CYCLE_STATE_CHOICES = [
        ("regular", "Regular - Consistent cycle length"),
        ("slightly_irregular", "Slightly Irregular - Mild variations in cycle length"),
        ("highly_irregular", "Highly Irregular - Unpredictable cycle patterns"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birthdate = models.DateField(null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    next_menstruation_start = models.DateField(null=True, blank=True)
    menstruation_status = models.CharField(max_length=100, null=True, blank=True)
    safe_sex_zone = models.BooleanField(default=False)
    cycle_state = models.CharField(
        max_length=20, choices=CYCLE_STATE_CHOICES, default="regular"
    )

    def __str__(self):
        return f"Profile of {self.user.username}"

    def save(self, *args, **kwargs):
        last_cycles = MenstrualCycle.objects.filter(user=self.user).order_by('-menstruation_start')[:6]

        if last_cycles:
            cycle_lengths = [
                (cycle.menstruation_end - cycle.menstruation_start).days for cycle in last_cycles if cycle.menstruation_end
            ]

            if cycle_lengths:
                avg_cycle_length = sum(cycle_lengths) // len(cycle_lengths)  # Average cycle length
                std_dev = max(cycle_lengths) - min(cycle_lengths)  # Cycle variability

                # Classify cycle regularity
                if std_dev <= 2:
                    self.cycle_state = "regular"
                elif 3 <= std_dev <= 6:
                    self.cycle_state = "slightly_irregular"
                else:
                    self.cycle_state = "highly_irregular"

            else:
                self.cycle_state = "regular"  # Default when no valid data

            last_cycle = last_cycles[0]  # Most recent cycle

            # Predict next menstruation start using average cycle length
            predicted_start_date = last_cycle.menstruation_end + timedelta(days=avg_cycle_length)
            self.next_menstruation_start = predicted_start_date

            # Determine menstruation status
            if last_cycle.menstruation_start <= date.today() <= last_cycle.menstruation_end:
                self.menstruation_status = "Currently menstruating"
            else:
                self.menstruation_status = "Not menstruating"

            # Determine safe sex zone
            if last_cycle.ovulation_window_start <= date.today() <= last_cycle.ovulation_window_end:
                self.safe_sex_zone = False  # Risky during ovulation
            else:
                self.safe_sex_zone = True  # Safe sex zone

        super().save(*args, **kwargs)


class MenstrualCycle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    menstruation_start = models.DateField()
    menstruation_end = models.DateField(null=True, blank=True)
    menstruation_duration = models.PositiveIntegerField(blank=True, null=True)
    cycle_length = models.PositiveIntegerField(default=28)
    cycle_start = models.DateField(null=True, blank=True)
    cycle_end = models.DateField(null=True, blank=True)
    ovulation_date = models.DateField(null=True, blank=True)
    ovulation_window_start = models.DateField(null=True, blank=True)
    ovulation_window_end = models.DateField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.menstruation_start and not self.menstruation_end:
            self.menstruation_end = self.menstruation_start + timedelta(days=5)
            self.menstruation_duration = 5  # Default duration

        if self.menstruation_start and self.menstruation_end:
            self.menstruation_duration = (self.menstruation_end - self.menstruation_start).days

        self.cycle_start = self.menstruation_start  # Set cycle start to menstruation start date

        if self.menstruation_end:
            self.cycle_length = 28  # Or calculate from previous cycles if available
            self.cycle_end = self.menstruation_end + timedelta(days=self.cycle_length)
            self.ovulation_date = self.cycle_end - timedelta(days=14)
            self.ovulation_window_start = self.ovulation_date - timedelta(days=2)
            self.ovulation_window_end = self.ovulation_date + timedelta(days=2)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Cycle {self.id} for {self.user.username}"



# Flow Intensity log model to record daily flow intensity
class FlowIntensityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cycle = models.ForeignKey(MenstrualCycle, on_delete=models.CASCADE)
    date = models.DateField()  # Date of the record
    intensity = models.CharField(max_length=10, choices=FLOW_INTENSITY_CHOICES, default='Light')  # Intensity for the day

    def __str__(self):
        return f"Flow Intensity for {self.user.username} on {self.date}"

    @classmethod
    def clean_old_data(cls):
        """Method to clean data older than 3 months."""
        three_months_ago = timezone.now().date() - timedelta(days=90)
        cls.objects.filter(date__lt=three_months_ago).delete()


# Menstrual Cycle History model to store previous cycles
class MenstrualCycleHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    related_cycle = models.ForeignKey(
        MenstrualCycle, on_delete=models.SET_NULL, null=True, blank=True
    )
    start_date = models.DateField()
    end_date = models.DateField()
    cycle_length = models.IntegerField()
    flow_logs = models.ManyToManyField(FlowIntensityLog, blank=True)
    symptoms = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Automatically calculate cycle length
        if self.start_date and self.end_date:
            self.cycle_length = (self.end_date - self.start_date).days

        super().save(*args, **kwargs)

        # Keep only the last 12 cycles (delete the oldest one if necessary)
        MAX_HISTORY_ENTRIES = 12
        past_cycles = MenstrualCycleHistory.objects.filter(user=self.user).order_by("-start_date")
        if past_cycles.count() > MAX_HISTORY_ENTRIES:
            past_cycles.last().delete()  # Delete the oldest cycle

    def __str__(self):
        return f"Cycle ({self.start_date} - {self.end_date}) - {self.user.username}"


# Prediction model to store predictions based on menstrual cycle data
class Prediction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    menstrual_cycle = models.ForeignKey(MenstrualCycle, on_delete=models.CASCADE)
    ovulation_prediction_accuracy = models.PositiveIntegerField(default=50)  # Accuracy of the ovulation prediction
    next_period_prediction = models.DateField(null=True, blank=True)  # Predicted date of the next period
    ovulation_prediction = models.DateField(null=True, blank=True)  # Predicted ovulation date

    def save(self, *args, **kwargs):
        # Automatically calculate predictions based on the menstrual cycle data
        self.calculate_predictions()

        # Call the parent save method
        super().save(*args, **kwargs)

    def calculate_predictions(self):
        if self.menstrual_cycle:
            # Calculate the next period prediction (based on cycle length)
            cycle_end_date = self.menstrual_cycle.cycle_end
            self.next_period_prediction = cycle_end_date + timedelta(days=self.menstrual_cycle.cycle_length)

            # Calculate the ovulation prediction (around 14 days before the next period)
            self.ovulation_prediction = self.next_period_prediction - timedelta(days=14)

    def __str__(self):
        return f"Prediction for {self.user.username} based on Cycle {self.menstrual_cycle.id}"